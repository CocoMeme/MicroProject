# GSM SMS Test Guide

This guide explains how to test the GSM SMS functionality in your MicroProject system.

## Prerequisites

1. **ESP32 with GSM module** connected and programmed with the `gsmmodule` code
2. **Raspberry Pi** running `server.py` with MQTT broker
3. **Python environment** with required packages

## Installation

Install the required Python package:

```bash
pip install paho-mqtt
```

## Configuration

Before running the test, update the following in `test_gsm_sms.py`:

1. **Phone Number**: Change `TEST_PHONE_NUMBER` to your actual phone number
   ```python
   TEST_PHONE_NUMBER = "+1234567890"  # Replace with your phone number
   ```

2. **MQTT Broker IP**: Verify the Raspberry Pi IP address
   ```python
   MQTT_BROKER = "10.195.139.227"  # Your Raspberry Pi IP
   ```

## Running the Test

1. **Make sure your system is running:**
   - ESP32 is powered on and connected to WiFi
   - Raspberry Pi is running `server.py`
   - GSM module has a working SIM card

2. **Run the test script:**
   ```bash
   cd backend
   python test_gsm_sms.py
   ```

3. **Expected Output:**
   ```
   === GSM SMS Test Script ===
   Target Phone: +1234567890
   Message: Your Parcel is Being Delivered
   MQTT Broker: 10.195.139.227:1883
   --------------------------------------------------
   ✅ Connected to MQTT broker
   
   📱 Sending test SMS...
   ✅ SMS request sent successfully!
   📋 Waiting for confirmation from ESP32 (30 seconds)...
   ✅ SMS successfully sent to +1234567890
   
   🔌 Disconnecting...
   ✅ Test completed
   ```

## Troubleshooting

### Connection Issues
- **MQTT connection failed**: Check if Raspberry Pi is reachable and MQTT broker is running
- **ESP32 not responding**: Check ESP32 serial monitor for connection status

### SMS Issues
- **SMS not received**: 
  - Verify GSM module has network signal
  - Check SIM card balance/credit
  - Confirm phone number format (include country code)
- **GSM module errors**: Check ESP32 serial monitor for AT command responses

### Log Monitoring

**On Raspberry Pi (server.py logs):**
```bash
tail -f app.log
```

**On ESP32 (serial monitor):**
- Use Arduino IDE Serial Monitor
- Look for GSM AT command responses
- Check for MQTT connection status

## Manual Testing via MQTT

You can also manually test by publishing directly to MQTT:

```bash
mosquitto_pub -h 10.195.139.227 -t "esp32/gsm/send" -m '{"phone":"+1234567890","message":"Your Parcel is Being Delivered"}'
```

## Integration Test

To test the full QR scanning → SMS flow:

1. Ensure `server.py` is running on Raspberry Pi
2. Scan a valid QR code through your web interface
3. Check that SMS is automatically sent to the contact number associated with the order

The message sent will be: **"Your Parcel is Being Delivered"**
