#!/usr/bin/env python3
"""
Simple curl-like test for motor endpoints
"""

import requests
import json

def test_endpoints():
    base_url = "http://localhost:5000"
    
    print("Testing motor endpoints...")
    
    # Test stop motor
    print("\n1. Testing STOP motor:")
    try:
        response = requests.post(f"{base_url}/api/stop-motor", 
                               headers={'Content-Type': 'application/json'})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test start motor  
    print("\n2. Testing START motor:")
    try:
        response = requests.post(f"{base_url}/api/start-motor",
                               headers={'Content-Type': 'application/json'})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_endpoints()
