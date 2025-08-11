# Loadcell Status Listening Enhancement

## Summary

Added support for listening to loadcell status messages on the `esp32/loadcell/status` topic to provide better visibility into loadcell operations.

## What Was Added

### New MQTT Topic Handler
- **Topic**: `esp32/loadcell/status`
- **Location**: `server.py` MQTT message handler
- **Purpose**: Monitor loadcell operational status and provide real-time feedback

### Status Messages Handled

#### 1. Loadcell Start Confirmation
- **ESP32 Message**: `"⚖️ Advanced load cell started"`
- **Server Action**: Logs confirmation and emits WebSocket event
- **WebSocket Event**:
  ```json
  {
    "step": 2.1,
    "status": "loadcell_started", 
    "message": "Load cell started and ready for measurement",
    "triggered_by": "loadcell_start_confirmation"
  }
  ```

#### 2. Weight Detection Notification  
- **ESP32 Message**: `"🔍 Weight detected! Collecting data..."`
- **Server Action**: Logs weight detection and emits WebSocket event
- **WebSocket Event**:
  ```json
  {
    "step": 2.2,
    "status": "weight_detected",
    "message": "Weight detected on load cell - collecting measurement data", 
    "triggered_by": "loadcell_weight_detection"
  }
  ```

#### 3. Generic Status Updates
- **Any Other Message**: Forwarded as generic loadcell status
- **WebSocket Event**:
  ```json
  {
    "status": "update",
    "message": "[original message]"
  }
  ```

## Technical Implementation

### Code Added to `server.py`
```python
# Handle loadcell status messages (Step 2: Load cell status updates)
elif topic.lower() == 'esp32/loadcell/status':
    try:
        logger.info(f"LOADCELL STATUS: {message}")
        
        # Check for specific loadcell status messages
        if "Advanced load cell started" in message:
            # Handle start confirmation
        elif "Weight detected! Collecting data" in message:
            # Handle weight detection
        else:
            # Generic status forwarding
```

### Integration Points
- **MQTT Subscription**: Already covered by `esp32/#` subscription
- **WebSocket Emission**: Real-time status updates to frontend
- **Logging**: All loadcell status messages logged with `LOADCELL STATUS:` prefix

## Benefits

### 1. **Enhanced Monitoring**
- Real-time visibility into loadcell operations
- Confirmation that loadcell starts successfully
- Immediate notification when weight is detected

### 2. **Better Debugging**
- Clear logs showing loadcell status progression
- WebSocket events allow frontend to show loadcell status
- Easier troubleshooting of weight measurement issues

### 3. **Improved User Experience**
- Frontend can show "Load cell starting..." status
- Progress indication during weight measurement
- Real-time feedback on measurement process

## Expected Log Output

```
INFO - LOADCELL STATUS: ⚖️ Advanced load cell started
INFO - ✅ LOADCELL: Advanced load cell started successfully
INFO - LOADCELL STATUS: 🔍 Weight detected! Collecting data...
INFO - 📊 LOADCELL: Weight detected, starting data collection
```

## Frontend Integration

The frontend can now listen for these WebSocket events:

```javascript
// Listen for loadcell workflow progress
socket.on('workflow_progress', (data) => {
  if (data.status === 'loadcell_started') {
    // Show "Load cell ready" indicator
  } else if (data.status === 'weight_detected') {
    // Show "Measuring weight..." indicator  
  }
});

// Listen for generic loadcell status
socket.on('loadcell_status', (data) => {
  // Display raw loadcell status message
  console.log('Loadcell:', data.message);
});
```

## Testing

To verify the feature:

1. **Start System**: Use frontend START button
2. **Trigger Loadcell**: Place object to trigger IR A → Motor A stops → Loadcell starts
3. **Check Logs**: Look for `LOADCELL STATUS:` messages
4. **Monitor WebSocket**: Check browser dev tools for `workflow_progress` events
5. **Verify Weight Detection**: Place weight on loadcell and check for weight detection message

## Files Modified

- `backend/server.py` - Added loadcell status message handler
- `backend/LOADCELL_STATUS_LISTENING.md` - This documentation

## Related Topics

This enhancement complements:
- Existing loadcell data handling (`esp32/loadcell/data`)  
- Weight unit consistency fixes
- Actuator removal and direct loadcell start
- Real-time workflow monitoring via WebSocket

The loadcell status listening provides the missing piece for complete loadcell operation visibility.

## Workflow Implementation Notes

### 2. IR B Behavior:
- **User Expectation**: "IR B Will start only when the first start on motor b not on this operation"
- **Current Implementation**: IR B starts with Motor B after Grabber2, gets disabled after first detection, and re-enables only on full cycle restart
- **Behavior**: IR B detection is sophisticated - it enables with Motor B first run, disables after detecting first object, and stays disabled until complete cycle restart

### 3. Motor B Second Run:
- **Implementation**: After QR validation, Motor B starts again but IR B stays disabled (doesn't restart until full cycle completion)
- **Logic**: The second Motor B run (post-QR validation) operates without IR B detection since the object has already been detected and processed
- **Cycle Management**: IR B only re-enables when the full cycle completes and restarts with Motor A
