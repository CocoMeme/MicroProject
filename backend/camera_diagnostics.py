#!/usr/bin/env python3
"""
Camera Diagnostics and Fix Script
Diagnoses camera issues and attempts automatic fixes
"""

import sys
import subprocess
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_picamera2_version():
    """Check if picamera2 is installed and get version"""
    try:
        import picamera2
        version = getattr(picamera2, '__version__', 'Unknown')
        logger.info(f"PiCamera2 version: {version}")
        return version
    except ImportError:
        logger.error("PiCamera2 not installed")
        return None

def check_camera_hardware():
    """Check if camera hardware is detected"""
    try:
        # Try to detect camera using vcgencmd (Raspberry Pi specific)
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(f"Camera hardware status: {result.stdout.strip()}")
            return "detected=1" in result.stdout
        else:
            logger.warning("Could not check camera hardware (not on Raspberry Pi?)")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        logger.warning("Camera hardware check failed (vcgencmd not available)")
        return None

def test_camera_import():
    """Test if we can import and create Picamera2 instance"""
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        logger.info("Successfully created Picamera2 instance")
        return True
    except Exception as e:
        logger.error(f"Failed to create Picamera2 instance: {e}")
        return False

def test_camera_configuration():
    """Test camera configuration"""
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        
        # Try new API first
        try:
            config = picam2.create_video_configuration(main={"size": (640, 480)})
            picam2.configure(config)
            logger.info("Camera configuration successful (new API)")
            return True
        except Exception as e1:
            logger.warning(f"New API failed: {e1}")
            
            # Try old API
            try:
                picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
                logger.info("Camera configuration successful (old API)")
                return True
            except Exception as e2:
                logger.error(f"Both configuration methods failed: {e1}, {e2}")
                return False
                
    except Exception as e:
        logger.error(f"Camera configuration test failed: {e}")
        return False

def test_camera_start_stop():
    """Test camera start and stop"""
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        
        # Configure
        config = picam2.create_video_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        
        # Start
        picam2.start()
        logger.info("Camera started successfully")
        
        # Brief pause
        time.sleep(1)
        
        # Stop
        picam2.stop()
        logger.info("Camera stopped successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Camera start/stop test failed: {e}")
        return False

def test_frame_capture():
    """Test frame capture for allocator errors"""
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        
        # Configure and start
        config = picam2.create_video_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        
        # Try to capture a few frames
        for i in range(3):
            frame = picam2.capture_array()
            logger.info(f"Frame {i+1} captured successfully: {frame.shape}")
            time.sleep(0.1)
        
        picam2.stop()
        logger.info("Frame capture test successful")
        return True
        
    except AttributeError as e:
        if "allocator" in str(e):
            logger.error("ALLOCATOR ERROR DETECTED - This is the known compatibility issue")
            return False
        else:
            logger.error(f"Attribute error in frame capture: {e}")
            return False
    except Exception as e:
        logger.error(f"Frame capture test failed: {e}")
        return False

def fix_picamera2_version():
    """Attempt to fix picamera2 version"""
    try:
        logger.info("Attempting to upgrade picamera2 to compatible version...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--upgrade', 
            'picamera2>=0.3.17,<0.4.0'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("PiCamera2 upgrade successful")
            return True
        else:
            logger.error(f"PiCamera2 upgrade failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to upgrade picamera2: {e}")
        return False

def main():
    """Run camera diagnostics"""
    logger.info("=" * 50)
    logger.info("Camera Diagnostics and Fix Script")
    logger.info("=" * 50)
    
    # Check PiCamera2 version
    version = check_picamera2_version()
    
    # Check hardware
    hardware_ok = check_camera_hardware()
    
    # Test import
    import_ok = test_camera_import()
    
    if not import_ok:
        logger.error("Cannot import PiCamera2 - camera will not work")
        return False
    
    # Test configuration
    config_ok = test_camera_configuration()
    
    # Test start/stop
    start_stop_ok = test_camera_start_stop()
    
    # Test frame capture (this is where allocator errors occur)
    capture_ok = test_frame_capture()
    
    # Summary
    logger.info("=" * 50)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 50)
    logger.info(f"PiCamera2 Version: {version}")
    logger.info(f"Hardware Detection: {'OK' if hardware_ok else 'FAILED' if hardware_ok is False else 'UNKNOWN'}")
    logger.info(f"Import Test: {'OK' if import_ok else 'FAILED'}")
    logger.info(f"Configuration Test: {'OK' if config_ok else 'FAILED'}")
    logger.info(f"Start/Stop Test: {'OK' if start_stop_ok else 'FAILED'}")
    logger.info(f"Frame Capture Test: {'OK' if capture_ok else 'FAILED'}")
    
    # Recommendations
    logger.info("=" * 50)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 50)
    
    if not capture_ok:
        logger.warning("Frame capture failed - this indicates the allocator error issue")
        logger.info("RECOMMENDED ACTION: Upgrade picamera2 to version >= 0.3.17")
        
        if input("Would you like to attempt automatic fix? (y/n): ").lower() == 'y':
            if fix_picamera2_version():
                logger.info("Fix applied successfully - please restart the application")
                return True
            else:
                logger.error("Automatic fix failed - manual intervention required")
                return False
    else:
        logger.info("All tests passed - camera should work correctly")
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Diagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Diagnostics script failed: {e}")
        sys.exit(1)
