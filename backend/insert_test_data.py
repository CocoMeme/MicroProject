#!/usr/bin/env python3
"""
Simple script to insert test package data directly into the database
"""

import sqlite3
from datetime import datetime
import os

def insert_test_package_data():
    """Insert dummy package data for testing visualization"""
    try:
        # Change to the backend directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        print("Inserting test data...")
        
        # Insert test package data into loaded_sensor_data table (the actual sensor data table)
        test_package_data = [
            (0.25, 15.0, 10.0, 8.0, "Small"),     # Wireless Headphones - 250g
            (0.18, 12.0, 8.0, 6.0, "Small"),      # Gaming Mouse - 180g
            (1.2, 25.0, 20.0, 15.0, "Large"),     # Coffee Maker - 1.2kg
            (0.05, 10.0, 5.0, 2.0, "Small"),      # Smartphone Case - 50g
            (0.8, 20.0, 15.0, 12.0, "Medium"),    # Desk Lamp - 800g
            (0.35, 18.0, 12.0, 9.0, "Small"),     # Bluetooth Speaker - 350g
            (2.1, 30.0, 25.0, 18.0, "Large"),     # Monitor - 2.1kg
            (0.15, 14.0, 9.0, 7.0, "Small"),      # Wireless Charger - 150g
            (0.9, 22.0, 16.0, 14.0, "Medium"),    # Tablet Stand - 900g
            (1.5, 28.0, 22.0, 16.0, "Large")      # Printer - 1.5kg
        ]
        
        # Insert test package data using the exact column structure from the app
        for weight, width, height, length, package_size in test_package_data:
            # Create timestamps
            current_time = datetime.now().isoformat()
            
            c.execute('''
                INSERT INTO loaded_sensor_data 
                (weight, width, height, length, package_size, loadcell_timestamp, box_dimensions_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (weight, width, height, length, package_size, current_time, current_time))
            
            print(f"✅ Inserted package data: {weight}kg, {width}x{height}x{length}cm, Size: {package_size}")
        
        conn.commit()
        
        # Display current package data
        print(f"\n📊 Database Summary:")
        c.execute('SELECT COUNT(*) FROM loaded_sensor_data')
        package_count = c.fetchone()[0]
        
        print(f"   Total Sensor Data Records: {package_count}")
        
        # Show the latest package data
        print(f"\n📦 Latest Package Information:")
        c.execute('''
            SELECT weight, width, height, length, package_size, created_at
            FROM loaded_sensor_data
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        packages = c.fetchall()
        if packages:
            print("   Weight | Dimensions (W×H×L) | Size   | Created At")
            print("   -------|-------------------|--------|-------------------")
            for pkg in packages:
                weight, width, height, length, size, created_at = pkg
                print(f"   {weight:>4.2f}kg | {width}×{height}×{length}cm        | {size:<6} | {created_at}")
        else:
            print("   No package data found")
        
        conn.close()
        
        print(f"\n🎉 Successfully inserted {len(test_package_data)} package data records!")
        return True
        
    except Exception as e:
        print(f"❌ Error inserting test package data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Inserting Test Package Data...")
    success = insert_test_package_data()
    if success:
        print("✅ Test data insertion completed successfully!")
    else:
        print("❌ Test data insertion failed!")
