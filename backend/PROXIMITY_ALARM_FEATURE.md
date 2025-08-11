# Proximity Sensor Metallic Detection & Alarm Feature

## Overview

Added proximity sensor monitoring functionality that detects metallic items and plays an al### Log Messages

### Success Messages
- `✅ Pygame mixer initialized for alarm sounds`
- `🚨 ALARM: Metallic item detected - Alarm sound played`
- `✅ PROXIMITY SENSOR: Proximity sensor started and active`

### Cooldown Messages
- `🔇 ALARM COOLDOWN: Metallic item detected but alarm in cooldown (12.3s remaining)`

### Warning Messages
- `⚠️ ALARM: Sound file not found: /sound/alarm.mp3`
- `⚠️ ALARM: Pygame mixer not available`

### Error Messages
- `❌ ALARM: Failed to play alarm sound: {error}`
- `Error processing proximity sensor status: {error}` metallic objects are detected in the workflow.

## What Was Added

### 1. Proximity Sensor Status Listening
- **Topic**: `esp32/proximity/status`
- **Location**: `server.py` MQTT message handler
- **Purpose**: Monitor proximity sensor for metallic item detection

### 2. Metallic Item Detection
- **Detection Keywords**: `metallic detected`, `metal detected`, `metallic item`, `metal object`
- **Action**: Plays alarm sound and sends alerts
- **Alert Type**: High-priority security alert

### 3. Alarm Sound System
- **Function**: `play_alarm_sound()`
- **Sound File**: `/sound/alarm.mp3` (on Raspberry Pi)
- **Technology**: Pygame mixer
- **Execution**: Non-blocking background thread
- **Cooldown**: 15-second cooldown between alarms to prevent spam
- **Spam Prevention**: Subsequent detections during cooldown are logged but don't trigger alarm

## Status Messages Handled

### Metallic Item Detection
- **ESP32 Message**: Contains keywords like `"metallic detected"`, `"metal detected"`, etc.
- **Server Action**: 
  1. Logs warning with 🚨 emoji
  2. Checks 15-second cooldown period
  3. Plays alarm sound (`/sound/alarm.mp3`) if not in cooldown
  4. Logs cooldown message if spam detected
  5. Emits WebSocket alerts with cooldown status
- **Cooldown System**: 
  - First detection: Plays alarm immediately
  - Subsequent detections: Logged with remaining cooldown time
  - Cooldown duration: 15 seconds
- **WebSocket Events**:
  ```json
  // Proximity Alert (Alarm Played)
  {
    "status": "metallic_detected",
    "message": "METALLIC ITEM DETECTED! Alarm sound played.",
    "alert_type": "danger",
    "alarm_played": true,
    "timestamp": "2025-08-11T...",
    "triggered_by": "proximity_sensor_metallic_detection"
  }
  
  // Proximity Alert (Cooldown Active)
  {
    "status": "metallic_detected",
    "message": "METALLIC ITEM DETECTED! Alarm in cooldown (12.3s remaining).",
    "alert_type": "danger", 
    "alarm_played": false,
    "timestamp": "2025-08-11T...",
    "triggered_by": "proximity_sensor_metallic_detection"
  }
  
  // Workflow Progress
  {
    "step": "proximity_alert",
    "status": "metallic_detected", 
    "message": "METALLIC ITEM DETECTED - Security alert triggered",
    "alarm_played": true,
    "timestamp": "2025-08-11T...",
    "triggered_by": "proximity_sensor_metallic_detection"
  }
  ```

### Proximity Sensor Status Updates
- **Started/Active**: `"started"`, `"active"`
- **Ready**: `"ready"`
- **Stopped/Disabled**: `"stopped"`, `"disabled"`

## Technical Implementation

### Dependencies
- **pygame**: Already included in `requirements.txt` (version 2.5.2)
- **threading**: For non-blocking alarm sound playback

### Code Location
- **MQTT Handler**: `server.py` line ~1461 (after IR B sensor handler)
- **Alarm Function**: `server.py` line ~128 (after reset_motor_b_cycle function)
- **Imports**: Added pygame import at top of `server.py`

### Sound File Requirements
- **Path**: `/sound/alarm.mp3`
- **Format**: MP3 audio file
- **Location**: Root filesystem on Raspberry Pi
- **Permissions**: Readable by the application user

## Integration with Existing Workflow

### Startup Integration
- Proximity sensor starts with Motor A when frontend START button is clicked
- Command: `esp32/proximity/request > start`
- Already integrated in existing startup sequence

### Monitoring Integration
- Continuous monitoring during workflow operation
- Independent of other sensor operations
- Does not interfere with existing workflow steps

## Frontend Integration

Frontend can listen for these WebSocket events:

```javascript
// Listen for proximity sensor alerts
socket.on('proximity_alert', (data) => {
  if (data.status === 'metallic_detected') {
    // Show critical security alert
    // Play visual/audio warning
    // Display: "METALLIC ITEM DETECTED!"
  }
});

// Listen for proximity sensor status in workflow
socket.on('workflow_progress', (data) => {
  if (data.step === 'proximity_sensor') {
    // Update proximity sensor status indicator
  } else if (data.step === 'proximity_alert') {
    // Handle metallic detection alert in workflow
  }
});
```

## Error Handling

### Pygame Initialization
- Graceful fallback if pygame mixer not available
- Warning logs if initialization fails
- Application continues normal operation

### Sound File Missing
- Warning log if `/sound/alarm.mp3` not found
- Alert still sent via WebSocket
- No application crash

### MQTT Processing
- Exception handling around proximity sensor message processing
- Logs errors without breaking MQTT connection

## Testing

To test the metallic detection feature:

1. **System Setup**: Ensure alarm.mp3 exists at `/sound/alarm.mp3`
2. **Start System**: Use frontend START button to activate proximity sensor
3. **Simulate Detection**: Send MQTT message with metallic keywords:
   ```bash
   mosquitto_pub -t esp32/proximity/status -m "metallic detected"
   ```
4. **Verify Response**: 
   - Check server logs for 🚨 alarm message
   - Verify alarm sound plays
   - Check WebSocket events in browser dev tools
   - Confirm proximity_alert event received

## Log Messages

### Success Messages
- `✅ Pygame mixer initialized for alarm sounds`
- `🚨 ALARM: Metallic item detected - Alarm sound played`
- `✅ PROXIMITY SENSOR: Proximity sensor started and active`

### Warning Messages
- `⚠️ ALARM: Sound file not found: /sound/alarm.mp3`
- `⚠️ ALARM: Pygame mixer not available`

### Error Messages
- `❌ ALARM: Failed to play alarm sound: {error}`
- `Error processing proximity sensor status: {error}`

## Security Considerations

### Immediate Response
- Alarm plays immediately upon detection
- No delays or batching of alerts
- High-priority logging with visual indicators

### Continuous Monitoring
- Proximity sensor active throughout workflow
- Independent monitoring thread
- No single point of failure

### Alert Distribution
- Local alarm sound on Raspberry Pi
- WebSocket alerts to all connected clients
- Persistent logging for audit trail

---

**Implementation Date**: August 11, 2025  
**Status**: Ready for deployment  
**Dependencies**: pygame (already installed)
