#!/usr/bin/env python3
"""
Test script to diagnose motor stop request issues
"""

import requests
import json
import time
import paho.mqtt.client as mqtt

def test_motor_endpoints():
    """Test both start and stop motor endpoints"""
    
    base_url = "http://localhost:5000"  # Adjust if server runs on different port
    
    print("🔧 Testing Motor Control Endpoints")
    print("=" * 50)
    
    # Test 1: Check server connectivity
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Server connectivity: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ Server not reachable: {e}")
        return
    
    # Test 2: Test start motor
    print("\n📋 TEST 1: Start Motor")
    try:
        response = requests.post(f"{base_url}/api/start-motor", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Start motor request successful")
        else:
            print(f"❌ Start motor failed: {response.json()}")
            
    except requests.RequestException as e:
        print(f"❌ Start motor request failed: {e}")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response: {response.text}")
    
    # Wait a moment
    time.sleep(2)
    
    # Test 3: Test stop motor
    print("\n📋 TEST 2: Stop Motor")
    try:
        response = requests.post(f"{base_url}/api/stop-motor", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Stop motor request successful")
        else:
            print(f"❌ Stop motor failed: {response.json()}")
            
    except requests.RequestException as e:
        print(f"❌ Stop motor request failed: {e}")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response: {response.text}")

def test_mqtt_connection():
    """Test MQTT connection and motor topics"""
    
    print("\n🔌 Testing MQTT Connection")
    print("=" * 50)
    
    broker_host = "localhost"
    broker_port = 1883
    
    received_messages = []
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT broker")
            # Subscribe to motor topics
            client.subscribe("esp32/motor/request")
            client.subscribe("esp32/motor/status")
            print("📡 Subscribed to motor topics")
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    def on_message(client, userdata, msg):
        topic = msg.topic
        message = msg.payload.decode('utf-8')
        timestamp = time.strftime('%H:%M:%S')
        
        print(f"📨 [{timestamp}] {topic} > {message}")
        received_messages.append((topic, message, timestamp))
    
    def on_disconnect(client, userdata, rc):
        print("🔌 Disconnected from MQTT broker")
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect and start listening
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        print("⏳ Listening for motor MQTT messages for 10 seconds...")
        print("   Try sending start/stop motor requests now...")
        
        # Listen for 10 seconds
        time.sleep(10)
        
        client.loop_stop()
        client.disconnect()
        
        print(f"\n📊 Received {len(received_messages)} MQTT messages:")
        for topic, message, timestamp in received_messages:
            print(f"  [{timestamp}] {topic} > {message}")
            
    except Exception as e:
        print(f"❌ MQTT test failed: {e}")

def test_direct_mqtt_commands():
    """Send direct MQTT commands to test ESP32 response"""
    
    print("\n📤 Testing Direct MQTT Commands")
    print("=" * 50)
    
    broker_host = "localhost"
    broker_port = 1883
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    
    try:
        # Connect to broker
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        print("🔌 Connected to MQTT broker")
        
        # Test start command
        print("\n📤 Sending direct start command")
        result = client.publish("esp32/motor/request", "start")
        if result.rc == 0:
            print("✅ Start command sent successfully")
        else:
            print(f"❌ Failed to send start command: {result.rc}")
        
        time.sleep(3)
        
        # Test stop command
        print("\n📤 Sending direct stop command")
        result = client.publish("esp32/motor/request", "stop")
        if result.rc == 0:
            print("✅ Stop command sent successfully")
        else:
            print(f"❌ Failed to send stop command: {result.rc}")
        
        time.sleep(2)
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Direct MQTT test failed: {e}")

if __name__ == "__main__":
    print("🚀 Motor Stop Request Diagnostic Tool")
    print("=" * 60)
    
    # Run tests
    test_motor_endpoints()
    test_mqtt_connection()
    test_direct_mqtt_commands()
    
    print("\n🏁 Diagnostic complete!")
    print("\nIf the API endpoints work but MQTT messages aren't received:")
    print("1. Check if MQTT broker is running")
    print("2. Verify ESP32 is connected to MQTT broker")
    print("3. Check ESP32 code is subscribed to 'esp32/motor/request'")
    print("4. Verify ESP32 responds to 'stop' command correctly")
