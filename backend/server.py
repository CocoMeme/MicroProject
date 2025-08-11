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
import os
import re
import sqlite3
import pygame
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize pygame mixer for alarm sounds
try:
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Pygame mixer initialized for alarm sounds")
except Exception as e:
    PYGAME_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Pygame mixer not available: {e}")

# Database helper function
def dict_factory(cursor, row):
    """Convert sqlite row to dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# Configure logging with improved format and separate levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set specific log levels for different components
logging.getLogger('paho').setLevel(logging.WARNING)  # Reduce MQTT client verbosity
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask verbosity

# Suppress ZBar decoder warnings
import sys
import warnings

# Suppress ZBar warnings at the Python level
warnings.filterwarnings("ignore", message=".*zbar.*")
warnings.filterwarnings("ignore", message=".*databar.*")

# Filter ZBar warnings from stderr output
class StderrFilter:
    def __init__(self):
        self.original_stderr = sys.stderr
        
    def write(self, s):
        # Filter out ZBar decoder warnings
        if '_zbar_decode_databar: Assertion' not in s and 'decoder/databar.c' not in s and 'WARNING: decoder/databar.c' not in s:
            self.original_stderr.write(s)
            
    def flush(self):
        self.original_stderr.flush()

# Apply stderr filter to suppress ZBar C library warnings
sys.stderr = StderrFilter()

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

# Global state variables for Motor B and IR B cycle control
motor_b_cycle_state = {
    'ir_b_enabled': False,          # Whether IR B detection is currently enabled
    'motor_b_first_run': False,     # Whether Motor B has completed its first run after grabber2
    'motor_b_second_run': False,    # Whether Motor B has completed its second run after QR validation
    'cycle_complete': False,        # Whether the full cycle is complete
    'grabber2_completed': False,    # Whether grabber2 has completed
    'qr_validated': False          # Whether QR validation has occurred
}

# Alarm cooldown system to prevent spam
alarm_cooldown = {
    'last_alarm_time': None,
    'cooldown_duration': 15  # 15 seconds cooldown between alarms
}

def reset_motor_b_cycle():
    """Reset the Motor B and IR B cycle state for a new cycle"""
    global motor_b_cycle_state
    logger.info("🔄 CYCLE RESET: Resetting Motor B and IR B cycle state for new process")
    motor_b_cycle_state = {
        'ir_b_enabled': False,
        'motor_b_first_run': False,
        'motor_b_second_run': False,
        'cycle_complete': False,
        'grabber2_completed': False,
        'qr_validated': False
    }

def play_alarm_sound():
    """Play alarm sound when metallic item is detected with cooldown to prevent spam"""
    global alarm_cooldown
    current_time = time.time()
    
    # Check if we're still in cooldown period
    if (alarm_cooldown['last_alarm_time'] is not None and 
        current_time - alarm_cooldown['last_alarm_time'] < alarm_cooldown['cooldown_duration']):
        
        remaining_time = alarm_cooldown['cooldown_duration'] - (current_time - alarm_cooldown['last_alarm_time'])
        logger.info(f"🔇 ALARM COOLDOWN: Metallic item detected but alarm in cooldown ({remaining_time:.1f}s remaining)")
        return False  # Return False to indicate alarm was not played due to cooldown
    
    def play_sound():
        try:
            if PYGAME_AVAILABLE and pygame.mixer.get_init():
                # Path to alarm sound on Raspberry Pi
                alarm_path = "/sound/alarm.mp3"
                if os.path.exists(alarm_path):
                    sound = pygame.mixer.Sound(alarm_path)
                    sound.play()
                    logger.info("🚨 ALARM: Metallic item detected - Alarm sound played")
                else:
                    logger.warning(f"⚠️ ALARM: Sound file not found: {alarm_path}")
            else:
                logger.warning("⚠️ ALARM: Pygame mixer not available")
        except Exception as e:
            logger.error(f"❌ ALARM: Failed to play alarm sound: {e}")
    
    # Update last alarm time
    alarm_cooldown['last_alarm_time'] = current_time
    
    # Play alarm sound in background thread to avoid blocking
    threading.Thread(target=play_sound, daemon=True).start()
    return True  # Return True to indicate alarm was played
    logger.info("✅ CYCLE RESET: Motor B and IR B cycle state reset complete")

# MQTT Listener Class
class MQTTListener:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        # Generate unique client ID for server to avoid conflicts
        import uuid
        server_client_id = f"server_{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=server_client_id, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT: Connected to broker successfully")
            self.is_connected = True
            client.subscribe("esp32/#")  # Subscribe to all ESP32-related topics
            # Emit connection status via WebSocket
            socketio.emit('mqtt_status', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"MQTT: Connection failed with code {rc}")
            self.is_connected = False

    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        try:
            message = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            message = msg.payload.decode('utf-8', errors='replace')
        
        topic = msg.topic
        logger.debug(f"MQTT [{timestamp}] {topic}: {message}")
        
        # Process specific MQTT topics for sensor data
        global mqtt_sensor_data
        try:
            # Handle loadcell weight data (Step 3: Load Sensor gets weight)
            # Support both /loadcell and esp32/loadcell/data topics
            if topic.lower() in ['/loadcell', 'esp32/loadcell/data']:
                try:
                    # Extract weight value from message - handle both raw numbers and formatted messages
                    weight = None
                    
                    # Check if message contains formatted weight (e.g., "📦 Final Weight: 418.6 g")
                    if "Final Weight:" in message:
                        # Extract the numeric value from formatted message
                        weight_match = re.search(r'Final Weight:\s*([0-9]+\.?[0-9]*)', message)
                        if weight_match:
                            weight_grams = float(weight_match.group(1))
                            weight = weight_grams / 1000  # Convert grams to kg for consistent storage
                            logger.info(f"LOADCELL: Parsed formatted weight: {weight_grams}g ({weight}kg) from message: {message}")
                            
                            # Store weight in database first, then start grabber1
                            def process_final_weight():
                                try:
                                    logger.info("STEP 3 - FINAL WEIGHT RECEIVED: Storing in database...")
                                    
                                    # Store weight data in database (weight is already in kg)
                                    mqtt_sensor_data['loadcell']['weight'] = weight
                                    mqtt_sensor_data['loadcell']['timestamp'] = datetime.now().isoformat()
                                    
                                    # Store weight in loaded_sensor_data database
                                    store_weight_data_in_db()
                                    
                                    logger.info("STEP 4 - WEIGHT STORED: Starting Grabber1...")
                                    
                                    # Send grabber1 start request via MQTT
                                    success = mqtt_listener.publish_message('esp32/grabber1/request', 'start')
                                    if success:
                                        logger.info("SUCCESS: Grabber1 START request sent (esp32/grabber1/request > start)")
                                        
                                        # Emit WebSocket notification
                                        socketio.emit('workflow_progress', {
                                            'step': 4,
                                            'status': 'grabber1_start_requested',
                                            'message': 'Weight stored in DB - Grabber1 start requested',
                                            'timestamp': datetime.now().isoformat(),
                                            'triggered_by': 'loadcell_final_weight',
                                            'weight': weight
                                        })
                                    else:
                                        logger.error("FAILED: Could not send grabber1 start request")
                                        
                                except Exception as e:
                                    logger.error(f"Error processing final weight: {e}")
                            
                            # Start processing in background thread
                            request_thread = threading.Thread(target=process_final_weight, daemon=True)
                            request_thread.start()
                    else:
                        # Try to parse as direct numeric value
                        weight = float(message)
                    
                    if weight is None:
                        raise ValueError(f"Could not extract weight from: {message}")
                    
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
                            weight_grams = weight * 1000  # Convert kg to grams
                            logger.info(f"STEP 3 - LOADCELL: Weight captured {weight_grams:.1f}g")
                            
                            # Store ONLY weight data in database (first entry)
                            store_weight_data_in_db()
                        else:
                            # Suppress spam logging for zero or very small weight readings
                            if weight <= min_weight:
                                pass  # Don't log zero/near-zero readings
                            else:
                                weight_grams = weight * 1000  # Convert kg to grams
                                logger.debug(f"LOADCELL: Ignoring similar weight reading {weight_grams:.1f}g")
                    else:
                        # No filtering - process all weight readings
                        mqtt_sensor_data['loadcell']['weight'] = weight
                        mqtt_sensor_data['loadcell']['timestamp'] = datetime.now().isoformat()
                        weight_grams = weight * 1000  # Convert kg to grams
                        logger.info(f"STEP 3 - LOADCELL: Weight captured {weight_grams:.1f}g")
                        store_weight_data_in_db()
                    
                except ValueError as e:
                    logger.warning(f"Invalid weight value received: {message} - Error: {e}")
            
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
                        logger.info(f"STEP 5 - SIZE SENSOR: Dimensions captured W:{width}, H:{height}, L:{length}cm")
                        
                        # Determine package size category
                        package_size = determine_package_size(width, height, length)
                        logger.info(f"PACKAGE SIZE DETERMINED: {package_size}")
                        
                        # Update existing weight record with dimensions (overwrite the weight-only entry)
                        update_sensor_data_with_dimensions()
                        
                    else:
                        logger.warning(f"Invalid box dimensions format: {message}")
                except ValueError:
                    logger.warning(f"Invalid box dimensions values: {message}")
            
            # Handle loadcell status messages (Step 2: Load cell status updates)
            elif topic.lower() == 'esp32/loadcell/status':
                try:
                    logger.info(f"LOADCELL STATUS: {message}")
                    
                    # Check for specific loadcell status messages
                    if "Advanced load cell started" in message:
                        logger.info("✅ LOADCELL: Advanced load cell started successfully")
                        
                        # Emit loadcell start status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.1,
                            'status': 'loadcell_started',
                            'message': 'Load cell started and ready for measurement',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'loadcell_start_confirmation'
                        })
                        
                    elif "Weight detected! Collecting data" in message:
                        logger.info("📊 LOADCELL: Weight detected, starting data collection")
                        
                        # Emit weight detection status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.2,
                            'status': 'weight_detected',
                            'message': 'Weight detected on load cell - collecting measurement data',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'loadcell_weight_detection'
                        })
                        
                    elif "load cell stopped" in message.lower() or "stopped" in message.lower():
                        logger.info("⏹️ LOADCELL: Load cell stopped")
                        
                        # Emit loadcell stop status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.9,
                            'status': 'loadcell_stopped',
                            'message': 'Load cell measurement stopped',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'loadcell_stop_confirmation'
                        })
                        
                    else:
                        # Generic loadcell status message
                        socketio.emit('loadcell_status', {
                            'status': 'update',
                            'message': message,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing loadcell status: {e}")
            
            # Handle actuator status messages (ESP32 autonomous actuator operations)
            elif topic.lower() == 'esp32/actuator/status':
                try:
                    logger.info(f"ACTUATOR STATUS: {message}")
                    
                    # Check for specific actuator status messages
                    if "pushing" in message.lower():
                        logger.info("🔧 ACTUATOR: Actuator pushing (autonomous ESP32 operation)")
                        
                        # Emit actuator start status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.1,
                            'status': 'actuator_pushing',
                            'message': 'Actuator pushing (ESP32 autonomous)',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'esp32_autonomous_actuator'
                        })
                        
                    elif "complete" in message.lower() or "cycle complete" in message.lower():
                        logger.info("✅ ACTUATOR: Actuator cycle complete (loadcell already started simultaneously)")
                        
                        # Just emit status update - loadcell was already started simultaneously
                        socketio.emit('workflow_progress', {
                            'step': 2.1,
                            'status': 'actuator_complete',
                            'message': 'Actuator cycle complete (loadcell already started)',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'actuator_complete'
                        })
                        
                    elif "started" in message.lower():
                        logger.info("⚡ ACTUATOR: Actuator started - Will start loadcell after completion")
                        
                        # Emit actuator start status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.1,
                            'status': 'actuator_started',
                            'message': 'Actuator started - Will start loadcell after completion',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'actuator_start_confirmed'
                        })
                        
                    elif "stopped" in message.lower():
                        logger.info("⏹️ ACTUATOR: Actuator stopped")
                        
                        # Emit actuator stop status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2.9,
                            'status': 'actuator_stopped',
                            'message': 'Actuator stopped',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'esp32_actuator_stop'
                        })
                        
                    else:
                        # Generic actuator status message
                        socketio.emit('actuator_status', {
                            'status': 'update',
                            'message': message,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing actuator status: {e}")
            
            # Handle IR sensor trigger (Step 1: IR sensor detects object approaching)
            # NOTE: This should ONLY respond to actual IR sensor data from ESP32 hardware
            # The ESP32 sends these messages autonomously when its physical IR sensor detects objects
            elif topic.lower() in ['esp32/ir/status', '/ir/sensor', 'esp32/sensor/ir']:
                try:
                    # Check for IR sensor triggered message from ESP32 hardware
                    if 'triggered' in message.lower() or 'detected' in message.lower() or message.strip() == '1':
                        logger.info("STEP 1 - IR SENSOR: ESP32 IR sensor detected object - Stopping Motor A")
                        
                        # Reset Motor B cycle at the start of a new process
                        reset_motor_b_cycle()
                        
                        
                        # First stop Motor A when IR A detects object
                        def stop_motor_a_and_continue():
                            try:
                                logger.info("IR A DETECTED: Sending STOP command to Motor A...")
                                
                                # Send motor stopA request via MQTT
                                motor_stop_success = mqtt_listener.publish_message('esp32/motor/request', 'stopA')
                                if motor_stop_success:
                                    logger.info("SUCCESS: Motor A STOP request sent (esp32/motor/request > stopA)")
                                    
                                    # Emit immediate IR sensor status via WebSocket
                                    socketio.emit('workflow_progress', {
                                        'step': 1,
                                        'status': 'ir_triggered_motor_stopping',
                                        'message': 'IR A triggered - Motor A stop requested',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    
                                    logger.info("🔄 WORKFLOW: IR A detected → Motor A stop requested → Waiting for Motor A status")
                                else:
                                    logger.error("FAILED: Could not send Motor A stop request")
                                    
                                    # Emit error status
                                    socketio.emit('workflow_progress', {
                                        'step': 1,
                                        'status': 'error',
                                        'message': 'IR A triggered but failed to stop Motor A',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    
                            except Exception as e:
                                logger.error(f"ERROR: Exception while stopping Motor A from IR A trigger: {e}")
                        
                        # Execute motor stop request in background thread
                        request_thread = threading.Thread(target=stop_motor_a_and_continue, daemon=True)
                        request_thread.start()
                        
                    else:
                        logger.debug(f"IR SENSOR: {message}")
                        
                except Exception as e:
                    logger.error(f"Error processing ESP32 IR sensor status: {e}")
            
            # Handle motor status messages (Step 2: Object detection triggers loadcell)
            elif topic.lower() == 'esp32/motor/status':
                try:
                    # Check for Motor A stopped by IR A message
                    if 'Motor A stopped by IR A' in message:
                        logger.info(f"STEP 2 - MOTOR STATUS: Motor A stopped by IR A - Starting actuator and loadcell immediately")
                        
                        # Start both actuator and loadcell at the same time (parallel execution, no delay)
                        def send_actuator_and_loadcell_simultaneously():
                            try:
                                logger.info("STEP 2.1 - IMMEDIATE START: Motor A stopped, starting actuator and loadcell immediately...")
                                
                                # No delay - start both immediately
                                
                                # Send actuator start request via MQTT
                                actuator_success = mqtt_listener.publish_message('esp32/actuator/request', 'start')
                                if actuator_success:
                                    logger.info("SUCCESS: Actuator START request sent (esp32/actuator/request > start)")
                                else:
                                    logger.error("FAILED: Could not send actuator start request")
                                
                                # Send loadcell start request via MQTT (at the same time)
                                loadcell_success = mqtt_listener.publish_message('esp32/loadcell/request', 'start')
                                if loadcell_success:
                                    logger.info("SUCCESS: Loadcell START request sent (esp32/loadcell/request > start)")
                                else:
                                    logger.error("FAILED: Could not send loadcell start request")
                                
                                # Emit WebSocket notification for simultaneous start
                                socketio.emit('workflow_progress', {
                                    'step': 2.1,
                                    'status': 'actuator_and_loadcell_start_requested',
                                    'message': 'Actuator and Loadcell started simultaneously (no delay)',
                                    'timestamp': datetime.now().isoformat(),
                                    'triggered_by': 'motor_a_stopped_ir_a',
                                    'actuator_started': actuator_success,
                                    'loadcell_started': loadcell_success
                                })
                                
                                if actuator_success and loadcell_success:
                                    logger.info("✅ WORKFLOW: Motor A stopped → Actuator & Loadcell started immediately (parallel)")
                                elif actuator_success or loadcell_success:
                                    logger.warning("⚠️ PARTIAL SUCCESS: Only one of actuator/loadcell started successfully")
                                else:
                                    logger.error("❌ FAILED: Both actuator and loadcell failed to start")
                                    
                            except Exception as e:
                                logger.error(f"Error in simultaneous actuator/loadcell sequence: {e}")
                        
                        # Start both systems in background thread
                        parallel_thread = threading.Thread(target=send_actuator_and_loadcell_simultaneously, daemon=True)
                        parallel_thread.start()
                        
                        # Emit immediate motor status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 2,
                            'status': 'motor_a_stopped_parallel_sequence',
                            'message': 'Motor A stopped by IR A - Starting actuator and loadcell immediately',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'motor_a_stopped_ir_a'
                        })
                    
                    # Check for IR B triggered message - only if IR B is enabled
                    elif '📍 IR B triggered' in message:
                        if motor_b_cycle_state['ir_b_enabled'] and motor_b_cycle_state['motor_b_first_run']:
                            logger.info(f"STEP - IR B: IR B triggered - Object detected, disabling IR B and starting QR validation")
                            
                            # Disable IR B detection immediately after first trigger
                            motor_b_cycle_state['ir_b_enabled'] = False
                            
                            # Stop IR B sensor when disabling detection
                            logger.info("STOPPING IR B SENSOR: IR B triggered, stopping IR B sensor...")
                            ir_b_stop_success = mqtt_listener.publish_message('esp32/irsensorB/request', 'stop')
                            if ir_b_stop_success:
                                logger.info("SUCCESS: IR B SENSOR STOP request sent (esp32/irsensorB/request > stop)")
                            else:
                                logger.error("FAILED: Could not stop IR B sensor")
                            
                            # Send Motor B stop request when IR B is triggered
                            def handle_ir_b_trigger():
                                try:
                                    logger.info("IR B TRIGGERED: Sending stopB command to Motor B...")
                                    
                                    # Send motor stopB request via MQTT
                                    motor_b_stop_success = mqtt_listener.publish_message('esp32/motor/request', 'stopB')
                                    if motor_b_stop_success:
                                        logger.info("SUCCESS: Motor B STOP request sent (esp32/motor/request > stopB)")
                                        
                                        # Emit WebSocket notification for Motor B stop
                                        socketio.emit('workflow_progress', {
                                            'step': 'motor_b_stop',
                                            'status': 'motor_b_stop_requested',
                                            'message': 'IR B triggered - Motor B stopped, IR B disabled, starting QR validation',
                                            'timestamp': datetime.now().isoformat(),
                                            'triggered_by': 'ir_b_triggered'
                                        })
                                        
                                        logger.info("🔄 WORKFLOW: IR B triggered → Motor B stopped → IR B disabled → QR validation active")
                                        
                                        # Start QR validation monitoring
                                        logger.info("🎯 QR VALIDATION: IR B detected object - QR validation now active")
                                        
                                    else:
                                        logger.error("FAILED: Could not send Motor B stop request")
                                        
                                except Exception as e:
                                    logger.error(f"Error handling IR B trigger: {e}")
                            
                            # Execute Motor B stop and QR validation start in background thread
                            motor_b_thread = threading.Thread(target=handle_ir_b_trigger, daemon=True)
                            motor_b_thread.start()
                        else:
                            logger.info(f"IR B triggered but detection is disabled or Motor B first run not complete (IR B enabled: {motor_b_cycle_state['ir_b_enabled']}, Motor B first run: {motor_b_cycle_state['motor_b_first_run']})")
                    
                    
                    # Check for Motor B stopped message  
                    elif 'Motor B stopped' in message or 'stopB' in message.lower():
                        logger.info(f"STEP - MOTOR B: Motor B stopped successfully")
                        
                        # Emit WebSocket notification for Motor B stopped
                        socketio.emit('workflow_progress', {
                            'step': 'motor_b_stopped',
                            'status': 'motor_b_stopped_complete',
                            'message': 'Motor B stopped successfully',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'motor_b_stop_complete'
                        })
                        
                        logger.info("✅ WORKFLOW: Motor B stopped successfully")
                    
                    # Check for Motor B timeout or restart messages
                    elif 'timeout' in message.lower() and 'motor b' in message.lower():
                        logger.warning(f"⚠️ MOTOR B TIMEOUT: {message}")
                        
                        # Attempt to restart Motor B
                        def restart_motor_b():
                            try:
                                logger.info("🔄 MOTOR B RESTART: Attempting to restart Motor B...")
                                
                                # Send motor startB request via MQTT
                                motor_b_restart_success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if motor_b_restart_success:
                                    logger.info("SUCCESS: Motor B RESTART request sent (esp32/motor/request > startB)")
                                    
                                    # Emit WebSocket notification for Motor B restart
                                    socketio.emit('workflow_progress', {
                                        'step': 'motor_b_restart',
                                        'status': 'motor_b_restart_requested',
                                        'message': 'Motor B restart requested after timeout',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'motor_b_timeout'
                                    })
                                    
                                    logger.info("🔄 WORKFLOW: Motor B timeout → Restart requested")
                                else:
                                    logger.error("FAILED: Could not send Motor B restart request")
                                    
                            except Exception as e:
                                logger.error(f"Error restarting Motor B: {e}")
                        
                        # Execute Motor B restart in background thread
                        restart_thread = threading.Thread(target=restart_motor_b, daemon=True)
                        restart_thread.start()
                    
                    # Check for object detection message (existing Motor B logic)
                    elif '📍 Object detected! Motor B paused' in message:
                        logger.info(f"STEP 2 - MOTOR STATUS: Object detected, motor paused")
                        
                        # Send immediate loadcell request (no delay needed)
                        def send_loadcell_request():
                            try:
                                logger.debug("Sending loadcell start request to ESP32...")
                                
                                # Send loadcell request via MQTT
                                success = mqtt_listener.publish_message('esp32/loadcell/request', 'start')
                                if success:
                                    logger.info("STEP 3 TRIGGER: Sent loadcell request (esp32/loadcell/request > start)")
                                    
                                    # Emit workflow progress via WebSocket
                                    socketio.emit('workflow_progress', {
                                        'step': 2.5,
                                        'status': 'loadcell_requested',
                                        'message': 'Object detected, loadcell reading requested',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                else:
                                    logger.error("Failed to send loadcell request")
                                    
                            except Exception as e:
                                logger.error(f"Error sending loadcell request: {e}")
                        
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
                        logger.info(f"MOTOR STATUS: {message}")
                        
                except Exception as e:
                    logger.error(f"Error processing motor status: {e}")
            
            # Handle parcel grabber status messages (Step 4: Parcel grabber operations)
            elif topic.lower() in ['esp32/parcel/status']:
                try:
                    logger.info(f"PARCEL GRABBER STATUS: {message}")
                    
                    # Check for grabber completion messages
                    if any(keyword in message.lower() for keyword in ['system ready', 'ready']):
                        logger.info("✅ PARCEL GRABBER: System ready and waiting")
                        
                        # Emit grabber ready status via WebSocket
                        socketio.emit('grabber_status', {
                            'status': 'ready',
                            'message': 'Parcel grabber system ready',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif 'started' in message.lower():
                        logger.info("🤖 STEP 4 ACTIVE: Parcel grabber operation initiated")
                        
                        # Emit grabber started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4,
                            'status': 'active',
                            'message': 'Parcel grabber started - beginning pickup sequence',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif 'grabbing parcel' in message.lower():
                        logger.info("🔧 STEP 4 PROGRESS: Grabbing parcel...")
                        
                        # Emit grabbing progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.1,
                            'status': 'grabbing',
                            'message': 'Grabbing parcel with servo arms',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif 'rotating' in message.lower() and 'forward' in message.lower():
                        logger.info("🔄 STEP 4 PROGRESS: Rotating 90° forward...")
                        
                        # Emit rotation progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.2,
                            'status': 'rotating',
                            'message': 'Rotating package 90° forward',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif 'releasing parcel' in message.lower():
                        logger.info("🤲 STEP 4 PROGRESS: Releasing parcel...")
                        
                        # Emit release progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.3,
                            'status': 'releasing',
                            'message': 'Releasing parcel at destination',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif 'rotating back' in message.lower():
                        logger.info("🔁 STEP 4 PROGRESS: Rotating back to start position...")
                        
                        # Emit return rotation progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.4,
                            'status': 'returning',
                            'message': 'Returning grabber to start position',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif '✅ Parcel process 1 complete' in message:
                        logger.info("✅ STEP 4 COMPLETE: Parcel process 1 complete (handled by parcel1 status handler)")
                        
                        # This completion is now handled by the specific esp32/parcel1/status handler
                        # to avoid duplicate box system triggers
                        
                    elif '✅ Parcel process 2 complete' in message:
                        logger.info("✅ STEP 5 COMPLETE: Parcel process 2 complete - Starting motor B...")
                        
                        # Send motor startB command when parcel process 2 is complete
                        def send_motor_startB_command():
                            try:
                                logger.info("STEP 6 - PARCEL PROCESS 2 COMPLETE: Sending motor startB command...")
                                
                                # Send motor startB request via MQTT
                                success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if success:
                                    logger.info("SUCCESS: Motor startB request sent (esp32/motor/request > startB)")
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 6,
                                        'status': 'motor_b_start_requested',
                                        'message': 'Parcel process 2 complete - Motor B start requested',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'parcel_process_2_complete'
                                    })
                                else:
                                    logger.error("FAILED: Could not send motor startB request")
                                    
                            except Exception as e:
                                logger.error(f"Error sending motor startB request: {e}")
                        
                        # Start request in background thread to not block MQTT processing
                        request_thread = threading.Thread(target=send_motor_startB_command, daemon=True)
                        request_thread.start()
                        
                    elif 'stopped' in message.lower():
                        logger.info("🛑 PARCEL GRABBER: Operation stopped")
                        
                        # Emit stopped status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4,
                            'status': 'stopped',
                            'message': 'Parcel grabber operation stopped',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing parcel grabber status: {e}")
                    
            # Handle parcel1 grabber status messages (Step 4: Parcel1 grabber operations)
            elif topic.lower() in ['esp32/parcel1/status']:
                try:
                    logger.info(f"PARCEL1 GRABBER STATUS: {message}")
                    
                    # Check for specific grabber1 status messages
                    if "🚚 Parcel process 1 started" in message:
                        logger.info("🤖 STEP 4 ACTIVE: Parcel grabber 1 operation initiated")
                        
                        # Emit grabber started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4,
                            'status': 'active',
                            'message': 'Parcel grabber 1 started - beginning pickup sequence',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "➡️ Moved to size checker" in message:
                        logger.info("🔄 STEP 4 PROGRESS: Moved to size checker...")
                        
                        # Emit movement progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.2,
                            'status': 'moving',
                            'message': 'Moving parcel to size checker',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "✅ Parcel process 1 complete" in message:
                        logger.info("✅ STEP 4 COMPLETE: Parcel grabber 1 process complete - Starting box system...")
                        
                        # Send box start command when parcel process 1 is complete
                        def send_box_start_command():
                            try:
                                logger.info("STEP 4.5 - PARCEL PROCESS 1 COMPLETE: Adding 5 second delay before starting box...")
                                
                                # Add 5 second delay as requested
                                time.sleep(5)
                                
                                logger.info("STEP 4.5 - DELAY COMPLETE: Sending box start command...")
                                
                                # Send box start request via MQTT
                                box_success = mqtt_listener.publish_message('esp32/box/request', 'start')
                                if box_success:
                                    logger.info("SUCCESS: Box START request sent (esp32/box/request > start)")
                                    
                                    # Emit WebSocket notification for box start
                                    socketio.emit('workflow_progress', {
                                        'step': 4.5,
                                        'status': 'box_start_requested',
                                        'message': 'Box system start requested after 5s delay',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'parcel_process_1_complete'
                                    })
                                else:
                                    logger.error("FAILED: Could not send box start request")
                                    
                            except Exception as e:
                                logger.error(f"Error sending box start request: {e}")
                        
                        # Start request in background thread to not block MQTT processing
                        request_thread = threading.Thread(target=send_box_start_command, daemon=True)
                        request_thread.start()
                        
                        # Emit completion status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4,
                            'status': 'complete',
                            'message': 'Parcel grabber 1 process complete',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing parcel1 grabber status: {e}")
                    
            # Handle box system status messages (Step 4.5: Box system operations)
            elif topic.lower() in ['esp32/box/status']:
                try:
                    logger.info(f"BOX SYSTEM STATUS: {message}")
                    
                    # Parse box dimensions from status message (e.g., "W: 6.87 in, L: 7.07 in, H: 5.83 in → 📦 Large")
                    if 'W:' in message and 'L:' in message and 'H:' in message and 'in' in message:
                        try:
                            # Extract dimensions using regex (handle negative values)
                            width_match = re.search(r'W:\s*([-]?[0-9.]+)\s*in', message)
                            length_match = re.search(r'L:\s*([-]?[0-9.]+)\s*in', message)
                            height_match = re.search(r'H:\s*([-]?[0-9.]+)\s*in', message)
                            
                            if width_match and length_match and height_match:
                                # Store actual sensor values in inches (no conversion)
                                width_inches = float(width_match.group(1))
                                length_inches = float(length_match.group(1))
                                height_inches = float(height_match.group(1))
                                
                                logger.info(f"RAW SENSOR VALUES: W:{width_inches:.2f}in, L:{length_inches:.2f}in, H:{height_inches:.2f}in")
                                
                                # Log info about negative values but keep them as-is
                                if width_inches <= 0 or length_inches <= 0 or height_inches <= 0:
                                    logger.info(f"ℹ️ RAW SENSOR DATA: Negative/zero values detected - storing as-is")
                                
                                # Store raw sensor values in inches (no conversion to cm)
                                mqtt_sensor_data['box_dimensions']['width'] = width_inches
                                mqtt_sensor_data['box_dimensions']['height'] = height_inches
                                mqtt_sensor_data['box_dimensions']['length'] = length_inches
                                mqtt_sensor_data['box_dimensions']['timestamp'] = datetime.now().isoformat()
                                
                                logger.info(f"STEP 5 - SIZE SENSOR: Raw sensor values stored - W:{width_inches:.2f}in, H:{height_inches:.2f}in, L:{length_inches:.2f}in")
                                
                                # Determine package size category using raw inch values
                                package_size = determine_package_size(width_inches, length_inches, height_inches)
                                logger.info(f"PACKAGE SIZE DETERMINED: {package_size}")
                                
                                # Update existing weight record with dimensions
                                update_sensor_data_with_dimensions()
                                
                        except Exception as e:
                            logger.error(f"Error parsing box dimensions from status: {e}")
                            logger.error(f"Failed to parse message: {message}")
                            # Check if message contains dimensions but in unexpected format
                            if 'W:' in message and 'L:' in message and 'H:' in message:
                                logger.warning("⚠️ Box dimensions detected but parsing failed - check message format")
                            else:
                                logger.info("ℹ️ Box status message doesn't contain dimensions")
                    
                    # Check for sensor home position messages
                    if "🏠 Sensor returned to home position" in message:
                        logger.info("✅ STEP 4.75 COMPLETE: 🏠 Sensor returned to home position")
                        
                        # Emit sensor home position status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.75,
                            'status': 'complete',
                            'message': '🏠 Sensor returned to home position',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    # Check for box completion messages
                    elif "✅ Box process complete" in message or "complete" in message.lower():
                        logger.info("✅ STEP 5 - BOX COMPLETE: Box system process complete - Storing size data...")
                        
                        # Store box system status and dimensions in database, then start grabber2
                        def process_box_completion():
                            try:
                                logger.info("STEP 5.1 - BOX COMPLETION: Storing box system status in loaded_sensor_data...")
                                
                                # Update sensor data with box system status and get the calculated package size
                                package_size = update_sensor_data_with_dimensions()
                                
                                # Store box system completion status
                                mqtt_sensor_data['box_system'] = {
                                    'status': 'complete',
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                # Use the package size directly from COMPLETE PACKAGE DATA (no recalculation)
                                if package_size:
                                    logger.info(f"USING SIZE FROM COMPLETE PACKAGE DATA: {package_size} (no dimension recalculation)")
                                    
                                    # Send stepper command with package size from COMPLETE PACKAGE DATA
                                    logger.info(f"STEP 5.2 - SENDING STEPPER: Using size '{package_size.lower()}' from COMPLETE PACKAGE DATA...")
                                    stepper_command = package_size.lower()  # small, medium, or large
                                    stepper_success = mqtt_listener.publish_message('esp32/stepper/request', stepper_command)
                                    
                                    if stepper_success:
                                        logger.info(f"SUCCESS: Stepper {stepper_command} request sent using COMPLETE PACKAGE DATA size (esp32/stepper/request > {stepper_command})")
                                        
                                        # Store current stepper size for later back command
                                        mqtt_sensor_data['stepper']['current_size'] = package_size
                                        
                                        # Emit WebSocket notification for stepper positioning
                                        socketio.emit('workflow_progress', {
                                            'step': 5.2,
                                            'status': 'stepper_positioning',
                                            'message': f'Stepper positioning for {package_size} package (from COMPLETE PACKAGE DATA)',
                                            'timestamp': datetime.now().isoformat(),
                                            'package_size': package_size,
                                            'triggered_by': 'complete_package_data_size'
                                        })
                                        
                                        logger.info(f"📦 WORKFLOW: COMPLETE PACKAGE DATA → Size={package_size} → Stepper positioning")
                                    else:
                                        logger.error(f"FAILED: Could not send stepper {stepper_command} request")
                                else:
                                    logger.warning("No package size returned from COMPLETE PACKAGE DATA - using fallback stepper command")
                                
                                logger.info("STEP 6 - BOX DATA STORED: Starting Grabber2...")
                                
                                # Send grabber2 start request via MQTT
                                grabber2_success = mqtt_listener.publish_message('esp32/grabber2/request', 'start')
                                if grabber2_success:
                                    logger.info("SUCCESS: Grabber2 START request sent (esp32/grabber2/request > start)")
                                    
                                    # Emit WebSocket notification for grabber2 start
                                    socketio.emit('workflow_progress', {
                                        'step': 6,
                                        'status': 'grabber2_start_requested',
                                        'message': 'Box data stored - Grabber2 start requested',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'box_process_complete'
                                    })
                                    
                                    logger.info("📦 WORKFLOW: Box complete → Size stored in DB → Grabber2 activated")
                                else:
                                    logger.error("FAILED: Could not send grabber2 start request")
                                    
                            except Exception as e:
                                logger.error(f"Error processing box completion: {e}")
                        
                        # Start processing in background thread
                        request_thread = threading.Thread(target=process_box_completion, daemon=True)
                        request_thread.start()
                        
                        # Emit box completion status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 5,
                            'status': 'complete',
                            'message': 'Box system process complete - Storing size data',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "started" in message.lower():
                        logger.info("🤖 STEP 4.5 ACTIVE: Box system operation initiated")
                        
                        # Emit box started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.5,
                            'status': 'active',
                            'message': 'Box system started',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing box system status: {e}")
                    
            # Handle sensor position status (Step 4.75: Sensor returning to home position)
            elif topic.lower() in ['esp32/sensor/position', 'esp32/sensor/home', 'esp32/position/status']:
                try:
                    logger.info(f"SENSOR POSITION STATUS: {message}")
                    
                    # Check for sensor home position messages
                    if "🏠 Sensor returned to home position" in message or "home position" in message.lower():
                        logger.info("✅ STEP 4.75 COMPLETE: 🏠 Sensor returned to home position")
                        
                        # Emit sensor home position status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.75,
                            'status': 'complete',
                            'message': '🏠 Sensor returned to home position',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "returning" in message.lower() or "moving to home" in message.lower():
                        logger.info("🔄 STEP 4.75 ACTIVE: Sensor returning to home position")
                        
                        # Emit sensor returning status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 4.75,
                            'status': 'active',
                            'message': 'Sensor returning to home position',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing sensor position status: {e}")
                    
            # Handle stepper status messages 
            elif topic.lower() in ['esp32/stepper/status']:
                try:
                    logger.info(f"STEPPER STATUS: {message}")
                    
                    # Update stepper status in sensor data
                    mqtt_sensor_data['stepper']['status'] = message
                    mqtt_sensor_data['stepper']['timestamp'] = datetime.now().isoformat()
                    
                    # Check for stepper positioning completion (small, medium, large)
                    if (("small" in message.lower() and "complete" in message.lower()) or 
                        ("medium" in message.lower() and "complete" in message.lower()) or 
                        ("large" in message.lower() and "complete" in message.lower())) and \
                       ("back" not in message.lower()):  # Ensure it's not a "back" command
                        
                        # Extract the size from the message
                        if "small" in message.lower():
                            size = "small"
                        elif "medium" in message.lower():
                            size = "medium"
                        elif "large" in message.lower():
                            size = "large"
                        
                        logger.info(f"✅ STEPPER POSITIONING COMPLETE: {size.upper()} position reached - scheduling back command in 5 seconds...")
                        
                        # Store current size for back command
                        mqtt_sensor_data['stepper']['current_size'] = size
                        
                        # Schedule back command after 5 seconds
                        def send_stepper_back_command():
                            try:
                                logger.info(f"⏳ STEPPER DELAY: Waiting 5 seconds before sending {size}back command...")
                                time.sleep(5)
                                
                                back_command = f"{size}back"
                                logger.info(f"🔄 STEPPER BACK: Sending {back_command} command...")
                                
                                back_success = mqtt_listener.publish_message('esp32/stepper/request', back_command)
                                if back_success:
                                    logger.info(f"SUCCESS: Stepper back request sent (esp32/stepper/request > {back_command})")
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 'stepper_back',
                                        'status': 'stepper_back_requested',
                                        'message': f'Stepper {back_command} command sent after 5s delay',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': f'stepper_{size}_complete'
                                    })
                                else:
                                    logger.error(f"FAILED: Could not send stepper back command {back_command}")
                                    
                            except Exception as e:
                                logger.error(f"Error in stepper back command sequence: {e}")
                        
                        # Execute back command in background thread
                        threading.Thread(target=send_stepper_back_command, daemon=True).start()
                        
                        # Emit WebSocket notification for stepper positioning complete
                        socketio.emit('workflow_progress', {
                            'step': 'stepper_positioned',
                            'status': 'stepper_positioned_complete',
                            'message': f'Stepper positioned for {size} package - back command scheduled',
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': f'stepper_{size}_complete'
                        })
                    
                    # Check for stepper back command completion (smallback, mediumback, largeback)
                    if ("smallback" in message.lower() or "mediumback" in message.lower() or "largeback" in message.lower()) and \
                       ("complete" in message.lower() or "done" in message.lower() or "finished" in message.lower()):
                        logger.info("✅ STEPPER BACK PROCESS COMPLETE: Cycle ending - ready for new cycle...")
                        
                        # Mark the cycle as complete when stepper back command finishes
                        motor_b_cycle_state['cycle_complete'] = True
                        logger.info("🏁 CYCLE COMPLETE: Full process cycle completed at stepper back - IR B will be re-enabled for next cycle")
                        
                        # Start the stop-all and restart sequence
                        def stop_and_restart_sequence():
                            try:
                                logger.info("🛑 LOOP RESTART: Starting emergency stop of all systems...")
                                
                                # Stop all MQTT systems
                                stop_commands = [
                                    ('esp32/motor/request', 'stopA', 'Motor A'),
                                    ('esp32/motor/request', 'stopB', 'Motor B'), 
                                    ('esp32/grabber1/request', 'stop', 'Grabber 1'),
                                    ('esp32/grabber2/request', 'stop', 'Grabber 2'),
                                    ('esp32/actuator/request', 'stop', 'Actuator'),
                                    ('esp32/loadcell/request', 'stop', 'Load Cell'),
                                    ('esp32/box/request', 'stop', 'Box System'),
                                    ('esp32/stepper/request', 'stop', 'Stepper Motor'),
                                    ('esp32/gsm/request', 'stop', 'GSM Module')
                                ]
                                
                                # Send stop commands to all systems
                                stopped_count = 0
                                for topic, command, system_name in stop_commands:
                                    try:
                                        success = mqtt_listener.publish_message(topic, command)
                                        if success:
                                            logger.info(f"🛑 {system_name} stopped (esp32 stop sequence)")
                                            stopped_count += 1
                                        else:
                                            logger.error(f"❌ Failed to stop {system_name}")
                                    except Exception as e:
                                        logger.error(f"❌ Error stopping {system_name}: {e}")
                                
                                logger.info(f"🛑 STOP COMPLETE: {stopped_count}/{len(stop_commands)} systems stopped")
                                
                                # NOTE: Sensor data clearing disabled to preserve frontend display
                                # clear_mqtt_sensor_data()
                                logger.info("🧹 Sensor data preserved for frontend display")
                                
                                # Wait 3 seconds for systems to fully stop
                                logger.info("⏳ LOOP RESTART: Waiting 3 seconds for systems to stop...")
                                time.sleep(3)
                                
                                # Start the loop again with motor startA
                                logger.info("🔄 LOOP RESTART: Sending motor startA to begin new cycle...")
                                restart_success = mqtt_listener.publish_message('esp32/motor/request', 'startA')
                                
                                if restart_success:
                                    logger.info("✅ LOOP RESTARTED: Motor startA sent - New cycle begun (esp32/motor/request > startA)")
                                    
                                    # Emit WebSocket notification about loop restart
                                    socketio.emit('workflow_restart', {
                                        'message': 'System loop restarted after stepper back completion',
                                        'stopped_systems': stopped_count,
                                        'total_systems': len(stop_commands),
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    
                                else:
                                    logger.error("❌ FAILED to restart loop - Could not send motor startA command")
                                    
                            except Exception as e:
                                logger.error(f"Error in stop and restart sequence: {e}")
                        
                        # Start stop and restart sequence in background thread
                        threading.Thread(target=stop_and_restart_sequence, daemon=True).start()
                        
                        # Emit WebSocket notification about back completion
                        socketio.emit('workflow_progress', {
                            'step': 'stepper_back_complete',
                            'status': 'complete',
                            'message': 'Stepper back process complete - Restarting system loop',
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Check for regular stepper completion messages (forward commands)
                    elif "complete" in message.lower() or "done" in message.lower() or "finished" in message.lower():
                        logger.info("✅ STEPPER PROCESS COMPLETE: Starting motor sequence...")
                        
                        # Start motor with 5 second delay
                        def start_motor_sequence():
                            try:
                                logger.info("MOTOR SEQUENCE: Adding 5 second delay before starting motor...")
                                time.sleep(5)
                                
                                logger.info("MOTOR SEQUENCE: Sending motor startB command...")
                                success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if success:
                                    logger.info("SUCCESS: Motor startB request sent (esp32/motor/request > startB)")
                                    
                                    # Get current stepper size to determine back command
                                    current_size = mqtt_sensor_data['stepper'].get('current_size')
                                    if current_size:
                                        # Wait another 5 seconds then send back command
                                        time.sleep(5)
                                        back_command = f"{current_size.lower()}back"
                                        
                                        logger.info(f"STEPPER BACK SEQUENCE: Sending {back_command} command...")
                                        back_success = mqtt_listener.publish_message('esp32/stepper/request', back_command)
                                        if back_success:
                                            logger.info(f"SUCCESS: Stepper back request sent (esp32/stepper/request > {back_command})")
                                        else:
                                            logger.error(f"FAILED: Could not send stepper back command {back_command}")
                                    else:
                                        logger.warning("WARNING: No current stepper size available for back command")
                                else:
                                    logger.error("FAILED: Could not send motor startB command")
                                    
                            except Exception as e:
                                logger.error(f"Error in motor sequence: {e}")
                        
                        # Start motor sequence in background thread
                        threading.Thread(target=start_motor_sequence, daemon=True).start()
                        
                        # Emit WebSocket notification
                        socketio.emit('workflow_progress', {
                            'step': 'stepper_complete',
                            'status': 'complete',
                            'message': 'Stepper process complete - Starting motor sequence',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing stepper status: {e}")
                    
            # Handle parcel2 grabber status messages (Step 5: Parcel2 grabber operations)
            elif topic.lower() in ['esp32/parcel2/status']:
                try:
                    logger.info(f"PARCEL2 GRABBER STATUS: {message}")
                    
                    # Check for specific grabber2 status messages
                    if "📦 Parcel process 2 started" in message:
                        logger.info("🤖 STEP 5 ACTIVE: Parcel grabber 2 operation initiated")
                        
                        # Emit grabber2 started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 5,
                            'status': 'active',
                            'message': 'Parcel grabber 2 started - beginning pickup sequence',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "➡️ Moved to conveyor 2" in message:
                        logger.info("🔄 STEP 5 PROGRESS: Moved to conveyor 2...")
                        
                        # Emit movement progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 5.1,
                            'status': 'moving',
                            'message': 'Moving parcel to conveyor 2',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "↩️ Returned to conveyor belt 1" in message:
                        logger.info("🔁 STEP 5 PROGRESS: Returned to conveyor belt 1 - Starting Motor B...")
                        
                        # Start Motor B when grabber2 returns to conveyor belt 1
                        def start_motor_b_after_return():
                            try:
                                logger.info("STEP 5.3 - MOTOR B START: Grabber2 returned to conveyor belt 1, starting Motor B...")
                                
                                # Update state - grabber2 has completed return journey
                                motor_b_cycle_state['grabber2_completed'] = True
                                motor_b_cycle_state['ir_b_enabled'] = True  # Enable IR B detection
                                
                                # Send motor startB request via MQTT
                                motor_b_success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if motor_b_success:
                                    logger.info("SUCCESS: Motor B START request sent after grabber2 return (esp32/motor/request > startB)")
                                    
                                    # Start IR B sensor after Motor B starts successfully
                                    logger.info("STARTING IR B SENSOR: Motor B started, now starting IR B sensor...")
                                    ir_b_success = mqtt_listener.publish_message('esp32/irsensorB/request', 'start')
                                    if ir_b_success:
                                        logger.info("SUCCESS: IR B SENSOR START request sent (esp32/irsensorB/request > start)")
                                    else:
                                        logger.error("FAILED: Could not start IR B sensor")
                                    
                                    # Update state
                                    motor_b_cycle_state['motor_b_first_run'] = True
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 5.3,
                                        'status': 'motor_b_and_ir_b_started',
                                        'message': 'Motor B and IR B sensor started after grabber2 returned to conveyor belt 1',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'grabber2_returned_to_belt1'
                                    })
                                    
                                    logger.info("✅ WORKFLOW: Grabber2 returned to belt 1 → Motor B started → IR B sensor started → IR B detection enabled")
                                else:
                                    logger.error("FAILED: Could not start Motor B after grabber2 return")
                                    
                            except Exception as e:
                                logger.error(f"Error starting Motor B after grabber2 return: {e}")
                        
                        # Start Motor B in background thread
                        motor_b_thread = threading.Thread(target=start_motor_b_after_return, daemon=True)
                        motor_b_thread.start()
                        
                        # Emit return movement progress via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 5.2,
                            'status': 'returned_starting_motor_b',
                            'message': 'Grabber returned to conveyor belt 1 - Starting Motor B',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    elif "✅ Parcel process 2 complete" in message:
                        logger.info("✅ STEP 5 COMPLETE: Parcel grabber 2 process complete - Starting Motor B for first run...")
                        
                        # Update state - grabber2 has completed
                        motor_b_cycle_state['grabber2_completed'] = True
                        motor_b_cycle_state['ir_b_enabled'] = True  # Enable IR B detection
                        
                        # Send motor startB command when parcel process 2 is complete (first run)
                        def send_motor_startB_first_run():
                            try:
                                logger.info("STEP 6 - GRABBER2 COMPLETE: Starting Motor B for first run after grabber2...")
                                
                                # Send motor startB request via MQTT
                                success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if success:
                                    logger.info("SUCCESS: Motor B START request sent for first run (esp32/motor/request > startB)")
                                    
                                    # Start IR B sensor after Motor B starts successfully
                                    logger.info("STARTING IR B SENSOR: Motor B started, now starting IR B sensor...")
                                    ir_b_success = mqtt_listener.publish_message('esp32/irsensorB/request', 'start')
                                    if ir_b_success:
                                        logger.info("SUCCESS: IR B SENSOR START request sent (esp32/irsensorB/request > start)")
                                    else:
                                        logger.error("FAILED: Could not start IR B sensor")
                                    
                                    # Update state
                                    motor_b_cycle_state['motor_b_first_run'] = True
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 6,
                                        'status': 'motor_b_and_ir_b_first_run_started',
                                        'message': 'Motor B and IR B sensor started for first run after grabber2 completion',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'grabber2_complete'
                                    })
                                else:
                                    logger.error("FAILED: Could not send Motor B start request for first run")
                                    
                            except Exception as e:
                                logger.error(f"Error sending Motor B start request for first run: {e}")
                        
                        # Start request in background thread to not block MQTT processing
                        request_thread = threading.Thread(target=send_motor_startB_first_run, daemon=True)
                        request_thread.start()
                        
                        # Emit completion status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 5,
                            'status': 'complete',
                            'message': 'Parcel grabber 2 process complete',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing parcel2 grabber status: {e}")
                    
            # Handle IR B sensor status messages (IR B sensor operations)
            elif topic.lower() in ['esp32/irsensorB/status', 'esp32/irsensorb/status']:
                try:
                    logger.info(f"IR B SENSOR STATUS: {message}")
                    
                    # Check for IR B sensor started messages
                    if "started" in message.lower() or "active" in message.lower():
                        logger.info("✅ IR B SENSOR: IR B sensor started and active")
                        
                        # Emit IR B sensor started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'ir_b_sensor',
                            'status': 'active',
                            'message': 'IR B sensor started and monitoring for objects',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    # Check for IR B sensor ready messages
                    elif "ready" in message.lower():
                        logger.info("🟢 IR B SENSOR: IR B sensor ready for detection")
                        
                        # Emit IR B sensor ready status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'ir_b_sensor',
                            'status': 'ready',
                            'message': 'IR B sensor ready for object detection',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    # Check for IR B sensor stopped messages
                    elif "stopped" in message.lower() or "disabled" in message.lower():
                        logger.info("🛑 IR B SENSOR: IR B sensor stopped/disabled")
                        
                        # Emit IR B sensor stopped status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'ir_b_sensor',
                            'status': 'stopped',
                            'message': 'IR B sensor stopped/disabled',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing IR B sensor status: {e}")
            
            # Handle proximity sensor status messages (metallic item detection)
            elif topic.lower() == 'esp32/proximity/status':
                try:
                    logger.info(f"PROXIMITY SENSOR STATUS: {message}")
                    
                    # Check for metallic item detection messages
                    if any(keyword in message.lower() for keyword in ['metallic detected', 'metal detected', 'metallic item', 'metal object']):
                        logger.warning("🚨 METALLIC ITEM DETECTED: Proximity sensor detected metallic object!")
                        
                        # Play alarm sound with cooldown protection
                        alarm_played = play_alarm_sound()
                        
                        if alarm_played:
                            # Alarm was played (not in cooldown)
                            alert_message = 'METALLIC ITEM DETECTED! Alarm sound played.'
                            workflow_message = 'METALLIC ITEM DETECTED - Security alert triggered'
                        else:
                            # Alarm was in cooldown
                            remaining_time = alarm_cooldown['cooldown_duration'] - (time.time() - alarm_cooldown['last_alarm_time'])
                            alert_message = f'METALLIC ITEM DETECTED! Alarm in cooldown ({remaining_time:.1f}s remaining).'
                            workflow_message = f'METALLIC ITEM DETECTED - Alarm in cooldown ({remaining_time:.1f}s remaining)'
                        
                        # Emit proximity sensor metallic detection alert via WebSocket
                        socketio.emit('proximity_alert', {
                            'status': 'metallic_detected',
                            'message': alert_message,
                            'alert_type': 'danger',
                            'alarm_played': alarm_played,
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'proximity_sensor_metallic_detection'
                        })
                        
                        # Also emit as workflow progress for monitoring
                        socketio.emit('workflow_progress', {
                            'step': 'proximity_alert',
                            'status': 'metallic_detected',
                            'message': workflow_message,
                            'alarm_played': alarm_played,
                            'timestamp': datetime.now().isoformat(),
                            'triggered_by': 'proximity_sensor_metallic_detection'
                        })
                        
                    # Check for proximity sensor started messages
                    elif "started" in message.lower() or "active" in message.lower():
                        logger.info("✅ PROXIMITY SENSOR: Proximity sensor started and active")
                        
                        # Emit proximity sensor started status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'proximity_sensor',
                            'status': 'active',
                            'message': 'Proximity sensor started and monitoring for metallic items',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    # Check for proximity sensor ready messages
                    elif "ready" in message.lower():
                        logger.info("🟢 PROXIMITY SENSOR: Proximity sensor ready for detection")
                        
                        # Emit proximity sensor ready status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'proximity_sensor',
                            'status': 'ready',
                            'message': 'Proximity sensor ready for metallic item detection',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    # Check for proximity sensor stopped messages
                    elif "stopped" in message.lower() or "disabled" in message.lower():
                        logger.info("🛑 PROXIMITY SENSOR: Proximity sensor stopped/disabled")
                        
                        # Emit proximity sensor stopped status via WebSocket
                        socketio.emit('workflow_progress', {
                            'step': 'proximity_sensor',
                            'status': 'stopped',
                            'message': 'Proximity sensor stopped/disabled',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    else:
                        # Generic proximity sensor status
                        logger.info(f"PROXIMITY SENSOR: {message}")
                        
                except Exception as e:
                    logger.error(f"Error processing proximity sensor status: {e}")
                    
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
            
            logger.debug(f"Emitting MQTT message via WebSocket: {mqtt_data}")
            
            # Emit to all connected clients
            socketio.emit('mqtt_message', mqtt_data)
            
            # Also broadcast to all namespaces
            socketio.emit('mqtt_message', mqtt_data, namespace='/')

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning("MQTT: Disconnected. Will attempt to reconnect...")
        else:
            logger.info("MQTT: Disconnected gracefully.")
        
        # Emit disconnection status via WebSocket
        socketio.emit('mqtt_status', {
            'status': 'disconnected',
            'timestamp': datetime.now().isoformat()
        })

    def start(self):
        """Start the MQTT listener in a separate thread"""
        def mqtt_loop():
            try:
                logger.info("MQTT Listener starting...")
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
                    logger.info(f"MQTT: Successfully published '{message}' to topic '{topic}'")
                    return True
                else:
                    logger.error(f"MQTT: Failed to publish message. Return code: {result.rc}")
                    return False
            else:
                logger.error("MQTT: Cannot publish - not connected to broker")
                return False
        except Exception as e:
            logger.error(f"MQTT: Error publishing message: {e}")
            return False

    def get_status(self):
        """Get MQTT connection status"""
        return {
            'connected': self.is_connected,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port
        }

    def send_sms_notification(self, phone_number, message):
        """Send SMS notification via ESP32 GSM module"""
        try:
            # Send "start:" command with phone number to ESP32 GSM module
            # Format: "start:+639612903652"
            start_command = f"start:{phone_number}"
            success = self.publish_message('esp32/gsm/send', start_command)
            
            if success:
                logger.info(f"SMS send command 'start:{phone_number}' sent to ESP32")
                return True
            else:
                logger.error(f"Failed to send SMS send command to ESP32")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            return False

# Initialize MQTT listener with correct broker IP
# Initialize and start MQTT listener
mqtt_listener = MQTTListener(
    broker_host=os.getenv('MQTT_BROKER_HOST', '10.194.125.227'), 
    broker_port=int(os.getenv('MQTT_BROKER_PORT', '1883'))
)

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
    },
    'stepper': {
        'status': None,
        'current_size': None,
        'timestamp': None
    },
    'package_size': None  # Calculated package size from COMPLETE PACKAGE DATA
}

# QR scan monitoring variables
last_scan_id = 0
sensor_data_loaded = False

# Motor restart prevention flag
prevent_auto_motor_restart = True  # Set to True to prevent automatic motor restarts

def test_gsm_sms(test_phone_number="09123456789"):
    """Test function to send SMS via GSM module"""
    try:
        logger.info(f"[TEST] Testing GSM SMS functionality...")
        logger.info(f"[TEST] Sending test SMS to: {test_phone_number}")
        
        message = "Your Parcel is Being Delivered"
        sms_sent = mqtt_listener.send_sms_notification(test_phone_number, message)
        
        if sms_sent:
            logger.info(f"[TEST] SMS test successful! Message sent to {test_phone_number}")
            print(f"✅ TEST PASSED: SMS sent to {test_phone_number}")
            print(f"📱 Message: {message}")
            return True
        else:
            logger.error(f"[TEST] SMS test failed for {test_phone_number}")
            print(f"❌ TEST FAILED: Could not send SMS to {test_phone_number}")
            return False
            
    except Exception as e:
        logger.error(f"[TEST] Error during GSM SMS test: {e}")
        print(f"❌ TEST ERROR: {e}")
        return False

def format_phone_number(phone_number):
    """Format phone number to international format for GSM"""
    if not phone_number:
        return phone_number
    
    original_number = phone_number
    # Remove any spaces, dashes, or other characters
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    # Convert Philippine local format (09xxxxxxxx) to international format (+639xxxxxxxx)
    if phone_number.startswith('09') and len(phone_number) == 11:
        phone_number = '+63' + phone_number[1:]
        logger.info(f"Phone number converted: {original_number} → {phone_number}")
    elif phone_number.startswith('639') and len(phone_number) == 12:
        phone_number = '+' + phone_number
        logger.info(f"Phone number formatted: {original_number} → {phone_number}")
    elif not phone_number.startswith('+'):
        # Add + if missing for international numbers
        phone_number = '+' + phone_number
        logger.info(f"Phone number formatted: {original_number} → {phone_number}")
    else:
        logger.info(f"Phone number unchanged: {phone_number}")
        
    return phone_number

def get_contact_number_from_qr(qr_data):
    """Get contact number from QR data by querying the backend API"""
    try:
        # Query the backend API to get order details for this QR code
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/validate-qr'
        payload = {'qr_data': qr_data}
        
        response = requests.post(backend_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('valid'):
                contact_number = result.get('contact_number')
                if contact_number and contact_number != 'N/A':
                    logger.info(f"Contact number found for QR {qr_data}: {contact_number}")
                    return contact_number
                else:
                    logger.warning(f"No contact number in order for QR: {qr_data}")
            else:
                logger.warning(f"Invalid QR or no order found for: {qr_data}")
        else:
            logger.error(f"Failed to validate QR code {qr_data}: HTTP {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Network error getting contact for QR {qr_data}: {e}")
    except Exception as e:
        logger.error(f"Error getting contact number for QR {qr_data}: {e}")
        
    return None

def check_for_new_qr_scans():
    """Check for new QR code scans and clear sensor data if valid scan detected"""
    global last_scan_id, sensor_data_loaded
    
    try:
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/qr-scans?limit=1'
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
                    
                    logger.info(f"NEW QR SCAN DETECTED: {qr_data} (Valid: {is_valid})")
                    
                    # If valid scan and we have sensor data loaded, process according to requirements
                    if is_valid and sensor_data_loaded:
                        logger.info("✅ QR VALIDATION SUCCESS: Valid QR detected - Starting sequence")
                        
                        # Process QR validation sequence according to requirements
                        def process_qr_validation_sequence():
                            try:
                                # Step 1: Print receipt first
                                logger.info("�️ STEP 1 - PRINTING RECEIPT: Generating receipt for valid QR...")
                                order_details = latest_scan.get('order', {})
                                order_number = latest_scan.get('order_number', qr_data)
                                
                                # Get order details from database for printing
                                conn = sqlite3.connect('database.db')
                                conn.row_factory = dict_factory
                                c = conn.cursor()
                                c.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
                                order_data = c.fetchone()
                                conn.close()
                                
                                if order_data:
                                    # Format order data for Raspberry Pi printer
                                    printer_data = {
                                        'orderNumber': order_data['order_number'],
                                        'customerName': order_data['customer_name'],
                                        'date': order_data['date'],
                                        'email': order_data['email'],
                                        'contactNumber': order_data.get('contact_number', 'N/A'),
                                        'address': order_data['address'],
                                        'productName': order_data['product_name'],
                                        'amount': f"₱{order_data['amount']:.2f}",
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    # Call Raspberry Pi print service directly
                                    receipt_response = requests.post(
                                        f'{os.getenv("RASPBERRY_PI_URL", "http://10.194.125.227:5001")}/print-receipt',
                                        json=printer_data,
                                        timeout=10
                                    )
                                else:
                                    logger.error(f"❌ ORDER NOT FOUND: Could not find order {order_number} in database")
                                    receipt_response = None
                                
                                if receipt_response.status_code == 200:
                                    logger.info(f"✅ RECEIPT PRINTED: Receipt generated successfully for Order {order_number}")
                                else:
                                    logger.error(f"❌ RECEIPT FAILED: Could not print receipt for Order {order_number}")
                                
                                # Step 2: Start Motor B
                                logger.info("🚀 STEP 2 - MOTOR B START: Starting Motor B after receipt printing...")
                                motor_b_cycle_state['qr_validated'] = True
                                
                                motor_b_start_success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
                                if motor_b_start_success:
                                    logger.info("SUCCESS: Motor B START after QR validation (esp32/motor/request > startB)")
                                    motor_b_cycle_state['motor_b_second_run'] = True
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 'qr_motor_b_start',
                                        'status': 'motor_b_started_after_qr',
                                        'message': 'Receipt printed - Motor B started after QR validation',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'qr_validated'
                                    })
                                else:
                                    logger.error("FAILED: Could not start Motor B after QR validation")
                                    return
                                
                                # Step 3: Disable IR B (already disabled from IR B trigger, but ensure it stays disabled)
                                motor_b_cycle_state['ir_b_enabled'] = False
                                logger.info("🚫 IR B DISABLED: IR B detection remains disabled after QR validation")
                                
                                # Step 4: Send GSM SMS
                                logger.info("📱 STEP 3 - GSM SMS: Sending SMS notification...")
                                contact_number = get_contact_number_from_qr(qr_data)
                                if contact_number:
                                    formatted_number = format_phone_number(contact_number)
                                    message = "Your Parcel is Being Delivered"
                                    sms_sent = mqtt_listener.send_sms_notification(formatted_number, message)
                                    
                                    if sms_sent:
                                        logger.info(f"✅ SMS SENT: Notification sent to {formatted_number} for QR: {qr_data}")
                                    else:
                                        logger.error(f"❌ SMS FAILED: Could not send to {formatted_number} for QR: {qr_data}")
                                else:
                                    logger.warning(f"⚠️ NO CONTACT: No contact number found for QR: {qr_data}")
                                
                                # Step 5: Wait 5 seconds then send stepper back command
                                logger.info("⏳ STEP 4 - WAITING: 5 second delay before stepper back command...")
                                time.sleep(5)
                                
                                # Get package size for stepper back command
                                current_size = mqtt_sensor_data['stepper'].get('current_size', 'medium').lower()
                                back_command = f"{current_size}back"
                                
                                logger.info(f"🔄 STEP 5 - STEPPER BACK: Sending {back_command} command after 5s delay...")
                                stepper_back_success = mqtt_listener.publish_message('esp32/stepper/request', back_command)
                                
                                if stepper_back_success:
                                    logger.info(f"SUCCESS: Stepper back command sent (esp32/stepper/request > {back_command})")
                                    
                                    # Emit WebSocket notification
                                    socketio.emit('workflow_progress', {
                                        'step': 'qr_stepper_back',
                                        'status': 'stepper_back_after_qr',
                                        'message': f'QR validation complete - Stepper {back_command} sent after 5s delay',
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'qr_gsm_5s_delay'
                                    })
                                    
                                    logger.info("✅ QR SEQUENCE COMPLETE: Receipt → Motor B → GSM → 5s delay → Stepper back")
                                else:
                                    logger.error(f"❌ STEPPER BACK FAILED: Could not send {back_command} command")
                                
                            except Exception as e:
                                logger.error(f"Error in QR validation sequence: {e}")
                        
                        # Execute QR validation sequence in background thread
                        qr_thread = threading.Thread(target=process_qr_validation_sequence, daemon=True)
                        qr_thread.start()
                        
                        # Link sensor data to order in database
                        try:
                            order_id = latest_scan.get('order_id')
                            order_number = latest_scan.get('order_number', qr_data)
                            
                            if order_id:
                                logger.info(f"🔗 LINKING ORDER: Connecting Order ID {order_id} ({order_number}) to sensor data...")
                                
                                # Get current sensor data
                                backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/sensor-data'
                                sensor_response = requests.get(backend_url, timeout=5)
                                
                                if sensor_response.status_code == 200:
                                    sensor_data = sensor_response.json()
                                    
                                    # Update loaded_sensor_data with order information
                                    update_sensor_with_order_data = {
                                        'order_id': order_id,
                                        'order_number': order_number,
                                        'qr_data': qr_data,
                                        'weight': sensor_data.get('weight'),
                                        'width': sensor_data.get('width'),
                                        'height': sensor_data.get('height'),
                                        'length': sensor_data.get('length'),
                                        'package_size': sensor_data.get('package_size'),
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    # Update sensor data with order info
                                    sensor_update_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/sensor-data'
                                    sensor_update_response = requests.put(sensor_update_url, json=update_sensor_with_order_data, timeout=5)
                                    
                                    if sensor_update_response.status_code in [200, 201]:
                                        logger.info(f"✅ SENSOR DATA UPDATED: Order {order_number} linked to sensor data")
                                    
                                    # Create package information record
                                    package_info_data = update_sensor_with_order_data.copy()
                                    package_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/package-information'
                                    package_response = requests.post(package_url, json=package_info_data, timeout=5)
                                    
                                    if package_response.status_code in [200, 201]:
                                        logger.info(f"✅ PACKAGE INFO CREATED: Order {order_number} package record created")
                                        
                                        weight = sensor_data.get('weight', 'N/A')
                                        width = sensor_data.get('width', 'N/A')
                                        height = sensor_data.get('height', 'N/A') 
                                        length = sensor_data.get('length', 'N/A')
                                        package_size = sensor_data.get('package_size', 'N/A')
                                        
                                        # Convert weight to grams for display
                                        if weight != 'N/A':
                                            weight_grams = weight * 1000
                                            weight_display = f"{weight_grams:.1f}g"
                                        else:
                                            weight_display = "N/A"
                                            
                                        logger.info(f"📦 ORDER COMPLETE: {order_number} - Weight: {weight_display}, Dimensions: {width}x{height}x{length}in, Size: {package_size}")
                                        
                        except Exception as e:
                            logger.error(f"Error linking sensor data to order: {e}")
                        
                        # Emit WebSocket notification about QR processing
                        socketio.emit('qr_scan_processed', {
                            'qr_data': qr_data,
                            'timestamp': timestamp,
                            'sequence_started': True,
                            'message': 'QR validation successful - Receipt printed, Motor B started, SMS sent, Stepper back initiated'
                        })
                        
                        # Add 10-second delay before restarting the cycle
                        def restart_cycle_after_delay():
                            try:
                                logger.info("🕐 CYCLE RESTART: Starting 10-second delay before restarting cycle...")
                                
                                # Emit WebSocket notification about the delay
                                socketio.emit('workflow_progress', {
                                    'step': 'cycle_delay',
                                    'status': 'waiting',
                                    'message': '10-second delay before cycle restart',
                                    'timestamp': datetime.now().isoformat(),
                                    'triggered_by': 'qr_processing_complete'
                                })
                                
                                # Wait 10 seconds
                                time.sleep(10)
                                
                                logger.info("🛑 CYCLE RESTART: 10-second delay complete - Stopping all systems...")
                                
                                # Stop all MQTT systems
                                stop_commands = [
                                    ('esp32/motor/request', 'stopA', 'Motor A'),
                                    ('esp32/motor/request', 'stopB', 'Motor B'), 
                                    ('esp32/grabber1/request', 'stop', 'Grabber 1'),
                                    ('esp32/grabber2/request', 'stop', 'Grabber 2'),
                                    ('esp32/actuator/request', 'stop', 'Actuator'),
                                    ('esp32/loadcell/request', 'stop', 'Load Cell'),
                                    ('esp32/box/request', 'stop', 'Box System'),
                                    ('esp32/stepper/request', 'stop', 'Stepper Motor'),
                                    ('esp32/gsm/request', 'stop', 'GSM Module')
                                ]
                                
                                # Send stop commands to all systems
                                stopped_count = 0
                                for topic, command, system_name in stop_commands:
                                    try:
                                        success = mqtt_listener.publish_message(topic, command)
                                        if success:
                                            logger.info(f"🛑 {system_name} stopped (cycle restart)")
                                            stopped_count += 1
                                        else:
                                            logger.error(f"❌ Failed to stop {system_name}")
                                    except Exception as e:
                                        logger.error(f"❌ Error stopping {system_name}: {e}")
                                
                                logger.info(f"🛑 STOP COMPLETE: {stopped_count}/{len(stop_commands)} systems stopped")
                                
                                # NOTE: Sensor data clearing disabled to preserve frontend display
                                # clear_mqtt_sensor_data()
                                logger.info("🧹 Sensor data preserved for frontend display")
                                
                                # Wait 3 seconds for systems to fully stop
                                logger.info("⏳ CYCLE RESTART: Waiting 3 seconds for systems to stop...")
                                time.sleep(3)
                                
                                # Start the loop again with motor startA
                                logger.info("🔄 CYCLE RESTART: Sending motor startA to begin new cycle...")
                                restart_success = mqtt_listener.publish_message('esp32/motor/request', 'startA')
                                
                                if restart_success:
                                    logger.info("✅ CYCLE RESTARTED: Motor startA sent - New cycle begun (esp32/motor/request > startA)")
                                    
                                    # Emit WebSocket notification about cycle restart
                                    socketio.emit('workflow_restart', {
                                        'message': 'Complete cycle restarted after QR processing and 10s delay',
                                        'stopped_systems': stopped_count,
                                        'total_systems': len(stop_commands),
                                        'timestamp': datetime.now().isoformat(),
                                        'triggered_by': 'qr_complete_10s_delay'
                                    })
                                    
                                    logger.info("🔄 WORKFLOW COMPLETE: QR processed → 10s delay → All systems stopped → New cycle started")
                                else:
                                    logger.error("❌ FAILED to restart cycle - Could not send motor startA command")
                                    
                            except Exception as e:
                                logger.error(f"Error in cycle restart sequence: {e}")
                        
                        # Start the cycle restart sequence in background thread
                        threading.Thread(target=restart_cycle_after_delay, daemon=True).start()
                        
                        logger.info("Workflow completed! 10-second delay initiated before cycle restart.")
                    elif not is_valid:
                        logger.info("Invalid QR scan - sensor data remains loaded")
                    elif not sensor_data_loaded:
                        logger.debug("QR scan detected but no sensor data to clear")
                        
    except requests.RequestException as e:
        logger.error(f"Error checking for QR scans: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in QR scan monitoring: {e}")

def clear_mqtt_sensor_data():
    """Clear MQTT sensor data after successful QR scan - CURRENTLY DISABLED to preserve frontend display"""
    global mqtt_sensor_data, sensor_data_loaded
    
    logger.info("⚠️ SENSOR DATA CLEARING DISABLED: Preserving data for frontend display")
    logger.info("💡 Use /api/clear-sensor-data endpoint to manually clear if needed")
    return  # Exit early - don't clear anything
    
    # Original clearing code (currently disabled)
    try:
        # Clear local MQTT data
        mqtt_sensor_data['loadcell']['weight'] = None
        mqtt_sensor_data['loadcell']['timestamp'] = None
        mqtt_sensor_data['box_dimensions']['width'] = None
        mqtt_sensor_data['box_dimensions']['height'] = None
        mqtt_sensor_data['box_dimensions']['length'] = None
        mqtt_sensor_data['box_dimensions']['timestamp'] = None
        mqtt_sensor_data['stepper']['status'] = None
        mqtt_sensor_data['stepper']['current_size'] = None
        mqtt_sensor_data['stepper']['timestamp'] = None
        
        # Clear sensor data from main backend database
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/sensor-data'
        response = requests.delete(backend_url, timeout=5)
        
        if response.status_code == 200:
            logger.info("Sensor data cleared from database successfully!")
            sensor_data_loaded = False
        else:
            logger.warning(f"Failed to clear sensor data from database: {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Error clearing sensor data from database: {e}")
    except Exception as e:
        logger.error(f"Unexpected error clearing sensor data: {e}")

def start_qr_monitoring():
    """Start QR scan monitoring in a background thread"""
    global last_scan_id
    
    # Initialize last_scan_id to current latest scan to avoid processing old scans
    try:
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/qr-scans?limit=1'
        response = requests.get(backend_url, timeout=5)
        if response.status_code == 200:
            scans = response.json()
            if scans and len(scans) > 0:
                last_scan_id = scans[0].get('id', 0)
                logger.info(f"Initialized QR monitoring from scan ID: {last_scan_id}")
    except:
        logger.warning("Could not initialize last scan ID - will start from 0")
    
    def monitor_loop():
        logger.info("Starting QR scan monitoring...")
        while True:
            try:
                check_for_new_qr_scans()
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                logger.error(f"Error in QR monitoring loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("✅ QR scan monitoring started in background")

def determine_package_size(width, height, length):
    """Determine package size category based on dimensions (supports negative values)"""
    try:
        # Keep raw values as provided by sensors (including negative values)
        logger.info(f"📏 PACKAGE CALCULATION: Raw dimensions W:{width:.2f}cm, H:{height:.2f}cm, L:{length:.2f}cm (negative values supported)")
        
        # Calculate volume and max dimension using absolute values for classification
        volume = abs(width * height * length)  # Use absolute volume for size classification
        max_dimension = max(abs(width), abs(height), abs(length))  # Use absolute max dimension
        
        logger.info(f"📐 PACKAGE CALCULATION: Absolute Volume={volume:.2f}in³, Absolute Max dimension={max_dimension:.2f}in")
        
        # Size classification logic based on absolute values
        # Adjusted thresholds for inch measurements
        if volume <= 61 or max_dimension <= 6:  # ~61 in³ ≈ 1000 cm³, 6in ≈ 15cm
            size = "Small"
        elif volume <= 488 or max_dimension <= 12:  # ~488 in³ ≈ 8000 cm³, 12in ≈ 30cm
            size = "Medium"
        else:
            size = "Large"
        
        logger.info(f"📦 FINAL PACKAGE SIZE: {size} (Absolute Volume: {volume:.2f}in³, Absolute Max: {max_dimension:.2f}in)")
        return size
            
    except Exception as e:
        logger.error(f"Error determining package size: {e}")
        return "Small"  # Default to Small if calculation fails

def store_weight_data_in_db():
    """Store ONLY weight data in database (Step 3: Load Sensor captures weight)"""
    global sensor_data_loaded
    
    try:
        # Send only weight data to main backend
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/sensor-data'
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
                weight_grams = weight * 1000  # Convert kg to grams
                logger.info(f"📊 Weight captured: {weight_grams:.1f}g - Ready for grabber to move package")
                
                # Weight data stored - grabber will be triggered by QR scan or other workflow step
                logger.info("📦 Package weight recorded - waiting for workflow trigger")
                
                # Emit weight capture completion via WebSocket
                socketio.emit('workflow_progress', {
                    'step': 3,
                    'status': 'complete',
                    'message': f'Weight captured: {weight_grams:.1f}g - Ready for next step',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Emit weight capture progress update via WebSocket
                socketio.emit('workflow_progress', {
                    'step': 3,
                    'status': 'completed',
                    'message': f'Weight captured: {weight_grams:.1f}g',
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
        backend_url = f'{os.getenv("BACKEND_URL", "http://10.194.125.225:5000")}/api/sensor-data'
        
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
            if weight != 'N/A':
                weight_grams = weight * 1000  # Convert kg to grams
                logger.info(f"📊 COMPLETE PACKAGE DATA: Weight={weight_grams:.1f}g, Dimensions={width}x{height}x{length}cm, Size={package_size}")
                weight_display = f"{weight_grams:.1f}g"
            else:
                logger.info(f"📊 COMPLETE PACKAGE DATA: Weight=N/A, Dimensions={width}x{height}x{length}cm, Size={package_size}")
                weight_display = "N/A"
            
            # Store the calculated package size in mqtt_sensor_data for stepper use
            mqtt_sensor_data['package_size'] = package_size
            
            # Emit workflow completion via WebSocket
            socketio.emit('workflow_progress', {
                'step': 5,
                'status': 'completed',
                'message': f'Package complete: {weight_display}, {width}x{height}x{length}cm ({package_size})',
                'package_data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
            
            # Return the calculated package size for direct use by stepper
            return package_size
            
        else:
            logger.warning(f"⚠️ Failed to update sensor data with dimensions: {response.status_code}")
            return "Small"  # Default fallback
        
    except requests.RequestException as e:
        logger.error(f"❌ Error updating sensor data with dimensions: {e}")
        return "Small"  # Default fallback
    except Exception as e:
        logger.error(f"❌ Unexpected error updating sensor data: {e}")
        return "Small"  # Default fallback

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
    """Manually clear stored sensor data - ONLY way to clear since auto-clearing is disabled"""
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
        backend_url = 'http://10.194.125.225:5000/api/validate-qr'
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
        backend_package_url = 'http://10.194.125.225:5000/api/package-information'
        package_response = requests.post(backend_package_url, json=package_data, timeout=10)
        
        if package_response.status_code == 200 or package_response.status_code == 201:
            # NOTE: Sensor data clearing disabled to preserve frontend display
            # Keep sensor data available for frontend after successful application
            # mqtt_sensor_data['loadcell']['weight'] = None
            # mqtt_sensor_data['loadcell']['timestamp'] = None
            # mqtt_sensor_data['box_dimensions']['width'] = None
            # mqtt_sensor_data['box_dimensions']['height'] = None
            # mqtt_sensor_data['box_dimensions']['length'] = None
            # mqtt_sensor_data['box_dimensions']['timestamp'] = None
            
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
        camera_data = camera.get_status()
        
        # Simplify camera status for frontend
        if camera_data.get('initialization_error'):
            camera_status = "error"
        elif not camera_data.get('has_camera'):
            camera_status = "unavailable"
        elif camera_data.get('camera_running'):
            camera_status = "running"
        else:
            camera_status = "available"
            
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
    """Start motor system and proximity sensor by sending MQTT commands to ESP32"""
    try:
        logger.info("🚀 FRONTEND START: Start button clicked - Initializing proximity sensor and Motor A")
        
        # Check prevention flag
        global prevent_auto_motor_restart
        if prevent_auto_motor_restart:
            logger.info("⚠️ Motor restart prevention is ENABLED - Only manual starts allowed")
        
        # Check if MQTT is connected
        if not mqtt_listener.is_connected:
            logger.warning("MQTT not connected - cannot start motor system")
            return jsonify({
                'error': 'MQTT not connected',
                'message': 'Cannot start motor system - MQTT broker not connected'
            }), 503
        
        logger.info("MQTT is connected, starting proximity sensor and Motor A...")
        
        # Step 1: Start proximity sensor first
        proximity_success = mqtt_listener.publish_message('esp32/proximity/request', 'start')
        if proximity_success:
            logger.info("✅ PROXIMITY SENSOR STARTED: Proximity sensor activated")
        else:
            logger.error("❌ PROXIMITY FAILED: Could not start proximity sensor")
        
        # Step 2: Start Motor A
        motor_success = mqtt_listener.publish_message('esp32/motor/request', 'startA')
        
        if motor_success:
            logger.info("✅ MOTOR A STARTED: Motor A activated - Waiting for IR A detection")
            
            # Emit WebSocket notification
            socketio.emit('system_command', {
                'command': 'start_system',
                'status': 'success',
                'message': 'Proximity sensor and Motor A started - Waiting for IR A detection',
                'timestamp': datetime.now().isoformat()
            })
            
            # Also emit initial system status
            socketio.emit('workflow_progress', {
                'step': 0,
                'status': 'system_started',
                'message': 'System started - Proximity sensor and Motor A active, monitoring for objects',
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': 'Proximity sensor and Motor A started successfully',
                'proximity_started': proximity_success,
                'motor_started': motor_success,
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error("❌ Failed to start Motor A")
            return jsonify({
                'error': 'Failed to send MQTT command',
                'message': 'Could not start Motor A'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting motor: {str(e)}")
        return jsonify({
            'error': 'Failed to start motor',
            'details': str(e)
        }), 500

@app.route('/api/stop-motor', methods=['POST'])
def stop_motor():
    """Stop all systems by sending MQTT stop commands to all ESP32 modules"""
    try:
        logger.info("🛑 Emergency stop request received - Stopping all systems")
        
        # Check if MQTT is connected
        if not mqtt_listener.is_connected:
            logger.warning("❌ MQTT not connected - cannot stop systems")
            return jsonify({
                'error': 'MQTT not connected',
                'message': 'Cannot stop systems - MQTT broker not connected'
            }), 503
        
        logger.info("✅ MQTT is connected, sending stop commands to all systems...")
        
        # List of all systems to stop with their stop commands
        stop_commands = [
            ('esp32/motor/request', 'stopA', 'Motor A'),
            ('esp32/motor/request', 'stopB', 'Motor B'), 
            ('esp32/grabber1/request', 'stop', 'Grabber 1'),
            ('esp32/grabber2/request', 'stop', 'Grabber 2'),
            ('esp32/actuator/request', 'stop', 'Actuator'),
            ('esp32/loadcell/request', 'stop', 'Load Cell'),
            ('esp32/box/request', 'stop', 'Box System'),
            ('esp32/stepper/request', 'stop', 'Stepper Motor'),
            ('esp32/gsm/request', 'stop', 'GSM Module')
        ]
        
        # Send stop commands to all systems
        results = []
        for topic, command, system_name in stop_commands:
            try:
                success = mqtt_listener.publish_message(topic, command)
                if success:
                    logger.info(f"🛑 {system_name} stopped via MQTT ({topic} > {command})")
                    results.append({'system': system_name, 'status': 'stopped', 'command': f"{topic} > {command}"})
                else:
                    logger.error(f"❌ Failed to stop {system_name} ({topic} > {command})")
                    results.append({'system': system_name, 'status': 'failed', 'command': f"{topic} > {command}"})
            except Exception as e:
                logger.error(f"❌ Error stopping {system_name}: {e}")
                results.append({'system': system_name, 'status': 'error', 'error': str(e)})
        
        # NOTE: Sensor data clearing disabled to preserve frontend display
        # Clear all sensor data to reset the system state
        try:
            # clear_mqtt_sensor_data()
            logger.info("🧹 Sensor data preserved for frontend display (emergency stop)")
        except Exception as e:
            logger.error(f"⚠️ Failed to clear sensor data: {e}")
        
        # Emit WebSocket notification about emergency stop
        socketio.emit('emergency_stop', {
            'message': 'All systems stopped',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
        # Also emit the legacy system_command for backward compatibility
        socketio.emit('system_command', {
            'command': 'emergency_stop',
            'status': 'success',
            'message': 'All systems stopped via emergency stop',
            'timestamp': datetime.now().isoformat()
        })
        
        successful_stops = len([r for r in results if r['status'] == 'stopped'])
        total_systems = len(results)
        
        logger.info(f"🛑 Emergency stop completed: {successful_stops}/{total_systems} systems stopped successfully")
        
        return jsonify({
            'success': True,
            'message': f'Emergency stop completed: {successful_stops}/{total_systems} systems stopped',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
            
    except Exception as e:
        logger.error(f"Error during emergency stop: {str(e)}")
        return jsonify({
            'error': 'Failed to execute emergency stop',
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
    camera_data = camera.get_status()
    
    # Simplify camera status for frontend
    if camera_data.get('initialization_error'):
        camera_status = "error"
    elif not camera_data.get('has_camera'):
        camera_status = "unavailable"
    elif camera_data.get('camera_running'):
        camera_status = "running"
    else:
        camera_status = "available"
        
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
        request_data = request.get_json()
        
        if not request_data:
            logger.warning("Print QR request received with no data")
            return jsonify({
                'error': 'No data provided'
            }), 400

        # Extract order number - can be from orderNumber field or direct value
        order_number = request_data.get('orderNumber') or request_data.get('order_number')
        
        if not order_number:
            logger.error("No order number provided for QR printing")
            return jsonify({
                'error': 'Order number is required',
                'details': 'Please provide orderNumber or order_number field'
            }), 400

        logger.info(f"QR print request received for order: {order_number}")

        # Check if printer is available
        if not printer.check_printer():
            logger.error("Printer is not available")
            return jsonify({
                'error': 'Printer is not available',
                'details': 'Please check printer connection and USB cable'
            }), 503

        # Print only QR code
        success, message = printer.print_qr_only(order_number)
        
        if success:
            logger.info(f"Successfully printed QR code for order {order_number}")
            return jsonify({
                'message': 'QR code printed successfully',
                'order_number': str(order_number),
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"Failed to print QR code: {message}")
            return jsonify({
                'error': 'Failed to print QR code',
                'details': message
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error processing QR print request: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/print-receipt', methods=['POST'])
def print_receipt():
    try:
        # Get order data from request
        order_data = request.get_json()
        
        if not order_data:
            logger.warning("Print receipt request received with no data")
            return jsonify({
                'error': 'No order data provided'
            }), 400

        logger.info(f"Receipt print request received for order: {order_data.get('orderNumber', 'Unknown')}")

        # Check if printer is available
        if not printer.check_printer():
            logger.error("Printer is not available")
            return jsonify({
                'error': 'Printer is not available',
                'details': 'Please check printer connection and USB cable'
            }), 503

        # Required fields check
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
            logger.info(f"Successfully printed full receipt for order {sanitized_data['orderNumber']}")
            return jsonify({
                'message': 'Full receipt printed successfully',
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
        logger.error(f"Unexpected error processing receipt print request: {str(e)}", exc_info=True)
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
        backend_url = 'http://10.194.125.225:5000/api/validate-qr'
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
        # Check if QR code is valid - process asynchronously to avoid blocking camera
        if validation_result.get('valid'):
            logger.info(f"VALID QR DETECTED: {qr_data} - Starting async processing")
            # Process valid QR in background thread to avoid blocking camera
            threading.Thread(
                target=process_valid_qr_async, 
                args=(qr_data, validation_result), 
                daemon=True
            ).start()
        else:
            # For invalid QR codes, just log (no blocking operations)
            logger.info(f"INVALID QR DETECTED: {qr_data} - {validation_result.get('message', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error in QR detection callback: {e}")

def process_valid_qr_async(qr_data, validation_result):
    """Process valid QR code asynchronously to avoid blocking camera"""
    try:
        logger.info(f"ASYNC QR PROCESSING: Starting background processing for {qr_data}")
        
        # Print receipt without QR code immediately
        try:
            # Prepare order data for printing (convert from validation_result format)
            receipt_data = {
                'orderNumber': validation_result.get('order_number', qr_data),
                'customerName': validation_result.get('customer_name', 'N/A'),
                'productName': validation_result.get('product_name', 'N/A'),
                'amount': str(validation_result.get('amount', '0.00')),
                'date': validation_result.get('date', datetime.now().strftime('%Y-%m-%d')),
                'address': validation_result.get('address', 'N/A'),
                'contactNumber': validation_result.get('contact_number', 'N/A'),
                'email': validation_result.get('email', '')
            }
            
            # Create and print receipt without QR code
            receipt = printer.create_receipt(receipt_data)
            if receipt:
                success, message = printer.print_receipt(receipt)
                if success:
                    logger.info(f"RECEIPT PRINTED: Successfully printed receipt for order {qr_data}")
                else:
                    logger.error(f"RECEIPT FAILED: Failed to print receipt for order {qr_data}: {message}")
            else:
                logger.error(f"RECEIPT CREATION FAILED: Failed to create receipt for order {qr_data}")
                
        except Exception as print_error:
            logger.error(f"RECEIPT ERROR: Error printing receipt for QR {qr_data}: {print_error}")
        
        # Send motor startB command immediately when QR is validated
        try:
            logger.info(f"QR VALIDATED - MOTOR CONTROL: Sending motor startB command for validated QR {qr_data}")
            
            # Send motor startB command to begin the workflow
            motor_success = mqtt_listener.publish_message('esp32/motor/request', 'startB')
            if motor_success:
                logger.info(f"SUCCESS: Motor startB command sent (esp32/motor/request > startB)")
                
                # Emit WebSocket notification in a try-catch to prevent blocking
                try:
                    socketio.emit('motor_command', {
                        'command': 'startB',
                        'trigger': 'qr_validation',
                        'qr_data': qr_data,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as ws_error:
                    logger.warning(f"WEBSOCKET WARNING: Failed to emit motor command event: {ws_error}")
                
            else:
                logger.error(f"FAILED: Could not send motor startB command for QR {qr_data}")
                
        except Exception as motor_error:
            logger.error(f"MOTOR ERROR: Error sending motor startB command for QR {qr_data}: {motor_error}")
            
        logger.info(f"ASYNC QR PROCESSING: Completed background processing for {qr_data}")
        
    except Exception as e:
        logger.error(f"ASYNC QR PROCESSING ERROR: Unexpected error processing QR {qr_data}: {e}")

# MQTT listeners and handlers

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
    """WebSocket handler for QR-only printing"""
    try:
        # Extract order number
        order_number = data.get('orderNumber') or data.get('order_number') if data else None
        
        logger.info(f"WebSocket QR print request received for order: {order_number or 'Unknown'}")
        
        # Emit progress status
        emit('print_status', {
            'status': 'processing',
            'message': 'Processing QR print request...',
            'order_number': order_number
        })

        # Validate input data
        if not data or not order_number:
            emit('print_error', {
                'error': 'Order number is required',
                'details': 'Please provide orderNumber or order_number field',
                'order_number': order_number
            })
            return

        # Check if printer is available
        if not printer.check_printer():
            logger.error("Printer is not available")
            emit('print_error', {
                'error': 'Printer is not available',
                'details': 'Please check printer connection and USB cable',
                'order_number': order_number
            })
            return

        # Emit progress status
        emit('print_status', {
            'status': 'creating',
            'message': 'Creating QR code...',
            'order_number': order_number
        })

        # Emit progress status
        emit('print_status', {
            'status': 'printing',
            'message': 'Sending QR code to printer...',
            'order_number': order_number
        })

        # Print QR code only
        success, message = printer.print_qr_only(order_number)
        
        if success:
            logger.info(f"Successfully printed QR code for order {order_number}")
            emit('print_success', {
                'message': 'QR code printed successfully',
                'order_number': str(order_number),
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"Failed to print QR code: {message}")
            emit('print_error', {
                'error': 'Failed to print QR code',
                'details': message,
                'order_number': order_number
            })

    except Exception as e:
        logger.error(f"Unexpected error in WebSocket QR print request: {str(e)}", exc_info=True)
        emit('print_error', {
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.now().isoformat(),
            'order_number': data.get('orderNumber') if data else 'Unknown'
        })

@socketio.on('print_receipt')
def handle_print_receipt(data):
    """WebSocket handler for full receipt printing"""
    try:
        logger.info(f"WebSocket receipt print request received for order: {data.get('orderNumber', 'Unknown')}")
        
        # Emit progress status
        emit('print_status', {
            'status': 'processing',
            'message': 'Processing receipt print request...',
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
            logger.info(f"Successfully printed full receipt for order {sanitized_data['orderNumber']}")
            emit('print_success', {
                'message': 'Full receipt printed successfully',
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
        logger.error(f"Unexpected error in WebSocket receipt print request: {str(e)}", exc_info=True)
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
        backend_url = 'http://10.194.125.225:5000/api/validate-qr'
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
        backend_url = 'http://10.194.125.225:5000/api/validate-qr'
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
    
    # Test GSM SMS functionality (uncomment the line below to test)
    # test_gsm_sms("09123456789")  # Replace with your test phone number
    
    # Run the server with SocketIO - simplified configuration
    logger.info("Starting Flask-SocketIO server with integrated MQTT listener and QR monitoring")
    
    # Simple SocketIO startup to avoid Werkzeug conflicts
    socketio.run(app, 
                host=os.getenv('RASPI_HOST', '0.0.0.0'), 
                port=int(os.getenv('RASPI_PORT', '5001')), 
                debug=False)
