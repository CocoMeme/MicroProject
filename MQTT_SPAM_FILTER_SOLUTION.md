# MQTT Spam Filter Implementation

## Problem Solved
The ESP32 was continuously sending `0.0` weight readings to `esp32/loadcell/data`, causing:
- Log spam with repeated identical messages
- Excessive WebSocket emissions
- Unnecessary database operations
- Poor performance and cluttered logs

## Solution Implemented

### 1. **Topic Compatibility**
- Updated server to listen for both `/loadcell` and `esp32/loadcell/data` topics
- Your ESP32 is sending to `esp32/loadcell/data` which wasn't being handled

### 2. **Smart Spam Filtering**
The system now filters messages based on:
- **Minimum Weight Threshold**: Only processes weights > 0.1kg (configurable)
- **Weight Change Threshold**: Only logs if weight changes by > 0.05kg (configurable)
- **Duplicate Prevention**: Ignores repeated similar readings

### 3. **Multi-Level Filtering**
Spam filtering applied to:
- ✅ **MQTT Processing**: Prevents unnecessary database operations
- ✅ **WebSocket Emissions**: Stops frontend spam
- ✅ **File Logging**: Keeps log files clean
- ✅ **Console Logging**: Reduces terminal noise

### 4. **Configurable Settings**
```python
LOADCELL_SPAM_FILTER = {
    'min_weight_threshold': 0.1,      # Minimum weight to consider (kg)
    'weight_change_threshold': 0.05,  # Minimum change to log (kg) 
    'enabled': True                   # Enable/disable filtering
}
```

## How It Works

### Before (Spam):
```
📨 MQTT [03:44:16] esp32/loadcell/data > 0.0
📨 MQTT [03:44:17] esp32/loadcell/data > 0.0
📨 MQTT [03:44:18] esp32/loadcell/data > 0.0
... (repeated hundreds of times)
```

### After (Filtered):
```
📨 MQTT [03:44:16] esp32/loadcell/data > 0.0  (filtered - not logged)
📨 MQTT [03:45:20] esp32/loadcell/data > 2.5  (processed - meaningful weight)
📏 STEP 3 - LOADCELL: Weight captured 2.5kg
```

## Control Tools

### 1. **Test Spam Filtering**
```bash
python test_spam_filter.py
```
Tests filtering with various weight values.

### 2. **Control Filter Settings**
```bash
# View current settings
python spam_filter_control.py

# Enable/disable filtering  
python spam_filter_control.py --enable
python spam_filter_control.py --disable

# Adjust thresholds
python spam_filter_control.py --min-weight 0.2
python spam_filter_control.py --weight-change 0.1

# Reset to defaults
python spam_filter_control.py --reset
```

### 3. **API Endpoints**
```bash
# Get current config
curl http://localhost:5000/api/spam-filter

# Update config
curl -X POST http://localhost:5000/api/spam-filter \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "min_weight_threshold": 0.2}'
```

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable spam filtering |
| `min_weight_threshold` | `0.1` | Minimum weight to process (kg) |
| `weight_change_threshold` | `0.05` | Minimum change to log new reading (kg) |

## Expected Behavior

### Filtered Messages (Ignored):
- Weight readings ≤ 0.1kg (near zero)
- Weight changes < 0.05kg from last reading
- No WebSocket emission
- No file logging
- No database storage

### Processed Messages (Handled Normally):
- Weight readings > 0.1kg
- Weight changes ≥ 0.05kg from last reading
- Full processing with logs and storage

## Benefits

✅ **Eliminated Spam**: No more repeated 0.0 messages  
✅ **Better Performance**: Reduced unnecessary processing  
✅ **Clean Logs**: Only meaningful weight readings logged  
✅ **Preserved Functionality**: Real weights still processed normally  
✅ **Configurable**: Easy to adjust thresholds as needed  

## Testing

1. **Start your server** with the updated code
2. **Run the test**: `python test_spam_filter.py`
3. **Check logs**: Should see filtering in action
4. **Verify**: Only meaningful weights (>0.1kg) are processed

The spam problem should now be completely resolved! 🎯
