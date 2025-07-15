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
			self.last_qr_time = None  # Add timestamp for last QR detection
			self.qr_cooldown = 3  # Minimum seconds between same QR detections
			self.capture_thread = None
			self.initialization_error = None
			self.scanned_qr_history = []  # Store history of scanned QR codes
			self.max_history = 50  # Keep last 50 scanned codes
			self.qr_callbacks = []  # Callbacks to notify when new QR is detected
			
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
					json={'qr_data': qr_data},
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
					current_time = time.time()
					
					# Validate QR code once and reuse the result
					validation_result = self.validate_qr_with_database(data)
					
					# Check if this is a new QR code or enough time has passed since last detection
					should_process = (
						data != self.last_qr_data or 
						self.last_qr_time is None or
						(current_time - self.last_qr_time) >= self.qr_cooldown
					)
					
					if should_process:
						self.last_qr_data = data
						self.last_qr_time = current_time
						
						# Save QR code image
						x, y, w, h = obj.rect
						image_data = self.save_qr_image(frame, data, (x, y, w, h))
						
						# Add to history with image data
						self.add_to_qr_history(data, validation_result, image_data)
						
						# Notify callbacks about new QR detection
						self._notify_qr_callbacks(data, validation_result)
						
						if validation_result['valid']:
							logger.info(f"Valid QR code detected: {data} - Order: {validation_result.get('order_number', 'N/A')}")
						else:
							logger.warning(f"Invalid QR code detected: {data} - {validation_result.get('message', 'Unknown error')}")

					# Draw a bounding box around the QR code
					points = obj.polygon
					if len(points) >= 4:
						# Use different colors based on validation
						color = (0, 255, 0) if validation_result['valid'] else (0, 0, 255)  # Green for valid, red for invalid
						
						pts = [(point.x, point.y) for point in points]
						cv2.polylines(frame, [cv2.convexHull(np.array(pts, dtype=np.int32))], isClosed=True, color=color, thickness=3)

					# Display the decoded text with validation status
					x, y, w, h = obj.rect
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
