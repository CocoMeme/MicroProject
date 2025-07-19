# MQTT Sensor Data and QR Code Integration System

## Overview

This system integrates MQTT sensor data (loadcell weight and box dimensions) with QR code scanning to automatically capture package information when orders are scanned.

## Components

### 1. MQTT Data Sources
- **Loadcell Topic**: `/loadcell` - Provides weight data in kg (e.g., "2.5")
- **Box Dimensions Topic**: `/box/results` - Provides dimensions as "width,height,length" in cm (e.g., "15.2,10.5,8.3")

### 2. Database Schema
A new `package_information` table stores physical package data:
```sql
CREATE TABLE package_information (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    order_number TEXT,
    weight REAL,
    width REAL,
    height REAL,
    length REAL,
    timestamp TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (id)
);
```

### 3. Workflow

#### Automatic Mode (Recommended)
1. **MQTT Data Reception**: System listens for loadcell and box dimension data
2. **Data Storage**: Incoming sensor data is temporarily stored in memory
3. **QR Code Scanning**: When a valid QR code is scanned:
   - System validates the order exists in the database
   - Available sensor data is automatically applied to the order
   - Package information is stored in the database
   - Sensor data is cleared after successful application
4. **Real-time Updates**: WebSocket events notify clients of updates

#### Manual Mode
1. **MQTT Data Reception**: Same as automatic mode
2. **Manual Trigger**: Use the `/api/apply-package-data` endpoint to manually apply sensor data to a specific order

## API Endpoints

### Raspberry Pi Server (Port 5001)

#### Get Current Sensor Data
```
GET /api/mqtt-sensor-data
```
Returns current loadcell and box dimension data.

#### Apply Package Data
```
POST /api/apply-package-data
Content-Type: application/json

{
    "order_number": "ORD-001"
}
```
Applies current sensor data to the specified order.

#### Clear Sensor Data
```
POST /api/clear-sensor-data
```
Manually clears stored sensor data.

#### Test MQTT Messages
```
POST /debug/test-mqtt
Content-Type: application/json

{
    "topic": "/loadcell",
    "message": "2.5"
}
```
Simulates MQTT messages for testing.

### Main Backend Server (Port 5000)

#### Create/Update Package Information
```
POST /api/package-information
Content-Type: application/json

{
    "order_number": "ORD-001",
    "order_id": 1,
    "weight": 2.5,
    "width": 15.2,
    "height": 10.5,
    "length": 8.3,
    "timestamp": "2025-07-19T10:30:00"
}
```

#### Get Package Information
```
GET /api/package-information/{order_id}
GET /api/package-information  // Get all records
```

#### Enhanced QR Validation
```
POST /api/validate-qr
Content-Type: application/json

{
    "qr_data": "ORD-001"
}
```
Now returns package information if available.

## WebSocket Events

### Client → Server
- `start_camera`: Start camera scanning
- `stop_camera`: Stop camera scanning

### Server → Client
- `qr_detected`: QR code detected with validation and sensor data
- `mqtt_message`: Raw MQTT message received
- `package_data_applied`: Package data successfully applied to order
- `package_information_updated`: Package information record updated
- `sensor_data_cleared`: Sensor data has been cleared

## Example Usage

### 1. Simulate MQTT Data
```python
import requests

# Send weight data
requests.post("http://localhost:5001/debug/test-mqtt", json={
    "topic": "/loadcell",
    "message": "2.5"
})

# Send dimension data
requests.post("http://localhost:5001/debug/test-mqtt", json={
    "topic": "/box/results", 
    "message": "15.2,10.5,8.3"
})
```

### 2. Scan QR Code (Automatic)
When a QR code like "ORD-001" is scanned by the camera, the system will:
- Validate the order exists
- Automatically apply any available sensor data
- Store the package information
- Clear the sensor data

### 3. Manual Package Data Application
```python
import requests

# Apply current sensor data to specific order
response = requests.post("http://localhost:5001/api/apply-package-data", json={
    "order_number": "ORD-001"
})
```

### 4. Retrieve Package Information
```python
import requests

# Get all package information
response = requests.get("http://localhost:5000/api/package-information")
packages = response.json()

for package in packages:
    print(f"Order {package['order_number']}: {package['weight']}kg, "
          f"{package['width']}x{package['height']}x{package['length']}cm")
```

## Testing

Run the test script to verify functionality:
```bash
cd backend
python test_mqtt_qr_system.py
```

This will:
1. Simulate MQTT sensor data
2. Create a test order
3. Validate QR codes
4. Apply package data
5. Retrieve stored information
6. Clear sensor data

## Real Hardware Integration

To integrate with real hardware:

1. **MQTT Broker**: Ensure your ESP32 or other devices publish to:
   - Topic: `/loadcell` with weight values
   - Topic: `/box/results` with "width,height,length" format

2. **Camera**: The existing camera system will automatically trigger package data application when QR codes are scanned

3. **Configuration**: Update MQTT broker settings in `server.py` if needed:
   ```python
   mqtt_listener = MQTTListener(broker_host="your_broker_ip", broker_port=1883)
   ```

## Error Handling

The system includes comprehensive error handling for:
- Invalid MQTT message formats
- Missing sensor data
- Invalid QR codes
- Database connection issues
- Network connectivity problems

All errors are logged and appropriate HTTP status codes are returned for API requests.
