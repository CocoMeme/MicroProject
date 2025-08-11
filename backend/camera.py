import cv2
import threading
import time
import logging
import numpy as np
from datetime import datetime
import requests
import json
import base64
import os
import sys
import warnings
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend server URL (your website)
BACKEND_SERVER = os.getenv('BACKEND_URL', 'http://10.194.125.225:5000')

# Try to import Raspberry Pi specific modules, fall back to mock if not available
try:
    from picamera2 import Picamera2
    MOCK_CAMERA = False
    PICAMERA2_VERSION = None
    try:
        import picamera2
        if hasattr(picamera2, '__version__'):
            PICAMERA2_VERSION = picamera2.__version__
    except:
        pass
except ImportError:
    MOCK_CAMERA = True
    PICAMERA2_VERSION = None
    
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

# Try to import QR code decoder
try:
    from pyzbar.pyzbar import decode
except ImportError:
    def decode(frame):
        # Mock QR code detection - return empty list
        return []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZBarWarningFilter(logging.Filter):
    """Filter to suppress ZBar decoder warnings"""
    
    def filter(self, record):
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            zbar_patterns = [
                '_zbar_decode_databar: Assertion',
                'decoder/databar.c',
                'WARNING: decoder/databar.c',
                'failed.',
                'f=-1(010) part=0'
            ]
            if any(pattern in message for pattern in zbar_patterns):
                return False
        return True

class StderrFilter:
    """Custom stderr filter to suppress ZBar warnings"""
    
    def __init__(self):
        self.original_stderr = sys.stderr
        self.buffer = ""
        
    def write(self, s):
        self.buffer += s
        
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            
            zbar_patterns = [
                '_zbar_decode_databar: Assertion',
                'decoder/databar.c',
                'WARNING: decoder/databar.c',
                'failed.\n        i=',
                'f=-1(010) part=0'
            ]
            
            should_filter = any(pattern in line for pattern in zbar_patterns)
            
            if not should_filter:
                self.original_stderr.write(line + '\n')
    
    def flush(self):
        if self.buffer:
            zbar_patterns = [
                '_zbar_decode_databar: Assertion',
                'decoder/databar.c',
                'WARNING: decoder/databar.c',
                'failed.\n        i=',
                'f=-1(010) part=0'
            ]
            
            should_filter = any(pattern in self.buffer for pattern in zbar_patterns)
            if not should_filter:
                self.original_stderr.write(self.buffer)
            self.buffer = ""
            
        self.original_stderr.flush()

class OSLevelStderrFilter:
    """OS-level stderr filter for ZBar warnings"""
    
    def __init__(self):
        self.original_stderr = sys.stderr
        self.temp_file = None
        
    def __enter__(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.original_stderr_fd = os.dup(2)
        os.dup2(self.temp_file.fileno(), 2)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.dup2(self.original_stderr_fd, 2)
        os.close(self.original_stderr_fd)
        
        if self.temp_file:
            self.temp_file.seek(0)
            content = self.temp_file.read()
            self.temp_file.close()
            
            if content:
                lines = content.split('\n')
                for line in lines:
                    zbar_patterns = [
                        '_zbar_decode_databar: Assertion',
                        'decoder/databar.c',
                        'WARNING: decoder/databar.c',
                        'failed.',
                        'f=-1(010) part=0'
                    ]
                    
                    if not any(pattern in line for pattern in zbar_patterns) and line.strip():
                        self.original_stderr.write(line + '\n')
            
            try:
                os.unlink(self.temp_file.name)
            except:
                pass

def suppress_zbar_fd_warnings():
    """Temporarily redirect stderr to null device during ZBar operations"""
    try:
        original_stderr_fd = os.dup(2)
        null_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null_fd, 2)
        os.close(null_fd)
        return original_stderr_fd
    except (ImportError, OSError, AttributeError):
        return None

def restore_stderr_fd(original_fd):
    """Restore original stderr file descriptor"""
    if original_fd is not None:
        try:
            os.dup2(original_fd, 2)
            os.close(original_fd)
        except:
            pass

# Initialize warning suppression
logger.info("ZBar warning suppression activated - decoder warnings will be filtered")

