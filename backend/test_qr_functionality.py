#!/usr/bin/env python3
"""
Test script to verify QR functionality
"""

import requests
import json

# Server URLs
RASPI_SERVER = 'http://localhost:5001'
BACKEND_SERVER = 'http://192.168.100.61:5000'

def test_qr_image_generation():
    """Test the QR image generation endpoint"""
    print("Testing QR image generation...")
    
    try:
        response = requests.post(f'{RASPI_SERVER}/debug/test-qr-image', 
                               json={'qr_code': 'ORD-TEST-123'},
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ QR image generation successful!")
            print(f"   Message: {data.get('message')}")
            print(f"   Image filename: {data.get('image_data', {}).get('filename')}")
            print(f"   Has base64 data: {'Yes' if data.get('image_data', {}).get('base64') else 'No'}")
            print(f"   Validation result: {data.get('validation', {})}")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_qr_history():
    """Test QR history retrieval"""
    print("\nTesting QR history retrieval...")
    
    try:
        response = requests.get(f'{RASPI_SERVER}/camera/qr-history', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            history = data.get('qr_history', [])
            print(f"✅ QR history retrieved successfully!")
            print(f"   Total entries: {len(history)}")
            
            if history:
                latest = history[0]
                print(f"   Latest scan: {latest.get('qr_data')}")
                print(f"   Has image data: {'Yes' if latest.get('image_data') else 'No'}")
                print(f"   Has base64: {'Yes' if latest.get('image_data', {}).get('base64') else 'No'}")
                print(f"   Validation: {latest.get('validation', {})}")
            
            return True
        else:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_qr_validation():
    """Test QR validation"""
    print("\nTesting QR validation...")
    
    try:
        response = requests.post(f'{RASPI_SERVER}/api/validate-qr',
                               json={'qr_data': 'ORD-001'},
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ QR validation successful!")
            print(f"   Validation result: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔍 Testing QR Code Functionality")
    print("=" * 50)
    
    # Run tests
    tests = [
        test_qr_validation,
        test_qr_image_generation,
        test_qr_history
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    print(f"   Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the server logs for more details.")

if __name__ == '__main__':
    main()
