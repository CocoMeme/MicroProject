// === FIXED ESP32 CODE - SEPARATE PROCESSES + DUAL STEPPER SYSTEM ===
#include <WiFi.h>
#include <PubSubClient.h>
#include <Stepper.h>
#include <ESP32Servo.h>

// === WiFi & MQTT Configuration ===
const char* ssid = "ESP32";
const char* password = "newpass1";
const char* mqtt_server = "10.194.125.227";

WiFiClient espClient;
PubSubClient client(espClient);

// === Stepper 1 (Grabber System) ===
const int stepsPerRevolution1 = 2048;
const int IN1_1 = 18;
const int IN2_1 = 19;
const int IN3_1 = 21;
const int IN4_1 = 22;
Stepper stepper1(stepsPerRevolution1, IN1_1, IN3_1, IN2_1, IN4_1);

// === Stepper 2 (MQTT + Serial Controlled) ===
const int stepsPerRevolution2 = 2048;
const int IN1_2 = 5;
const int IN2_2 = 17;
const int IN3_2 = 16;
const int IN4_2 = 33;
Stepper stepper2(stepsPerRevolution2, IN1_2, IN3_2, IN2_2, IN4_2);
volatile bool stopFlag = false;

// === Servo Pins ===
const int servoRightPin = 13;
const int servoLeftPin = 32;
const int servoLifterPin = 23;
Servo servoRight, servoLeft, servoLifter;

// === Lifter Angles ===
const int startPos = 0;
const int endPos = 45;

bool system_active = false;

// === Sizing Pins ===
Servo myServo;
const int servoPin = 4;
const int trigPin1 = 12;
const int echoPin1 = 14;
const int trigPin2 = 27;
const int echoPin2 = 26;
const int trigPin3 = 25;
const int echoPin3 = 34; // ⚠ Replace with 33 if you see boot looping

long duration;
float boxWidth = 0.0;
float boxLength = 0.0;
float boxHeight = 0.0;
bool measure_active = false;

// === MQTT Topics ===
const char* stepperTopic = "esp32/stepper/request";
const char* statusTopic = "esp32/stepper/status";

// === Common MQTT Publish Function ===
void safePublish(const char* topic, const char* message) {
  if (client.connected()) {
    client.publish(topic, message);
    delay(10);
  }
}

// === Grabber Functions ===
void servograb(int processNumber) {
  servoRight.write(118);
  servoLeft.write(28);
  String topic = "esp32/parcel" + String(processNumber) + "/status";
  safePublish(topic.c_str(), "🤖 Grabbed parcel");
}

void servorelease(int processNumber) {
  servoRight.write(103);
  servoLeft.write(43);
  String topic = "esp32/parcel" + String(processNumber) + "/status";
  safePublish(topic.c_str(), "👐 Released parcel");
}

void lifterup(int processNumber) {
  for (int pos = startPos; pos <= endPos; pos++) {
    servoLifter.write(pos);
    delay(15);
  }
  String topic = "esp32/parcel" + String(processNumber) + "/status";
  safePublish(topic.c_str(), "⬆️ Lifter up");
}

void lifterdown(int processNumber) {
  for (int pos = endPos; pos >= startPos; pos--) {
    servoLifter.write(pos);
    delay(15);
  }
  String topic = "esp32/parcel" + String(processNumber) + "/status";
  safePublish(topic.c_str(), "⬇️ Lifter down");
}

void weightlifter(int processNumber) {
  for (int pos = 0; pos <= 90; pos++) {
    servoLifter.write(pos);
    delay(15);
  }
  String topic = "esp32/parcel" + String(processNumber) + "/status";
  safePublish(topic.c_str(), "⚖️ Lifted to weight check height");
}

void processParcel1() {
  Serial.println("[SYSTEM] Starting parcel process 1");
  safePublish("esp32/parcel1/status", "🚚 Parcel process 1 started");

  delay(2000);
  lifterdown(1);
  delay(2000);
  servograb(1);
  delay(1500);
  lifterup(1);
  delay(2000);

  stepper1.step(-stepsPerRevolution1 / 4); Serial.println("a1");

  delay(1500);
  safePublish("esp32/parcel1/status", "➡️ Moved to size checker");

  lifterdown(1);
  delay(2000);
  servorelease(1);
  delay(2000);

  weightlifter(1);
  safePublish("esp32/parcel1/status", "✅ Parcel process 1 complete");
  Serial.println("[SYSTEM] Parcel process 1 complete");
}

