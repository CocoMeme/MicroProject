#!/usr/bin/env python3
"""
Comprehensive Motor Stop Request Debugger
"""

import requests
import json
import time
import paho.mqtt.client as mqtt
import threading
from datetime import datetime

class MotorDebugger:
    def __init__(self):
        self.server_url = "http://localhost:5000"
        self.mqtt_broker = "localhost"
        self.mqtt_port = 1883
        self.received_messages = []
        self.mqtt_client = None
        
    def test_server_connectivity(self):
        """Test if the server is reachable"""
        print("🔍 Testing Server Connectivity")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.server_url}/", timeout=5)
            print(f"✅ Server reachable: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Server status: {data.get('status', 'unknown')}")
                print(f"   MQTT status: {data.get('mqtt', {}).get('connected', 'unknown')}")
                return True
        except requests.RequestException as e:
            print(f"❌ Server not reachable: {e}")
            return False
    
    def test_motor_endpoints(self):
        """Test both start and stop motor endpoints"""
        print("\n🔍 Testing Motor Endpoints")
        print("-" * 40)
        
        # Test stop motor
        print("1. Testing STOP motor endpoint:")
        try:
            response = requests.post(
                f"{self.server_url}/api/stop-motor",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=4)}")
            
            if response.status_code == 200:
                print("   ✅ Stop motor API call successful")
            else:
                print(f"   ❌ Stop motor API call failed")
                
        except requests.RequestException as e:
            print(f"   ❌ Stop motor request error: {e}")
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response: {response.text}")
        
        print()
        
        # Test start motor for comparison
        print("2. Testing START motor endpoint:")
        try:
            response = requests.post(
                f"{self.server_url}/api/start-motor",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=4)}")
            
            if response.status_code == 200:
                print("   ✅ Start motor API call successful")
            else:
                print(f"   ❌ Start motor API call failed")
                
        except requests.RequestException as e:
            print(f"   ❌ Start motor request error: {e}")
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response: {response.text}")
    
    def setup_mqtt_listener(self):
        """Setup MQTT client to monitor messages"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("   ✅ Connected to MQTT broker")
                client.subscribe("esp32/motor/request")
                client.subscribe("esp32/motor/status")
                client.subscribe("esp32/#")  # Subscribe to all ESP32 topics
                print("   📡 Subscribed to ESP32 topics")
            else:
                print(f"   ❌ MQTT connection failed: {rc}")
        
        def on_message(client, userdata, msg):
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            topic = msg.topic
            message = msg.payload.decode('utf-8')
            
            self.received_messages.append({
                'timestamp': timestamp,
                'topic': topic,
                'message': message
            })
            
            print(f"   📨 [{timestamp}] {topic} > {message}")
        
        def on_disconnect(client, userdata, rc):
            print("   🔌 Disconnected from MQTT broker")
        
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.on_disconnect = on_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            return True
        except Exception as e:
            print(f"   ❌ MQTT connection error: {e}")
            return False
    
    def test_mqtt_monitoring(self):
        """Monitor MQTT messages while testing endpoints"""
        print("\n🔍 Testing MQTT Message Flow")
        print("-" * 40)
        
        if not self.setup_mqtt_listener():
            return
        
        # Start MQTT loop in background
        self.mqtt_client.loop_start()
        
        print("📡 MQTT listener started. Monitoring messages...")
        time.sleep(2)  # Let connection stabilize
        
        # Clear previous messages
        self.received_messages.clear()
        
        # Test stop motor while monitoring
        print("\n🛑 Sending STOP motor request while monitoring MQTT...")
        try:
            response = requests.post(f"{self.server_url}/api/stop-motor", timeout=5)
            print(f"   API Response: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"   API Error: {e}")
        
        # Wait for MQTT messages
        time.sleep(3)
        
        # Test start motor while monitoring
        print("\n🚀 Sending START motor request while monitoring MQTT...")
        try:
            response = requests.post(f"{self.server_url}/api/start-motor", timeout=5)
            print(f"   API Response: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"   API Error: {e}")
        
        # Wait for more MQTT messages
        time.sleep(3)
        
        # Stop MQTT monitoring
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        # Analyze results
        print(f"\n📊 MQTT Messages Analysis:")
        print(f"   Total messages received: {len(self.received_messages)}")
        
        motor_request_messages = [m for m in self.received_messages if m['topic'] == 'esp32/motor/request']
        print(f"   Motor request messages: {len(motor_request_messages)}")
        
        for msg in motor_request_messages:
            print(f"     [{msg['timestamp']}] {msg['topic']} > {msg['message']}")
    
    def test_direct_mqtt_publish(self):
        """Test direct MQTT publishing to verify broker functionality"""
        print("\n🔍 Testing Direct MQTT Publishing")
        print("-" * 40)
        
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        
        try:
            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            
            print("✅ Connected to MQTT broker for direct testing")
            
            # Test direct stop command
            print("📤 Sending direct STOP command...")
            result = client.publish("esp32/motor/request", "stop")
            if result.rc == 0:
                print("   ✅ Direct stop command sent successfully")
            else:
                print(f"   ❌ Direct stop command failed: {result.rc}")
            
            time.sleep(2)
            
            # Test direct start command
            print("📤 Sending direct START command...")
            result = client.publish("esp32/motor/request", "start")
            if result.rc == 0:
                print("   ✅ Direct start command sent successfully")
            else:
                print(f"   ❌ Direct start command failed: {result.rc}")
            
            time.sleep(2)
            
            client.loop_stop()
            client.disconnect()
            
        except Exception as e:
            print(f"❌ Direct MQTT test failed: {e}")
    
    def run_full_diagnosis(self):
        """Run complete diagnostic sequence"""
        print("🔧 MOTOR STOP REQUEST DIAGNOSTIC TOOL")
        print("=" * 60)
        print(f"Timestamp: {datetime.now()}")
        print()
        
        # Test 1: Server connectivity
        if not self.test_server_connectivity():
            print("\n❌ Cannot proceed - server is not reachable")
            return
        
        # Test 2: Motor endpoints
        self.test_motor_endpoints()
        
        # Test 3: MQTT monitoring
        self.test_mqtt_monitoring()
        
        # Test 4: Direct MQTT
        self.test_direct_mqtt_publish()
        
        print("\n🏁 DIAGNOSIS COMPLETE")
        print("=" * 60)
        
        # Summary and recommendations
        print("\n📋 TROUBLESHOOTING GUIDE:")
        print("1. If API calls return 503: MQTT broker is not connected")
        print("2. If API calls return 200 but no MQTT messages: Check MQTT broker")
        print("3. If MQTT messages sent but ESP32 doesn't respond: Check ESP32 code")
        print("4. If start works but stop doesn't: Check ESP32 stop command handling")
        print("5. Check server logs for detailed error messages")

if __name__ == "__main__":
    debugger = MotorDebugger()
    debugger.run_full_diagnosis()
