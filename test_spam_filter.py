#!/usr/bin/env python3
"""
Test script to verify MQTT spam filtering
"""

import paho.mqtt.client as mqtt
import time
import random

def test_spam_filtering():
    """Test the spam filtering by sending various loadcell values"""
    
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
        
        print("📋 Testing MQTT Spam Filtering")
        print("=" * 40)
        
        # Test 1: Send spam messages (should be filtered)
        print("1. Sending SPAM messages (should be filtered out):")
        spam_values = ["0.0", "0.01", "0.05", "0.1"]
        
        for value in spam_values:
            print(f"   Sending: {value}kg")
            client.publish("esp32/loadcell/data", value)
            time.sleep(0.5)
        
        print("   ↳ These should NOT appear in server logs/WebSocket")
        print()
        
        # Test 2: Send meaningful weight values (should be processed)
        print("2. Sending MEANINGFUL weight values (should be processed):")
        meaningful_values = ["0.5", "1.2", "2.8", "5.0"]
        
        for value in meaningful_values:
            print(f"   Sending: {value}kg")
            client.publish("esp32/loadcell/data", value)
            time.sleep(2)  # Longer delay to see processing
        
        print("   ↳ These SHOULD appear in server logs and trigger weight storage")
        print()
        
        # Test 3: Send similar values (should be filtered after first)
        print("3. Sending SIMILAR weight values (should filter duplicates):")
        similar_values = ["3.0", "3.01", "3.02", "3.03", "3.04"]  # Within 0.05kg threshold
        
        for value in similar_values:
            print(f"   Sending: {value}kg")
            client.publish("esp32/loadcell/data", value)
            time.sleep(1)
        
        print("   ↳ Only the FIRST should be processed, others filtered")
        print()
        
        # Test 4: Send significantly different value (should be processed)
        print("4. Sending SIGNIFICANTLY different value:")
        print("   Sending: 4.0kg (difference > 0.05kg)")
        client.publish("esp32/loadcell/data", "4.0")
        time.sleep(2)
        
        print("   ↳ This SHOULD be processed as it's significantly different")
        print()
        
        # Test 5: Test other topics (should work normally)
        print("5. Testing other topics (should work normally):")
        client.publish("esp32/motor/status", "📍 Object detected! Motor B paused for 3 seconds")
        time.sleep(1)
        client.publish("/box/results", "20,15,10")
        time.sleep(1)
        
        print("   ↳ Motor and box dimension messages should work normally")
        print()
        
        print("🎉 Test completed!")
        print()
        print("📊 Expected Results:")
        print("- Spam messages (0.0, 0.01, etc.) should be filtered")
        print("- Meaningful weights (0.5, 1.2, etc.) should be processed")
        print("- Similar weights should be filtered after first")
        print("- Significantly different weights should be processed")
        print("- Other topics should work normally")
        print()
        print("Check your server logs to verify filtering is working!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    finally:
        client.loop_stop()
        client.disconnect()
        print("🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    print("🚀 Starting MQTT Spam Filter Test")
    print("=" * 50)
    test_spam_filtering()
