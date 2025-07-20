#!/usr/bin/env python3
"""
Test script to simulate the motor status workflow
"""

import paho.mqtt.client as mqtt
import time
import json

def test_motor_workflow():
    """Test the motor status to loadcell workflow"""
    
    # MQTT configuration
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
        
        # Test 1: Send motor status message
        print("📋 TEST 1: Sending motor status message")
        print("Topic: esp32/motor/status")
        print("Message: 📍 Object detected! Motor B paused for 3 seconds")
        
        result = client.publish("esp32/motor/status", "📍 Object detected! Motor B paused for 3 seconds")
        if result.rc == 0:
            print("✅ Motor status message sent successfully")
        else:
            print("❌ Failed to send motor status message")
        
        print()
        print("⏳ The server should now:")
        print("  1. Receive the motor status message")
        print("  2. Wait 3 seconds")
        print("  3. Send 'start' to esp32/loadcell/request")
        print()
        print("🔍 Check the server logs for confirmation...")
        print()
        
        # Wait a bit to see the workflow
        print("⏳ Waiting 10 seconds to observe workflow...")
        time.sleep(10)
        
        # Test 2: Simulate weight response (optional)
        print("📋 TEST 2: Simulating loadcell weight response")
        print("Topic: /loadcell")
        print("Message: 2.5")
        
        result = client.publish("/loadcell", "2.5")
        if result.rc == 0:
            print("✅ Weight response sent successfully")
        else:
            print("❌ Failed to send weight response")
        
        print()
        time.sleep(2)
        
        # Test 3: Simulate dimensions response (optional)
        print("📋 TEST 3: Simulating box dimensions response")
        print("Topic: /box/results")
        print("Message: 20,15,10")
        
        result = client.publish("/box/results", "20,15,10")
        if result.rc == 0:
            print("✅ Dimensions response sent successfully")
        else:
            print("❌ Failed to send dimensions response")
        
        print()
        print("🎉 Workflow test completed!")
        print("Check the server logs and database to verify the workflow")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    finally:
        client.loop_stop()
        client.disconnect()
        print("🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    print("🚀 Starting Motor Workflow Test")
    print("=" * 50)
    test_motor_workflow()
