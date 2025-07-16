import paho.mqtt.client as mqtt
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker successfully!")
        client.subscribe("esp32/#")  # Subscribe to all ESP32-related topics
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    message = msg.payload.decode()
    print(f"📨 [{timestamp}] {msg.topic} > {message}")
    with open("mqtt_messages.log", "a") as f:
        f.write(f"[{timestamp}] {msg.topic} > {message}\n")

def on_disconnect(client, userdata, rc):
    print("🔌 Disconnected. Reconnecting..." if rc != 0 else "🔌 Disconnected gracefully.")

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

print("🚀 MQTT Listener Starting...")
client.connect("localhost", 1883, 60)
client.loop_forever()  # Blocking loop that listens forever
