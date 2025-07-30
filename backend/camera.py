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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend server URL (your website)
BACKEND_SERVER = os.getenv('BACKEND_URL', 'http://10.194.125.225:5000')  # Your Flask backend

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

# Log that ZBar warning suppression is active
logger.info("ZBar warning suppression activated - decoder warnings will be filtered")

# Suppress ZBar decoder warnings
class ZBarWarningFilter(logging.Filter):
    def filter(self, record):
        # Filter out ZBar databar decoder warnings
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if '_zbar_decode_databar: Assertion' in message or 'decoder/databar.c' in message:
                return False
        return True

# Apply the filter to suppress ZBar warnings from stderr
import sys
import warnings

# Suppress ZBar warnings at the C library level
warnings.filterwarnings("ignore", message=".*zbar.*")
warnings.filterwarnings("ignore", message=".*databar.*")

# Set environment variable to suppress ZBar debug output
import os
os.environ['ZBAR_DEBUG'] = '0'

# Additional environment variables that might help suppress ZBar warnings
os.environ['ZBAR_QUIET'] = '1'
os.environ['ZBAR_SILENCE'] = '1'

# Try to suppress at system level
try:
    # On Unix-like systems, try to redirect stderr to /dev/null during imports
    import signal
    
    def signal_handler(sig, frame):
        pass
    
    # Install signal handlers to prevent crashes from C library issues
    signal.signal(signal.SIGABRT, signal_handler)
except (ImportError, AttributeError):
    pass

# Additional ZBar warning suppression
try:
    # Try to suppress ZBar warnings at the library level if available
    import zbar
    # Disable ZBar's internal debug/warning output
    if hasattr(zbar, 'set_verbosity'):
        zbar.set_verbosity(0)
except (ImportError, AttributeError):
    # ZBar module not available or doesn't have verbosity control
    pass

# Try to suppress warnings at C library level using ctypes
try:
    import ctypes
    import ctypes.util
    
    # Try to find and configure libzbar
    libzbar_path = ctypes.util.find_library('zbar')
    if libzbar_path:
        libzbar = ctypes.CDLL(libzbar_path)
        # Try to disable debug output if the function exists
        if hasattr(libzbar, 'zbar_set_verbosity'):
            libzbar.zbar_set_verbosity(0)
        if hasattr(libzbar, 'zbar_symbol_set_verbosity'):
            libzbar.zbar_symbol_set_verbosity(0)
except (ImportError, OSError, AttributeError):
    # ctypes or libzbar not available
    pass

# Alternative approach: Try to redirect stderr at file descriptor level
try:
    import atexit
    
    # Create a null device for discarding ZBar warnings
    NULL_DEVICE = os.devnull
    
    def suppress_zbar_fd_warnings():
        """Temporarily redirect stderr to null device during ZBar operations"""
        original_stderr_fd = os.dup(2)
        null_fd = os.open(NULL_DEVICE, os.O_WRONLY)
        os.dup2(null_fd, 2)
        os.close(null_fd)
        return original_stderr_fd
    
    def restore_stderr_fd(original_fd):
        """Restore original stderr file descriptor"""
        os.dup2(original_fd, 2)
        os.close(original_fd)
        
except (ImportError, OSError, AttributeError):
    # OS operations not available or supported
    def suppress_zbar_fd_warnings():
        return None
    def restore_stderr_fd(fd):
        pass

# Also suppress stderr output from ZBar C library
class StderrFilter:
    def __init__(self):
        self.original_stderr = sys.stderr
        self.buffer = ""
        
    def write(self, s):
        # Add to buffer for line-based filtering
        self.buffer += s
        
        # Process complete lines
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            
            # Filter out ZBar decoder warnings with comprehensive patterns
            zbar_patterns = [
                '_zbar_decode_databar: Assertion',
                'decoder/databar.c',
                'WARNING: decoder/databar.c',
                'failed.\n        i=',
                'f=-1(010) part=0'
            ]
            
            # Check if line contains any ZBar warning pattern
            should_filter = any(pattern in line for pattern in zbar_patterns)
            
            if not should_filter:
                self.original_stderr.write(line + '\n')
    
    def flush(self):
        # Write any remaining buffer content (if not a ZBar warning)
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

