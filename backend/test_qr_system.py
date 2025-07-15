import requests
import json

# Test the QR validation endpoint
def test_qr_validation():
    backend_url = 'http://192.168.100.61:5000/api/validate-qr'
    test_qr_codes = ['ORD-001', 'ORD-002', 'ORD-003', 'INVALID-QR']
    
    print("Testing QR validation:")
    for qr_code in test_qr_codes:
        try:
            response = requests.post(backend_url, json={'qr_data': qr_code}, timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"  {qr_code}: Valid={result.get('valid', False)}, Order={result.get('order_number', 'N/A')}")
            else:
                print(f"  {qr_code}: HTTP Error {response.status_code}")
        except Exception as e:
            print(f"  {qr_code}: Error - {e}")

# Test the Raspberry Pi QR history endpoint
def test_qr_history():
    raspi_url = 'http://192.168.100.63:5001/camera/qr-history'
    
    print("\nTesting QR history:")
    try:
        response = requests.get(raspi_url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            history = result.get('qr_history', [])
            print(f"  Found {len(history)} scans in history")
            for i, scan in enumerate(history[:3]):  # Show first 3
                has_image = 'image_data' in scan and scan['image_data'] and scan['image_data'].get('base64')
                print(f"    {i+1}. {scan.get('qr_data', 'N/A')} - Valid: {scan.get('validation', {}).get('valid', False)} - Has Image: {has_image}")
        else:
            print(f"  HTTP Error {response.status_code}")
    except Exception as e:
        print(f"  Error - {e}")

# Test the test QR image endpoint
def test_qr_image_creation():
    raspi_url = 'http://192.168.100.63:5001/debug/test-qr-image'
    
    print("\nTesting QR image creation:")
    try:
        response = requests.post(raspi_url, json={'qr_code': 'ORD-001'}, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"  Successfully created test image for ORD-001")
            print(f"  Image data available: {bool(result.get('image_data', {}).get('base64'))}")
        else:
            print(f"  HTTP Error {response.status_code}")
    except Exception as e:
        print(f"  Error - {e}")

if __name__ == '__main__':
    print("QR System Test Script")
    print("====================")
    
    test_qr_validation()
    test_qr_history()
    test_qr_image_creation()
    
    print("\nTest complete!")
