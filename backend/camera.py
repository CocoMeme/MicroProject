import cv2
import threading
import time
import logging
from picamera2 import Picamera2
from pyzbar.pyzbar import decode

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
        
        try:
            self.picam2 = Picamera2()
            # Test if we can actually access the camera
            self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
            logger.info("Camera initialized successfully")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Failed to initialize camera: {str(e)}")

    def start_camera(self):
        if self.initialization_error:
            logger.error(f"Cannot start camera due to initialization error: {self.initialization_error}")
            return False
            
        if self.running:
            logger.warning("Camera is already running")
            return False
            
        if not self.picam2:
            logger.error("Camera not initialized")
            return False
            
        try:
            logger.info("Attempting to start camera...")
            self.picam2.start()
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info("Camera started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera: {str(e)}")
            self.running = False
            if self.picam2:
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
            logger.info("Stopping camera...")
            self.running = False
            if self.picam2:
                self.picam2.stop()
            if self.capture_thread:
                self.capture_thread.join(timeout=2.0)
            logger.info("Camera stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping camera: {str(e)}")
            return False

    def _capture_loop(self):
        if not self.picam2:
            logger.error("Camera not initialized")
            self.running = False
            return
            
        logger.info("Starting capture loop")
        while self.running:
            try:
                frame = self.picam2.capture_array()
                with self.lock:
                    self.frame = frame.copy()
                self._scan_qr_code(frame)
                time.sleep(0.03)
            except Exception as e:
                logger.error(f"Error in capture loop: {str(e)}")
                self.running = False
                break

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            try:
                _, jpeg = cv2.imencode('.jpg', self.frame)
                return jpeg.tobytes()
            except Exception as e:
                logger.error(f"Error encoding frame: {str(e)}")
                return None

    def _scan_qr_code(self, frame):
        try:
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                if data != self.last_qr_data:
                    self.last_qr_data = data
                    logger.info(f"New QR code detected: {data}")
        except Exception as e:
            logger.error(f"Error scanning QR code: {str(e)}")

    def get_status(self):
        status = {
            "camera_running": self.running,
            "initialization_error": self.initialization_error,
            "has_camera": self.picam2 is not None
        }
        return status

    def get_last_qr(self):
        return self.last_qr_data if self.last_qr_data else ""