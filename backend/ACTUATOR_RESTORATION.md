# Actuator Restoration to Workflow

## Change Summary

**Restored the actuator activation sequence back to the workflow when Motor A stops (detected by IR A).**

## What Changed

### Before (After Removal)
1. IR A detects object → Motor A stops
2. Loadcell starts immediately
3. Loadcell measures weight

### After (Restored)  
1. IR A detects object → Motor A stops
2. 5-second delay → Actuator starts 
3. Actuator completes → Loadcell starts
4. Loadcell measures weight

## Technical Implementation

### Code Changes in `server.py`

**Modified function**: Motor status message handler for "Motor A stopped by IR A"

**Before (Direct Loadcell):**
```python
logger.info("ℹ️ AUTONOMOUS ESP32: ESP32 will automatically start actuator → loadcell sequence")
```

**After (Manual Actuator Control):**
```python
def send_actuator_then_loadcell():
    # STEP 1: Start actuator with 5 second delay
    time.sleep(5)
    actuator_success = mqtt_listener.publish_message('esp32/actuator/request', 'start')
    # STEP 2: Loadcell will start after actuator completion
```

**Enhanced actuator completion handler:**
```python
def start_loadcell_after_actuator():
    loadcell_success = mqtt_listener.publish_message('esp32/loadcell/request', 'start')
```

### Workflow Changes

**Restored steps:**
- 5-second delay after Motor A stops
- Actuator activation (`esp32/actuator/request > start`)
- Waiting for actuator completion
- Loadcell starts after actuator completion

**Enhanced workflow:**
- IR A triggers → Motor A stops → 5s delay → Actuator starts → Actuator completes → Loadcell starts

## Benefits

1. **Physical Process Control**: Actuator ensures proper positioning/preparation before weight measurement
2. **Predictable Sequence**: Clear step-by-step workflow with proper timing
3. **Enhanced Reliability**: Fallback to direct loadcell if actuator fails
4. **Better Monitoring**: Detailed WebSocket events for each step

## Expected Behavior

### Log Messages After Restoration
```
INFO - STEP 2 - MOTOR STATUS: Motor A stopped by IR A - Starting actuator sequence
INFO - STEP 2.1 - ACTUATOR: Motor A stopped, starting actuator with 5 second delay...
INFO - SUCCESS: Actuator START request sent (esp32/actuator/request > start)
INFO - ✅ ACTUATOR: Actuator cycle complete - Starting loadcell
INFO - STEP 2.2 - LOADCELL: Actuator complete, starting loadcell...
INFO - SUCCESS: Loadcell START request sent after actuator completion
INFO - ✅ WORKFLOW: Actuator complete → Loadcell started → Weight measurement
```

### WebSocket Events
```json
{
  "step": 2,
  "status": "motor_a_stopped_actuator_sequence",
  "message": "Motor A stopped by IR A - Starting actuator sequence",
  "triggered_by": "motor_a_stopped_ir_a"
}

{
  "step": 2.1,
  "status": "actuator_start_requested", 
  "message": "Actuator started after 5s delay - will start loadcell after completion",
  "triggered_by": "motor_a_stopped_ir_a"
}

{
  "step": 2.1,
  "status": "actuator_complete",
  "message": "Actuator cycle complete - Starting loadcell",
  "triggered_by": "actuator_complete"
}

{
  "step": 2.2,
  "status": "loadcell_start_requested",
  "message": "Loadcell started after actuator completion", 
  "triggered_by": "actuator_complete"
}
```

## Hardware Impact

### Now active in workflow:
- Linear actuator (restored to critical path)
- Actuator timing/delay mechanisms
- Proper sequencing control

### Still active:
- All other hardware components remain unchanged
- IR A sensor still triggers Motor A stop
- Loadcell operation unchanged after start

## Testing Verification

To verify the restored actuator workflow:

1. **Start System**: Use frontend START button
2. **Trigger IR A**: Place object to trigger IR A sensor  
3. **Check Logs**: Look for "Starting actuator sequence" message
4. **Verify Timing**: 5-second delay should occur before actuator starts
5. **Confirm Sequence**: Actuator should complete before loadcell starts
6. **Monitor WebSocket**: Check browser dev tools for workflow_progress events

## Files Modified

- `backend/server.py` - Restored actuator sequence, enhanced status handling
- `backend/WORKFLOW_CYCLE_DOCUMENTATION.md` - Should be updated to reflect restored workflow
- `backend/ACTUATOR_RESTORATION.md` - This documentation

## Rollback Information

If actuator needs to be removed again, refer to `ACTUATOR_REMOVAL_FIX.md` for the previous implementation.

## Related Hardware

This change affects:
- Motor A operation (still stops on IR A detection)
- **Actuator operation (restored to workflow)**
- Loadcell functionality (now starts after actuator completion)
- IR sensor A operation (unchanged)

The actuator is now back in the critical workflow path and is required for proper operation.