# Suppress warnings at various levels
warnings.filterwarnings("ignore", message=".*zbar.*")
warnings.filterwarnings("ignore", message=".*databar.*")

# Set environment variables to suppress ZBar debug output
os.environ['ZBAR_DEBUG'] = '0'
os.environ['ZBAR_QUIET'] = '1'
os.environ['ZBAR_SILENCE'] = '1'

# Apply stderr filter
sys.stderr = StderrFilter()

# Try to suppress ZBar warnings at library level
try:
    import zbar
    if hasattr(zbar, 'set_verbosity'):
        zbar.set_verbosity(0)
except (ImportError, AttributeError):
    pass

# Try to configure libzbar using ctypes
try:
    import ctypes
    import ctypes.util
    
    libzbar_path = ctypes.util.find_library('zbar')
    if libzbar_path:
        libzbar = ctypes.CDLL(libzbar_path)
        if hasattr(libzbar, 'zbar_set_verbosity'):
            libzbar.zbar_set_verbosity(0)
except (ImportError, OSError, AttributeError):
    pass

class CameraManager:
    """
    Camera manager for QR code scanning with Raspberry Pi or mock camera
    """
    
    def __init__(self):
        # Camera setup
        self.picam2 = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.capture_thread = None
        self.initialization_error = None
        
        # QR code detection and validation
        self.last_qr_data = None
        self.last_qr_time = None
        self.qr_cooldown = 3  # Minimum seconds between same QR detections
        self.qr_callbacks = []
        self.scanned_qr_codes = set()
        self.duplicate_prevention_enabled = True
        
        # QR validation cache to prevent repeated database calls
        self.validation_cache = {}  # qr_data -> (validation_result, timestamp)
        self.validation_cache_timeout = 30  # Cache for 30 seconds
        
        # QR code history and storage
        self.scanned_qr_history = []
        self.max_history = 50
        
        # Display message system
        self.display_message = None
        self.display_message_color = None
        self.display_message_start_time = None
        self.display_message_duration = 0
        self.pending_already_scanned = False
        self.pending_already_scanned_start_time = None
        self.current_qr_data = None
        self.current_qr_rect = None
        
        # Scanning cycle configuration
        self.scanning_enabled = False
        self.scan_start_time = None
        self.countdown_delay = 10.0  # 10 seconds countdown
        self.scanning_duration = 60.0  # 60 seconds active scanning
        self.scanning_session_start = None
        self.scanning_state = "countdown"  # "countdown", "scanning", "session_ended"
        
        # Initialize camera and create QR images directory
        self._setup_qr_images_directory()
        self._initialize_camera()

    def _setup_qr_images_directory(self):
        """Create directory for storing QR code images"""
        self.qr_images_dir = 'qr_images'
        if not os.path.exists(self.qr_images_dir):
            os.makedirs(self.qr_images_dir)

    def _initialize_camera(self):
        """Initialize the camera (Raspberry Pi or mock) with version compatibility"""
        try:
            self.picam2 = Picamera2()
            if not MOCK_CAMERA:
                # Handle different PiCamera2 versions
                try:
                    # Try newer PiCamera2 API (v0.3.13+)
                    config = self.picam2.create_video_configuration(main={"size": (640, 480)})
                    self.picam2.configure(config)
                except Exception as config_error:
                    logger.warning(f"New API failed, trying compatibility mode: {config_error}")
                    try:
                        # Fallback for older versions
                        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
                    except Exception as fallback_error:
                        logger.error(f"Both camera configuration methods failed: {fallback_error}")
                        raise fallback_error
                        
            logger.info(f"Camera initialized successfully {'(MOCK MODE)' if MOCK_CAMERA else ''} - PiCamera2 version: {PICAMERA2_VERSION or 'Unknown'}")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Camera initialization failed: {e}")
            # Try to create a mock camera as fallback
            if not MOCK_CAMERA:
                logger.info("Attempting to create mock camera as fallback")
                try:
                    self.picam2 = type('MockPicam2', (), {
                        'configure': lambda self, config: None,
                        'create_video_configuration': lambda self, main=None: {},
                        'start': lambda self: None,
                        'stop': lambda self: None,
                        'capture_array': lambda self: self._mock_frame()
                    })()
                    
                    def _mock_frame():
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "CAMERA ERROR - USING MOCK", (50, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        return frame
                    
                    self.picam2._mock_frame = _mock_frame
                    logger.info("Mock camera fallback created")
                except Exception as mock_error:
                    logger.error(f"Failed to create mock camera fallback: {mock_error}")

    # QR Code Callback Management
    def add_qr_callback(self, callback):
        """Add a callback function to be called when new QR is detected"""
        self.qr_callbacks.append(callback)

    def _notify_qr_callbacks(self, qr_data, validation_result):
        """Notify all registered callbacks about new QR detection with timeout protection"""
        for callback in self.qr_callbacks:
            try:
                # Use threading to prevent callback from blocking camera
                callback_thread = threading.Thread(
                    target=self._safe_callback_wrapper,
                    args=(callback, qr_data, validation_result),
                    daemon=True
                )
                callback_thread.start()
                logger.debug(f"QR callback started in background thread for {qr_data}")
            except Exception as e:
                logger.error(f"QR callback thread creation error: {e}")
    
    def _safe_callback_wrapper(self, callback, qr_data, validation_result):
        """Wrapper for safe callback execution with error handling"""
        try:
            callback(qr_data, validation_result)
        except Exception as e:
            logger.error(f"QR callback execution error: {e}")

    # QR Code Duplicate Prevention
    def is_qr_already_scanned(self, qr_data):
        """Check if QR code has already been scanned"""
        return qr_data in self.scanned_qr_codes

    def mark_qr_as_scanned(self, qr_data):
        """Mark QR code as scanned to prevent duplicate scanning"""
        self.scanned_qr_codes.add(qr_data)
        logger.info(f"QR code marked as scanned: {qr_data}")

    def clear_scanned_qr(self, qr_data):
        """Remove QR code from scanned list to allow rescanning"""
        if qr_data in self.scanned_qr_codes:
            self.scanned_qr_codes.remove(qr_data)
            # Also clear from validation cache
            if qr_data in self.validation_cache:
                del self.validation_cache[qr_data]
            logger.info(f"QR code cleared for rescanning: {qr_data}")
            return True
        return False

    def clear_all_scanned_qr_codes(self):
        """Clear all scanned QR codes to allow rescanning of everything"""
        count = len(self.scanned_qr_codes)
        self.scanned_qr_codes.clear()
        # Also clear validation cache
        self.validation_cache.clear()
        logger.info(f"Cleared {count} scanned QR codes and validation cache")
        return count

    def get_scanned_qr_codes(self):
        """Get list of all scanned QR codes"""
        return list(self.scanned_qr_codes)

    def set_duplicate_prevention(self, enabled):
        """Enable or disable duplicate prevention"""
        self.duplicate_prevention_enabled = enabled
        logger.info(f"Duplicate prevention {'enabled' if enabled else 'disabled'}")

    def get_duplicate_prevention_status(self):
        """Get current duplicate prevention status"""
        return {
            'enabled': self.duplicate_prevention_enabled,
            'scanned_count': len(self.scanned_qr_codes),
            'scanned_codes': list(self.scanned_qr_codes)
        }

    # Scanning Cycle Management
    def reset_scan_cycle(self):
        """Reset the scanning cycle to start countdown again"""
        self.scanning_enabled = False
        self.scan_start_time = time.time()
        self.scanning_state = "countdown"
        self.scanning_session_start = None
        self._clear_display_messages()
        logger.info(f"Scanning cycle reset - Starting countdown ({self.countdown_delay}s countdown, {self.scanning_duration}s scanning session)")

    def reset_scan_cycle_if_running(self):
        """Reset the scanning cycle even if camera is already running"""
        if self.running:
            self.scanning_enabled = False
            self.scan_start_time = time.time()
            self.scanning_state = "countdown"
            self.scanning_session_start = None
            self._clear_display_messages()
            logger.info(f"Scanning cycle reset while camera running - Starting countdown ({self.countdown_delay}s countdown, {self.scanning_duration}s scanning session)")
            return True
        else:
            logger.warning("Cannot reset scan cycle - camera is not running")
            return False

    def start_scanning_session_immediately(self):
        """Start scanning session immediately, skipping countdown"""
        self.scanning_enabled = True
        self.scanning_state = "scanning"
        self.scanning_session_start = time.time()
        self.scan_start_time = None
        logger.info(f"Scanning session started immediately - {self.scanning_duration}s active period")

    def get_scanning_status(self):
        """Get current scanning cycle status"""
        if not self.scan_start_time and not self.scanning_session_start:
            return {
                "state": "disabled",
                "scanning_enabled": False,
                "time_remaining": 0,
                "countdown_seconds": self.countdown_delay,
                "scanning_duration": self.scanning_duration
            }
        
        current_time = time.time()
        
        if self.scanning_state == "countdown" and self.scan_start_time:
            time_elapsed = current_time - self.scan_start_time
            time_remaining = max(0, self.countdown_delay - time_elapsed)
            return {
                "state": "countdown",
                "scanning_enabled": False,
                "time_remaining": int(time_remaining),
                "countdown_seconds": self.countdown_delay,
                "scanning_duration": self.scanning_duration
            }
        elif self.scanning_state == "scanning" and self.scanning_session_start:
            session_elapsed = current_time - self.scanning_session_start
            time_remaining = max(0, self.scanning_duration - session_elapsed)
            return {
                "state": "scanning",
                "scanning_enabled": True,
                "time_remaining": int(time_remaining),
                "countdown_seconds": self.countdown_delay,
                "scanning_duration": self.scanning_duration
            }
        else:
            return {
                "state": "unknown",
                "scanning_enabled": self.scanning_enabled,
                "time_remaining": 0,
                "countdown_seconds": self.countdown_delay,
                "scanning_duration": self.scanning_duration
            }

    def _clear_display_messages(self):
        """Clear all display messages and related state"""
        self.display_message = None
        self.display_message_start_time = None
        self.pending_already_scanned = False
        self.pending_already_scanned_start_time = None
        self.current_qr_data = None
        self.current_qr_rect = None

    # QR Code Image Storage
    def save_qr_image(self, frame, qr_data, qr_bounds):
        """Save an image of the detected QR code"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            clean_qr_data = qr_data.replace('/', '_').replace('\\', '_')[:20]
            filename = f"qr_{timestamp}_{clean_qr_data}.jpg"
            filepath = os.path.join(self.qr_images_dir, filename)
            
            # Crop image around QR code if bounds are available
            if qr_bounds:
                x, y, w, h = qr_bounds
                padding = 50
                x_start = max(0, x - padding)
                y_start = max(0, y - padding)
                x_end = min(frame.shape[1], x + w + padding)
                y_end = min(frame.shape[0], y + h + padding)
                
                cropped_frame = frame[y_start:y_end, x_start:x_end]
                cv2.imwrite(filepath, cropped_frame)
            else:
                cv2.imwrite(filepath, frame)
            
            # Convert image to base64
            _, buffer = cv2.imencode('.jpg', cropped_frame if qr_bounds else frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.info(f"Saved QR image: {filename}")
            return {
                'filename': filename,
                'filepath': filepath,
                'base64': img_base64
            }
        except Exception as e:
            logger.error(f"Failed to save QR image: {e}")
            return None

    # QR Code Validation and Backend Communication
    def get_cached_validation(self, qr_data):
        """Get cached validation result if available and not expired"""
        if qr_data in self.validation_cache:
            result, timestamp = self.validation_cache[qr_data]
            if time.time() - timestamp < self.validation_cache_timeout:
                return result
            else:
                # Remove expired cache entry
                del self.validation_cache[qr_data]
        return None
    
    def cache_validation_result(self, qr_data, validation_result):
        """Cache validation result with timestamp"""
        self.validation_cache[qr_data] = (validation_result, time.time())
        # Clean up old cache entries (keep only last 10)
        if len(self.validation_cache) > 10:
            oldest_key = min(self.validation_cache.keys(), 
                           key=lambda k: self.validation_cache[k][1])
            del self.validation_cache[oldest_key]

    def validate_qr_with_database(self, qr_data):
        """Validate QR code against orders database via HTTP request to website backend"""
        # Check cache first
        cached_result = self.get_cached_validation(qr_data)
        if cached_result:
            logger.debug(f"Using cached validation for {qr_data}")
            return cached_result
            
        try:
            logger.info(f"Validating QR code: {qr_data} with backend at {BACKEND_SERVER}")
            response = requests.post(
                f'{BACKEND_SERVER}/api/validate-qr',
                json={
                    'qr_data': qr_data,
                    'source': 'camera',
                    'skip_print': True
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Validation result for {qr_data}: {result}")
                # Cache the result
                self.cache_validation_result(qr_data, result)
                return result
            else:
                logger.warning(f"Backend server error for {qr_data}: {response.status_code} - {response.text}")
                result = {'valid': False, 'message': f'Backend server error: {response.status_code}'}
                self.cache_validation_result(qr_data, result)
                return result
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error validating {qr_data}: {e}")
            result = {'valid': False, 'message': f'Connection error: {str(e)}'}
            self.cache_validation_result(qr_data, result)
            return result
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error validating {qr_data}: {e}")
            result = {'valid': False, 'message': f'Timeout error: {str(e)}'}
            self.cache_validation_result(qr_data, result)
            return result
        except requests.RequestException as e:
            logger.error(f"HTTP request error validating {qr_data}: {e}")
            result = {'valid': False, 'message': f'Connection error: {str(e)}'}
            self.cache_validation_result(qr_data, result)
            return result
        except Exception as e:
            logger.error(f"Validation error for {qr_data}: {e}")
            result = {'valid': False, 'message': f'Validation error: {str(e)}'}
            self.cache_validation_result(qr_data, result)
            return result

    def sync_qr_history_to_backend(self):
        """Send QR history to the main backend server"""
        try:
            if self.scanned_qr_history:
                logger.info(f"Syncing {len(self.scanned_qr_history)} QR scans to backend...")
                response = requests.post(
                    f'{BACKEND_SERVER}/api/qr-scans',
                    json={'scans': self.scanned_qr_history},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info("QR history synced to backend successfully")
                else:
                    logger.warning(f"Failed to sync QR history: {response.status_code} - {response.text}")
            else:
                logger.info("No QR history to sync")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error syncing QR history: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error syncing QR history: {e}")
        except Exception as e:
            logger.error(f"Failed to sync QR history: {e}")

    def add_to_qr_history(self, qr_data, validation_result, image_data=None):
        """Add scanned QR code to history"""
        history_entry = {
            'qr_data': qr_data,
            'timestamp': datetime.now().isoformat(),
            'validation': validation_result,
            'device': 'raspberry_pi',
            'image_data': image_data
        }
        
        self.scanned_qr_history.insert(0, history_entry)
        
        # Keep only the last max_history entries
        if len(self.scanned_qr_history) > self.max_history:
            self.scanned_qr_history = self.scanned_qr_history[:self.max_history]
        
        logger.info(f"Added QR to history: {qr_data} - Valid: {validation_result.get('valid', False)}")
        
        # Sync to backend in a separate thread
        threading.Thread(target=self.sync_qr_history_to_backend, daemon=True).start()

    def get_qr_history(self):
        """Get the history of scanned QR codes"""
        return self.scanned_qr_history

    # Camera Control Methods
    def start_camera(self):
        """Start the camera and begin capture loop"""
        if self.initialization_error:
            logger.error(f"Cannot start camera: {self.initialization_error}")
            return False

        if self.running:
            logger.warning("Camera already running")
            return False

        try:
            self.picam2.start()
            self.running = True
            # Initialize scanning cycle
            self.scanning_enabled = False
            self.scan_start_time = time.time()
            self.scanning_state = "countdown"
            self.scanning_session_start = None
            logger.info(f"Camera started - QR scanning countdown begins ({self.countdown_delay}s countdown, {self.scanning_duration}s scanning session)")
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
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
        """Stop the camera and cleanup"""
        if not self.running:
            logger.warning("Camera is not running")
            return False

        try:
            self.running = False
            # Reset scanning cycle state when camera stops
            self.scanning_enabled = False
            self.scan_start_time = None
            self.scanning_state = "countdown"
            self.scanning_session_start = None
            self._clear_display_messages()
            
            self.picam2.stop()
            if self.capture_thread:
                self.capture_thread.join(timeout=2.0)
            logger.info("Camera stopped and scanning cycle reset")
            return True
        except Exception as e:
            logger.error(f"Failed to stop camera: {e}")
            return False

    def _capture_loop(self):
        """Main capture loop running in separate thread with enhanced error handling"""
        logger.info("Capture loop started")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                # Attempt to capture frame with error recovery
                frame = self._safe_capture_frame()
                if frame is not None:
                    frame_with_qr = self._scan_qr_code(frame)
                    with self.lock:
                        self.frame = frame_with_qr
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    consecutive_errors += 1
                    logger.warning(f"Failed to capture frame (consecutive errors: {consecutive_errors})")
                    
                # Check if too many consecutive errors occurred
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive capture errors ({consecutive_errors}), stopping camera")
                    self.running = False
                    break
                    
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Capture loop error: {e} (consecutive errors: {consecutive_errors})")
                
                # Stop after too many errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Maximum consecutive errors reached, stopping capture loop")
                    self.running = False
                    break
                    
                # Brief pause before retry
                time.sleep(0.1)

    def _safe_capture_frame(self):
        """Safely capture a frame with error handling for different PiCamera2 versions"""
        try:
            # Try to capture frame
            return self.picam2.capture_array()
        except AttributeError as attr_error:
            if "'Picamera2' object has no attribute 'allocator'" in str(attr_error):
                logger.error("PiCamera2 allocator error detected - this is a known version compatibility issue")
                logger.info("Attempting to restart camera to recover from allocator error")
                
                # Try to recover by restarting the camera
                try:
                    self.picam2.stop()
                    time.sleep(0.5)
                    self.picam2.start()
                    time.sleep(0.5)
                    return self.picam2.capture_array()
                except Exception as recovery_error:
                    logger.error(f"Camera recovery failed: {recovery_error}")
                    # Return a mock frame as fallback
                    return self._create_error_frame("Camera Error - Recovery Failed")
            else:
                logger.error(f"Camera attribute error: {attr_error}")
                return self._create_error_frame("Camera Attribute Error")
                
        except Exception as e:
            logger.error(f"Camera capture error: {e}")
            return self._create_error_frame(f"Capture Error: {str(e)[:50]}")

    def _create_error_frame(self, error_message):
        """Create an error frame when camera capture fails"""
        try:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, error_message, (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", (50, 280), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            return frame
        except Exception as e:
            logger.error(f"Failed to create error frame: {e}")
            return np.zeros((480, 640, 3), dtype=np.uint8)

    def _scan_qr_code(self, frame):
        """Main QR code scanning logic with display overlay and cycle management"""
        try:
            current_time = time.time()
            
            # Handle scanning cycle state transitions
            self._update_scanning_cycle(current_time, frame)
            
            # Return early if scanning is not enabled
            if not self.scanning_enabled:
                return self._add_countdown_overlay(frame)
            
            # Update display messages
            self._update_display_messages(current_time, frame)
            
            # Decode QR codes with warning suppression
            decoded_objects = self._decode_qr_codes_safely(frame)
            
            # Process each detected QR code
            for obj in decoded_objects:
                self._process_qr_code(obj, frame, current_time)
                
        except Exception as e:
            logger.error(f"QR code scan error: {e}")
        
        return frame

    def _update_scanning_cycle(self, current_time, frame):
        """Update scanning cycle state and display appropriate messages"""
        if self.scan_start_time is None:
            return
            
        if self.scanning_state == "countdown":
            time_elapsed = current_time - self.scan_start_time
            if time_elapsed < self.countdown_delay:
                remaining_time = int(self.countdown_delay - time_elapsed)
                cv2.putText(frame, f"Scanning starts in: {remaining_time}s", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.putText(frame, "Position QR code now", 
                           (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                # Start scanning session
                self.scanning_enabled = True
                self.scanning_state = "scanning"
                self.scanning_session_start = current_time
                logger.info(f"QR scanning session started - {self.scanning_duration}s active period")
                
        elif self.scanning_state == "scanning":
            session_elapsed = current_time - self.scanning_session_start
            if session_elapsed >= self.scanning_duration:
                # End scanning session, restart countdown
                self.scanning_enabled = False
                self.scanning_state = "countdown"
                self.scan_start_time = current_time
                self.scanning_session_start = None
                logger.info(f"Scanning session ended - Starting new countdown ({self.countdown_delay}s)")
            else:
                # Show active scanning status
                remaining_scan_time = int(self.scanning_duration - session_elapsed)
                cv2.putText(frame, f"SCANNING ACTIVE: {remaining_scan_time}s left", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    def _add_countdown_overlay(self, frame):
        """Add countdown overlay when scanning is not active"""
        if self.scanning_state == "countdown":
            cv2.putText(frame, "Preparing to scan...", 
                       (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        return frame

    def _update_display_messages(self, current_time, frame):
        """Update and display QR scan result messages"""
        # Check if we need to show "Already Scanned!" message after valid message expires
        if (self.pending_already_scanned and 
            self.pending_already_scanned_start_time and 
            current_time >= self.pending_already_scanned_start_time):
            self.display_message = "Already Scanned!"
            self.display_message_color = (0, 165, 255)  # Orange
            self.display_message_start_time = current_time
            self.display_message_duration = 3.0
            self.pending_already_scanned = False
            self.pending_already_scanned_start_time = None
        
        # Display current message if active
        if (self.display_message and 
            self.display_message_start_time and 
            current_time - self.display_message_start_time < self.display_message_duration and
            self.current_qr_rect):
            x, y, w, h = self.current_qr_rect
            cv2.putText(frame, f"{self.current_qr_data} - {self.display_message}", 
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.display_message_color, 2)
        
        # Clear expired messages
        if (self.display_message_start_time and 
            current_time - self.display_message_start_time >= self.display_message_duration):
            self._clear_display_messages()

    def _decode_qr_codes_safely(self, frame):
        """Decode QR codes with comprehensive warning suppression"""
        try:
            with OSLevelStderrFilter():
                original_stderr_fd = suppress_zbar_fd_warnings()
                try:
                    decoded_objects = decode(frame)
                finally:
                    restore_stderr_fd(original_stderr_fd)
                return decoded_objects
        except Exception as decode_error:
            # Fallback to regular decode
            try:
                return decode(frame)
            except Exception:
                logger.debug(f"QR decode failed: {decode_error}")
                return []

    def _process_qr_code(self, obj, frame, current_time):
        """Process a single detected QR code"""
        data = obj.data.decode('utf-8')
        
        # Check if QR code is already locally marked as scanned FIRST
        is_locally_scanned = self.is_qr_already_scanned(data)
        
        if is_locally_scanned:
            # For locally scanned QR codes, just show visual feedback and exit early
            validation_result = {
                'valid': True,
                'already_scanned': True,
                'message': f'Order {data} already scanned successfully',
                'order_number': data
            }
            self._draw_qr_bounding_box(obj, frame, validation_result)
            
            # Update display message only if not in cooldown
            should_process = (
                data != self.last_qr_data or 
                self.last_qr_time is None or
                (current_time - self.last_qr_time) >= self.qr_cooldown
            )
            
            if should_process:
                self.display_message = "Already Scanned!"
                self.display_message_color = (0, 165, 255)  # Orange
                self.display_message_start_time = current_time
                self.display_message_duration = 3.0
                self.current_qr_data = data
                self.current_qr_rect = obj.rect
                self.last_qr_data = data
                self.last_qr_time = current_time
                logger.debug(f"Locally scanned QR code displayed: {data} - No backend validation or callbacks triggered")
            
            return  # Exit early - no backend validation, no callbacks, no actions
        
        # Continue with normal processing for non-locally-scanned codes
        # Check for cooldown period
        should_process = (
            data != self.last_qr_data or 
            self.last_qr_time is None or
            (current_time - self.last_qr_time) >= self.qr_cooldown
        )
        
        # Determine validation result
        if should_process:
            # Only call backend validation during the first detection or after cooldown
            validation_result = self.validate_qr_with_database(data)
        else:
            # During cooldown, try to use cached validation result
            cached_result = self.get_cached_validation(data)
            if cached_result:
                validation_result = cached_result
            else:
                # Fallback minimal result for display purposes only
                validation_result = {
                    'valid': False,
                    'already_scanned': False,
                    'message': 'Cooldown period - scanning paused'
                }
        
        # Always draw bounding box for visual feedback
        self._draw_qr_bounding_box(obj, frame, validation_result)
        
        # Only process QR code actions if should_process is True
        if not should_process:
            return
        
        # Update tracking variables
        self.last_qr_data = data
        self.last_qr_time = current_time
        self.current_qr_data = data
        self.current_qr_rect = obj.rect
        
        # Save QR image
        x, y, w, h = obj.rect
        image_data = self.save_qr_image(frame, data, (x, y, w, h))
        
        # Handle different validation results
        if validation_result.get('already_scanned', False):
            self._handle_already_scanned_qr(data, validation_result, image_data, current_time)
        elif not validation_result['valid']:
            self._handle_invalid_qr(data, validation_result, image_data, current_time)
        else:
            self._handle_valid_qr(data, validation_result, image_data, current_time)
        
        # Draw bounding box
        self._draw_qr_bounding_box(obj, frame, validation_result)

    def _handle_already_scanned_qr(self, data, validation_result, image_data, current_time):
        """Handle QR code that was already scanned"""
        self.display_message = "Already Scanned!"
        self.display_message_color = (0, 165, 255)  # Orange
        self.display_message_start_time = current_time
        self.display_message_duration = 3.0
        
        # For already scanned QR codes, we only add to history but DO NOT trigger callbacks
        # This prevents triggering printing, sound, or any other actions
        self.add_to_qr_history(data, validation_result, image_data)
        logger.info(f"Already scanned QR code detected: {data} - No actions triggered, cycle will NOT proceed")

    def _handle_invalid_qr(self, data, validation_result, image_data, current_time):
        """Handle invalid QR code"""
        self.display_message = "QR Not Found in Database!"
        self.display_message_color = (0, 0, 255)  # Red
        self.display_message_start_time = current_time
        self.display_message_duration = 3.0
        
        self.add_to_qr_history(data, validation_result, image_data)
        self._notify_qr_callbacks(data, validation_result)
        logger.warning(f"Invalid QR code detected: {data} - {validation_result.get('message', 'Not found in orders database')} - Cycle will NOT proceed")

    def _handle_valid_qr(self, data, validation_result, image_data, current_time):
        """Handle valid QR code"""
        self.display_message = "Scanned Successfully!"
        self.display_message_color = (0, 255, 0)  # Green
        self.display_message_start_time = current_time
        self.display_message_duration = 5.0
        
        # Mark as scanned locally for duplicate prevention
        if self.duplicate_prevention_enabled:
            self.mark_qr_as_scanned(data)
        
        self.add_to_qr_history(data, validation_result, image_data)
        self._notify_qr_callbacks(data, validation_result)
        logger.info(f"Valid QR code detected: {data} - Order: {validation_result.get('order_number', 'N/A')} - Cycle will proceed with Motor B, GSM, and receipt printing")

    def _draw_qr_bounding_box(self, obj, frame, validation_result):
        """Draw bounding box around QR code with appropriate color"""
        points = obj.polygon
        if len(points) >= 4:
            # Determine color based on validation result
            if validation_result.get('already_scanned', False):
                color = (0, 165, 255)  # Orange for already scanned
            elif not validation_result['valid']:
                color = (0, 0, 255)  # Red for invalid
            else:
                color = (0, 255, 0)  # Green for valid
            
            pts = [(point.x, point.y) for point in points]
            cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], 
                         isClosed=True, color=color, thickness=3)

    # Frame and Status Methods
    def get_frame(self):
        """Get the current frame as JPEG bytes"""
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
        """Get camera status information"""
        return {
            "camera_running": self.running,
            "initialization_error": self.initialization_error,
            "has_camera": self.picam2 is not None,
            "duplicate_prevention": self.get_duplicate_prevention_status()
        }

    def get_last_qr(self):
        """Get the last detected QR code data"""
        return self.last_qr_data or ""