# Apply stderr filter
sys.stderr = StderrFilter()

# Additional OS-level stderr suppression for ZBar C library warnings
import os
import subprocess
import tempfile

# Create a more aggressive stderr filter that works at OS level
class OSLevelStderrFilter:
    def __init__(self):
        self.original_stderr = sys.stderr
        self.temp_file = None
        
    def __enter__(self):
        # Redirect stderr to a temporary file during ZBar operations
        self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.original_stderr_fd = os.dup(2)  # Duplicate stderr file descriptor
        os.dup2(self.temp_file.fileno(), 2)  # Redirect stderr to temp file
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original stderr
        os.dup2(self.original_stderr_fd, 2)
        os.close(self.original_stderr_fd)
        
        # Read the temp file and filter out ZBar warnings
        if self.temp_file:
            self.temp_file.seek(0)
            content = self.temp_file.read()
            self.temp_file.close()
            
            # Filter and write non-ZBar content to original stderr
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
            
            # Clean up temp file
            try:
                os.unlink(self.temp_file.name)
            except:
                pass

class CameraManager:
		def __init__(self):
			self.picam2 = None
			self.frame = None
			self.running = False
			self.lock = threading.Lock()
			self.last_qr_data = None
			self.last_qr_time = None  # Add timestamp for last QR detection
			self.qr_cooldown = 3  # Minimum seconds between same QR detections
			self.capture_thread = None
			self.initialization_error = None
			self.scanned_qr_history = []  # Store history of scanned QR codes
			self.max_history = 50  # Keep last 50 scanned codes
			self.qr_callbacks = []  # Callbacks to notify when new QR is detected
			self.scanned_qr_codes = set()  # Track already scanned QR codes to prevent duplicates
			self.duplicate_prevention_enabled = True  # Flag to enable/disable duplicate prevention
			
			# Message display timing variables
			self.display_message = None
			self.display_message_color = None
			self.display_message_start_time = None
			self.display_message_duration = 0
			self.pending_already_scanned = False
			self.pending_already_scanned_start_time = None
			self.current_qr_data = None
			self.current_qr_rect = None
			
			# QR scanning cycle variables
			self.scanning_enabled = False
			self.scan_start_time = None
			self.countdown_delay = 10.0  # 10 seconds countdown before scanning
			self.scanning_duration = 60.0  # 60 seconds of active scanning
			self.scanning_session_start = None
			self.scanning_state = "countdown"  # "countdown", "scanning", "session_ended"
			
			# Create directory for QR code images
			self.qr_images_dir = 'qr_images'
			if not os.path.exists(self.qr_images_dir):
				os.makedirs(self.qr_images_dir)

			try:
				self.picam2 = Picamera2()
				if not MOCK_CAMERA:
					self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
				logger.info(f"Camera initialized successfully {'(MOCK MODE)' if MOCK_CAMERA else ''}")
			except Exception as e:
				self.initialization_error = str(e)
				logger.error(f"Camera initialization failed: {e}")

		def add_qr_callback(self, callback):
			"""Add a callback function to be called when new QR is detected"""
			self.qr_callbacks.append(callback)

		def _notify_qr_callbacks(self, qr_data, validation_result):
			"""Notify all registered callbacks about new QR detection"""
			for callback in self.qr_callbacks:
				try:
					callback(qr_data, validation_result)
				except Exception as e:
					logger.error(f"QR callback error: {e}")

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
				logger.info(f"QR code cleared for rescanning: {qr_data}")
				return True
			return False

		def clear_all_scanned_qr_codes(self):
			"""Clear all scanned QR codes to allow rescanning of everything"""
			count = len(self.scanned_qr_codes)
			self.scanned_qr_codes.clear()
			logger.info(f"Cleared {count} scanned QR codes")
			return count

		def get_scanned_qr_codes(self):
			"""Get list of all scanned QR codes"""
			return list(self.scanned_qr_codes)

		def set_duplicate_prevention(self, enabled):
			"""Enable or disable duplicate prevention"""
			self.duplicate_prevention_enabled = enabled
			logger.info(f"Duplicate prevention {'enabled' if enabled else 'disabled'}")

		def reset_scan_cycle(self):
			"""Reset the scanning cycle to start countdown again"""
			self.scanning_enabled = False
			self.scan_start_time = time.time()
			self.scanning_state = "countdown"
			self.scanning_session_start = None
			# Clear any existing messages
			self.display_message = None
			self.display_message_start_time = None
			self.pending_already_scanned = False
			self.pending_already_scanned_start_time = None
			self.current_qr_data = None
			self.current_qr_rect = None
			logger.info(f"Scanning cycle reset - Starting countdown ({self.countdown_delay}s countdown, {self.scanning_duration}s scanning session)")

		def reset_scan_cycle_if_running(self):
			"""Reset the scanning cycle even if camera is already running"""
			if self.running:
				self.scanning_enabled = False
				self.scan_start_time = time.time()
				self.scanning_state = "countdown"
				self.scanning_session_start = None
				# Clear any existing messages
				self.display_message = None
				self.display_message_start_time = None
				self.pending_already_scanned = False
				self.pending_already_scanned_start_time = None
				self.current_qr_data = None
				self.current_qr_rect = None
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

		def get_duplicate_prevention_status(self):
			"""Get current duplicate prevention status"""
			return {
				'enabled': self.duplicate_prevention_enabled,
				'scanned_count': len(self.scanned_qr_codes),
				'scanned_codes': list(self.scanned_qr_codes)
			}

		def save_qr_image(self, frame, qr_data, qr_bounds):
			"""Save an image of the detected QR code"""
			try:
				timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
				# Clean the QR data for filename (replace problematic characters)
				clean_qr_data = qr_data.replace('/', '_').replace('\\', '_')[:20]
				filename = f"qr_{timestamp}_{clean_qr_data}.jpg"
				filepath = os.path.join(self.qr_images_dir, filename)
				
				# If QR bounds are available, crop the image around the QR code
				if qr_bounds:
					x, y, w, h = qr_bounds
					# Add some padding around the QR code
					padding = 50
					x_start = max(0, x - padding)
					y_start = max(0, y - padding)
					x_end = min(frame.shape[1], x + w + padding)
					y_end = min(frame.shape[0], y + h + padding)
					
					cropped_frame = frame[y_start:y_end, x_start:x_end]
					cv2.imwrite(filepath, cropped_frame)
				else:
					# Save the full frame if no bounds available
					cv2.imwrite(filepath, frame)
				
				# Convert image to base64 for storage/transmission
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

		def validate_qr_with_database(self, qr_data):
			"""Validate QR code against orders database via HTTP request to website backend"""
			try:
				logger.info(f"Validating QR code: {qr_data} with backend at {BACKEND_SERVER}")
				# Make HTTP request to backend server to validate QR code
				response = requests.post(
					f'{BACKEND_SERVER}/api/validate-qr',
					json={
						'qr_data': qr_data,
						'source': 'camera',  # Indicate this request comes from camera
						'skip_print': True   # Skip automatic print request since we'll handle it locally
					},
					timeout=5
				)
				
				if response.status_code == 200:
					result = response.json()
					logger.info(f"Validation result for {qr_data}: {result}")
					return result
				else:
					logger.warning(f"Backend server error for {qr_data}: {response.status_code} - {response.text}")
					return {'valid': False, 'message': f'Backend server error: {response.status_code}'}
					
			except requests.exceptions.ConnectionError as e:
				logger.error(f"Connection error validating {qr_data}: {e}")
				return {'valid': False, 'message': f'Connection error: {str(e)}'}
			except requests.exceptions.Timeout as e:
				logger.error(f"Timeout error validating {qr_data}: {e}")
				return {'valid': False, 'message': f'Timeout error: {str(e)}'}
			except requests.RequestException as e:
				logger.error(f"HTTP request error validating {qr_data}: {e}")
				return {'valid': False, 'message': f'Connection error: {str(e)}'}
			except Exception as e:
				logger.error(f"Validation error for {qr_data}: {e}")
				return {'valid': False, 'message': f'Validation error: {str(e)}'}

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
						# Clear local history after successful sync
						# self.scanned_qr_history.clear()  # Uncomment if you want to clear after sync
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
				'device': 'raspberry_pi',  # Identify source
				'image_data': image_data  # Add image data
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
				self.display_message = None
				self.display_message_start_time = None
				self.pending_already_scanned = False
				self.pending_already_scanned_start_time = None
				self.current_qr_data = None
				self.current_qr_rect = None
				
				self.picam2.stop()
				if self.capture_thread:
					self.capture_thread.join(timeout=2.0)
				logger.info("Camera stopped and scanning cycle reset")
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
				# Handle display messages with timing
				current_time = time.time()
				
				# Handle scanning cycle states
				if self.scan_start_time is not None:
					if self.scanning_state == "countdown":
						# Countdown phase
						time_elapsed = current_time - self.scan_start_time
						if time_elapsed < self.countdown_delay:
							remaining_time = int(self.countdown_delay - time_elapsed)
							cv2.putText(frame, f"Scanning starts in: {remaining_time}s", 
									   (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
							cv2.putText(frame, "Position QR code now", 
									   (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
							return frame
						else:
							# Countdown finished, start scanning session
							self.scanning_enabled = True
							self.scanning_state = "scanning"
							self.scanning_session_start = current_time
							logger.info(f"QR scanning session started - {self.scanning_duration}s active period")
					
					elif self.scanning_state == "scanning":
						# Active scanning phase
						session_elapsed = current_time - self.scanning_session_start
						if session_elapsed >= self.scanning_duration:
							# Scanning session ended, restart countdown
							self.scanning_enabled = False
							self.scanning_state = "countdown"
							self.scan_start_time = current_time
							self.scanning_session_start = None
							logger.info(f"Scanning session ended - Starting new countdown ({self.countdown_delay}s)")
							return frame
						else:
							# Show scanning session status
							remaining_scan_time = int(self.scanning_duration - session_elapsed)
							cv2.putText(frame, f"SCANNING ACTIVE: {remaining_scan_time}s left", 
									   (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
				
				# If scanning is not enabled, show appropriate message
				if not self.scanning_enabled:
					if self.scanning_state == "countdown":
						cv2.putText(frame, "Preparing to scan...", 
								   (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
					return frame
				
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
				
				# Clear message when expired
				if (self.display_message_start_time and 
					current_time - self.display_message_start_time >= self.display_message_duration):
					self.display_message = None
					self.display_message_color = None
					self.display_message_start_time = None
					self.current_qr_data = None
					self.current_qr_rect = None

				# Decode QR codes with comprehensive warning suppression
				original_stderr_fd = None
				try:
					# Try OS-level stderr suppression first
					with OSLevelStderrFilter():
						# Also try file descriptor level suppression
						original_stderr_fd = suppress_zbar_fd_warnings()
						decoded_objects = decode(frame)
						if original_stderr_fd is not None:
							restore_stderr_fd(original_stderr_fd)
							original_stderr_fd = None
				except Exception as decode_error:
					# Ensure stderr is restored if there was an error
					if original_stderr_fd is not None:
						try:
							restore_stderr_fd(original_stderr_fd)
						except:
							pass
					
					# Fallback to regular decode
					try:
						decoded_objects = decode(frame)
					except Exception as fallback_error:
						logger.debug(f"QR decode failed: {fallback_error}")
						decoded_objects = []
				for obj in decoded_objects:
					data = obj.data.decode('utf-8')
					current_time = time.time()
					
					# Validate QR code with the database first
					validation_result = self.validate_qr_with_database(data)
					
					# Check if this QR code was already scanned according to the backend
					if validation_result.get('already_scanned', False):
						# Show "Already Scanned!" message
						should_process = (
							data != self.last_qr_data or 
							self.last_qr_time is None or
							(current_time - self.last_qr_time) >= self.qr_cooldown
						)
						
						if should_process:
							self.last_qr_data = data
							self.last_qr_time = current_time
							
							# Store QR data and rect for message display
							self.current_qr_data = data
							self.current_qr_rect = obj.rect
							
							# Show "Already Scanned!" message
							self.display_message = "Already Scanned!"
							self.display_message_color = (0, 165, 255)  # Orange
							self.display_message_start_time = current_time
							self.display_message_duration = 3.0
							
							# Save QR code image
							x, y, w, h = obj.rect
							image_data = self.save_qr_image(frame, data, (x, y, w, h))
							
							# Add to history with image data
							self.add_to_qr_history(data, validation_result, image_data)
							
							# Notify callbacks about new QR detection
							self._notify_qr_callbacks(data, validation_result)
							
							logger.info(f"Already scanned QR code detected: {data} - Cycle will NOT proceed")
						
						# Draw orange box for already scanned QR codes
						points = obj.polygon
						if len(points) >= 4:
							pts = [(point.x, point.y) for point in points]
							cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], isClosed=True, color=(0, 165, 255), thickness=3)
						
						continue  # Skip further processing this QR code
					
					# Check if this is invalid (not verified)
					if not validation_result['valid']:
						# Show message for invalid QR codes
						should_process = (
							data != self.last_qr_data or 
							self.last_qr_time is None or
							(current_time - self.last_qr_time) >= self.qr_cooldown
						)
						
						if should_process:
							self.last_qr_data = data
							self.last_qr_time = current_time
							
							# Store QR data and rect for message display
							self.current_qr_data = data
							self.current_qr_rect = obj.rect
							
							# Show "QR Not Found in Database!" message
							self.display_message = "QR Not Found in Database!"
							self.display_message_color = (0, 0, 255)  # Red
							self.display_message_start_time = current_time
							self.display_message_duration = 3.0
							
							# Save QR code image
							x, y, w, h = obj.rect
							image_data = self.save_qr_image(frame, data, (x, y, w, h))
							
							# Add to history with image data
							self.add_to_qr_history(data, validation_result, image_data)
							
							# Notify callbacks about new QR detection
							self._notify_qr_callbacks(data, validation_result)
							
							logger.warning(f"Invalid QR code detected: {data} - {validation_result.get('message', 'Not found in orders database')} - Cycle will NOT proceed")
						
						# Draw red box for invalid QR codes
						points = obj.polygon
						if len(points) >= 4:
							pts = [(point.x, point.y) for point in points]
							cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], isClosed=True, color=(0, 0, 255), thickness=3)
						
						continue
					
					# Valid QR code that hasn't been scanned before
					# Check for duplicate prevention for local scanning (time-based cooldown)
					should_process = (
						data != self.last_qr_data or 
						self.last_qr_time is None or
						(current_time - self.last_qr_time) >= self.qr_cooldown
					)
					
					if should_process:
						self.last_qr_data = data
						self.last_qr_time = current_time
						
						# Store QR data and rect for message display
						self.current_qr_data = data
						self.current_qr_rect = obj.rect
						
						# Show "Scanned Successfully!" message
						self.display_message = "Scanned Successfully!"
						self.display_message_color = (0, 255, 0)  # Green
						self.display_message_start_time = current_time
						self.display_message_duration = 5.0
						
						# Mark QR code as scanned locally for duplicate prevention
						if self.duplicate_prevention_enabled:
							self.mark_qr_as_scanned(data)
						
						# Save QR code image
						x, y, w, h = obj.rect
						image_data = self.save_qr_image(frame, data, (x, y, w, h))
						
						# Add to history with image data
						self.add_to_qr_history(data, validation_result, image_data)
						
						# Notify callbacks about new QR detection (for cycle integration)
						self._notify_qr_callbacks(data, validation_result)
						
						logger.info(f"Valid QR code detected: {data} - Order: {validation_result.get('order_number', 'N/A')} - Cycle will proceed with Motor B, GSM, and receipt printing")

					# Draw a bounding box around the QR code
					points = obj.polygon
					if len(points) >= 4:
						# Green color for valid QR codes
						color = (0, 255, 0)
						pts = [(point.x, point.y) for point in points]
						cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], isClosed=True, color=color, thickness=3)

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
				"has_camera": self.picam2 is not None,
				"duplicate_prevention": self.get_duplicate_prevention_status()
			}

		def get_last_qr(self):
			return self.last_qr_data or ""

		def get_qr_history(self):
			"""Get the history of scanned QR codes"""
			return self.scanned_qr_history
