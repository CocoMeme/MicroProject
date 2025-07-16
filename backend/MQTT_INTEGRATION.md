# MQTT Integration for Raspberry Pi Server

This document explains the MQTT listener integration that has been added to the Flask server.

## Overview

The MQTT listener has been integrated directly into the `server.py` file, allowing it to start automatically when you run the server. This eliminates the need to run `mqtt_listener.py` separately.

## Features Added

### 1. **Integrated MQTT Listener Class**
- `MQTTListener` class handles all MQTT communication
- Automatically connects to the MQTT broker on startup
- Logs all received messages to `mqtt_messages.log`
- Provides real-time status updates via WebSocket

### 2. **New API Endpoints**
- `GET /mqtt/status` - Get current MQTT connection status
- `POST /mqtt/restart` - Restart the MQTT listener
- Updated `GET /status` and `GET /` endpoints now include MQTT status

### 3. **WebSocket Integration**
- Real-time MQTT message broadcasting via WebSocket
- MQTT connection status updates
- System status includes both camera and MQTT information

### 4. **WebSocket Events**
- `mqtt_message` - Broadcasts received MQTT messages
- `mqtt_status` - Broadcasts MQTT connection status changes
- `get_mqtt_status` - Client can request current MQTT status
- `restart_mqtt` - Client can restart MQTT connection

## Configuration

### MQTT Broker Settings
The MQTT listener is configured to connect to:
- **Host**: `localhost` (127.0.0.1)
- **Port**: `1883` (default MQTT port)
- **Topics**: Subscribes to `esp32/#` (all ESP32-related topics)

### Log File
- MQTT messages are logged to `mqtt_messages.log` in the backend directory
- Format: `[HH:MM:SS] topic > message`

## Usage

### Starting the Server
Simply run the server as usual:
```bash
python server.py
```

The MQTT listener will start automatically and you'll see:
```
🚀 MQTT Listener Starting...
✅ MQTT: Connected to broker successfully!
MQTT listener started at startup
```

### Monitoring MQTT Messages
1. **Via Logs**: Check `mqtt_messages.log` file
2. **Via WebSocket**: Connect to the WebSocket and listen for `mqtt_message` events
3. **Via API**: Use `/mqtt/status` endpoint to check connection status

### Troubleshooting
If MQTT connection fails:
1. Check if MQTT broker (Mosquitto) is running on the Raspberry Pi
2. Use the `/mqtt/restart` endpoint to restart the connection
3. Check the server logs for detailed error messages

## Dependencies

The following package has been added to both `requirements.txt` and `requirements-pi.txt`:
- `paho-mqtt==1.6.1`

Install dependencies:
```bash
pip install -r requirements-pi.txt
```

## Example WebSocket Client Code

```javascript
// Connect to WebSocket
const socket = io('http://your-raspi-ip:5001');

// Listen for MQTT messages
socket.on('mqtt_message', (data) => {
    console.log(`MQTT Message - Topic: ${data.topic}, Message: ${data.message}`);
});

// Listen for MQTT status changes
socket.on('mqtt_status', (data) => {
    console.log(`MQTT Status: ${data.status}`);
});

// Request current MQTT status
socket.emit('get_mqtt_status');
```

## Benefits

1. **Simplified Deployment**: No need to run multiple Python scripts
2. **Real-time Monitoring**: WebSocket integration for live MQTT message viewing
3. **Centralized Logging**: All system components logged in one place
4. **Better Error Handling**: Automatic reconnection and status reporting
5. **API Control**: Start/stop/restart MQTT via HTTP endpoints
