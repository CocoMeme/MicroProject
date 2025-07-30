#include <WiFi.h>
#include <PubSubClient.h>
#include <HardwareSerial.h>
#include "HX711.h"

// === WiFi & MQTT Configuration ===
const char* ssid = "ESP32";
const char* password = "newpass1";
const char* mqtt_server = "10.195.139.227";

WiFiClient espClient;
PubSubClient client(espClient);

// === GSM UART Setup ===
HardwareSerial gsmSerial(1);  // UART1: RX=16, TX=17

// === Motor A ===
const int in1 = 4;
const int in2 = 5;
const int ena = 2;

// === Motor B ===
const int in3 = 26;
const int in4 = 27;
const int enb = 15;

// === Linear Actuator ===
const int ACTUATOR_PIN = 25;  // Changed from 26 to avoid conflict with in3
bool actuatorActive = false;

// === IR Sensors ===
const int irSensorA = 35;
const int irSensorB = 34;

// === Proximity Sensor ===
const int PROX_SENSOR = 14;  // Proximity sensor pin
bool proximityActive = false;  // State flag for proximity sensor

// === Load Cell with Advanced Weight Processing ===
#define DOUT 22
#define SCK  23
HX711 scale;

// Advanced weight processing parameters
float calibration_factor = 500.95;
const float noise_threshold = 47.0;  // Ignore weights below this (in grams)

// Weight collection and analysis parameters
#define MAX_SAMPLES 200           // Maximum number of weight samples to collect
#define COLLECTION_TIME_MS 10000  // 10 seconds data collection
#define WEIGHT_TRIGGER_THRESHOLD 50.0  // Weight threshold to start collection (grams)
#define RANGE_BUCKET_SIZE 5.0     // Size of each weight range bucket for frequency analysis

float weight_samples[MAX_SAMPLES];
int sample_count = 0;
bool collecting_data = false;
unsigned long collection_start_time = 0;
bool loadCellActive = false;

// === State Flags ===
bool motorA_active = false;
bool motorB_active = false;

// === Linear Actuator Control Function ===
void handleLinearActuator(const char* action) {
  if (strcmp(action, "start") == 0 && !actuatorActive) {
    actuatorActive = true;
    // Push
    digitalWrite(ACTUATOR_PIN, HIGH);
    client.publish("esp32/actuator/status", "🔄 Actuator pushing");
    Serial.println("🔄 Actuator pushing");
    delay(2000);  // Wait for push
    
    // Auto-retract
    digitalWrite(ACTUATOR_PIN, LOW);
    client.publish("esp32/actuator/status", "✅ Actuator cycle complete");
    Serial.println("✅ Actuator cycle complete");
  }
  else if (strcmp(action, "stop") == 0) {
    digitalWrite(ACTUATOR_PIN, LOW);  // Ensure retracted
    actuatorActive = false;
    client.publish("esp32/actuator/status", "⏹️ Actuator stopped");
    Serial.println("⏹️ Actuator stopped");
  }
}

// === WiFi Setup ===
void setup_wifi() {
  Serial.print("Connecting to WiFi: ");
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500); Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected");
    Serial.print("IP: "); Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi failed. Restarting...");
    delay(2000); ESP.restart();
  }
}

// === GSM SMS Sending Function ===
void sendGSMMessage(String phoneNumber, String message) {
  Serial.println("[GSM] Sending message...");
  gsmSerial.println("AT+CMGF=1"); delay(500);
  gsmSerial.print("AT+CMGS=\""); gsmSerial.print(phoneNumber); gsmSerial.println("\"");
  delay(500);
  gsmSerial.println(message);
  delay(500);
  gsmSerial.write(26);  // CTRL+Z
  delay(1000);
  Serial.println("[GSM] Message sent successfully.");
}

// === Advanced Weight Processing Functions ===

