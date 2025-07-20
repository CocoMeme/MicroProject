#!/usr/bin/env python3
"""
Sensor Workflow Simulation Script

This script simulates the real sensor workflow:
1. Loads fake sensor data into the database
2. Waits for QR code scan
3. Automatically clears sensor data after successful scan

This mimics the production behavior where:
- ESP32 sensors send data via MQTT
- User scans QR code
- System processes the scan and clears sensor data
"""

import sqlite3
import json
import requests
import time
import threading
from datetime import datetime
import random

# Configuration
BACKEND_URL = 'http://192.168.100.61:5000'
DATABASE_PATH = 'backend/database.db'
CHECK_INTERVAL = 2  # Check for scans every 2 seconds

class SensorWorkflowSimulator:
    def __init__(self):
        self.running = False
        self.sensor_data_loaded = False
        self.last_scan_count = 0
        
    def generate_realistic_sensor_data(self):
        """Generate realistic sensor data similar to what ESP32 would send"""
        # Simulate different package sizes
        packages = [
            {"weight": 0.5, "width": 10, "height": 5, "length": 15},   # Small package
            {"weight": 1.2, "width": 15, "height": 8, "length": 20},   # Medium package  
            {"weight": 2.8, "width": 20, "height": 12, "length": 30},  # Large package
            {"weight": 4.5, "width": 25, "height": 15, "length": 35},  # Extra large
        ]
        
        # Pick a random package and add some variance
        base_package = random.choice(packages)
        
        return {
            'weight': round(base_package['weight'] + random.uniform(-0.1, 0.1), 2),
            'width': round(base_package['width'] + random.uniform(-1, 1), 1),
            'height': round(base_package['height'] + random.uniform(-0.5, 0.5), 1),
            'length': round(base_package['length'] + random.uniform(-1, 1), 1),
            'loadcell_timestamp': datetime.now().isoformat(),
            'box_dimensions_timestamp': datetime.now().isoformat()
        }
    
    def load_sensor_data(self):
        """Load sensor data into the database"""
        print("\n🔧 Simulating sensor data loading...")
        
        sensor_data = self.generate_realistic_sensor_data()
        
        print(f"📊 Generated sensor data:")
        print(f"   Weight: {sensor_data['weight']} kg")
        print(f"   Dimensions: {sensor_data['width']} x {sensor_data['height']} x {sensor_data['length']} cm")
        
        try:
            response = requests.post(f'{BACKEND_URL}/api/sensor-data', json=sensor_data, timeout=5)
            if response.status_code == 200:
                print("✅ Sensor data loaded successfully!")
                self.sensor_data_loaded = True
                return True
            else:
                print(f"❌ Failed to load sensor data: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def check_for_new_scans(self):
        """Check for new QR code scans"""
        try:
            response = requests.get(f'{BACKEND_URL}/api/qr-scans?limit=1', timeout=5)
            if response.status_code == 200:
                scans = response.json()
                if scans and len(scans) > 0:
                    latest_scan = scans[0]
                    scan_id = latest_scan.get('id', 0)
                    
                    # Check if this is a new scan
                    if scan_id > self.last_scan_count:
                        self.last_scan_count = scan_id
                        return latest_scan
            return None
        except requests.RequestException as e:
            print(f"❌ Error checking for scans: {e}")
            return None
    
    def clear_sensor_data(self):
        """Clear sensor data from database"""
        try:
            response = requests.delete(f'{BACKEND_URL}/api/sensor-data', timeout=5)
            if response.status_code == 200:
                print("🗑️ Sensor data cleared successfully!")
                self.sensor_data_loaded = False
                return True
            else:
                print(f"❌ Failed to clear sensor data: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Error clearing sensor data: {e}")
            return False
    
    def get_current_sensor_data(self):
        """Get current sensor data from database"""
        try:
            response = requests.get(f'{BACKEND_URL}/api/sensor-data', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('sensor_data')
            return None
        except requests.RequestException as e:
            print(f"❌ Error getting sensor data: {e}")
            return None
    
    def monitor_scans(self):
        """Monitor for QR code scans in a separate thread"""
        print("👀 Monitoring for QR code scans...")
        print("   (Scan a QR code to trigger data processing)")
        
        while self.running:
            if self.sensor_data_loaded:
                new_scan = self.check_for_new_scans()
                if new_scan:
                    print(f"\n🔍 NEW QR SCAN DETECTED!")
                    print(f"   QR Data: {new_scan.get('qr_data', 'Unknown')}")
                    print(f"   Valid: {new_scan.get('is_valid', False)}")
                    print(f"   Timestamp: {new_scan.get('timestamp', 'Unknown')}")
                    
                    if new_scan.get('is_valid', False):
                        print("✅ Valid QR code - Processing...")
                        
                        # Wait a moment to simulate processing time
                        time.sleep(1)
                        
                        # Clear sensor data (simulating real workflow)
                        if self.clear_sensor_data():
                            print("🎉 Workflow completed! Sensor data has been processed and cleared.")
                            print("\n💡 Ready for next package - loading new sensor data...")
                            time.sleep(2)
                            self.load_sensor_data()
                    else:
                        print("❌ Invalid QR code - sensor data remains loaded")
            
            time.sleep(CHECK_INTERVAL)
    
    def start(self):
        """Start the sensor workflow simulation"""
        print("🚀 Starting Sensor Workflow Simulator")
        print("=" * 60)
        
        # Initialize by getting current scan count
        try:
            response = requests.get(f'{BACKEND_URL}/api/qr-scans?limit=1', timeout=5)
            if response.status_code == 200:
                scans = response.json()
                if scans and len(scans) > 0:
                    self.last_scan_count = scans[0].get('id', 0)
        except:
            pass
        
        # Load initial sensor data
        if not self.load_sensor_data():
            print("❌ Failed to load initial sensor data. Please check backend connection.")
            return
        
        # Start monitoring in background thread
        self.running = True
        monitor_thread = threading.Thread(target=self.monitor_scans, daemon=True)
        monitor_thread.start()
        
        try:
            print("\n" + "=" * 60)
            print("🎯 SIMULATION ACTIVE")
            print("=" * 60)
            print("📦 Sensor data is loaded and waiting for QR scan")
            print("🔍 Scan any QR code to trigger the workflow")
            print("⏹️  Press Ctrl+C to stop simulation")
            print("=" * 60)
            
            # Keep main thread alive and show status
            while True:
                current_data = self.get_current_sensor_data()
                if current_data and self.sensor_data_loaded:
                    print(f"\r💾 Sensor data ready - Weight: {current_data.get('weight', 'N/A')}kg, " +
                          f"Size: {current_data.get('width', 'N/A')}x{current_data.get('height', 'N/A')}x{current_data.get('length', 'N/A')}cm " +
                          f"| Waiting for scan...", end="", flush=True)
                elif not self.sensor_data_loaded:
                    print(f"\r⏳ No sensor data loaded - Next package coming soon...", end="", flush=True)
                else:
                    print(f"\r❌ No sensor data in database", end="", flush=True)
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping simulation...")
            self.running = False
            
            # Clean up - clear any remaining sensor data
            if self.sensor_data_loaded:
                print("🧹 Cleaning up - clearing sensor data...")
                self.clear_sensor_data()
            
            print("👋 Sensor Workflow Simulator stopped!")

def main():
    """Main function"""
    simulator = SensorWorkflowSimulator()
    simulator.start()

if __name__ == '__main__':
    main()
