#!/usr/bin/env python3
"""
Script to create complete test flow: orders + sensor data + QR validation
This simulates the complete package scanning workflow
"""

import sqlite3
import requests
import json
from datetime import datetime
import os

def create_test_flow():
    """Create complete test workflow with orders, sensor data, and QR validation"""
    try:
        # Change to the backend directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        print("🚀 Creating Complete Test Flow...")
        
        # Step 1: Create test orders
        test_orders = [
            ("ORD001", "John Doe", "123-456-7890", "123 Main St", "PROD001", "Wireless Headphones", 89.99),
            ("ORD002", "Jane Smith", "987-654-3210", "456 Oak Ave", "PROD002", "Gaming Mouse", 59.99),
            ("ORD003", "Bob Johnson", "555-123-4567", "789 Pine St", "PROD003", "Coffee Maker", 129.99),
            ("ORD004", "Alice Brown", "444-555-6666", "321 Elm St", "PROD004", "Smartphone Case", 24.99),
            ("ORD005", "Charlie Wilson", "777-888-9999", "654 Maple Dr", "PROD005", "Desk Lamp", 79.99)
        ]
        
        print("\n📦 Step 1: Creating test orders...")
        
        for order_number, customer, phone, address, product_id, product_name, amount in test_orders:
            # Check if order already exists
            c.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
            existing = c.fetchone()
            
            if not existing:
                c.execute('''
                    INSERT INTO orders (order_number, customer_name, contact_number, address, product_id, product_name, amount, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_number, customer, phone, address, product_id, product_name, amount, datetime.now().isoformat()))
                print(f"✅ Created order: {order_number} - {product_name} for {customer}")
            else:
                print(f"⏭️  Order {order_number} already exists")
        
        conn.commit()
        
        # Step 2: Create sensor data and simulate QR scanning workflow
        test_sensor_data = [
            ("ORD001", 0.25, 15.0, 10.0, 8.0, "Small"),     # Wireless Headphones
            ("ORD002", 0.18, 12.0, 8.0, 6.0, "Small"),      # Gaming Mouse
            ("ORD003", 1.2, 25.0, 20.0, 15.0, "Large"),     # Coffee Maker
            ("ORD004", 0.05, 10.0, 5.0, 2.0, "Small"),      # Smartphone Case
            ("ORD005", 0.8, 20.0, 15.0, 12.0, "Medium")     # Desk Lamp
        ]
        
        print("\n🔍 Step 2: Simulating complete scan workflow...")
        
        for order_number, weight, width, height, length, package_size in test_sensor_data:
            print(f"\n--- Processing {order_number} ---")
            
            # Step 2a: Insert sensor data (simulating MQTT sensor readings)
            print(f"📊 Inserting sensor data for {order_number}...")
            c.execute('DELETE FROM loaded_sensor_data')  # Clear any existing sensor data
            
            current_time = datetime.now().isoformat()
            c.execute('''
                INSERT INTO loaded_sensor_data 
                (weight, width, height, length, package_size, loadcell_timestamp, box_dimensions_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (weight, width, height, length, package_size, current_time, current_time))
            
            conn.commit()
            print(f"✅ Sensor data inserted: {weight}kg, {width}x{height}x{length}cm, Size: {package_size}")
            
            # Step 2b: Simulate QR code validation (this will create package_information record)
            print(f"🔍 Validating QR code: {order_number}...")
            
            # Use the actual validation endpoint to simulate real workflow
            try:
                response = requests.post('http://192.168.100.61:5000/api/validate-qr', 
                                       json={'qr_data': order_number},
                                       timeout=5)
                
                if response.ok:
                    result = response.json()
                    if result.get('valid') and not result.get('already_scanned'):
                        print(f"✅ QR validation successful for {order_number}")
                        if result.get('sensor_data_applied'):
                            print(f"📦 Package information created with sensor data")
                        else:
                            print(f"⚠️  No sensor data was applied")
                    elif result.get('already_scanned'):
                        print(f"⏭️  {order_number} was already scanned")
                    else:
                        print(f"❌ QR validation failed for {order_number}")
                else:
                    print(f"❌ QR validation request failed: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not connect to backend server: {e}")
                print("💡 Make sure the backend server is running on localhost:5000")
                
                # Fallback: manually create package_information record
                print("🔧 Creating package_information record manually...")
                c.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
                order = c.fetchone()
                
                if order:
                    order_id = order[0]
                    c.execute('''
                        INSERT INTO package_information 
                        (order_id, order_number, weight, width, height, length, package_size, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (order_id, order_number, weight, width, height, length, package_size, current_time))
                    
                    # Also create scanned_codes record
                    c.execute('''
                        INSERT OR IGNORE INTO scanned_codes (order_id, order_number, isverified, device)
                        VALUES (?, ?, ?, ?)
                    ''', (order_id, order_number, 'yes', 'test_script'))
                    
                    conn.commit()
                    print(f"✅ Package information created manually for {order_number}")
        
        # Step 3: Show summary
        print("\n📊 Summary:")
        
        c.execute('SELECT COUNT(*) FROM orders')
        order_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM package_information')
        package_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM scanned_codes')
        scanned_count = c.fetchone()[0]
        
        print(f"   📦 Total Orders: {order_count}")
        print(f"   📊 Package Information Records: {package_count}")
        print(f"   ✅ Scanned Codes: {scanned_count}")
        
        # Show package information
        print(f"\n📦 Package Information Records:")
        c.execute('''
            SELECT pi.order_number, o.customer_name, o.product_name, 
                   pi.weight, pi.width, pi.height, pi.length, pi.package_size, pi.created_at
            FROM package_information pi
            JOIN orders o ON pi.order_id = o.id
            ORDER BY pi.created_at DESC
        ''')
        
        packages = c.fetchall()
        if packages:
            print("   Order    | Customer      | Product               | Weight | Dimensions (W×H×L) | Size   | Created")
            print("   ---------|---------------|----------------------|--------|-------------------|--------|----------")
            for pkg in packages:
                order_num, customer, product, weight, width, height, length, size, created = pkg
                created_short = created[:19] if created else 'N/A'
                print(f"   {order_num:<8} | {customer:<13} | {product:<20} | {weight:>4.2f}kg | {width}×{height}×{length}cm      | {size:<6} | {created_short}")
        else:
            print("   No package data found")
        
        conn.close()
        
        print(f"\n🎉 Test flow completed successfully!")
        print(f"💡 You can now view the package data in the Scanner.js frontend!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating test flow: {e}")
        return False

if __name__ == "__main__":
    success = create_test_flow()
    if success:
        print("✅ Test flow creation completed!")
    else:
        print("❌ Test flow creation failed!")
