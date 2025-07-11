from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import random
from datetime import datetime
import requests
import os
import sqlite3
from dotenv import load_dotenv
from products_data import products_data

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper function to convert row to dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Configuration for Raspberry Pi
RASPBERRY_PI_URL = os.getenv('RASPBERRY_PI_URL', 'http://localhost:5001')  # Default value if not set

# Sample data for demonstration
parcel_data = {
    "total_parcels": 1247,
    "processed_today": 89,
    "pending_parcels": 23,
    "sorting_rate": 145,  # parcels per hour
    "system_status": "operational",
    "conveyor_speed": 2.5,  # m/s
    "last_update": datetime.now().isoformat()
}

# Sample recent parcels data
recent_parcels = [
    {"id": "PKG-2025-001", "weight": 2.3, "size": "Medium", "destination": "Zone A", "timestamp": "2025-07-03T10:30:00"},
    {"id": "PKG-2025-002", "weight": 1.1, "size": "Small", "destination": "Zone B", "timestamp": "2025-07-03T10:28:00"},
    {"id": "PKG-2025-003", "weight": 3.8, "size": "Large", "destination": "Zone C", "timestamp": "2025-07-03T10:25:00"},
    {"id": "PKG-2025-004", "weight": 0.8, "size": "Small", "destination": "Zone A", "timestamp": "2025-07-03T10:22:00"},
    {"id": "PKG-2025-005", "weight": 2.9, "size": "Medium", "destination": "Zone B", "timestamp": "2025-07-03T10:18:00"},
]

# Sample orders data
orders_data = {
    "1": {
        "orderNumber": "ORD-001",
        "customerName": "John Smith",
        "date": "2024-03-20",
        "status": "Pending",
        "id": "1"
    },
    "2": {
        "orderNumber": "ORD-002",
        "customerName": "Jane Doe",
        "date": "2024-03-20",
        "status": "Processing",
        "id": "2"
    },
    "3": {
        "orderNumber": "ORD-003",
        "customerName": "Bob Johnson",
        "date": "2024-03-19",
        "status": "Completed",
        "id": "3"
    }
}

@app.route('/')
def home():
    return jsonify({
        "message": "Parcel Sorting Machine API",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/dashboard')
def get_dashboard_data():
    # Simulate real-time data updates
    parcel_data["processed_today"] = random.randint(85, 95)
    parcel_data["pending_parcels"] = random.randint(15, 30)
    parcel_data["sorting_rate"] = random.randint(140, 150)
    parcel_data["conveyor_speed"] = round(random.uniform(2.0, 3.0), 1)
    parcel_data["last_update"] = datetime.now().isoformat()
    
    return jsonify(parcel_data)

@app.route('/api/recent-parcels')
def get_recent_parcels():
    return jsonify(recent_parcels)

@app.route('/api/system-status')
def get_system_status():
    return jsonify({
        "conveyor_belt": "running",
        "sorting_arms": "operational",
        "sensors": "active",
        "esp32_connection": "connected",
        "raspberry_pi": "healthy",
        "temperature": random.randint(20, 30),
        "humidity": random.randint(40, 60),
        "uptime": "2 days, 14 hours"
    })

@app.route('/api/print-qr', methods=['POST'])
def print_qr_code():
    try:
        data = request.get_json()
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'error': 'Order ID is required'}), 400

        # Get order details from database
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order_data = c.fetchone()
        conn.close()

        if not order_data:
            return jsonify({'error': 'Order not found'}), 404

        # Format order data for the printer
        printer_data = {
            'orderNumber': order_data['order_number'],
            'customerName': order_data['customer_name'],
            'date': order_data['date'],
            'status': order_data['status'],
            'email': order_data['email'],
            'address': order_data['address'],
            'productName': order_data['product_name'],
            'amount': f"₱{order_data['amount']:.2f}",
            'timestamp': datetime.now().isoformat()
        }

        # Forward the print request to the Raspberry Pi
        try:
            response = requests.post(
                f"{RASPBERRY_PI_URL}/print-qr",
                json=printer_data,
                headers={'Content-Type': 'application/json'},
                timeout=10  # Add timeout to prevent hanging
            )
            
            if response.status_code == 200:
                return jsonify({
                    'message': f'QR code print request sent for order {order_id}',
                    'printer_response': response.json()
                }), 200
            else:
                return jsonify({
                    'error': 'Failed to print QR code',
                    'details': response.text
                }), response.status_code
                
        except requests.RequestException as e:
            error_msg = str(e)
            # Check if it's a connection error
            if "Connection refused" in error_msg:
                return jsonify({
                    'error': 'Printer service is not available',
                    'details': 'Please check if the Raspberry Pi printer service is running'
                }), 503
            return jsonify({
                'error': 'Failed to connect to printer service',
                'details': error_msg
            }), 503

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(products_data)

@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = sqlite3.connect('database.db')
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY date DESC')
    orders = c.fetchall()
    conn.close()
    return jsonify(orders)

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        required_fields = ['customerName', 'email', 'address', 'productId']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Find selected product
        product = next((p for p in products_data if p['id'] == data['productId']), None)
        if not product:
            return jsonify({'error': 'Invalid product ID'}), 400
        
        # Connect to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Get the next order ID
        c.execute('SELECT COUNT(*) FROM orders')
        order_count = c.fetchone()[0]
        new_order_number = f"ORD-{str(order_count + 1).zfill(3)}"
        
        # Insert new order
        c.execute('''
            INSERT INTO orders (
                order_number, customer_name, email, address,
                product_id, product_name, amount, date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_order_number,
            data['customerName'],
            data['email'],
            data['address'],
            data['productId'],
            product['name'],
            float(product['price'].replace('₱', '')),  # Convert price string to float
            datetime.now().strftime("%Y-%m-%d"),
            'Pending'
        ))
        
        # Get the inserted order
        order_id = c.lastrowid
        conn.commit()
        
        # Fetch the created order
        conn.row_factory = dict_factory
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        new_order = c.fetchone()
        conn.close()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': new_order
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
