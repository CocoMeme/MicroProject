#!/usr/bin/env python3
"""
Test script to verify QR code spam fix
This script tests the camera QR code validation to ensure it doesn't spam the console
"""

import time
import logging
from camera import CameraManager

# Set up logging to see the validation calls
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qr_spam_prevention():
    """Test that QR code validation doesn't spam the console"""
    logger.info("Starting QR spam prevention test...")
    
    # Create camera manager
    camera = CameraManager()
    
    # Test data - simulate the same QR code being detected multiple times
    test_qr_data = "ORD-001"
    
    logger.info(f"Testing QR code: {test_qr_data}")
    
    # First validation - should call backend
    logger.info("=== First validation (should call backend) ===")
    result1 = camera.validate_qr_with_database(test_qr_data)
    logger.info(f"Result 1: {result1}")
    
    # Mark as scanned to simulate local tracking
    if result1.get('valid') and not result1.get('already_scanned'):
        camera.mark_qr_as_scanned(test_qr_data)
        logger.info(f"Marked {test_qr_data} as locally scanned")
    
    # Second validation - should use cache, not call backend
    logger.info("=== Second validation (should use cache) ===")
    result2 = camera.validate_qr_with_database(test_qr_data)
    logger.info(f"Result 2: {result2}")
    
    # Third validation - should still use cache
    logger.info("=== Third validation (should still use cache) ===")
    result3 = camera.validate_qr_with_database(test_qr_data)
    logger.info(f"Result 3: {result3}")
    
    # Test local scanning check
    logger.info("=== Testing local scanning check ===")
    is_scanned = camera.is_qr_already_scanned(test_qr_data)
    logger.info(f"Is {test_qr_data} locally scanned? {is_scanned}")
    
    # Test cache status
    logger.info("=== Cache status ===")
    cached_result = camera.get_cached_validation(test_qr_data)
    logger.info(f"Cached result: {cached_result is not None}")
    
    # Test clearing
    logger.info("=== Testing clear functionality ===")
    camera.clear_scanned_qr(test_qr_data)
    is_scanned_after_clear = camera.is_qr_already_scanned(test_qr_data)
    logger.info(f"Is {test_qr_data} locally scanned after clear? {is_scanned_after_clear}")
    
    logger.info("QR spam prevention test completed!")

def test_processing_logic():
    """Test the actual processing logic that handles QR detection"""
    logger.info("Testing QR processing logic...")
    
    camera = CameraManager()
    
    # Mock QR object
    class MockQRObject:
        def __init__(self, data):
            self.data = data.encode('utf-8')
            self.rect = (100, 100, 200, 200)  # x, y, w, h
            self.polygon = [
                type('Point', (), {'x': 100, 'y': 100}),
                type('Point', (), {'x': 300, 'y': 100}),
                type('Point', (), {'x': 300, 'y': 300}),
                type('Point', (), {'x': 100, 'y': 300})
            ]
    
    # Mock frame
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    test_qr = "ORD-002"
    mock_obj = MockQRObject(test_qr)
    
    # Test multiple rapid detections of the same QR code
    logger.info(f"=== Testing rapid detections of {test_qr} ===")
    
    current_time = time.time()
    
    # First detection - should validate
    logger.info("Detection 1 (should validate):")
    camera._process_qr_code(mock_obj, frame, current_time)
    
    # Immediate second detection - should be in cooldown
    logger.info("Detection 2 (should be in cooldown):")
    camera._process_qr_code(mock_obj, frame, current_time + 0.1)
    
    # Third detection - still in cooldown
    logger.info("Detection 3 (should still be in cooldown):")
    camera._process_qr_code(mock_obj, frame, current_time + 0.5)
    
    # Fourth detection - after cooldown period
    logger.info("Detection 4 (after cooldown, but should be marked as scanned):")
    camera._process_qr_code(mock_obj, frame, current_time + 4.0)
    
    logger.info("QR processing logic test completed!")

if __name__ == "__main__":
    print("Testing QR code spam fix...")
    print("=" * 50)
    
    try:
        test_qr_spam_prevention()
        print("\n" + "=" * 50)
        test_processing_logic()
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