// Function to sort array for statistical calculations
void quickSort(float arr[], int low, int high) {
  if (low < high) {
    int pi = partition(arr, low, high);
    quickSort(arr, low, pi - 1);
    quickSort(arr, pi + 1, high);
  }
}

int partition(float arr[], int low, int high) {
  float pivot = arr[high];
  int i = (low - 1);
  
  for (int j = low; j <= high - 1; j++) {
    if (arr[j] < pivot) {
      i++;
      float temp = arr[i];
      arr[i] = arr[j];
      arr[j] = temp;
    }
  }
  float temp = arr[i + 1];
  arr[i + 1] = arr[high];
  arr[high] = temp;
  return (i + 1);
}

// Remove outliers using IQR method
int removeOutliers(float samples[], int count) {
  if (count < 4) return count;  // Need at least 4 samples for IQR
  
  // Create a copy for sorting (preserve original order)
  float sorted_samples[MAX_SAMPLES];
  for (int i = 0; i < count; i++) {
    sorted_samples[i] = samples[i];
  }
  
  quickSort(sorted_samples, 0, count - 1);
  
  // Calculate Q1, Q3, and IQR
  int q1_index = count / 4;
  int q3_index = 3 * count / 4;
  float q1 = sorted_samples[q1_index];
  float q3 = sorted_samples[q3_index];
  float iqr = q3 - q1;
  
  float lower_bound = q1 - 1.5 * iqr;
  float upper_bound = q3 + 1.5 * iqr;
  
  // Remove outliers and negative values
  int clean_count = 0;
  for (int i = 0; i < count; i++) {
    if (samples[i] >= 0 && samples[i] >= lower_bound && samples[i] <= upper_bound) {
      samples[clean_count++] = samples[i];
    }
  }
  
  return clean_count;
}

// Find most frequent weight range
float findMostFrequentRange(float samples[], int count) {
  if (count == 0) return 0.0;
  
  // Find min and max to determine range
  float min_weight = samples[0];
  float max_weight = samples[0];
  
  for (int i = 1; i < count; i++) {
    if (samples[i] < min_weight) min_weight = samples[i];
    if (samples[i] > max_weight) max_weight = samples[i];
  }
  
  // Create buckets for frequency analysis
  int num_buckets = ((max_weight - min_weight) / RANGE_BUCKET_SIZE) + 1;
  if (num_buckets > 50) num_buckets = 50;  // Limit bucket count
  
  int bucket_counts[50] = {0};
  
  // Count samples in each bucket
  for (int i = 0; i < count; i++) {
    int bucket_index = (samples[i] - min_weight) / RANGE_BUCKET_SIZE;
    if (bucket_index >= 0 && bucket_index < num_buckets) {
      bucket_counts[bucket_index]++;
    }
  }
  
  // Find bucket with highest frequency
  int max_count = 0;
  int best_bucket = 0;
  
  for (int i = 0; i < num_buckets; i++) {
    if (bucket_counts[i] > max_count) {
      max_count = bucket_counts[i];
      best_bucket = i;
    }
  }
  
  // Return the center of the most frequent range
  return min_weight + (best_bucket * RANGE_BUCKET_SIZE) + (RANGE_BUCKET_SIZE / 2.0);
}

// Analyze collected weight data
void analyzeWeightData() {
  if (sample_count == 0) {
    return;
  }
  
  // Remove outliers
  int clean_count = removeOutliers(weight_samples, sample_count);
  
  if (clean_count == 0) {
    return;
  }
  
  // Find most frequent range
  float most_frequent = findMostFrequentRange(weight_samples, clean_count);
  
  // Send result via MQTT and Serial
  char payload[64];
  snprintf(payload, sizeof(payload), "📦 Final Weight: %.2f g", most_frequent);
  client.publish("esp32/loadcell/data", payload);
  
  Serial.print("Most frequent weight range: ");
  Serial.print(most_frequent, 2);
  Serial.println(" g");
  
  // Stop load cell data collection
  loadCellActive = false;
  collecting_data = false;
  sample_count = 0;
}

