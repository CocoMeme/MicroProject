import cv2
import threading
import time
import logging
import numpy as np
from datetime import datetime
import requests
import json

# Backend server URL (your website)
BACKEND_SERVER = 'http://192.168.100.61:5000'  # Your Flask backend

# Try to import Raspberry Pi specific modules, fall back to mock if not available
try:
    from picamera2 import Picamera2
    MOCK_CAMERA = False
except ImportError:
    MOCK_CAMERA = True
    class Picamera2:
        def __init__(self):
            pass
        def configure(self, config):
            pass
        def create_video_configuration(self, main=None):
            return {}
        def start(self):
            pass
        def stop(self):
            pass
        def capture_array(self):
            # Return a mock frame with some text
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "MOCK CAMERA - NO RASPBERRY PI", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            return frame

try:
    from pyzbar.pyzbar import decode
except ImportError:
    def decode(frame):
        # Mock QR code detection - return empty list
        return []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraManager:
    def __init__(self):
        self.picam2 = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.last_qr_data = None
        self.capture_thread = None
        self.initialization_error = None
        self.scanned_qr_history = []  # Store history of scanned QR codes
        self.max_history = 50  # Keep last 50 scanned codes

        try:
            self.picam2 = Picamera2()
            if not MOCK_CAMERA:
                self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
            logger.info(f"Camera initialized successfully {'(MOCK MODE)' if MOCK_CAMERA else ''}")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Camera initialization failed: {e}")

    def validate_qr_with_database(self, qr_data):
        """Validate QR code against orders database via HTTP request to website backend"""
        try:
            # Make HTTP request to backend server to validate QR code
            response = requests.post(
                f'{BACKEND_SERVER}/api/validate-qr',
                json={'qr_data': qr_data},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'valid': False, 'message': f'Backend server error: {response.status_code}'}
                
        except requests.RequestException as e:
            logger.error(f"HTTP request error: {e}")
            return {'valid': False, 'message': f'Connection error: {str(e)}'}
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {'valid': False, 'message': f'Validation error: {str(e)}'}

    def sync_qr_history_to_backend(self):
        """Send QR history to the main backend server"""
        try:
            if self.scanned_qr_history:
                response = requests.post(
                    f'{BACKEND_SERVER}/api/qr-scans',
                    json={'scans': self.scanned_qr_history},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info("QR history synced to backend successfully")
                else:
                    logger.warning(f"Failed to sync QR history: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to sync QR history: {e}")

    def add_to_qr_history(self, qr_data, validation_result):
        """Add scanned QR code to history"""
        history_entry = {
            'qr_data': qr_data,
            'timestamp': datetime.now().isoformat(),
            'validation': validation_result,
            'device': 'raspberry_pi'  # Identify source
        }
        
        self.scanned_qr_history.insert(0, history_entry)  # Add to beginning
        
        # Keep only the last max_history entries
        if len(self.scanned_qr_history) > self.max_history:
            self.scanned_qr_history = self.scanned_qr_history[:self.max_history]
        
        logger.info(f"Added QR to history: {qr_data} - Valid: {validation_result.get('valid', False)}")
        
        # Sync to backend in a separate thread to avoid blocking
        threading.Thread(target=self.sync_qr_history_to_backend, daemon=True).start()

    def start_camera(self):
        if self.initialization_error:
            logger.error(f"Cannot start camera: {self.initialization_error}")
            return False

        if self.running:
            logger.warning("Camera already running")
            return False

        try:
            self.picam2.start()
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info("Camera started")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.running = False
            try:
                self.picam2.stop()
            except:
                pass
            return False

    def stop_camera(self):
        if not self.running:
            logger.warning("Camera is not running")
            return False

        try:
            self.running = False
            self.picam2.stop()
            if self.capture_thread:
                self.capture_thread.join(timeout=2.0)
            logger.info("Camera stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop camera: {e}")
            return False

    def _capture_loop(self):
        logger.info("Capture loop started")
        while self.running:
            try:
                frame = self.picam2.capture_array()
                frame_with_qr = self._scan_qr_code(frame)
                with self.lock:
                    self.frame = frame_with_qr
                time.sleep(0.03)
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                self.running = False
                break

    def _scan_qr_code(self, frame):
        try:
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                if data != self.last_qr_data:
                    self.last_qr_data = data
                    
                    # Validate QR code against database
                    validation_result = self.validate_qr_with_database(data)
                    
                    # Add to history
                    self.add_to_qr_history(data, validation_result)
                    
                    if validation_result['valid']:
                        logger.info(f"Valid QR code detected: {data} - Order: {validation_result['order_number']}")
                    else:
                        logger.warning(f"Invalid QR code detected: {data} - {validation_result['message']}")

                # Draw a bounding box around the QR code
                points = obj.polygon
                if len(points) >= 4:
                    # Use different colors based on validation
                    validation_result = self.validate_qr_with_database(data)
                    color = (0, 255, 0) if validation_result['valid'] else (0, 0, 255)  # Green for valid, red for invalid
                    
                    pts = [(point.x, point.y) for point in points]
                    cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], isClosed=True, color=color, thickness=3)

                # Display the decoded text with validation status
                x, y, w, h = obj.rect
                validation_result = self.validate_qr_with_database(data)
                status_text = "Valid" if validation_result['valid'] else "Not Valid"
                display_text = f"{data} - {status_text}"
                text_color = (0, 255, 0) if validation_result['valid'] else (0, 0, 255)
                cv2.putText(frame, display_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

        except Exception as e:
            logger.error(f"QR code scan error: {e}")
        return frame

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            try:
                _, jpeg = cv2.imencode('.jpg', self.frame)
                return jpeg.tobytes()
            except Exception as e:
                logger.error(f"Frame encoding error: {e}")
                return None

    def get_status(self):
        return {
            "camera_running": self.running,
            "initialization_error": self.initialization_error,
            "has_camera": self.picam2 is not None
        }

    def get_last_qr(self):
        return self.last_qr_data or ""

    def get_qr_history(self):
        """Get the history of scanned QR codes"""
        return self.scanned_qr_history
