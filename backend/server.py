from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from print import ReceiptPrinter
from camera import CameraManager
import paho.mqtt.client as mqtt
import logging
from datetime import datetime
import threading
import time
import requests
import requests
import os
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('printer_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-raspi'

# Enable CORS and SocketIO
CORS(app, 
     origins=["*"],  # Allow all origins
     methods=["GET", "POST", "OPTIONS"],  # Allow these methods
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)  # Allow credentials

# Initialize SocketIO with minimal configuration to avoid conflicts
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=False,  # Disable verbose logging
                   engineio_logger=False,
                   transport=['websocket', 'polling'],  # Support both transports
                   ping_timeout=60,
                   ping_interval=25)

printer = ReceiptPrinter()
camera = CameraManager()

# MQTT Listener Class
class MQTTListener:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ MQTT: Connected to broker successfully!")
            self.is_connected = True
            client.subscribe("esp32/#")  # Subscribe to all ESP32-related topics
            # Emit connection status via WebSocket
            socketio.emit('mqtt_status', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"❌ MQTT: Connection failed with code {rc}")
            self.is_connected = False

    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        try:
            message = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            message = msg.payload.decode('utf-8', errors='replace')
        
        topic = msg.topic
        logger.info(f"📨 MQTT [{timestamp}] {topic} > {message}")
        
        # Process specific MQTT topics for sensor data
        global mqtt_sensor_data
        try:
            # Handle loadcell weight data (Step 3: Load Sensor gets weight)
            # Support both /loadcell and esp32/loadcell/data topics
            if topic.lower() in ['/loadcell', 'esp32/loadcell/data']:
                try:
                    weight = float(message)
                    
                    # Apply spam filtering if enabled
                    if LOADCELL_SPAM_FILTER['enabled']:
                        # Filter out spam messages - only process if weight is meaningful
                        # and different from last reading
                        min_weight = LOADCELL_SPAM_FILTER['min_weight_threshold']
                        change_threshold = LOADCELL_SPAM_FILTER['weight_change_threshold']
                        
                        if (weight > min_weight and 
                            (mqtt_sensor_data['loadcell']['weight'] is None or 
                             abs(weight - (mqtt_sensor_data['loadcell']['weight'] or 0)) > change_threshold)):
                            
                            mqtt_sensor_data['loadcell']['weight'] = weight
                            mqtt_sensor_data['loadcell']['timestamp'] = datetime.now().isoformat()
                            logger.info(f"📏 STEP 3 - LOADCELL: Weight captured {weight}kg")
                            
                            # Store ONLY weight data in database (first entry)
                            store_weight_data_in_db()
                        else:
                            # Suppress spam logging for zero or very small weight readings
                            if weight <= min_weight:
                                pass  # Don't log zero/near-zero readings
                            else:
                                logger.debug(f"📏 LOADCELL: Ignoring similar weight reading {weight}kg")
                    else:
                        # No filtering - process all weight readings
                        mqtt_sensor_data['loadcell']['weight'] = weight
                        mqtt_sensor_data['loadcell']['timestamp'] = datetime.now().isoformat()
                        logger.info(f"📏 STEP 3 - LOADCELL: Weight captured {weight}kg")
                        store_weight_data_in_db()
                    
                except ValueError:
                    logger.warning(f"Invalid weight value received: {message}")
            
            # Handle box dimensions data (Step 5: Size Sensor gets dimensions after grabber moves box)
            elif topic.lower() == '/box/results':
                try:
                    # Expecting format: "width,height,length"
                    dimensions = message.split(',')
                    if len(dimensions) == 3:
                        width, height, length = [float(dim.strip()) for dim in dimensions]
                        mqtt_sensor_data['box_dimensions']['width'] = width
                        mqtt_sensor_data['box_dimensions']['height'] = height
                        mqtt_sensor_data['box_dimensions']['length'] = length
                        mqtt_sensor_data['box_dimensions']['timestamp'] = datetime.now().isoformat()
                        logger.info(f"📦 STEP 5 - SIZE SENSOR: Dimensions captured W:{width}, H:{height}, L:{length}cm")
                        
                        # Determine package size category
                        package_size = determine_package_size(width, height, length)
                        logger.info(f"📏 PACKAGE SIZE DETERMINED: {package_size}")
                        
                        # Update existing weight record with dimensions (overwrite the weight-only entry)
                        update_sensor_data_with_dimensions()
                        
                    else:
                        logger.warning(f"Invalid box dimensions format: {message}")
                except ValueError:
                    logger.warning(f"Invalid box dimensions values: {message}")
            # Handle motor status messages (Step 2: Object detection triggers loadcell)
            elif topic.lower() == 'esp32/motor/status':
                try:
                    # Check for object detection message (updated pattern)
                    if '📍 Object detected! Motor B paused' in message:
                        logger.info(f"🚛 STEP 2 - MOTOR STATUS: Object detected, motor paused")
                        
                        # Send immediate loadcell request (no delay needed)
                        def send_loadcell_request():
                            try:
                                logger.info("📤 Sending loadcell start request to ESP32...")
                                
                                # Send loadcell request via MQTT
                                success = mqtt_listener.publish_message('esp32/loadcell/request', 'start')
                                if success:
                                    logger.info("✅ STEP 3 TRIGGER: Sent loadcell request (esp32/loadcell/request > start)")
                                    
                                    # Emit workflow progress via WebSocket
                                    socketio.emit('workflow_progress', {
                                        'step': 2.5,
                                        'status': 'loadcell_requested',
                                        'message': 'Object detected, loadcell reading requested',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                else:
                                    logger.error("❌ Failed to send loadcell request")
                                    
                            except Exception as e:
                                logger.error(f"❌ Error sending loadcell request: {e}")
                        
                        # Start request in background thread to not block MQTT processing
                        request_thread = threading.Thread(target=send_loadcell_request, daemon=True)
                        request_thread.start()
                        
                        # Emit immediate motor status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2,
                            'status': 'object_detected',
                            'message': 'Object detected! Motor paused, requesting weight measurement',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    else:
                        logger.info(f"🚛 MOTOR STATUS: {message}")
                        
                except Exception as e:
                    logger.error(f"Error processing motor status: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing MQTT sensor data: {e}")
        
        # Log to file (filter out spam messages)
        should_log_to_file = True
        
        # Filter loadcell spam from file logging
        if LOADCELL_SPAM_FILTER['enabled'] and topic.lower() in ['esp32/loadcell/data', '/loadcell']:
            try:
                weight_value = float(message)
                if weight_value <= LOADCELL_SPAM_FILTER['min_weight_threshold']:
                    should_log_to_file = False
            except ValueError:
                pass  # If not a number, log normally
        
        if should_log_to_file:
            try:
                with open("mqtt_messages.log", "a", encoding='utf-8') as f:
                    f.write(f"[{timestamp}] {topic} > {message}\n")
            except Exception as e:
                logger.error(f"Failed to write MQTT log: {e}")
        
        # Emit MQTT message via WebSocket for real-time monitoring
        # Filter out spam messages for certain topics
        should_emit_websocket = True
        
        # Filter loadcell spam (zero or very small readings)
        if LOADCELL_SPAM_FILTER['enabled'] and topic.lower() in ['esp32/loadcell/data', '/loadcell']:
            try:
                weight_value = float(message)
                if weight_value <= LOADCELL_SPAM_FILTER['min_weight_threshold']:
                    should_emit_websocket = False
            except ValueError:
                pass  # If not a number, emit normally
        
        if should_emit_websocket:
            mqtt_data = {
                'topic': topic,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'raw_timestamp': timestamp,
                'sensor_data': mqtt_sensor_data.copy()  # Include current sensor data state
            }
            
            logger.info(f"Emitting MQTT message via WebSocket: {mqtt_data}")
            
            # Emit to all connected clients
            socketio.emit('mqtt_message', mqtt_data)
            
            # Also broadcast to all namespaces
            socketio.emit('mqtt_message', mqtt_data, namespace='/')

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning("🔌 MQTT: Disconnected. Will attempt to reconnect...")
        else:
            logger.info("🔌 MQTT: Disconnected gracefully.")
        
        # Emit disconnection status via WebSocket
        socketio.emit('mqtt_status', {
            'status': 'disconnected',
            'timestamp': datetime.now().isoformat()
        })

    def start(self):
        """Start the MQTT listener in a separate thread"""
        def mqtt_loop():
            try:
                logger.info("🚀 MQTT Listener Starting...")
                self.client.connect(self.broker_host, self.broker_port, 60)
                self.client.loop_forever()  # Blocking loop that listens forever
            except Exception as e:
                logger.error(f"MQTT connection error: {e}")
                self.is_connected = False
        
        mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
        mqtt_thread.start()
        logger.info("MQTT listener thread started")
        return mqtt_thread

    def stop(self):
        """Stop the MQTT listener"""
        try:
            self.client.disconnect()
            logger.info("MQTT listener stopped")
        except Exception as e:
            logger.error(f"Error stopping MQTT listener: {e}")

    def publish_message(self, topic, message):
        """Publish a message to MQTT broker"""
        try:
            if self.is_connected:
                result = self.client.publish(topic, message)
                if result.rc == 0:
                    logger.info(f"📤 MQTT: Successfully published '{message}' to topic '{topic}'")
                    return True
                else:
                    logger.error(f"❌ MQTT: Failed to publish message. Return code: {result.rc}")
                    return False
            else:
                logger.error("❌ MQTT: Cannot publish - not connected to broker")
                return False
        except Exception as e:
            logger.error(f"❌ MQTT: Error publishing message: {e}")
            return False

    def get_status(self):
        """Get MQTT connection status"""
        return {
            'connected': self.is_connected,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port
        }

# Initialize MQTT listener
mqtt_listener = MQTTListener()

# Spam filtering configuration
LOADCELL_SPAM_FILTER = {
    'min_weight_threshold': 0.1,  # Minimum weight to consider (kg)
    'weight_change_threshold': 0.05,  # Minimum change to log new reading (kg)
    'enabled': True  # Enable/disable spam filtering
}

# Temporary storage for MQTT sensor data
mqtt_sensor_data = {
    'loadcell': {
        'weight': None,
        'timestamp': None
    },
    'box_dimensions': {
        'width': None,
        'height': None, 
        'length': None,
        'timestamp': None
    }
}

# QR scan monitoring variables
last_scan_id = 0
sensor_data_loaded = False

def check_for_new_qr_scans():
    """Check for new QR code scans and clear sensor data if valid scan detected"""
    global last_scan_id, sensor_data_loaded
    
    try:
        backend_url = 'http://192.168.100.61:5000/api/qr-scans?limit=1'
        response = requests.get(backend_url, timeout=5)
        
        if response.status_code == 200:
            scans = response.json()
            if scans and len(scans) > 0:
                latest_scan = scans[0]
                scan_id = latest_scan.get('id', 0)
                
                # Check if this is a new scan
                if scan_id > last_scan_id:
                    last_scan_id = scan_id
                    
                    # Log the new scan
                    qr_data = latest_scan.get('qr_data', 'Unknown')
                    is_valid = latest_scan.get('is_valid', False)
                    timestamp = latest_scan.get('timestamp', 'Unknown')
                    
                    logger.info(f"🔍 NEW QR SCAN DETECTED: {qr_data} (Valid: {is_valid})")
                    
                    # If valid scan and we have sensor data loaded, clear it
                    if is_valid and sensor_data_loaded:
                        logger.info("✅ Valid QR scan detected - clearing sensor data...")
                        clear_mqtt_sensor_data()
                        
                        # Emit WebSocket notification
                        socketio.emit('qr_scan_processed', {
                            'qr_data': qr_data,
                            'timestamp': timestamp,
                            'sensor_data_cleared': True
                        })
                        
                        logger.info("🎉 Workflow completed! Ready for next package.")
                    elif not is_valid:
                        logger.info("❌ Invalid QR scan - sensor data remains loaded")
                    elif not sensor_data_loaded:
                        logger.info("ℹ️ QR scan detected but no sensor data to clear")
                        
    except requests.RequestException as e:
        logger.error(f"❌ Error checking for QR scans: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error in QR scan monitoring: {e}")

def clear_mqtt_sensor_data():
    """Clear MQTT sensor data after successful QR scan"""
    global mqtt_sensor_data, sensor_data_loaded
    
    try:
        # Clear local MQTT data
        mqtt_sensor_data['loadcell']['weight'] = None
        mqtt_sensor_data['loadcell']['timestamp'] = None
        mqtt_sensor_data['box_dimensions']['width'] = None
        mqtt_sensor_data['box_dimensions']['height'] = None
        mqtt_sensor_data['box_dimensions']['length'] = None
        mqtt_sensor_data['box_dimensions']['timestamp'] = None
        
        # Clear sensor data from main backend database
        backend_url = 'http://192.168.100.61:5000/api/sensor-data'
        response = requests.delete(backend_url, timeout=5)
        
        if response.status_code == 200:
            logger.info("🗑️ Sensor data cleared from database successfully!")
            sensor_data_loaded = False
        else:
            logger.warning(f"⚠️ Failed to clear sensor data from database: {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"❌ Error clearing sensor data from database: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error clearing sensor data: {e}")

def start_qr_monitoring():
    """Start QR scan monitoring in a background thread"""
    global last_scan_id
    
    # Initialize last_scan_id to current latest scan to avoid processing old scans
    try:
        backend_url = 'http://192.168.100.61:5000/api/qr-scans?limit=1'
        response = requests.get(backend_url, timeout=5)
        if response.status_code == 200:
            scans = response.json()
            if scans and len(scans) > 0:
                last_scan_id = scans[0].get('id', 0)
                logger.info(f"📊 Initialized QR monitoring from scan ID: {last_scan_id}")
    except:
        logger.warning("⚠️ Could not initialize last scan ID - will start from 0")
    
    def monitor_loop():
        logger.info("👀 Starting QR scan monitoring...")
        while True:
            try:
                check_for_new_qr_scans()
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                logger.error(f"❌ Error in QR monitoring loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("✅ QR scan monitoring started in background")

def determine_package_size(width, height, length):
    """Determine package size category based on dimensions"""
    try:
        # Calculate volume in cubic centimeters
        volume = width * height * length
        
        # Calculate max dimension
        max_dimension = max(width, height, length)
        
        # Size classification logic (you can adjust these thresholds)
        if volume <= 1000 or max_dimension <= 15:  # 1000 cm³ or max 15cm
            return "Small"
        elif volume <= 8000 or max_dimension <= 30:  # 8000 cm³ or max 30cm
            return "Medium"
        else:
            return "Large"
            
    except Exception as e:
        logger.error(f"Error determining package size: {e}")
        return "Unknown"

def store_weight_data_in_db():
    """Store ONLY weight data in database (Step 3: Load Sensor captures weight)"""
    global sensor_data_loaded
    
    try:
        # Send only weight data to main backend
        backend_url = 'http://192.168.100.61:5000/api/sensor-data'
        sensor_data = {
            'weight': mqtt_sensor_data['loadcell']['weight'],
            'width': None,  # Dimensions not captured yet
            'height': None,
            'length': None,
            'loadcell_timestamp': mqtt_sensor_data['loadcell']['timestamp'],
            'box_dimensions_timestamp': None
        }
        
        # Only send if we have weight data
        if sensor_data['weight'] is not None:
            response = requests.post(backend_url, json=sensor_data, timeout=5)
            if response.status_code == 200:
                logger.info("✅ STEP 3 COMPLETE: Weight data stored in database")
                sensor_data_loaded = True  # Mark that we have sensor data loaded
                
                weight = sensor_data['weight']
                logger.info(f"📊 Weight captured: {weight}kg - Ready for grabber to move package")
                
                # Emit progress update via WebSocket
                socketio.emit('workflow_progress', {
                    'step': 3,
                    'status': 'completed',
                    'message': f'Weight captured: {weight}kg',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.warning(f"⚠️ Failed to store weight data: {response.status_code}")
        
    except requests.RequestException as e:
        logger.error(f"❌ Error storing weight data in database: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error storing weight data: {e}")

def update_sensor_data_with_dimensions():
    """Update existing weight record with dimensions (Step 5: Size Sensor overrides with complete data)"""
    global sensor_data_loaded
    
    try:
        # Send complete sensor data to main backend (this will overwrite the weight-only entry)
        backend_url = 'http://192.168.100.61:5000/api/sensor-data'
        
        # Determine package size
        width = mqtt_sensor_data['box_dimensions']['width']
        height = mqtt_sensor_data['box_dimensions']['height'] 
        length = mqtt_sensor_data['box_dimensions']['length']
        package_size = determine_package_size(width, height, length)
        
        sensor_data = {
            'weight': mqtt_sensor_data['loadcell']['weight'],
            'width': width,
            'height': height,
            'length': length,
            'package_size': package_size,
            'loadcell_timestamp': mqtt_sensor_data['loadcell']['timestamp'],
            'box_dimensions_timestamp': mqtt_sensor_data['box_dimensions']['timestamp']
        }
        
        # Send complete data (this overwrites the previous weight-only entry)
        response = requests.post(backend_url, json=sensor_data, timeout=5)
        if response.status_code == 200:
            logger.info("✅ STEP 5 COMPLETE: Package data updated with dimensions")
            
            # Log complete package information
            weight = sensor_data['weight'] or 'N/A'
            logger.info(f"📊 COMPLETE PACKAGE DATA: Weight={weight}kg, Dimensions={width}x{height}x{length}cm, Size={package_size}")
            
            # Emit workflow completion via WebSocket
            socketio.emit('workflow_progress', {
                'step': 5,
                'status': 'completed',
                'message': f'Package complete: {weight}kg, {width}x{height}x{length}cm ({package_size})',
                'package_data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
            
        else:
            logger.warning(f"⚠️ Failed to update sensor data with dimensions: {response.status_code}")
        
    except requests.RequestException as e:
        logger.error(f"❌ Error updating sensor data with dimensions: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error updating sensor data: {e}")

def store_sensor_data_in_db():
    """Legacy function - now replaced by step-specific functions"""
    logger.warning("⚠️ Legacy store_sensor_data_in_db() called - use step-specific functions instead")
    
    # For backward compatibility, determine which step we're in
    has_weight = mqtt_sensor_data['loadcell']['weight'] is not None
    has_dimensions = all([
        mqtt_sensor_data['box_dimensions']['width'] is not None,
        mqtt_sensor_data['box_dimensions']['height'] is not None,
        mqtt_sensor_data['box_dimensions']['length'] is not None
    ])
    
    if has_weight and not has_dimensions:
        # Step 3: Only weight available
        store_weight_data_in_db()
    elif has_weight and has_dimensions:
        # Step 5: Both weight and dimensions available
        update_sensor_data_with_dimensions()
    else:
        logger.warning("⚠️ Incomplete sensor data - cannot determine workflow step")

@app.route('/api/clear-sensor-data', methods=['POST'])
def clear_sensor_data():
    """Manually clear stored sensor data"""
    try:
        global mqtt_sensor_data, sensor_data_loaded
        mqtt_sensor_data['loadcell']['weight'] = None
        mqtt_sensor_data['loadcell']['timestamp'] = None
        mqtt_sensor_data['box_dimensions']['width'] = None
        mqtt_sensor_data['box_dimensions']['height'] = None
        mqtt_sensor_data['box_dimensions']['length'] = None
        mqtt_sensor_data['box_dimensions']['timestamp'] = None
        sensor_data_loaded = False  # Mark that sensor data is cleared
        
        # Emit update via WebSocket
        socketio.emit('sensor_data_cleared', {
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("🗑️ Sensor data manually cleared")
        
        return jsonify({
            'message': 'Sensor data cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing sensor data: {str(e)}")
        return jsonify({
            'error': 'Failed to clear sensor data',
            'details': str(e)
        }), 500

@app.route('/api/mqtt-sensor-data')
def get_mqtt_sensor_data():
    """Get current MQTT sensor data"""
    try:
        return jsonify({
            'sensor_data': mqtt_sensor_data,
            'sensor_data_loaded': sensor_data_loaded,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting MQTT sensor data: {str(e)}")
        return jsonify({
            'error': 'Failed to get MQTT sensor data',
            'details': str(e)
        }), 500

@app.route('/api/sensor-status')
def get_sensor_status():
    """Get sensor workflow status"""
    try:
        # Check if we have any sensor data
        has_weight = mqtt_sensor_data['loadcell']['weight'] is not None
        has_dimensions = any([
            mqtt_sensor_data['box_dimensions']['width'] is not None,
            mqtt_sensor_data['box_dimensions']['height'] is not None,
            mqtt_sensor_data['box_dimensions']['length'] is not None
        ])
        
        return jsonify({
            'sensor_data_loaded': sensor_data_loaded,
            'has_weight_data': has_weight,
            'has_dimension_data': has_dimensions,
            'last_scan_id': last_scan_id,
            'current_sensor_data': mqtt_sensor_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting sensor status: {str(e)}")
        return jsonify({
            'error': 'Failed to get sensor status',
            'details': str(e)
        }), 500

@app.route('/api/apply-package-data', methods=['POST'])
def apply_package_data():
    """Apply MQTT sensor data to a scanned QR order"""
    try:
        data = request.get_json()
        order_number = data.get('order_number')
        
        if not order_number:
            return jsonify({'error': 'No order number provided'}), 400
        
        # Validate order exists by calling main backend
        backend_url = 'http://192.168.100.61:5000/api/validate-qr'
        validation_response = requests.post(backend_url, json={'qr_data': order_number}, timeout=10)
        
        if validation_response.status_code != 200:
            return jsonify({
                'error': 'Failed to validate order',
                'details': 'Could not connect to main backend'
            }), 500
        
        validation_data = validation_response.json()
        if not validation_data.get('valid'):
            return jsonify({
                'error': 'Invalid order number',
                'message': validation_data.get('message', 'Order not found')
            }), 400
        
        # Check if we have sensor data
        weight = mqtt_sensor_data['loadcell']['weight']
        dimensions = mqtt_sensor_data['box_dimensions']
        
        if weight is None and all(d is None for d in [dimensions['width'], dimensions['height'], dimensions['length']]):
            return jsonify({
                'error': 'No sensor data available',
                'message': 'Please ensure loadcell and box dimension sensors have provided data'
            }), 400
        
        # Apply package data to main backend
        package_data = {
            'order_number': order_number,
            'order_id': validation_data['order_id'],
            'weight': weight,
            'width': dimensions['width'],
            'height': dimensions['height'],
            'length': dimensions['length'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Send package data to main backend
        backend_package_url = 'http://192.168.100.61:5000/api/package-information'
        package_response = requests.post(backend_package_url, json=package_data, timeout=10)
        
        if package_response.status_code == 200 or package_response.status_code == 201:
            # Clear sensor data after successful application
            mqtt_sensor_data['loadcell']['weight'] = None
            mqtt_sensor_data['loadcell']['timestamp'] = None
            mqtt_sensor_data['box_dimensions']['width'] = None
            mqtt_sensor_data['box_dimensions']['height'] = None
            mqtt_sensor_data['box_dimensions']['length'] = None
            mqtt_sensor_data['box_dimensions']['timestamp'] = None
            
            # Emit update via WebSocket
            socketio.emit('package_data_applied', {
                'order_number': order_number,
                'package_data': package_data,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'message': 'Package data applied successfully',
                'order_number': order_number,
                'package_data': package_data
            })
        else:
            return jsonify({
                'error': 'Failed to apply package data',
                'details': 'Backend service error'
            }), 500
            
    except requests.RequestException as e:
        logger.error(f"Error connecting to main backend: {e}")
        return jsonify({
            'error': 'Connection to main backend failed',
            'details': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error applying package data: {e}")
        return jsonify({
            'error': 'Failed to apply package data',
            'details': str(e)
        }), 500

@app.route('/status')
def status():
    """General status endpoint"""
    try:
        printer_status = "available" if printer.check_printer() else "unavailable"
        camera_status = camera.get_status()
        mqtt_status = mqtt_listener.get_status()
        return jsonify({
            "status": "running",
            "printer": printer_status,
            "camera": camera_status,
            "mqtt": mqtt_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/mqtt/status')
def mqtt_status():
    """Get MQTT listener status"""
    try:
        status = mqtt_listener.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting MQTT status: {str(e)}")
        return jsonify({
            'error': 'Failed to get MQTT status',
            'details': str(e)
        }), 500

@app.route('/mqtt/restart', methods=['POST'])
def restart_mqtt():
    """Restart MQTT listener"""
    try:
        mqtt_listener.stop()
        time.sleep(1)  # Wait a moment before restarting
        mqtt_listener.start()
        return jsonify({
            'message': 'MQTT listener restarted',
            'status': mqtt_listener.get_status()
        })
    except Exception as e:
        logger.error(f"Error restarting MQTT listener: {str(e)}")
        return jsonify({
            'error': 'Failed to restart MQTT listener',
            'details': str(e)
        }), 500

@app.route('/api/start-motor', methods=['POST'])
def start_motor():
    """Start motor by sending MQTT command to ESP32"""
    try:
        logger.info("🚀 Start motor request received")
        
        # Check if MQTT is connected
        if not mqtt_listener.is_connected:
            logger.warning("❌ MQTT not connected - cannot start motor")
            return jsonify({
                'error': 'MQTT not connected',
                'message': 'Cannot start motor - MQTT broker not connected'
            }), 503
        
        logger.info("✅ MQTT is connected, sending start command...")
        
        # Publish start command to ESP32
        success = mqtt_listener.publish_message('esp32/motor/request', 'start')
        
        if success:
            logger.info("🚀 Motor started via MQTT command")
            # Emit WebSocket notification
            socketio.emit('system_command', {
                'command': 'start_motor',
                'status': 'success',
                'message': 'Motor started',
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': 'Motor started successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error("❌ Failed to publish start command to MQTT")
            return jsonify({
                'error': 'Failed to send MQTT command',
                'message': 'Could not publish start command to ESP32'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting motor: {str(e)}")
        return jsonify({
            'error': 'Failed to start motor',
            'details': str(e)
        }), 500

@app.route('/api/stop-motor', methods=['POST'])
def stop_motor():
    """Stop motor by sending MQTT command to ESP32"""
    try:
        logger.info("🛑 Stop motor request received")
        
        # Check if MQTT is connected
        if not mqtt_listener.is_connected:
            logger.warning("❌ MQTT not connected - cannot stop motor")
            return jsonify({
                'error': 'MQTT not connected',
                'message': 'Cannot stop motor - MQTT broker not connected'
            }), 503
        
        logger.info("✅ MQTT is connected, sending stop command...")
        
        # Publish stop command to ESP32
        success = mqtt_listener.publish_message('esp32/motor/request', 'stop')
        
        if success:
            logger.info("🛑 Motor stopped via MQTT command")
            # Emit WebSocket notification
            socketio.emit('system_command', {
                'command': 'stop_motor',
                'status': 'success',
                'message': 'Motor stopped',
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': 'Motor stopped successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error("❌ Failed to publish stop command to MQTT")
            return jsonify({
                'error': 'Failed to send MQTT command',
                'message': 'Could not publish stop command to ESP32'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping motor: {str(e)}")
        return jsonify({
            'error': 'Failed to stop motor',
            'details': str(e)
        }), 500

@app.route('/api/motor-status', methods=['GET'])
def get_motor_status():
    """Get current motor control status and MQTT connectivity"""
    try:
        mqtt_status = mqtt_listener.get_status()
        
        return jsonify({
            'motor_control': {
                'mqtt_connected': mqtt_listener.is_connected,
                'mqtt_broker': mqtt_listener.broker_host,
                'mqtt_port': mqtt_listener.broker_port,
                'can_send_commands': mqtt_listener.is_connected
            },
            'mqtt_details': mqtt_status,
            'endpoints': {
                'start_motor': '/api/start-motor',
                'stop_motor': '/api/stop-motor'
            },
            'mqtt_topics': {
                'motor_request': 'esp32/motor/request',
                'motor_status': 'esp32/motor/status'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting motor status: {str(e)}")
        return jsonify({
            'error': 'Failed to get motor status',
            'details': str(e)
        }), 500

@app.route('/api/spam-filter', methods=['GET'])
def get_spam_filter_config():
    """Get current spam filter configuration"""
    return jsonify({
        'spam_filter': LOADCELL_SPAM_FILTER,
        'description': {
            'min_weight_threshold': 'Minimum weight to consider (kg)',
            'weight_change_threshold': 'Minimum change to log new reading (kg)',
            'enabled': 'Enable/disable spam filtering'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/spam-filter', methods=['POST'])
def update_spam_filter_config():
    """Update spam filter configuration"""
    try:
        global LOADCELL_SPAM_FILTER
        data = request.get_json()
        
        # Update configuration with provided values
        if 'min_weight_threshold' in data:
            LOADCELL_SPAM_FILTER['min_weight_threshold'] = float(data['min_weight_threshold'])
        
        if 'weight_change_threshold' in data:
            LOADCELL_SPAM_FILTER['weight_change_threshold'] = float(data['weight_change_threshold'])
        
        if 'enabled' in data:
            LOADCELL_SPAM_FILTER['enabled'] = bool(data['enabled'])
        
        logger.info(f"🔧 Spam filter configuration updated: {LOADCELL_SPAM_FILTER}")
        
        return jsonify({
            'success': True,
            'message': 'Spam filter configuration updated',
            'new_config': LOADCELL_SPAM_FILTER,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating spam filter config: {str(e)}")
        return jsonify({
            'error': 'Failed to update spam filter configuration',
            'details': str(e)
        }), 500
def after_request(response):
    """Ensure CORS headers are set"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/')
def home():
    """Health check endpoint"""
    printer_status = "available" if printer.check_printer() else "unavailable"
    camera_status = camera.get_status()
    mqtt_status = mqtt_listener.get_status()
    return jsonify({
        "status": "running",
        "printer": printer_status,
        "camera": camera_status,
        "mqtt": mqtt_status
    })

@app.route('/print-qr', methods=['POST'])
def print_qr():
    try:
        # Get order data from request
        order_data = request.get_json()
        
        if not order_data:
            logger.warning("Print request received with no data")
            return jsonify({
                'error': 'No order data provided'
            }), 400

        logger.info(f"Print request received for order: {order_data.get('orderNumber', 'Unknown')}")

        # Check if printer is available
        if not printer.check_printer():
            logger.error("Printer is not available")
            return jsonify({
                'error': 'Printer is not available',
                'details': 'Please check printer connection and USB cable'
            }), 503

        # Required fields check (made more flexible)
        required_fields = ['orderNumber', 'customerName', 'productName', 'amount', 'date']
        missing_fields = [field for field in required_fields if not order_data.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'received_data': list(order_data.keys())
            }), 400

        # Validate and sanitize data
        try:
            sanitized_data = {
                'orderNumber': str(order_data['orderNumber']).strip(),
                'customerName': str(order_data['customerName']).strip(),
                'productName': str(order_data['productName']).strip(),
                'amount': str(order_data['amount']).strip(),
                'date': str(order_data['date']).strip(),
                'address': str(order_data.get('address', 'N/A')).strip(),
                'contactNumber': str(order_data.get('contactNumber', 'N/A')).strip(),
                'email': str(order_data.get('email', '')).strip()
            }
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return jsonify({
                'error': 'Invalid data format',
                'details': str(e)
            }), 400

        # Create receipt image
        receipt = printer.create_receipt(sanitized_data)
        
        if not receipt:
            logger.error("Failed to create receipt image")
            return jsonify({
                'error': 'Failed to create receipt',
                'details': 'Receipt generation failed'
            }), 500

        # Print receipt
        success, message = printer.print_receipt(receipt)
        
        if success:
            logger.info(f"Successfully printed receipt for order {sanitized_data['orderNumber']}")
            return jsonify({
                'message': 'Receipt printed successfully',
                'order_number': sanitized_data['orderNumber'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"Failed to print receipt: {message}")
            return jsonify({
                'error': 'Failed to print receipt',
                'details': message
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error processing print request: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def generate_frames():
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera/start', methods=['POST'])
def start_camera():
    """Start the camera"""
    try:
        if camera.start_camera():
            logger.info("Camera started successfully")
            return jsonify({
                'message': 'Camera started successfully',
                'status': camera.get_status()
            })
        else:
            return jsonify({
                'error': 'Camera is already running'
            }), 400
    except Exception as e:
        logger.error(f"Error starting camera: {str(e)}")
        return jsonify({
            'error': 'Failed to start camera',
            'details': str(e)
        }), 500

@app.route('/camera/stop', methods=['POST'])
def stop_camera():
    """Stop the camera"""
    try:
        if camera.stop_camera():
            logger.info("Camera stopped successfully")
            return jsonify({
                'message': 'Camera stopped successfully',
                'status': camera.get_status()
            })
        else:
            return jsonify({
                'error': 'Failed to stop camera'
            }), 500
    except Exception as e:
        logger.error(f"Error stopping camera: {str(e)}")
        return jsonify({
            'error': 'Failed to stop camera',
            'details': str(e)
        }), 500

@app.route('/camera/status')
def camera_status():
    """Get camera status"""
    try:
        status = camera.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting camera status: {str(e)}")
        return jsonify({
            'error': 'Failed to get camera status',
            'details': str(e)
        }), 500

@app.route('/camera/last-qr')
def get_last_qr():
    """Get the last scanned QR code"""
    try:
        last_qr = camera.get_last_qr()
        return jsonify({
            'last_qr_data': last_qr
        })
    except Exception as e:
        logger.error(f"Error getting last QR code: {str(e)}")
        return jsonify({
            'error': 'Failed to get last QR code',
            'details': str(e)
        }), 500

@app.route('/camera/qr-history')
def get_qr_history():
    """Get the history of scanned QR codes"""
    try:
        history = camera.get_qr_history()
        return jsonify({
            'qr_history': history
        })
    except Exception as e:
        logger.error(f"Error getting QR history: {str(e)}")
        return jsonify({
            'error': 'Failed to get QR history',
            'details': str(e)
        }), 500

@app.route('/camera/duplicate-prevention/status')
def get_duplicate_prevention_status():
    """Get duplicate prevention status and scanned QR codes"""
    try:
        status = camera.get_duplicate_prevention_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting duplicate prevention status: {str(e)}")
        return jsonify({
            'error': 'Failed to get duplicate prevention status',
            'details': str(e)
        }), 500

@app.route('/camera/duplicate-prevention/toggle', methods=['POST'])
def toggle_duplicate_prevention():
    """Enable or disable duplicate prevention"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        camera.set_duplicate_prevention(enabled)
        return jsonify({
            'success': True,
            'duplicate_prevention_enabled': enabled,
            'message': f'Duplicate prevention {"enabled" if enabled else "disabled"}'
        })
    except Exception as e:
        logger.error(f"Error toggling duplicate prevention: {str(e)}")
        return jsonify({
            'error': 'Failed to toggle duplicate prevention',
            'details': str(e)
        }), 500

@app.route('/camera/duplicate-prevention/clear-all', methods=['POST'])
def clear_all_scanned_qr():
    """Clear all scanned QR codes to allow rescanning"""
    try:
        count = camera.clear_all_scanned_qr_codes()
        return jsonify({
            'success': True,
            'cleared_count': count,
            'message': f'Cleared {count} scanned QR codes'
        })
    except Exception as e:
        logger.error(f"Error clearing scanned QR codes: {str(e)}")
        return jsonify({
            'error': 'Failed to clear scanned QR codes',
            'details': str(e)
        }), 500

@app.route('/camera/duplicate-prevention/clear-qr', methods=['POST'])
def clear_specific_qr():
    """Clear a specific QR code to allow rescanning"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return jsonify({'error': 'No QR data provided'}), 400
            
        success = camera.clear_scanned_qr(qr_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'QR code "{qr_data}" cleared for rescanning'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'QR code "{qr_data}" was not in scanned list'
            })
            
    except Exception as e:
        logger.error(f"Error clearing specific QR code: {str(e)}")
        return jsonify({
            'error': 'Failed to clear QR code',
            'details': str(e)
        }), 500

@app.route('/camera/duplicate-prevention/scanned-codes')
def get_scanned_qr_codes():
    """Get list of all scanned QR codes"""
    try:
        scanned_codes = camera.get_scanned_qr_codes()
        return jsonify({
            'scanned_codes': scanned_codes,
            'count': len(scanned_codes)
        })
    except Exception as e:
        logger.error(f"Error getting scanned QR codes: {str(e)}")
        return jsonify({
            'error': 'Failed to get scanned QR codes',
            'details': str(e)
        }), 500

@app.route('/camera/scanning-status')
def get_scanning_status():
    """Get current QR scanning delay status"""
    try:
        status = camera.get_scanning_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting scanning status: {str(e)}")
        return jsonify({
            'error': 'Failed to get scanning status',
            'details': str(e)
        }), 500

@app.route('/camera/reset-cycle', methods=['POST'])
def reset_scan_cycle():
    """Reset the scanning cycle (countdown + scanning session)"""
    try:
        # Use the new method that works even when camera is running
        success = camera.reset_scan_cycle_if_running()
        status = camera.get_scanning_status()
        
        if success:
            return jsonify({
                'message': 'Scanning cycle reset successfully (camera was running)',
                'status': status
            })
        else:
            # If camera is not running, try regular reset
            camera.reset_scan_cycle()
            status = camera.get_scanning_status()
            return jsonify({
                'message': 'Scanning cycle reset successfully (camera was not running)',
                'status': status
            })
    except Exception as e:
        logger.error(f"Error resetting scan cycle: {str(e)}")
        return jsonify({
            'error': 'Failed to reset scanning cycle',
            'details': str(e)
        }), 500

@app.route('/camera/start-session', methods=['POST'])
def start_scanning_session_immediately():
    """Start scanning session immediately, skipping countdown"""
    try:
        camera.start_scanning_session_immediately()
        status = camera.get_scanning_status()
        return jsonify({
            'message': 'Scanning session started immediately',
            'status': status
        })
    except Exception as e:
        logger.error(f"Error starting scanning session: {str(e)}")
        return jsonify({
            'error': 'Failed to start scanning session immediately',
            'details': str(e)
        }), 500

@app.route('/camera/session-start', methods=['POST'])
def handle_session_start():
    """Handle when a new session/page load occurs - reset scanning delay"""
    try:
        # Always reset the delay when a new session starts
        if camera.running:
            success = camera.reset_scan_delay_if_running()
            status = camera.get_scanning_status()
            return jsonify({
                'message': 'New session started - scanning delay reset',
                'camera_running': True,
                'delay_reset': success,
                'status': status
            })
        else:
            # Camera is not running, just return status
            return jsonify({
                'message': 'New session started - camera not running',
                'camera_running': False,
                'delay_reset': False,
                'status': {'enabled': False, 'time_remaining': 0}
            })
    except Exception as e:
        logger.error(f"Error handling session start: {str(e)}")
        return jsonify({
            'error': 'Failed to handle session start',
            'details': str(e)
        }), 500

@app.route('/api/validate-qr', methods=['POST'])
def validate_qr():
    """Validate QR code by forwarding to main backend"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return jsonify({'valid': False, 'message': 'No QR data provided'}), 400
        
        # Forward the validation request to the main backend server
        backend_url = 'http://192.168.100.61:5000/api/validate-qr'
        response = requests.post(backend_url, json={'qr_data': qr_data}, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({
                'valid': False,
                'message': f'Backend validation failed: {response.status_code}'
            }), 200
            
    except requests.RequestException as e:
        logger.error(f"Error connecting to main backend: {e}")
        return jsonify({
            'valid': False,
            'message': f'Connection to main backend failed: {str(e)}'
        }), 200
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }), 500

# QR detection callback
def on_qr_detected(qr_data, validation_result):
    """Callback function called when new QR is detected"""
    try:
        # Get the latest history to include image data
        history = camera.get_qr_history()
        latest_scan = history[0] if history else None
        
        # If QR is valid and we have sensor data, automatically apply package data
        if validation_result.get('valid') and validation_result.get('order_id'):
            weight = mqtt_sensor_data['loadcell']['weight']
            dimensions = mqtt_sensor_data['box_dimensions']
            
            # Check if we have any sensor data to apply
            if weight is not None or any(d is not None for d in [dimensions['width'], dimensions['height'], dimensions['length']]):
                try:
                    # Apply package data automatically
                    package_data = {
                        'order_number': qr_data,
                        'order_id': validation_result['order_id'],
                        'weight': weight,
                        'width': dimensions['width'],
                        'height': dimensions['height'],
                        'length': dimensions['length'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Send package data to main backend
                    backend_package_url = 'http://192.168.100.61:5000/api/package-information'
                    package_response = requests.post(backend_package_url, json=package_data, timeout=10)
                    
                    if package_response.status_code in [200, 201]:
                        # Clear sensor data after successful application
                        mqtt_sensor_data['loadcell']['weight'] = None
                        mqtt_sensor_data['loadcell']['timestamp'] = None
                        mqtt_sensor_data['box_dimensions']['width'] = None
                        mqtt_sensor_data['box_dimensions']['height'] = None
                        mqtt_sensor_data['box_dimensions']['length'] = None
                        mqtt_sensor_data['box_dimensions']['timestamp'] = None
                        
                        logger.info(f"✅ Automatically applied package data for order {qr_data}: W:{weight}, D:{dimensions['width']}x{dimensions['height']}x{dimensions['length']}")
                        
                        # Add package data to validation result for emission
                        validation_result['package_data_applied'] = True
                        validation_result['package_data'] = package_data
                    else:
                        logger.warning(f"⚠️ Failed to apply package data for order {qr_data}: {package_response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ Error auto-applying package data for {qr_data}: {e}")
            else:
                logger.info(f"ℹ️ No sensor data available to apply for order {qr_data}")
        
        socketio.emit('qr_detected', {
            'data': qr_data,
            'timestamp': datetime.now().isoformat(),
            'type': 'QR Code',
            'validation': validation_result,
            'latest_scan': latest_scan,
            'sensor_data': mqtt_sensor_data.copy()  # Include current sensor data
        })
        
        # Emit updated history for real-time updates
        socketio.emit('qr_history_updated', {
            'history': history[:10]  # Send only the latest 10 entries
        })
        
        logger.info(f"Broadcasted QR detection via WebSocket: {qr_data}")
    except Exception as e:
        logger.error(f"Error broadcasting QR detection: {e}")

def periodic_status_broadcast():
    """Periodically broadcast system status"""
    while True:
        try:
            socketio.emit('system_status', {
                'camera_system': camera.get_status(),
                'mqtt_system': mqtt_listener.get_status(),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Status broadcast error: {e}")
        
        time.sleep(5)  # Broadcast status every 5 seconds

# SocketIO event handlers with better error handling
@socketio.on('connect')
def handle_connect():
    try:
        logger.info('Client connected to Raspberry Pi WebSocket')
        emit('camera_status', {'status': 'connected'})
    except Exception as e:
        logger.error(f"Error in connect handler: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    try:
        logger.info('Client disconnected from Raspberry Pi WebSocket')
    except Exception as e:
        logger.error(f"Error in disconnect handler: {e}")

@socketio.on('start_camera')
def handle_start_camera():
    try:
        if camera.start_camera():
            emit('camera_status', {'status': 'started'})
        else:
            emit('camera_error', {'error': 'Failed to start camera'})
    except Exception as e:
        logger.error(f"Error in start_camera handler: {e}")
        emit('camera_error', {'error': str(e)})

@socketio.on('stop_camera')
def handle_stop_camera():
    try:
        if camera.stop_camera():
            emit('camera_status', {'status': 'stopped'})
        else:
            emit('camera_error', {'error': 'Failed to stop camera'})
    except Exception as e:
        logger.error(f"Error in stop_camera handler: {e}")
        emit('camera_error', {'error': str(e)})

@socketio.on('get_system_status')
def handle_get_system_status():
    try:
        emit('system_status', {
            'camera_system': camera.get_status(),
            'mqtt_system': mqtt_listener.get_status(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in get_system_status handler: {e}")
        emit('camera_error', {'error': str(e)})

@socketio.on('get_mqtt_status')
def handle_get_mqtt_status():
    try:
        emit('mqtt_status', mqtt_listener.get_status())
    except Exception as e:
        logger.error(f"Error in get_mqtt_status handler: {e}")
        emit('mqtt_error', {'error': str(e)})

@socketio.on('restart_mqtt')
def handle_restart_mqtt():
    try:
        mqtt_listener.stop()
        time.sleep(1)
        mqtt_listener.start()
        emit('mqtt_status', {
            'status': 'restarted',
            'details': mqtt_listener.get_status()
        })
    except Exception as e:
        emit('mqtt_error', {'error': str(e)})

@socketio.on('print_qr')
def handle_print_qr(data):
    """WebSocket handler for QR printing - better for slow connections"""
    try:
        logger.info(f"WebSocket print request received for order: {data.get('orderNumber', 'Unknown')}")
        
        # Emit progress status
        emit('print_status', {
            'status': 'processing',
            'message': 'Processing print request...',
            'order_number': data.get('orderNumber')
        })

        # Validate input data
        if not data:
            emit('print_error', {
                'error': 'No order data provided',
                'order_number': data.get('orderNumber')
            })
            return

        # Check if printer is available
        if not printer.check_printer():
            logger.error("Printer is not available")
            emit('print_error', {
                'error': 'Printer is not available',
                'details': 'Please check printer connection and USB cable',
                'order_number': data.get('orderNumber')
            })
            return

        # Required fields check
        required_fields = ['orderNumber', 'customerName', 'productName', 'amount', 'date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            emit('print_error', {
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'received_data': list(data.keys()),
                'order_number': data.get('orderNumber')
            })
            return

        # Emit progress status
        emit('print_status', {
            'status': 'creating',
            'message': 'Creating receipt image...',
            'order_number': data.get('orderNumber')
        })

        # Validate and sanitize data
        try:
            sanitized_data = {
                'orderNumber': str(data['orderNumber']).strip(),
                'customerName': str(data['customerName']).strip(),
                'productName': str(data['productName']).strip(),
                'amount': str(data['amount']).strip(),
                'date': str(data['date']).strip(),
                'address': str(data.get('address', 'N/A')).strip(),
                'contactNumber': str(data.get('contactNumber', 'N/A')).strip(),
                'email': str(data.get('email', '')).strip()
            }
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            emit('print_error', {
                'error': 'Invalid data format',
                'details': str(e),
                'order_number': data.get('orderNumber')
            })
            return

        # Create receipt image
        receipt = printer.create_receipt(sanitized_data)
        
        if not receipt:
            logger.error("Failed to create receipt image")
            emit('print_error', {
                'error': 'Failed to create receipt',
                'details': 'Receipt generation failed',
                'order_number': data.get('orderNumber')
            })
            return

        # Emit progress status
        emit('print_status', {
            'status': 'printing',
            'message': 'Sending to printer...',
            'order_number': data.get('orderNumber')
        })

        # Print receipt
        success, message = printer.print_receipt(receipt)
        
        if success:
            logger.info(f"Successfully printed receipt for order {sanitized_data['orderNumber']}")
            emit('print_success', {
                'message': 'Receipt printed successfully',
                'order_number': sanitized_data['orderNumber'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"Failed to print receipt: {message}")
            emit('print_error', {
                'error': 'Failed to print receipt',
                'details': message,
                'order_number': data.get('orderNumber')
            })

    except Exception as e:
        logger.error(f"Unexpected error in WebSocket print request: {str(e)}", exc_info=True)
        emit('print_error', {
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.now().isoformat(),
            'order_number': data.get('orderNumber') if data else 'Unknown'
        })

@socketio.on('check_printer_status')
def handle_check_printer_status():
    """WebSocket handler to check printer status"""
    try:
        is_available = printer.check_printer()
        emit('printer_status', {
            'available': is_available,
            'device': printer.printer_device,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking printer status: {e}")
        emit('printer_status', {
            'available': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/debug/test-mqtt', methods=['POST'])
def test_mqtt():
    """Debug endpoint to simulate MQTT sensor data messages"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        message = data.get('message')
        
        if not topic or not message:
            return jsonify({'error': 'Both topic and message are required'}), 400
        
        # Simulate the MQTT message processing by calling the on_message method directly
        class MockMsg:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload.encode('utf-8')
        
        # Create a mock message and process it
        mock_msg = MockMsg(topic, message)
        mqtt_listener.on_message(None, None, mock_msg)
        
        return jsonify({
            'message': f'Test MQTT message processed for topic {topic}',
            'topic': topic,
            'data': message,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing test MQTT message: {e}")
        return jsonify({
            'error': 'Failed to process test MQTT message',
            'details': str(e)
        }), 500

@app.route('/debug/test-mqtt-message', methods=['POST'])
def test_mqtt_message():
    """Debug endpoint to test MQTT message emission"""
    try:
        data = request.get_json()
        test_message = data.get('message', 'W: 2.27 in, L: 4.22 in, H: 1.59 in → 📦 Small')
        test_topic = data.get('topic', 'esp32/box/result')
        
        # Create the same message structure as the real MQTT listener
        mqtt_data = {
            'topic': test_topic,
            'message': test_message,
            'timestamp': datetime.now().isoformat(),
            'raw_timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        logger.info(f"📨 TEST MQTT [{mqtt_data['raw_timestamp']}] {test_topic} > {test_message}")
        logger.info(f"Emitting test MQTT message via WebSocket: {mqtt_data}")
        
        # Emit the message just like the real MQTT listener would
        socketio.emit('mqtt_message', mqtt_data)
        
        return jsonify({
            'message': 'Test MQTT message sent',
            'data': mqtt_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending test MQTT message: {e}")
        return jsonify({
            'error': 'Failed to send test MQTT message',
            'details': str(e)
        }), 500

@app.route('/debug/simulate-qr-scan', methods=['POST'])
def simulate_qr_scan():
    """Debug endpoint to simulate a QR code scan"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', 'ORD-001')
        
        # Validate the QR code using the same method as camera
        backend_url = 'http://192.168.100.61:5000/api/validate-qr'
        validation_response = requests.post(backend_url, json={'qr_data': qr_code}, timeout=10)
        
        if validation_response.status_code == 200:
            validation_data = validation_response.json()
        else:
            validation_data = {'valid': False, 'message': 'Validation failed'}
        
        # Create a mock scan entry
        scan_entry = {
            'qr_data': qr_code,
            'timestamp': datetime.now().isoformat(),
            'validation': validation_data,
            'device': 'debug_simulation'
        }
        
        # Add to camera history if available
        if camera:
            # Create mock image data for simulation
            mock_image_data = {
                'filename': f'simulated_qr_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg',
                'filepath': None,
                'base64': None  # Could generate a mock QR image here if needed
            }
            camera.add_to_qr_history(qr_code, validation_data, mock_image_data)
        
        # Emit via WebSocket
        socketio.emit('qr_detected', {
            'data': qr_code,
            'timestamp': datetime.now().isoformat(),
            'type': 'QR Code (Simulated)',
            'validation': validation_data
        })
        
        return jsonify({
            'message': f'Simulated QR scan for {qr_code}',
            'scan_entry': scan_entry
        }), 200
        
    except Exception as e:
        logger.error(f"Error simulating QR scan: {e}")
        return jsonify({
            'error': 'Failed to simulate QR scan',
            'details': str(e)
        }), 500

@app.route('/camera/qr-image/<filename>')
def get_qr_image(filename):
    """Serve QR code images"""
    try:
        from flask import send_from_directory
        qr_images_dir = os.path.join(os.getcwd(), 'qr_images')
        return send_from_directory(qr_images_dir, filename)
    except Exception as e:
        logger.error(f"Error serving QR image {filename}: {str(e)}")
        return jsonify({
            'error': 'Failed to get QR image',
            'details': str(e)
        }), 500

@app.route('/debug/test-qr-image', methods=['POST'])
def test_qr_image():
    """Debug endpoint to test QR image generation"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', 'ORD-001')
        
        # Create a simple test image with the QR code text
        import numpy as np
        import cv2
        import base64
        
        # Create a test image
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img.fill(255)  # White background
        
        # Add text to simulate QR code
        cv2.putText(img, qr_code, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, "TEST QR", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Validate the QR code
        backend_url = 'http://192.168.100.61:5000/api/validate-qr'
        try:
            validation_response = requests.post(backend_url, json={'qr_data': qr_code}, timeout=10)
            if validation_response.status_code == 200:
                validation_data = validation_response.json()
            else:
                validation_data = {'valid': False, 'message': 'Validation failed'}
        except:
            validation_data = {'valid': False, 'message': 'Backend unavailable'}
        
        # Create test image data
        test_image_data = {
            'filename': f'test_qr_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg',
            'filepath': None,
            'base64': img_base64
        }
        
        # Add to camera history if available
        if camera:
            camera.add_to_qr_history(qr_code, validation_data, test_image_data)
        
        # Emit via WebSocket
        socketio.emit('qr_detected', {
            'data': qr_code,
            'timestamp': datetime.now().isoformat(),
            'type': 'QR Code (Test)',
            'validation': validation_data
        })
        
        # Get updated history and emit
        if camera:
            history = camera.get_qr_history()
            socketio.emit('qr_history_updated', {
                'history': history[:10]
            })
        
        return jsonify({
            'message': f'Test QR image created for {qr_code}',
            'image_data': test_image_data,
            'validation': validation_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating test QR image: {e}")
        return jsonify({
            'error': 'Failed to create test QR image',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    # Check printer availability at startup
    if printer.check_printer():
        logger.info("Printer is available")
    else:
        logger.warning("Printer is not available - please check connection")
    
    # Register QR detection callback
    camera.add_qr_callback(on_qr_detected)
    logger.info("QR detection callback registered")
    
    # Auto-start the camera at startup
    try:
        if camera.start_camera():
            logger.info("Camera auto-started at startup")
        else:
            logger.warning("Camera failed to auto-start at startup")
    except Exception as e:
        logger.warning(f"Failed to auto-start camera at startup: {str(e)}")
    
    # Start periodic status broadcast thread
    status_thread = threading.Thread(target=periodic_status_broadcast, daemon=True)
    status_thread.start()
    logger.info("Status broadcast thread started")
    
    # Start MQTT listener at startup
    try:
        mqtt_listener.start()
        logger.info("MQTT listener started at startup")
    except Exception as e:
        logger.error(f"Failed to start MQTT listener at startup: {str(e)}")
    
    # Start QR scan monitoring
    try:
        start_qr_monitoring()
        logger.info("QR scan monitoring started at startup")
    except Exception as e:
        logger.error(f"Failed to start QR scan monitoring at startup: {str(e)}")
    
    # Run the server with SocketIO - simplified configuration
    logger.info("Starting Flask-SocketIO server with integrated MQTT listener and QR monitoring")
    
    # Simple SocketIO startup to avoid Werkzeug conflicts
    socketio.run(app, 
                host='0.0.0.0', 
                port=5001, 
                debug=False)
