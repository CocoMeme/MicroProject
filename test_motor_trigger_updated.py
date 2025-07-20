#!/usr/bin/env python3
"""
Test script for updated motor status trigger
"""

import paho.mqtt.client as mqtt
import time

def test_motor_status_trigger():
    """Test the updated motor status message trigger"""
    
    broker_host = "localhost"
    broker_port = 1883
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    
    try:
        # Connect to broker
        print("🔌 Connecting to MQTT broker...")
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        print("✅ Connected to MQTT broker")
        print()
        
        print("📋 Testing Updated Motor Status Trigger")
        print("=" * 50)
        
        # Test the new message format
        test_message = "📍 Object detected! Motor B paused"
        print(f"📤 Sending motor status: {test_message}")
        print(f"📡 Topic: esp32/motor/status")
        
        result = client.publish("esp32/motor/status", test_message)
        if result.rc == 0:
            print("✅ Motor status message sent successfully")
        else:
            print("❌ Failed to send motor status message")
        
        print()
        print("🔍 Expected server behavior:")
        print("  1. ✅ Detect '📍 Object detected! Motor B paused' message")
        print("  2. 📤 Immediately send 'start' to esp32/loadcell/request")
        print("  3. 📡 Emit WebSocket workflow progress events")
        print("  4. 📝 Log the loadcell request in server logs")
        print()
        
        print("⏳ Waiting 5 seconds to observe server response...")
        time.sleep(5)
        
        print()
        print("🎉 Test completed!")
        print("Check your server logs to verify:")
        print("  - '🚛 STEP 2 - MOTOR STATUS: Object detected, motor paused'")
        print("  - '✅ STEP 3 TRIGGER: Sent loadcell request'")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    finally:
        client.loop_stop()
        client.disconnect()
        print("🔌 Disconnected from MQTT broker")

def test_variations():
    """Test different message variations to ensure robustness"""
    
    broker_host = "localhost" 
    broker_port = 1883
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    
    try:
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        print("\n📋 Testing Message Variations")
        print("=" * 40)
        
        # Test messages that should trigger
        trigger_messages = [
            "📍 Object detected! Motor B paused",
            "📍 Object detected! Motor B paused for 2 seconds",
            "Status: 📍 Object detected! Motor B paused - waiting",
        ]
        
        print("✅ Messages that SHOULD trigger loadcell request:")
        for i, msg in enumerate(trigger_messages, 1):
            print(f"  {i}. {msg}")
            client.publish("esp32/motor/status", msg)
            time.sleep(2)
        
        print()
        
        # Test messages that should NOT trigger
        non_trigger_messages = [
            "Motor B running normally",
            "Object not detected",
            "Motor A paused",
            "System status: OK"
        ]
        
        print("❌ Messages that should NOT trigger loadcell request:")
        for i, msg in enumerate(non_trigger_messages, 1):
            print(f"  {i}. {msg}")
            client.publish("esp32/motor/status", msg)
            time.sleep(1)
        
        print()
        print("🔍 Check server logs to verify only the first set triggered loadcell requests")
        
    except Exception as e:
        print(f"❌ Error during variation test: {e}")
    
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    print("🚀 Motor Status Trigger Test")
    print("=" * 60)
    
    test_motor_status_trigger()
    test_variations()
    
    print("\n📋 Summary:")
    print("The server should now respond to '📍 Object detected! Motor B paused'")
    print("by immediately sending a loadcell start request to ESP32.")
    print("No 3-second delay - instant response!")
