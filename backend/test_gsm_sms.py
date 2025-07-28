#!/usr/bin/env python3
"""
GSM SMS Test Script
This script tests the GSM SMS functionality by sending a test message via MQTT to the ESP32 GSM module.
"""

import json
import time
import paho.mqtt.client as mqtt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT Configuration (should match your Raspberry Pi settings)
MQTT_BROKER = "10.195.139.227"  # Your Raspberry Pi IP
MQTT_PORT = 1883
MQTT_CLIENT_ID = "GSM_SMS_Tester"

# Test phone number (replace with your actual phone number)
TEST_PHONE_NUMBER = "+639612903652"  # Philippine format: +63 + number without leading 0
TEST_MESSAGE = "Your Parcel is Being Delivered"

class GSMSMSTester:
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            self.connected = True
            # Subscribe to GSM status topic to get confirmation
            client.subscribe("esp32/gsm/status")
            logger.info("Subscribed to esp32/gsm/status for confirmation messages")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            message = msg.payload.decode('utf-8')
            logger.info(f"📨 Received message on topic '{topic}': {message}")
            
            if topic == "esp32/gsm/status":
                try:
                    status_data = json.loads(message)
                    if status_data.get("status") == "sent":
                        phone = status_data.get('phone', 'unknown')
                        original = status_data.get('original', 'N/A')
                        logger.info(f"✅ SMS successfully sent to {phone}")
                        logger.info(f"🔍 Original message: {original}")
                        logger.info(f"🔍 Phone in status: '{phone}' (length: {len(phone)})")
                        print(f"🎉 CONFIRMATION RECEIVED: SMS sent to {phone}")
                    elif status_data.get("status") == "error":
                        error_msg = status_data.get('message', 'Unknown error')
                        logger.error(f"❌ SMS sending failed: {error_msg}")
                        print(f"❌ ERROR RECEIVED: {error_msg}")
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON status message: {message}")
                    print(f"⚠️ Non-JSON status: {message}")
            else:
                logger.info(f"📡 Message from other topic '{topic}': {message}")
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            print(f"❌ Message processing error: {e}")
            
    def on_disconnect(self, client, userdata, rc):
        logger.info("Disconnected from MQTT broker")
        self.connected = False
        
    def connect_to_broker(self):
        try:
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
            if not self.connected:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
            
    def send_test_sms(self, phone_number, message):
        if not self.connected:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            logger.info(f"Sending SMS start command to ESP32")
            logger.info(f"Target Phone: {phone_number} (hardcoded in ESP32)")
            logger.info(f"Message: {message} (hardcoded in ESP32)")
            
            # Send "start:" command with phone number to ESP32
            # Format: "start:+639612903652"
            start_command = f"start:{phone_number}"
            logger.info(f"🔍 Sending command: '{start_command}' (length: {len(start_command)})")
            
            result = self.client.publish("esp32/gsm/send", start_command)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ SMS start command sent to ESP32 via MQTT")
                return True
            else:
                logger.error(f"❌ Failed to publish MQTT message. Return code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending test SMS: {e}")
            return False
            
    def test_mqtt_connectivity(self):
        """Test basic MQTT connectivity and message flow"""
        if not self.connected:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            logger.info("🔧 Testing MQTT connectivity...")
            
            # Send a test message to see if MQTT is working
            test_msg = "ping"
            result = self.client.publish("esp32/gsm/send", test_msg)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ MQTT publish successful")
                print("✅ MQTT connection is working")
                return True
            else:
                logger.error(f"❌ MQTT publish failed. Return code: {result.rc}")
                print(f"❌ MQTT publish failed. Return code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing MQTT connectivity: {e}")
            print(f"❌ MQTT connectivity test error: {e}")
            return False

    def test_gsm_request_start(self, phone_number):
        """Test the esp32/gsm/send > start: command specifically"""
        if not self.connected:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            logger.info("🧪 Testing esp32/gsm/send > start: command")
            logger.info(f"📱 Target Phone: {phone_number} (hardcoded in ESP32)")
            
            # Send the specific "start:" command with phone number to esp32/gsm/send topic
            # This matches exactly what server.py sends: "start:+639612903652"
            start_command = f"start:{phone_number}"
            
            logger.info(f"📡 Publishing to topic: esp32/gsm/send")
            logger.info(f"💬 Command: '{start_command}'")
            
            result = self.client.publish("esp32/gsm/send", start_command)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ esp32/gsm/send > start: command sent successfully!")
                return True
            else:
                logger.error(f"❌ Failed to publish command. Return code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing GSM request start: {e}")
            return False
            
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()