void processParcel2() {
  Serial.println("[SYSTEM] Starting parcel process 2");
  safePublish("esp32/parcel2/status", "📦 Parcel process 2 started");

  delay(2000);
  lifterdown(2);
  delay(2000);
  servograb(2);
  delay(1500);
  lifterup(2);
  delay(2000);

  stepper1.step(-stepsPerRevolution1 / 4); Serial.println("a1");
  delay(1500);
  safePublish("esp32/parcel2/status", "➡️ Moved to conveyor 2");

  lifterdown(2);
  delay(2000);
  servorelease(2);
  delay(1500);
  lifterup(2);
  delay(2000);

  stepper1.step(stepsPerRevolution1 / 2); Serial.println("b1");

  delay(1500);
  safePublish("esp32/parcel2/status", "↩️ Returned to conveyor belt 1");
  safePublish("esp32/parcel2/status", "✅ Parcel process 2 complete");
  Serial.println("[SYSTEM] Parcel process 2 complete");
}

// === Sizing Functions ===
float readDistanceCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

float cmToInch(float cm) {
  return cm / 2.54;
}

String classifyBox(float width, float length, float height) {
  Serial.println("==== FINAL DIMENSIONS ====");
  Serial.print("Width: "); Serial.print(width); Serial.println(" in");
  Serial.print("Length: "); Serial.print(length); Serial.println(" in");
  Serial.print("Height: "); Serial.print(height); Serial.println(" in");

  if (length >= 4.5)
    return "📦 Large";
  else if (length >= 3.4)
    return "📦 Medium";
  else
    return "📦 Small";
}

void classifyAndMeasureBox() {
  Serial.println("📏 Starting box measurement...");
  safePublish("esp32/box/status", "📏 Measuring box dimensions...");
  
  Serial.println("Holding at 0° (5 deg)...");
  delay(4000);

  float d1_cm = readDistanceCM(trigPin1, echoPin1); // Top
  float d2_cm = readDistanceCM(trigPin2, echoPin2); // Front Left
  float d3_cm = readDistanceCM(trigPin3, echoPin3); // Front Right

  float d1_in = cmToInch(d1_cm);
  float d2_in = cmToInch(d2_cm);
  float d3_in = cmToInch(d3_cm);

  boxHeight = 9.2 - d1_in;
  boxWidth = 10.5 - (d2_in + d3_in);

  delay(1500);
  Serial.println("Rotating to 105°...");
  safePublish("esp32/box/status", "🔄 Rotating sensor to measure length...");
  
  for (int pos = 5; pos <= 105; pos++) {
    myServo.write(pos);
    delay(20);
  }

  delay(4000);

  float d2b_cm = readDistanceCM(trigPin2, echoPin2);
  float d3b_cm = readDistanceCM(trigPin3, echoPin3);
  float d2b_in = cmToInch(d2b_cm);
  float d3b_in = cmToInch(d3b_cm);

  boxLength = 10.5 - (d2b_in + d3b_in);

  delay(1000);

  String result = classifyBox(boxWidth, boxLength, boxHeight);
  Serial.println(result);
  Serial.println("==========================");

  // Create detailed message
  String message = "W: " + String(boxWidth, 2) + " in, " +
                   "L: " + String(boxLength, 2) + " in, " +
                   "H: " + String(boxHeight, 2) + " in → " + result;
  
  // Publish to BOTH topics to ensure compatibility
  safePublish("esp32/box/result", message.c_str());
  safePublish("esp32/box/status", message.c_str());
  
  // Also publish a completion status
  safePublish("esp32/box/status", "✅ Box measurement complete");
  
  Serial.println("📡 Published measurement results to MQTT");

  delay(2000);

  Serial.println("Returning to 5°...");
  safePublish("esp32/box/status", "↩️ Returning sensor to home position...");
  
  for (int pos = 105; pos >= 5; pos--) {
    myServo.write(pos);
    delay(20);
  }

  safePublish("esp32/box/status", "🏠 Sensor returned to home position");
  delay(3000);
}

