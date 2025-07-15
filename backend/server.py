from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from print import ReceiptPrinter
from camera import CameraManager
import logging
from datetime import datetime

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

# Enable CORS - more permissive configuration for development
CORS(app, 
     origins=["*"],  # Allow all origins
     methods=["GET", "POST", "OPTIONS"],  # Allow these methods
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)  # Allow credentials

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

if __name__ == '__main__':
    # Check printer availability at startup
    if printer.check_printer():
        logger.info("Printer is available")
    else:
        logger.warning("Printer is not available - please check connection")
    
    # Auto-start the camera at startup
    try:
        if camera.start_camera():
            logger.info("Camera auto-started at startup")
        else:
            logger.warning("Camera failed to auto-start at startup")
    except Exception as e:
        logger.warning(f"Failed to auto-start camera at startup: {str(e)}")
    
    # Run the server
    app.run(host='0.0.0.0', port=5001, debug=False)