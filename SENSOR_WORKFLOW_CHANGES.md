# Sensor Data Workflow Changes

## Overview
Modified the sensor data storage logic to follow the new workflow:

**Step 2**: Motor detects object → Immediately request loadcell reading
**Step 3**: Load Sensor captures weight → Store weight-only data
**Step 4**: Grabber holds and moves parcel (no data storage)
**Step 5**: Size Sensor captures dimensions → Overwrite existing record with complete data

## Changes Made

### 1. Backend/server.py Changes

#### Modified MQTT Message Processing
- **Step 2 (`esp32/motor/status` topic)**: Detects object with "📍 Object detected! Motor B paused", immediately sends loadcell request
- **Step 3 (`/loadcell` or `esp32/loadcell/data` topics)**: Now calls `store_weight_data_in_db()` to store only weight
- **Step 5 (`/box/results` topic)**: Now calls `update_sensor_data_with_dimensions()` to overwrite with complete data

#### New Functions Added

**`determine_package_size(width, height, length)`**
- Calculates package size category (Small/Medium/Large) based on dimensions
- Uses volume and max dimension thresholds

**`store_weight_data_in_db()`**
- Stores ONLY weight data in database (Step 3)
- Sets dimensions to NULL
- Emits workflow progress via WebSocket

**`update_sensor_data_with_dimensions()`**
- Updates existing weight record with dimensions (Step 5)
- Determines package size category
- Overwrites the weight-only entry with complete data
- Emits workflow completion via WebSocket

**`store_sensor_data_in_db()` (Legacy)**
- Kept for backward compatibility
- Auto-detects workflow step and calls appropriate function

### 2. Backend/app.py Changes

#### Database Schema Updates
- Added `package_size TEXT` column to `loaded_sensor_data` table
- Added migration logic to add column to existing databases

#### API Enhancements

**POST `/api/sensor-data`**
- Now handles `package_size` field
- Enhanced logging to show Step 3 vs Step 5 operations
- Returns more detailed response with package information

**GET `/api/workflow-status`** (New Endpoint)
- Returns current workflow step based on sensor data
- Shows workflow status: waiting, weight_captured, complete, incomplete
- Provides detailed status messages

#### Workflow States
- **Step 0**: Waiting for QR scan
- **Step 2**: Object detected, motor paused, requesting loadcell
- **Step 3**: Weight captured, ready for grabber
- **Step 5**: Complete package data with dimensions and size

## Database Flow

### Step 3: Weight Capture
```sql
INSERT INTO loaded_sensor_data (
    weight, 
    width, height, length,  -- NULL
    package_size,           -- NULL
    loadcell_timestamp,
    box_dimensions_timestamp -- NULL
)
```

### Step 5: Dimension Capture (Overwrites Step 3)
```sql
DELETE FROM loaded_sensor_data;  -- Clear previous entry
INSERT INTO loaded_sensor_data (
    weight,                 -- From Step 3
    width, height, length,  -- New dimensions
    package_size,           -- Calculated size
    loadcell_timestamp,     -- From Step 3
    box_dimensions_timestamp -- New timestamp
)
```

## Package Size Classification

- **Small**: Volume ≤ 1000cm³ OR max dimension ≤ 15cm
- **Medium**: Volume ≤ 8000cm³ OR max dimension ≤ 30cm  
- **Large**: Volume > 8000cm³ AND max dimension > 30cm

## WebSocket Events

### New Events Emitted
- `workflow_progress`: Step completion notifications
- `sensor_data_cleared`: When workflow resets

### Event Structure
```json
{
    "step": 3,
    "status": "completed",
    "message": "Weight captured: 2.5kg",
    "timestamp": "2025-07-21T10:30:00Z"
}
```

## Testing the Workflow

1. **Step 2 Test**: Send motor status via MQTT `esp32/motor/status` topic
   - Message: "📍 Object detected! Motor B paused"
   - Should immediately trigger loadcell request (no delay)

2. **Step 3 Test**: Send weight via MQTT `/loadcell` or `esp32/loadcell/data` topic
   - Should store weight-only record
   - Check `GET /api/workflow-status` shows step 3

3. **Step 5 Test**: Send dimensions via MQTT `/box/results` topic  
   - Should overwrite with complete data including package size
   - Check `GET /api/workflow-status` shows step 5 complete

4. **Verify Database**: Check `loaded_sensor_data` table shows single record with all data

### Using the Test Script
Run the updated test script to simulate the new workflow:
```bash
python test_motor_trigger_updated.py
```

## Backward Compatibility

- Legacy `store_sensor_data_in_db()` function maintained
- Existing API endpoints still work
- Database migration handles existing installations