// === MQTT Callback ===
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  msg.trim(); msg.toLowerCase();

  String topicStr = String(topic);
  Serial.println("=== MQTT MESSAGE RECEIVED ===");
  Serial.println("Topic: " + topicStr);
  Serial.println("Message: " + msg);
  Serial.println("=============================");

  // Stepper2 MQTT
  if (topicStr == stepperTopic) {
    if (msg == "stop") {
      stopFlag = true;
      safePublish(statusTopic, "Stepper2: Stop flag set");
      return;
    }
    stopFlag = false;
    if (msg == "small") {
      stepper2.step(stepsPerRevolution2 / 4); Serial.println("a2");
    } else if (msg == "smallback") {
      stepper2.step(-stepsPerRevolution2 / 4); Serial.println("b2");
    } else if (msg == "large") {
      stepper2.step(-stepsPerRevolution2 / 4); Serial.println("c2");
    } else if (msg == "largeback") {
      stepper2.step(stepsPerRevolution2 / 4); Serial.println("d2");
    } else {
      safePublish(statusTopic, "Stepper2: Invalid command");
    }
  }

  // Grabber & Box Process
  if (topicStr == "esp32/grabber1/request") {
    if (msg == "start") { system_active = true; processParcel1(); system_active = false; }
  }
  else if (topicStr == "esp32/grabber2/request") {
    if (msg == "start") { system_active = true; processParcel2(); system_active = false; }
  }
  else if (topicStr == "esp32/box/request") {
    if (msg == "start") measure_active = true;
  }
}

// === MQTT & WiFi ===
void setup_wifi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries++ < 20) {
    delay(500); Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("✅ WiFi connected");
  } else {
    Serial.println("❌ Failed to connect");
    ESP.restart();
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    
    // Create unique client ID using MAC address
    String clientId = "ESP32_PART2_" + WiFi.macAddress();
    clientId.replace(":", ""); // Remove colons from MAC address
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      Serial.println("Client ID: " + clientId);
      client.subscribe("esp32/grabber1/request");
      client.subscribe("esp32/grabber2/request");
      client.subscribe("esp32/box/request");
      client.subscribe(stepperTopic);
    } else {
      Serial.print("Failed, rc="); Serial.print(client.state()); Serial.println(" retrying...");
      delay(5000);
    }
  }
}

void manualStepperControl() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();  // Remove spaces, \n, \r

    if (input.length() != 2) {
      Serial.println("[ERROR] Invalid command format. Use a–h followed by 1 or 2 (e.g., a1, f2)");
      return;
    }

    char cmd = input.charAt(0);
    char motor = input.charAt(1);

    int degrees = 0;
    switch (cmd) {
      case 'a': degrees = 90; break;
      case 'b': degrees = 180; break;
      case 'c': degrees = 270; break;
      case 'd': degrees = 360; break;
      case 'e': degrees = -90; break;
      case 'f': degrees = -180; break;
      case 'g': degrees = -270; break;
      case 'h': degrees = -360; break;
      default:
        Serial.println("[ERROR] Invalid command. Use a–h only.");
        return;
    }

    int steps1 = (degrees * stepsPerRevolution1) / 360;
    int steps2 = (degrees * stepsPerRevolution2) / 360;

    if (motor == '1') {
      stepper1.step(steps1);
      Serial.print("Stepper1 moved ");
    } else if (motor == '2') {
      stepper2.step(steps2);
      Serial.print("Stepper2 moved ");
    } else {
      Serial.println("[ERROR] Invalid motor. Use 1 or 2.");
      return;
    }

    Serial.print(degrees);
    Serial.println(" degrees.");
  }
}



// === SETUP & LOOP ===
void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Starting...");

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  stepper1.setSpeed(10);
  stepper2.setSpeed(10);

  servoRight.setPeriodHertz(50);
  servoLeft.setPeriodHertz(50);
  servoLifter.setPeriodHertz(50);
  myServo.setPeriodHertz(50);

  servoRight.attach(servoRightPin, 500, 2400);
  servoLeft.attach(servoLeftPin, 500, 2400);
  servoLifter.attach(servoLifterPin, 500, 2400);
  servoLifter.write(45);
  servorelease(0);

  myServo.attach(servoPin, 500, 2400);
  myServo.write(5);

  pinMode(trigPin1, OUTPUT); pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT); pinMode(echoPin2, INPUT);
  pinMode(trigPin3, OUTPUT); pinMode(echoPin3, INPUT);

  Serial.println("✅ Setup complete. Awaiting MQTT or Serial input.");
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  if (measure_active) {
    classifyAndMeasureBox();
    measure_active = false;
  }

  manualStepperControl();
}