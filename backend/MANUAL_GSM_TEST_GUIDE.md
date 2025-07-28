# Manual GSM Test Commands

## Option 1: Using Python Script
```bash
cd backend
python manual_gsm_test.py
```

## Option 2: Using mosquitto_pub (if installed)
```bash
# Replace +639612903652 with your actual phone number
mosquitto_pub -h 192.168.100.63 -t "esp32/gsm/request" -m "start:+639612903652"
```

## Option 3: Using mosquitto_pub with status monitoring
```bash
# Terminal 1 - Monitor status responses
mosquitto_sub -h 192.168.100.63 -t "esp32/gsm/status"

# Terminal 2 - Send GSM request (replace with your number)
mosquitto_pub -h 192.168.100.63 -t "esp32/gsm/request" -m "start:+639612903652"
```

## What the command does:
- **Topic**: `esp32/gsm/request`
- **Message**: `start:+639612903652` (replace with your number)
- **ESP32 Action**: Sends SMS "Your Parcel is Being Delivered" to the specified number
- **Response**: ESP32 sends confirmation to `esp32/gsm/status`

## Expected ESP32 Serial Output:
```
[MQTT] GSM Request Command Received
[MQTT] Full message: start:+639612903652
[INFO] Final Phone Number: +639612903652
[INFO] Message: Your Parcel is Being Delivered
[INFO] Sending SMS with fixed message
[GSM] Sending message...
[GSM] To: +639612903652
[GSM] Message: Your Parcel is Being Delivered
[GSM] Message sent successfully.
[INFO] Confirmation sent: {"status":"sent","phone":"+639612903652","original":"start:+639612903652"}
```

## Troubleshooting:
1. **No response**: Check ESP32 is connected to WiFi and MQTT
2. **SMS not received**: Check GSM module signal and SIM card credit
3. **Connection failed**: Verify Raspberry Pi IP (192.168.100.63) is correct