// === MQTT Callback ===
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  String topicStr = String(topic);

  // === Motor/Load Cell/Actuator Handling ===
  if (topicStr == "esp32/motor/request") {
    if (msg == "startA") {
      startMotorA(); motorA_active = true;
      Serial.println("▶️ Motor A started");
      client.publish("esp32/motor/status", "▶️ Motor A started");
    } else if (msg == "stopA") {
      stopMotorA(); motorA_active = false;
      Serial.println("⏹️ Motor A stopped");
      client.publish("esp32/motor/status", "⏹️ Motor A stopped");
    } else if (msg == "startB") {
      startMotorB(); motorB_active = true;
      Serial.println("▶️ Motor B started");
      client.publish("esp32/motor/status", "▶️ Motor B started");
    } else if (msg == "stopB") {
      stopMotorB(); motorB_active = false;
      Serial.println("⏹️ Motor B stopped");
      client.publish("esp32/motor/status", "⏹️ Motor B stopped");
    }
  } else if (topicStr == "esp32/actuator/request") {
    if (msg == "start") {
      handleLinearActuator("start");
    } else if (msg == "stop") {
      handleLinearActuator("stop");
    }
  } else if (topicStr == "esp32/proximity/request") {
    if (msg == "start") {
      proximityActive = true;
      Serial.println("👁️ Proximity sensor started");
      client.publish("esp32/proximity/status", "👁️ Proximity sensor started");
    } else if (msg == "stop") {
      proximityActive = false;
      Serial.println("⏹️ Proximity sensor stopped");
      client.publish("esp32/proximity/status", "⏹️ Proximity sensor stopped");
    }
  } else if (topicStr == "esp32/loadcell/request") {
    if (msg == "start") {
      loadCellActive = true;
      collecting_data = false;
      sample_count = 0;
      Serial.println("⚖️ Advanced load cell started");
      client.publish("esp32/loadcell/status", "⚖️ Advanced load cell started");
    }
  }

  // === GSM SMS Handler ===
  else if (topicStr == "esp32/gsm/send" && msg.startsWith("start:")) {
    String phoneNumber = msg.substring(6);
    String message = "Your Parcel is Being Delivered";
    if (phoneNumber.startsWith("09") && phoneNumber.length() == 11)
      phoneNumber = "+63" + phoneNumber.substring(1);

    sendGSMMessage(phoneNumber, message);

    String confirmMsg = "{\"status\":\"sent\",\"phone\":\"" + phoneNumber + "\",\"original\":\"" + msg + "\"}";
    client.publish("esp32/gsm/status", confirmMsg.c_str());
    Serial.println("[GSM] Confirmation sent: " + confirmMsg);
  }
}

// === MQTT Reconnect ===
void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32_Integrated")) {
      Serial.println("connected.");
      client.subscribe("esp32/motor/request");
      client.subscribe("esp32/loadcell/request");
      client.subscribe("esp32/gsm/send");
      client.subscribe("esp32/actuator/request");
      client.subscribe("esp32/proximity/request");
    } else {
      Serial.print("failed, rc="); Serial.print(client.state());
      Serial.println(". Retrying in 5 sec...");
      delay(5000);
    }
  }
}

// === Motor Control ===
void startMotorA() {
  pinMode(in1, OUTPUT); pinMode(in2, OUTPUT); pinMode(ena, OUTPUT);
  pinMode(irSensorA, INPUT);
  digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
  analogWrite(ena, 102);  // ~30% speed
}

void stopMotorA() {
  digitalWrite(in1, LOW); digitalWrite(in2, LOW);
  analogWrite(ena, 0);
}

void startMotorB() {
  pinMode(in3, OUTPUT); pinMode(in4, OUTPUT); pinMode(enb, OUTPUT);
  pinMode(irSensorB, INPUT);
  digitalWrite(in3, HIGH); digitalWrite(in4, LOW);
  analogWrite(enb, 102);
}

