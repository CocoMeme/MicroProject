# Updated Workflow Cycle Documentation

## Current Cycle Implementation (Updated to Match Requirements)

### Step 0: START (Frontend Button Click)
- **Frontend Action**: User clicks START button
- **Backend Response**: 
  1. Starts proximity sensor (`esp32/proximity/request > start`)
  2. Starts Motor A (`esp32/motor/request > startA`)
- **Status**: System ready and monitoring for objects

### Step 1: IR A Detection
- **Trigger**: IR A sensor detects object approaching
- **Actions**:
  1. Stops Motor A (`esp32/motor/request > stopA`)
  2. Starts actuator after 5-second delay (`esp32/actuator/request > start`)
  3. Starts loadcell (`esp32/loadcell/request > start`)

### Step 2: Weight Measurement
- **Trigger**: Loadcell completes weight measurement
- **Actions**:
  1. Stores weight data in database
  2. Starts Grabber1 (`esp32/grabber1/request > start`)

### Step 3: Grabber1 Operation
- **Trigger**: Grabber1 completes parcel pickup
- **Actions**:
  1. Starts Box system after 5-second delay (`esp32/box/request > start`)

### Step 4: Box System (Size Measurement)
- **Trigger**: Box system completes dimension measurement
- **Actions**:
  1. Stores dimensions in database
  2. Determines package size (small/medium/large)
  3. Sends stepper positioning command based on package size
  4. Starts Grabber2 (`esp32/grabber2/request > start`)

### Step 5: Grabber2 Operation
- **Trigger**: Grabber2 completes parcel transfer
- **Actions**:
  1. Starts Motor B (first run) (`esp32/motor/request > startB`)
  2. Enables IR B detection for object detection

### Step 6: IR B Detection
- **Trigger**: IR B detects object
- **Actions**:
  1. Stops Motor B (`esp32/motor/request > stopB`)
  2. **DISABLES IR B** for object detection (as per requirements)
  3. Starts QR validation monitoring

### Step 7: QR Validation Process
- **Trigger**: Valid QR code scanned
- **Sequential Actions** (as per requirements):
  1. **Print Receipt** for the order
  2. **Start Motor B** (second run) (`esp32/motor/request > startB`)
  3. **Disable IR B** (remains disabled from Step 6)
  4. **Send GSM SMS** to contact number from QR order
  5. **Wait 5 seconds**
  6. **Send Stepper Back** command based on package size (`esp32/stepper/request > {size}back`)

### Step 8: Cycle Completion
- **Trigger**: Stepper back command completes
- **Actions**:
  1. Stops all systems (emergency stop sequence)
  2. Waits 3 seconds for systems to stop
  3. **Restarts cycle** with Motor A (`esp32/motor/request > startA`)
  4. **Re-enables IR B** for next cycle

## Key Improvements Made

### 1. **Added Proximity Sensor Start**
- Frontend start now activates both proximity sensor and Motor A
- Matches requirement: "START PROXIMITY AND MOTOR A START"

### 2. **Improved IR B Logic**
- IR B detection properly disables after first object detection
- Remains disabled until cycle completion
- Matches requirement: "DISABLE IR B FOR OBJECT DETECTION ONCE DETECTED AN OBJECT AND IT WOULD START AGAIN WHEN CYCLE IS COMPLETED"

### 3. **Correct QR Validation Sequence**
- QR validation now triggers after IR B detection
- Proper sequence: Receipt → Motor B → GSM → 5s delay → Stepper back
- Matches requirement: "START QR VALIDATION → IF QR IS VALID → PRINT RECEIPT → START MOTORB → SEND GSM MODULE → AFTER 5 SECONDS → STEPPER WOULD BACK"

### 4. **Enhanced Motor B Control**
- First run: After Grabber2 completion (enables IR B)
- Second run: After QR validation (IR B stays disabled)
- Proper state management throughout cycle

### 5. **Proper Cycle Restart**
- Complete system stop after stepper back completion
- Clean restart with Motor A
- IR B re-enabled for new cycle

## State Variables

The system uses `motor_b_cycle_state` to track:
- `ir_b_enabled`: Whether IR B detection is active
- `motor_b_first_run`: Whether Motor B first run completed
- `motor_b_second_run`: Whether Motor B second run completed  
- `cycle_complete`: Whether full cycle is complete
- `grabber2_completed`: Whether grabber2 has finished
- `qr_validated`: Whether QR validation occurred

## MQTT Topics Used

### Input Topics (from ESP32):
- `esp32/ir/status` - IR A sensor triggers
- `esp32/irsensorB/status` - IR B sensor status and triggers
- `esp32/motor/status` - Motor status updates
- `esp32/loadcell/data` - Weight measurements
- `esp32/box/status` - Dimension measurements
- `esp32/parcel1/status` - Grabber1 status
- `esp32/parcel2/status` - Grabber2 status
- `esp32/stepper/status` - Stepper position status

### Output Topics (to ESP32):
- `esp32/proximity/request` - Start proximity sensor
- `esp32/motor/request` - Motor A/B control (startA, stopA, startB, stopB)
- `esp32/irsensorB/request` - IR B sensor control (start, stop)
- `esp32/actuator/request` - Actuator control
- `esp32/loadcell/request` - Load cell control
- `esp32/grabber1/request` - Grabber1 control
- `esp32/grabber2/request` - Grabber2 control
- `esp32/box/request` - Box system control
- `esp32/stepper/request` - Stepper positioning (small, medium, large, smallback, mediumback, largeback)
- `esp32/gsm/send` - SMS sending with phone number

## Database Integration

The system integrates with:
- `loaded_sensor_data` - Real-time sensor measurements
- `package_information` - Links orders to sensor data
- `qr_codes` and `orders` - QR validation and order details

This updated implementation now fully matches your specified workflow requirements.