def main():
    print("=== GSM SMS Test Script ===")
    print(f"Target Phone: {TEST_PHONE_NUMBER}")
    print(f"Message: {TEST_MESSAGE}")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print("-" * 50)
    
    # Validate phone number
    if TEST_PHONE_NUMBER == "+639612903652":
        print("⚠️  WARNING: Please update TEST_PHONE_NUMBER with your actual phone number!")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled.")
            return
    
    # Ask user which test to run
    print("\n📋 Select test type:")
    print("1. Full SMS Test (send_test_sms)")
    print("2. GSM Send Start Test (esp32/gsm/send > start:)")
    print("3. Both tests")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    # Create tester instance
    tester = GSMSMSTester()
    
    try:
        # Connect to MQTT broker
        if not tester.connect_to_broker():
            print("❌ Failed to connect to MQTT broker. Please check:")
            print("  1. Raspberry Pi is running and reachable")
            print("  2. MQTT broker is running on Raspberry Pi")
            print("  3. Network connectivity")
            return
            
        print("✅ Connected to MQTT broker")
        
        # Test MQTT connectivity first
        print("\n🔧 Testing MQTT connectivity...")
        if not tester.test_mqtt_connectivity():
            print("❌ MQTT connectivity test failed. Check ESP32 connection.")
            return
        
        # Execute based on user choice
        if choice == "1":
            print("\n📱 Running Full SMS Test...")
            success = tester.send_test_sms(TEST_PHONE_NUMBER, TEST_MESSAGE)
            if success:
                print("✅ Full SMS test request sent!")
                print("📋 Waiting for confirmation from ESP32...")
                print("   (Watch for 🎉 CONFIRMATION RECEIVED message above)")
                print("   Press Ctrl+C to stop waiting")
                
                # Wait with countdown
                for i in range(30, 0, -1):
                    print(f"   ⏰ Waiting... {i} seconds remaining", end='\r')
                    time.sleep(1)
                print("\n⏱️ Wait time completed")
            else:
                print("❌ Failed to send full SMS test")
                
        elif choice == "2":
            print("\n🧪 Running GSM Request Start Test...")
            success = tester.test_gsm_request_start(TEST_PHONE_NUMBER)
            if success:
                print("✅ GSM Request Start command sent!")
                print("📋 Waiting for confirmation from ESP32 (30 seconds)...")
                time.sleep(30)
            else:
                print("❌ Failed to send GSM Request Start command")
                
        elif choice == "3":
            print("\n📱 Running Both Tests...")
            print("\n1️⃣ First: Full SMS Test")
            success1 = tester.send_test_sms(TEST_PHONE_NUMBER, TEST_MESSAGE)
            
            print("\n2️⃣ Second: GSM Request Start Test")
            success2 = tester.test_gsm_request_start(TEST_PHONE_NUMBER)
            
            if success1 and success2:
                print("✅ Both tests sent successfully!")
                print("📋 Waiting for confirmations from ESP32 (30 seconds)...")
                time.sleep(30)
            else:
                print("❌ One or both tests failed")
                
        else:
            print("❌ Invalid choice. Please run again and select 1, 2, or 3.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        
    finally:
        print("\n🔌 Disconnecting...")
        tester.disconnect()
        print("✅ Test completed")

if __name__ == "__main__":
    main()