void stopMotorB() {
  digitalWrite(in3, LOW); digitalWrite(in4, LOW);
  analogWrite(enb, 0);
}

// === IR Logic ===
void handleIRSensorA() {
  if (!motorA_active) return;
  if (digitalRead(irSensorA) == LOW) {
    stopMotorA(); motorA_active = false;
    client.publish("esp32/motor/status", "⛔ Motor A stopped by IR A");
    Serial.println("⛔ Motor A stopped by IR A");
  }
}

void handleIRSensorB() {
  if (!motorB_active) return;
  if (digitalRead(irSensorB) == LOW) {
    stopMotorB();
    motorB_active = false;
    client.publish("esp32/motor/status", "⛔ Motor B stopped by IR B");
    Serial.println("⛔ Motor B stopped by IR B");
  }
}

// === Proximity Sensor Logic ===
void handleProximitySensor() {
  if (!proximityActive) return;  // Only check if sensor is active
  
  static bool lastState = false;  // Track last detection state
  bool currentState = digitalRead(PROX_SENSOR) == HIGH;  // Active HIGH for proximity detection
  
  if (currentState != lastState) {  // Only publish on state change
    if (currentState) {
      client.publish("esp32/proximity/data", "true");  // Send detection state via MQTT
      client.publish("esp32/proximity/status", "🔍 Metallic item detected!");
      Serial.println("🔍 Metallic item detected!");
    } else {
      client.publish("esp32/proximity/data", "false");  // Send detection state via MQTT
    }
    lastState = currentState;
    delay(50);  // Small debounce delay
  }
}


// === Advanced Load Cell Logic ===
void handleLoadCell() {
  if (!loadCellActive || !scale.is_ready()) return;

  float current_weight = scale.get_units(5);  // Quick reading for monitoring
  
  // Filter out small noise
  if (abs(current_weight) < noise_threshold) {
    current_weight = 0.0;
  }
  
  // Check if we should start data collection
  if (!collecting_data && current_weight > WEIGHT_TRIGGER_THRESHOLD) {
    collecting_data = true;
    collection_start_time = millis();
    sample_count = 0;
    Serial.println("🔍 Weight detected! Starting 10-second data collection...");
    client.publish("esp32/loadcell/status", "🔍 Weight detected! Collecting data...");
  }
  
  // Collect data during collection period
  if (collecting_data) {
    unsigned long elapsed = millis() - collection_start_time;
    
    if (elapsed < COLLECTION_TIME_MS && sample_count < MAX_SAMPLES) {
      // Collect sample if it's significant
      if (current_weight > 0) {  // Exclude negative values
        weight_samples[sample_count++] = current_weight;
      }
    } else {
      // Collection period finished
      collecting_data = false;
      analyzeWeightData();
    }
  }
}

// === Setup ===
void setup() {
  Serial.begin(115200);
  gsmSerial.begin(9600, SERIAL_8N1, 16, 17);
  setup_wifi();

  // Initialize Proximity Sensor
  pinMode(PROX_SENSOR, INPUT);

  // Initialize Linear Actuator
  pinMode(ACTUATOR_PIN, OUTPUT);
  digitalWrite(ACTUATOR_PIN, LOW);  // Ensure actuator is retracted initially

  // Initialize HX711 with advanced processing
  scale.begin(DOUT, SCK);
  scale.set_scale();
  delay(2000);  // Let it settle before taring
  scale.tare();  // Zero the scale
  delay(1000);   // Wait after taring
  scale.set_scale(calibration_factor);
  Serial.println("HX711 Ready & Tared with Advanced Processing");

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  delay(3000);
}

// === Loop ===
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  handleIRSensorA();
  handleIRSensorB();
  handleProximitySensor();
  handleLoadCell();

  delay(50);
}
