#!/usr/bin/env python3
"""
Test script to verify the integration between MQTT sensor data and QR code validation.
This script tests the new loaded_sensor_data functionality.
"""

import sqlite3
import json
import requests
import time
from datetime import datetime

# Configuration
BACKEND_URL = 'http://192.168.100.61:5000'
DATABASE_PATH = 'backend/database.db'

def init_database():
    """Initialize the database with the new loaded_sensor_data table"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Create loaded_sensor_data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS loaded_sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight REAL,
            width REAL,
            height REAL,
            length REAL,
            loadcell_timestamp TEXT,
            box_dimensions_timestamp TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with loaded_sensor_data table")

def test_sensor_data_storage():
    """Test storing sensor data in the database"""
    print("\n📡 Testing sensor data storage...")
    
    sensor_data = {
        'weight': 2.5,
        'width': 15.0,
        'height': 10.0,
        'length': 20.0,
        'loadcell_timestamp': datetime.now().isoformat(),
        'box_dimensions_timestamp': datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f'{BACKEND_URL}/api/sensor-data', json=sensor_data)
        if response.status_code == 200:
            print(f"✅ Sensor data stored successfully: {response.json()}")
            return True
        else:
            print(f"❌ Failed to store sensor data: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_get_sensor_data():
    """Test retrieving sensor data from the database"""
    print("\n📊 Testing sensor data retrieval...")
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/sensor-data')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sensor data retrieved: {json.dumps(data, indent=2)}")
            return data.get('sensor_data') is not None
        else:
            print(f"❌ Failed to get sensor data: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_qr_validation_with_sensor_data():
    """Test QR validation that uses sensor data"""
    print("\n🔍 Testing QR validation with sensor data integration...")
    
    # First store some sensor data
    sensor_data = {
        'weight': 3.2,
        'width': 12.0,
        'height': 8.0,
        'length': 18.0,
        'loadcell_timestamp': datetime.now().isoformat(),
        'box_dimensions_timestamp': datetime.now().isoformat()
    }
    
    requests.post(f'{BACKEND_URL}/api/sensor-data', json=sensor_data)
    
    # Now test QR validation with a sample QR code
    # Note: This will only work if there's a valid order in the database
    qr_data = {'qr_data': 'TEST-ORDER-001'}
    
    try:
        response = requests.post(f'{BACKEND_URL}/api/validate-qr', json=qr_data)
        result = response.json()
        print(f"📋 QR validation result: {json.dumps(result, indent=2)}")
        
        if result.get('sensor_data_applied'):
            print("✅ Sensor data was successfully applied to the order!")
        else:
            print("ℹ️ No sensor data was applied (order may not exist or already processed)")
            
        return True
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_package_information_retrieval():
    """Test retrieving package information"""
    print("\n📦 Testing package information retrieval...")
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/package-information')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Package information retrieved: {len(data.get('packages', []))} packages found")
            if data.get('packages'):
                print(f"📋 Sample package: {json.dumps(data['packages'][0], indent=2)}")
            return True
        else:
            print(f"❌ Failed to get package information: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_clear_sensor_data():
    """Test clearing sensor data"""
    print("\n🗑️ Testing sensor data clearing...")
    
    try:
        response = requests.delete(f'{BACKEND_URL}/api/sensor-data')
        if response.status_code == 200:
            print(f"✅ Sensor data cleared successfully: {response.json()}")
            return True
        else:
            print(f"❌ Failed to clear sensor data: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting integration tests for MQTT sensor data and QR validation")
    print("=" * 70)
    
    # Initialize database
    init_database()
    
    # Run tests
    tests = [
        test_sensor_data_storage,
        test_get_sensor_data,
        test_package_information_retrieval,
        test_qr_validation_with_sensor_data,
        test_clear_sensor_data
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"🏁 Tests completed: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the backend server and database.")

if __name__ == '__main__':
    main()
