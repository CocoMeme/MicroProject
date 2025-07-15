from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from print import ReceiptPrinter
from camera import CameraManager
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

# Initialize SocketIO with CORS enabled
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

printer = ReceiptPrinter()
camera = CameraManager()

@app.route('/status')
def status():
    """General status endpoint"""
    try:
        printer_status = "available" if printer.check_printer() else "unavailable"
        camera_status = camera.get_status()
        return jsonify({
            "status": "running",
            "printer": printer_status,
            "camera": camera_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.after_request
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
    return jsonify({
        "status": "running",
        "printer": printer_status,
        "camera": camera_status
    })

@app.route('/print-qr', methods=['POST'])
def print_qr():
    try:
        # Get order data from request
        order_data = request.get_json()
        
        if not order_data:
            return jsonify({
                'error': 'No order data provided'
            }), 400

        # Check if printer is available
        if not printer.check_printer():
            return jsonify({
                'error': 'Printer is not available',
                'details': 'Please check printer connection'
            }), 503

        # Required fields check
        required_fields = ['orderNumber', 'customerName', 'email', 'productName', 'amount', 'date']
        missing_fields = [field for field in required_fields if field not in order_data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        # Create receipt image
        receipt = printer.create_receipt(order_data)
        
        if not receipt:
            return jsonify({
                'error': 'Failed to create receipt'
            }), 500

        # Print receipt
        success, message = printer.print_receipt(receipt)
        
        if success:
            logger.info(f"Successfully printed receipt for order {order_data['orderNumber']}")
            return jsonify({
                'message': 'Receipt printed successfully',
                'order_number': order_data['orderNumber']
            })
        else:
            logger.error(f"Failed to print receipt: {message}")
            return jsonify({
                'error': 'Failed to print receipt',
                'details': message
            }), 500

    except Exception as e:
        logger.error(f"Error processing print request: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
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
        
        socketio.emit('qr_detected', {
            'data': qr_data,
            'timestamp': datetime.now().isoformat(),
            'type': 'QR Code',
            'validation': validation_result,
            'latest_scan': latest_scan
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
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Status broadcast error: {e}")
        
        time.sleep(5)  # Broadcast status every 5 seconds

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to Raspberry Pi WebSocket')
    emit('camera_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from Raspberry Pi WebSocket')

@socketio.on('start_camera')
def handle_start_camera():
    try:
        if camera.start_camera():
            emit('camera_status', {'status': 'started'})
        else:
            emit('camera_error', {'error': 'Failed to start camera'})
    except Exception as e:
        emit('camera_error', {'error': str(e)})

@socketio.on('stop_camera')
def handle_stop_camera():
    try:
        if camera.stop_camera():
            emit('camera_status', {'status': 'stopped'})
        else:
            emit('camera_error', {'error': 'Failed to stop camera'})
    except Exception as e:
        emit('camera_error', {'error': str(e)})

@socketio.on('get_system_status')
def handle_get_system_status():
    try:
        emit('system_status', {
            'camera_system': camera.get_status(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        emit('camera_error', {'error': str(e)})

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
    
    # Run the server with SocketIO
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)