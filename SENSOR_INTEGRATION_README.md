# MQTT Sensor Data Integration Implementation

## Overview
This implementation creates a complete integration between MQTT sensor data (/loadcell and /box/results topics) and QR code validation, storing the data in a new `loaded_sensor_data` table and applying it to orders when QR codes are scanned.

## Database Changes

### New Table: `loaded_sensor_data`
```sql
CREATE TABLE loaded_sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weight REAL,
    width REAL,
    height REAL,
    length REAL,
    loadcell_timestamp TEXT,
    box_dimensions_timestamp TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

This table temporarily stores sensor data from MQTT topics until a QR code is scanned and validated.

## Backend Changes

### 1. Updated `server.py` (Raspberry Pi Server)
- **Enhanced MQTT message processing**: Now stores sensor data in the database when messages are received
- **Added `store_sensor_data_in_db()` function**: Sends sensor data to the main backend API
- **Topics handled**:
  - `/loadcell` - stores weight measurements
  - `/box/results` - stores dimensions (width,height,length format: "15.0,10.0,20.0")

### 2. Updated `app.py` (Main Backend)
- **New API endpoints**:
  - `POST /api/sensor-data` - Store sensor data from MQTT
  - `GET /api/sensor-data` - Retrieve current sensor data
  - `DELETE /api/sensor-data` - Clear sensor data
  - `GET /api/package-information` - Enhanced to return package data in the expected format

- **Enhanced QR validation logic**: 
  - When a QR code is validated, the system checks for stored sensor data
  - If sensor data exists, it creates a package_information record and clears the sensor data
  - Returns `sensor_data_applied: true` in the response when data is applied

## Frontend Changes

### Updated `Scanner.js`
- **New state variables**:
  - `packageInformation` - stores package data
  - `isLoadingPackages` - loading state for package data

- **New functions**:
  - `getPackageInformation()` - fetches package information from backend
  - Enhanced `handleQRDetected()` - now refreshes package information when QR is detected

- **Enhanced Package Information Table**:
  - Displays Order ID, Order Number, Weight, Height, Width, Length, Timestamp
  - Auto-refreshes every 10 seconds
  - Shows loading states and empty states
  - Refresh button for manual updates

## Integration Flow

1. **MQTT Data Collection**:
   ```
   /loadcell → weight measurement → stored in loaded_sensor_data
   /box/results → "width,height,length" → stored in loaded_sensor_data
   ```

2. **QR Code Scanning**:
   ```
   QR Scanned → Validate against orders → If valid:
   - Check for sensor data in loaded_sensor_data
   - Create package_information record with sensor data
   - Clear sensor data from loaded_sensor_data
   - Mark order as scanned
   ```

3. **Display in Scanner.js**:
   ```
   Package Information Table → Shows all package_information records
   Auto-refreshes when QR codes are detected
   ```

## API Endpoints

### Sensor Data Management
- `POST /api/sensor-data` - Store sensor data
- `GET /api/sensor-data` - Get current sensor data  
- `DELETE /api/sensor-data` - Clear sensor data

### Package Information
- `GET /api/package-information` - Get all package records
- `POST /api/package-information` - Create package record (existing)

### QR Validation (Enhanced)
- `POST /api/validate-qr` - Validate QR and apply sensor data if available

## Testing

Run the integration test:
```bash
cd d:\VSC\MicroProject
python test_integration.py
```

This tests:
- Database table creation
- Sensor data storage and retrieval
- QR validation with sensor data integration
- Package information retrieval
- Sensor data clearing

## Usage

1. **Start the servers**:
   ```bash
   # Main backend
   cd backend && python app.py

   # Raspberry Pi server  
   cd backend && python server.py
   ```

2. **Start the frontend**:
   ```bash
   cd frontend && npm start
   ```

3. **MQTT Workflow**:
   - Send weight data to `/loadcell` topic: `"2.5"`
   - Send dimensions to `/box/results` topic: `"15.0,10.0,20.0"`
   - Scan a QR code in the Scanner.js interface
   - The system will validate the QR, apply the sensor data to the order, and clear the sensor data
   - View the results in the Package Information table

## Error Handling

- Invalid MQTT data formats are logged but don't crash the system
- Database connection errors are handled gracefully
- API timeouts are managed with appropriate error messages
- Frontend displays loading states and error messages appropriately

## Notes

- Sensor data is automatically cleared after successful QR validation
- Only one set of sensor data is stored at a time (new data overwrites old)
- Package information table shows the most recent 50 records
- All timestamps are in ISO format for consistency
