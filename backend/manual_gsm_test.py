#!/usr/bin/env python3
"""
Manual GSM Test Command
This script sends a direct esp32/gsm/request > start command to test the GSM module.
"""

import paho.mqtt.client as mqtt
import time
import sys

# MQTT Configuration
MQTT_BROKER = "10.195.139.227"  # Your Raspberry Pi IP
MQTT_PORT = 1883
MQTT_CLIENT_ID = "Manual_GSM_Tester"

# Test phone number - UPDATE THIS WITH YOUR NUMBER
TEST_PHONE_NUMBER = "+639612903652"  # Change this to your actual number

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
        # Subscribe to status updates
        client.subscribe("esp32/gsm/status")
        print("📡 Subscribed to esp32/gsm/status for confirmations")
    else:
        print(f"❌ Failed to connect. Return code: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode('utf-8')
    print(f"📨 Received: [{topic}] {message}")

def on_disconnect(client, userdata, rc):
    print("🔌 Disconnected from MQTT broker")

def send_gsm_request():
    print("=== Manual GSM Test Command ===")
    print(f"📱 Target Phone: {TEST_PHONE_NUMBER}")
    print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"🎯 Topic: esp32/gsm/request")
    print("-" * 50)
    
    # Create MQTT client
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        print("🔗 Connecting to MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Send the GSM request command
        command = f"start:{TEST_PHONE_NUMBER}"
        print(f"📤 Sending command: '{command}'")
        
        result = client.publish("esp32/gsm/request", command)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ GSM request command sent successfully!")
            print("⏳ Waiting for ESP32 response (15 seconds)...")
            
            # Wait for response
            time.sleep(15)
            
        else:
            print(f"❌ Failed to send command. Return code: {result.rc}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        print("🔌 Disconnecting...")
        client.loop_stop()
        client.disconnect()
        print("✅ Test completed")

if __name__ == "__main__":
    # Check if phone number needs to be updated
    if TEST_PHONE_NUMBER == "+639612903652":
        print("⚠️  Please update TEST_PHONE_NUMBER in the script with your actual phone number!")
        response = input("Continue with current number? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled. Please update the phone number in the script.")
            sys.exit(1)
    
    send_gsm_request()
