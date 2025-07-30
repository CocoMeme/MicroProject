from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import time
import random
from datetime import datetime
import requests
import os
import sqlite3
from dotenv import load_dotenv
import threading
import logging
import paho.mqtt.client as mqtt
import json
from products_data import products_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
CORS(app)  # Enable CORS for all routes

# Initialize SocketIO with CORS enabled
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Track application startup time for uptime calculation
app_startup_time = datetime.now()

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Check if orders table exists with old schema (has status column)
    c.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in c.fetchall()]
    
    # If status column exists, we need to migrate the table
    if 'status' in columns:
        logger.info("Migrating orders table to remove status column...")
        
        # Create backup of existing data
        c.execute("SELECT * FROM orders")
        existing_orders = c.fetchall()
        
        # Drop the old table
        c.execute("DROP TABLE IF EXISTS orders")
        
        # Create new table without status column
        c.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                email TEXT,
                contact_number TEXT NOT NULL,
                address TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        
        # Restore data (excluding status column)
        for order in existing_orders:
            c.execute('''
                INSERT INTO orders (
                    id, order_number, customer_name, email, contact_number, 
                    address, product_id, product_name, amount, date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', order[:10])  # Take first 10 columns (excluding status which was the last)
        
        logger.info("Migration completed successfully!")
    else:
        # Create table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                contact_number TEXT NOT NULL,
                address TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL
            )
        ''')
    
    # Create QR scans table to store scan history
    c.execute('''
        CREATE TABLE IF NOT EXISTS qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            device TEXT NOT NULL,
            is_valid BOOLEAN NOT NULL,
            order_id INTEGER,
            validation_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create package information table to store physical package data
    c.execute('''
        CREATE TABLE IF NOT EXISTS package_information (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            order_number TEXT,
            weight REAL,
            width REAL,
            height REAL,
            length REAL,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Create scanned_codes table to track verified scanned QR codes
    c.execute('''
        CREATE TABLE IF NOT EXISTS scanned_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            order_number TEXT NOT NULL,
            isverified TEXT NOT NULL CHECK(isverified IN ('yes', 'no')),
            scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            device TEXT DEFAULT 'raspberry_pi',
            FOREIGN KEY (order_id) REFERENCES orders (id),
            UNIQUE(order_id) -- Prevent duplicate entries for same order
        )
    ''')
    
    # Create index for faster lookups
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_scanned_codes_order_id ON scanned_codes(order_id)')
    except sqlite3.OperationalError:
        # Index might already exist
        pass
    
    # Clean up any duplicate entries that might exist (keep the oldest scan)
    c.execute('''
        DELETE FROM scanned_codes 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM scanned_codes 
            GROUP BY order_id
        )
    ''')
    
    if c.rowcount > 0:
        logger.info(f"Cleaned up {c.rowcount} duplicate scanned codes")
    
    conn.commit()
    
    # Create loaded_sensor_data table to store MQTT sensor data temporarily
    c.execute('''
        CREATE TABLE IF NOT EXISTS loaded_sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight REAL,
            width REAL,
            height REAL,
            length REAL,
            package_size TEXT,
            loadcell_timestamp TEXT,
            box_dimensions_timestamp TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add package_size column if it doesn't exist (migration)
    try:
        c.execute("PRAGMA table_info(loaded_sensor_data)")
        columns = [column[1] for column in c.fetchall()]
        if 'package_size' not in columns:
            c.execute("ALTER TABLE loaded_sensor_data ADD COLUMN package_size TEXT")
            logger.debug("Added package_size column to loaded_sensor_data table")
    except Exception as e:
        logger.debug(f"Could not add package_size column (may already exist): {e}")
    
    # Add package_size column to package_information table if it doesn't exist (migration)
    try:
        c.execute("PRAGMA table_info(package_information)")
        columns = [column[1] for column in c.fetchall()]
        if 'package_size' not in columns:
            c.execute("ALTER TABLE package_information ADD COLUMN package_size TEXT")
            logger.debug("Added package_size column to package_information table")
    except Exception as e:
        logger.debug(f"Could not add package_size column to package_information (may already exist): {e}")
    
    conn.commit()
    conn.close()

def migrate_database():
    """Remove email column from existing orders table if it exists"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check if email column exists
        c.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'email' in columns:
            logger.info("Removing email column from orders table...")
            
            # Create new table without email column
            c.execute('''
                CREATE TABLE orders_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    contact_number TEXT NOT NULL,
                    address TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL
                )
            ''')
            
            # Copy data from old table to new table (excluding email)
            c.execute('''
                INSERT INTO orders_new (
                    id, order_number, customer_name, contact_number, address,
                    product_id, product_name, amount, date
                )
                SELECT id, order_number, customer_name, contact_number, address,
                       product_id, product_name, amount, date
                FROM orders
            ''')
            
            # Drop old table and rename new table
            c.execute('DROP TABLE orders')
            c.execute('ALTER TABLE orders_new RENAME TO orders')
            
            conn.commit()
            
        conn.close()
    except Exception as e:
        logger.error(f"Database migration failed: {e}")

# Initialize database
init_db()

# Run database migration
migrate_database()

# Helper function to convert row to dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Configuration for Raspberry Pi
RASPBERRY_PI_URL = os.getenv('RASPBERRY_PI_URL', 'http://10.194.125.227:5001')  # Default value if not set

def send_print_request_to_raspi(order_data):
    """Send print request to Raspberry Pi with order details"""
    try:
        # Prepare order data for printing
        print_data = {
            'orderNumber': order_data['order_number'],
            'customerName': order_data['customer_name'],
            'productName': order_data['product_name'],
            'amount': str(order_data['amount']),
            'date': order_data['date'],
            'address': order_data.get('address', 'N/A'),
            'contactNumber': order_data.get('contact_number', 'N/A'),
            'email': order_data.get('email', '')
        }
        
        logger.info(f"Sending print request to Raspberry Pi for order {order_data['order_number']}")
        
        # Send print request to Raspberry Pi
        response = requests.post(
            f"{RASPBERRY_PI_URL}/print-receipt",
            json=print_data,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent print request for order {order_data['order_number']}")
            return True, "Print request sent successfully"
        else:
            error_msg = f"Print request failed with status {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f": {error_data.get('error', 'Unknown error')}"
            except:
                error_msg += f": {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Print request to Raspberry Pi timed out"
        logger.error(error_msg)
        return False, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Cannot connect to Raspberry Pi printer service"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Print request failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_system_uptime():
    """Calculate and return system uptime as formatted string"""
    uptime_delta = datetime.now() - app_startup_time
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} days, {hours} hours"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes"
    else:
        return f"{minutes} minutes"

def get_real_time_dashboard_data():
    """Get real-time dashboard data from database"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Get today's date for filtering
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get QR scans today (from qr_scans table)
        c.execute('''
            SELECT COUNT(*) FROM qr_scans 
            WHERE DATE(timestamp) = ? AND is_valid = 1
        ''', (today,))
        scans_today = c.fetchone()[0] or 0
        
        # Get prints today (from scanned_codes table - these represent successful prints)
        c.execute('''
            SELECT COUNT(*) FROM scanned_codes 
            WHERE DATE(scanned_at) = ? AND isverified = 'yes'
        ''', (today,))
        prints_today = c.fetchone()[0] or 0
        
        # Get total packages processed (from package_information table)
        c.execute('SELECT COUNT(*) FROM package_information')
        total_packages = c.fetchone()[0] or 0
        
        # Get pending parcels (loaded_sensor_data without linked orders)
        c.execute('''
            SELECT COUNT(*) FROM loaded_sensor_data lsd
            LEFT JOIN package_information pi ON lsd.id = pi.id
            WHERE pi.id IS NULL
        ''')
        pending_parcels = c.fetchone()[0] or 0
        
        # Calculate uptime
        uptime_str = get_system_uptime()
        
        # Calculate sorting rate (packages per hour based on today's activity)
        if scans_today > 0:
            # Rough calculation: scans per hour based on time elapsed today
            current_time = datetime.now()
            start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            hours_elapsed = max(1, (current_time - start_of_day).seconds / 3600)
            sorting_rate = int(scans_today / hours_elapsed) if hours_elapsed > 0 else scans_today
        else:
            sorting_rate = 0
            
        conn.close()
        
        return {
            "total_parcels": total_packages,
            "processed_today": scans_today,
            "pending_parcels": pending_parcels,
            "sorting_rate": sorting_rate,
            "system_status": "operational",
            "conveyor_speed": 2.5,  # This could be made dynamic if you have sensor data
            "last_update": datetime.now().isoformat(),
            "uptime": uptime_str,
            "scans_today": scans_today,
            "prints_today": prints_today
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time dashboard data: {e}")
        # Return fallback data if database query fails
        return {
            "total_parcels": 0,
            "processed_today": 0,
            "pending_parcels": 0,
            "sorting_rate": 0,
            "system_status": "error",
            "conveyor_speed": 0.0,
            "last_update": datetime.now().isoformat(),
            "uptime": "unknown",
            "scans_today": 0,
            "prints_today": 0
        }

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
    # Get real-time data from database
    real_time_data = get_real_time_dashboard_data()
    return jsonify(real_time_data)

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
        "uptime": get_system_uptime()
    })

@app.route('/api/qr-scans', methods=['POST'])
def receive_qr_scans():
    """Receive QR scan data from Raspberry Pi"""
    try:
        data = request.get_json()
        scans = data.get('scans', [])
        
        if not scans:
            return jsonify({'error': 'No scan data provided'}), 400
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Store each scan in the database
        for scan in scans:
            validation = scan.get('validation', {})
            c.execute('''
                INSERT INTO qr_scans (
                    qr_data, timestamp, device, is_valid, 
                    order_id, validation_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                scan.get('qr_data'),
                scan.get('timestamp'),
                scan.get('device', 'unknown'),
                validation.get('valid', False),
                validation.get('order_id'),
                validation.get('message', '')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Successfully stored {len(scans)} scan records',
            'count': len(scans)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/qr-scans', methods=['GET'])
@app.route('/api/qr-history', methods=['GET'])  # Alias for frontend compatibility
def get_qr_scans():
    """Get QR scan history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM qr_scans 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        scans = c.fetchall()
        conn.close()
        
        return jsonify(scans), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

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
            'email': order_data['email'],
            'contactNumber': order_data.get('contact_number', 'N/A'),
            'address': order_data['address'],
            'productName': order_data['product_name'],
            'amount': f"₱{order_data['amount']:.2f}",
            'timestamp': datetime.now().isoformat()
        }

        # Forward the print request to the Raspberry Pi with retries
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to print QR code (attempt {attempt + 1}/{max_retries})")
                response = requests.post(
                    f"{RASPBERRY_PI_URL}/print-qr",
                    json=printer_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=15  # Increased timeout for stability
                )

                if response.status_code == 200:
                    response_data = response.json()
                    return jsonify({
                        'message': f'QR code printed successfully for order {order_id}',
                        'printer_response': response_data,
                        'order_number': printer_data['orderNumber']
                    }), 200
                elif response.status_code == 503:
                    # Printer unavailable - don't retry
                    return jsonify({
                        'error': 'Printer is not available',
                        'details': 'Please check if the thermal printer is connected to the Raspberry Pi'
                    }), 503
                else:
                    # Other errors - might be temporary, so retry
                    if attempt == max_retries - 1:  # Last attempt
                        return jsonify({
                            'error': 'Failed to print QR code',
                            'details': response.text,
                            'status_code': response.status_code
                        }), response.status_code
                    else:
                        logger.warning(f"Print attempt failed with status {response.status_code}, retrying...")
                        time.sleep(retry_delay)

            except requests.exceptions.ConnectTimeout:
                error_msg = "Connection to Raspberry Pi timed out"
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': 'Printer service timeout',
                        'details': error_msg
                    }), 504
                else:
                    logger.warning(f"Connection timeout (attempt {attempt + 1}), retrying...")
                    time.sleep(retry_delay)
                    
            except requests.exceptions.ConnectionError:
                error_msg = "Cannot connect to Raspberry Pi printer service"
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': 'Printer service is not available',
                        'details': 'Please check if the Raspberry Pi printer service is running at ' + RASPBERRY_PI_URL
                    }), 503
                else:
                    logger.warning(f"Connection error (attempt {attempt + 1}), retrying...")
                    time.sleep(retry_delay)
                    
            except requests.RequestException as e:
                error_msg = str(e)
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': 'Failed to connect to printer service',
                        'details': error_msg
                    }), 500
                else:
                    logger.warning(f"Request error (attempt {attempt + 1}): {error_msg}, retrying...")
                    time.sleep(retry_delay)

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
        required_fields = ['customerName', 'email', 'contactNumber', 'address', 'productId']

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
                order_number, customer_name, email, contact_number, address,
                product_id, product_name, amount, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_order_number,
            data['customerName'],
            data['email'],
            data['contactNumber'],
            data['address'],
            data['productId'],
            product['name'],
            float(product['price'].replace('₱', '')),  # Convert price string to float
            datetime.now().strftime("%Y-%m-%d")
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

@app.route('/api/manual-orders', methods=['POST'])
def create_manual_order():
    try:
        data = request.get_json()
        required_fields = ['customerName', 'contactNumber', 'address', 'productName', 'price']

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validate price is a number
        try:
            price = float(data['price'])
            if price < 0:
                return jsonify({'error': 'Price must be a positive number'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid price format'}), 400

        # Connect to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Get the next order ID
        c.execute('SELECT COUNT(*) FROM orders')
        order_count = c.fetchone()[0]
        new_order_number = f"ORD-{str(order_count + 1).zfill(3)}"

        # Insert new manual order
        c.execute('''
            INSERT INTO orders (
                order_number, customer_name, contact_number, address,
                product_id, product_name, amount, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_order_number,
            data['customerName'],
            data['contactNumber'],
            data['address'],
            'MANUAL',  # Special product ID for manual orders
            data['productName'],
            price,
            datetime.now().strftime("%Y-%m-%d")
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
            'message': 'Manual order created successfully',
            'order': new_order
        }), 201

    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/camera/status')
def get_camera_status():
    """Get the status of the Raspberry Pi camera"""
    try:
        response = requests.get(f"{RASPBERRY_PI_URL}/camera/status")
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Start the Raspberry Pi camera"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/start")
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to start camera',
            'details': str(e)
        }), 503

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Stop the Raspberry Pi camera"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/stop")
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to stop camera',
            'details': str(e)
        }), 503

@app.route('/api/camera/last-qr')
def get_last_scanned_qr():
    """Get the last QR code scanned by the camera"""
    try:
        response = requests.get(f"{RASPBERRY_PI_URL}/camera/last-qr")
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to get last QR code',
            'details': str(e)
        }), 503

@app.route('/api/camera/stream-url')
def get_camera_stream_url():
    """Get the URL for the camera stream"""
    try:
        # Test if camera is accessible
        status_response = requests.get(f"{RASPBERRY_PI_URL}/camera/status")
        if status_response.status_code == 200:
            camera_status = status_response.json()
            if camera_status.get('camera_running', False):
                return jsonify({
                    'stream_url': f"{RASPBERRY_PI_URL}/video_feed",
                    'status': 'active'
                })
            else:
                return jsonify({
                    'error': 'Camera is not running',
                    'status': 'inactive'
                }), 400
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/camera/scanning-status')
def get_scanning_status():
    """Get current QR scanning delay status"""
    try:
        response = requests.get(f"{RASPBERRY_PI_URL}/camera/scanning-status")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'error': 'Failed to get scanning status',
                'details': response.text
            }), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/camera/reset-cycle', methods=['POST'])
def reset_scan_cycle():
    """Reset the scanning cycle (countdown + scanning session)"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/reset-cycle")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'error': 'Failed to reset scanning cycle',
                'details': response.text
            }), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/camera/start-session', methods=['POST'])
def start_scanning_session_immediately():
    """Start scanning session immediately, skipping countdown"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/start-session")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'error': 'Failed to start scanning session',
                'details': response.text
            }), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/camera/session-start', methods=['POST'])
def handle_camera_session_start():
    """Handle when a new session/page load occurs - reset scanning delay"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/session-start")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'error': 'Failed to handle session start',
                'details': response.text
            }), response.status_code
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to connect to camera service',
            'details': str(e)
        }), 503

@app.route('/api/system/status')
def get_full_system_status():
    """Get status of all system components including camera"""
    try:
        # Get camera status
        camera_response = requests.get(f"{RASPBERRY_PI_URL}/camera/status", timeout=2)
        camera_status = camera_response.json() if camera_response.ok else {'error': 'Camera service unavailable'}
        
        # Get printer status
        printer_response = requests.get(f"{RASPBERRY_PI_URL}/", timeout=2)
        printer_status = printer_response.json() if printer_response.ok else {'error': 'Printer service unavailable'}
        
        # Combine with existing system status
        system_status = {
            "conveyor_belt": "running",
            "sorting_arms": "operational",
            "sensors": "active",
            "esp32_connection": "connected",
            "raspberry_pi": "healthy" if camera_response.ok and printer_response.ok else "issues detected",
            "temperature": random.randint(20, 30),
            "humidity": random.randint(40, 60),
            "uptime": get_system_uptime(),
            "camera_system": camera_status,
            "printer_system": printer_status
        }
        
        return jsonify(system_status)
    except requests.RequestException as e:
        return jsonify({
            'error': 'Failed to get complete system status',
            'details': str(e)
        }), 503

@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the motor system via Raspberry Pi"""
    try:
        # Check if Raspberry Pi is reachable
        health_response = requests.get(f"{RASPBERRY_PI_URL}/", timeout=5)
        if not health_response.ok:
            return jsonify({
                'error': 'Raspberry Pi unreachable',
                'message': 'Cannot connect to Raspberry Pi server'
            }), 503
        
        # Send start command to Raspberry Pi
        start_response = requests.post(f"{RASPBERRY_PI_URL}/api/start-motor", timeout=10)
        
        if start_response.ok:
            response_data = start_response.json()
            
            # Log the system start event
            logger.info(f"Motor system started: {response_data.get('message', 'Motor initiated')}")
            
            # Emit WebSocket notification to connected clients
            socketio.emit('system_started', {
                'message': 'Motor system started',
                'timestamp': datetime.now().isoformat(),
                'initiated_from': 'admin_dashboard'
            })
            
            return jsonify({
                'success': True,
                'message': 'Motor system started successfully',
                'details': response_data.get('message', 'Motor initiated'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            error_data = start_response.json() if start_response.headers.get('content-type', '').startswith('application/json') else {}
            return jsonify({
                'error': 'Failed to start motor system',
                'message': error_data.get('message', 'Raspberry Pi returned an error'),
                'details': error_data.get('details', f'HTTP {start_response.status_code}')
            }), start_response.status_code
            
    except requests.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'Raspberry Pi did not respond in time'
        }), 504
    except requests.RequestException as e:
        return jsonify({
            'error': 'Communication error',
            'message': 'Failed to communicate with Raspberry Pi',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop the motor system via Raspberry Pi"""
    try:
        # Check if Raspberry Pi is reachable
        health_response = requests.get(f"{RASPBERRY_PI_URL}/", timeout=5)
        if not health_response.ok:
            return jsonify({
                'error': 'Raspberry Pi unreachable',
                'message': 'Cannot connect to Raspberry Pi server'
            }), 503
        
        # Send stop command to Raspberry Pi
        stop_response = requests.post(f"{RASPBERRY_PI_URL}/api/stop-motor", timeout=10)
        
        if stop_response.ok:
            response_data = stop_response.json()
            
            # Log the system stop event
            logger.info(f"Motor system stopped: {response_data.get('message', 'Motor stopped')}")
            
            # Emit WebSocket notification to connected clients
            socketio.emit('system_stopped', {
                'message': 'Motor system stopped',
                'timestamp': datetime.now().isoformat(),
                'initiated_from': 'admin_dashboard'
            })
            
            return jsonify({
                'success': True,
                'message': 'Motor system stopped successfully',
                'details': response_data.get('message', 'Motor stopped'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            error_data = stop_response.json() if stop_response.headers.get('content-type', '').startswith('application/json') else {}
            return jsonify({
                'error': 'Failed to stop motor system',
                'message': error_data.get('message', 'Raspberry Pi returned an error'),
                'details': error_data.get('details', f'HTTP {stop_response.status_code}')
            }), stop_response.status_code
            
    except requests.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'Raspberry Pi did not respond in time'
        }), 504
    except requests.RequestException as e:
        return jsonify({
            'error': 'Communication error',
            'message': 'Failed to communicate with Raspberry Pi',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    logger.info('WebSocket client connected')
    emit('status', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('WebSocket client disconnected')

@socketio.on('start_camera_stream')
def handle_start_camera(data=None):
    """Start camera and begin streaming QR code data"""
    try:
        # Start camera via HTTP request to Raspberry Pi
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/start", timeout=5)
        if response.ok:
            emit('camera_status', {'status': 'started'})
            # Start background thread for QR code polling
            socketio.start_background_task(qr_polling_task)
        else:
            emit('camera_error', {'error': 'Failed to start camera'})
    except requests.RequestException as e:
        emit('camera_error', {'error': f'Failed to connect to camera: {str(e)}'})

@socketio.on('stop_camera_stream')
def handle_stop_camera(data=None):
    """Stop camera streaming"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/camera/stop", timeout=5)
        if response.ok:
            emit('camera_status', {'status': 'stopped'})
        else:
            emit('camera_error', {'error': 'Failed to stop camera'})
    except requests.RequestException as e:
        emit('camera_error', {'error': f'Failed to connect to camera: {str(e)}'})

@socketio.on('get_system_status')
def handle_get_system_status(data=None):
    """Get current system status and emit to client"""
    try:
        # Get camera status
        camera_response = requests.get(f"{RASPBERRY_PI_URL}/camera/status", timeout=2)
        camera_status = camera_response.json() if camera_response.ok else {'error': 'Camera service unavailable'}
        
        system_status = {
            "conveyor_belt": "running",
            "sorting_arms": "operational", 
            "sensors": "active",
            "esp32_connection": "connected",
            "raspberry_pi": "healthy" if camera_response.ok else "issues detected",
            "temperature": random.randint(20, 30),
            "humidity": random.randint(40, 60),
            "uptime": get_system_uptime(),
            "camera_system": camera_status
        }
        
        emit('system_status', system_status)
    except requests.RequestException as e:
        emit('system_status', {
            'error': 'Failed to get system status',
            'details': str(e)
        })

@socketio.on('test_message')
def handle_test_message(data=None):
    """Handle test messages from clients"""
    logger.debug(f'Received test message: {data}')
    emit('test_response', {
        'message': f'Server received: {data.get("message", "No message") if data else "No data"}',
        'timestamp': datetime.now().isoformat()
    })

def qr_polling_task():
    """Background task to poll for QR codes and emit to clients"""
    last_qr_data = None
    while True:
        try:
            response = requests.get(f"{RASPBERRY_PI_URL}/camera/last-qr", timeout=2)
            if response.ok:
                data = response.json()
                if data.get('last_qr_data') and data['last_qr_data'] != last_qr_data:
                    last_qr_data = data['last_qr_data']
                    socketio.emit('qr_detected', {
                        'data': last_qr_data,
                        'timestamp': datetime.now().isoformat(),
                        'type': 'QR Code'
                    })
            time.sleep(1)  # Poll every second
        except requests.RequestException:
            # If we can't connect to camera, stop polling
            break
        except Exception as e:
            logger.error(f"Error in QR polling: {e}")
            break

@app.route('/api/package-information', methods=['POST'])
def create_package_information():
    """Store package information (weight and dimensions) for an order"""
    try:
        data = request.get_json()
        
        required_fields = ['order_number', 'order_id', 'timestamp']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate that at least one measurement is provided
        measurements = ['weight', 'width', 'height', 'length']
        if not any(data.get(field) is not None for field in measurements):
            return jsonify({'error': 'At least one measurement (weight, width, height, or length) must be provided'}), 400
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check if package information already exists for this order
        c.execute('SELECT id FROM package_information WHERE order_id = ?', (data['order_id'],))
        existing = c.fetchone()
        
        if existing:
            # Update existing record
            c.execute('''
                UPDATE package_information 
                SET weight = ?, width = ?, height = ?, length = ?, timestamp = ?
                WHERE order_id = ?
            ''', (
                data.get('weight'),
                data.get('width'), 
                data.get('height'),
                data.get('length'),
                data['timestamp'],
                data['order_id']
            ))
            message = 'Package information updated successfully'
        else:
            # Insert new record
            c.execute('''
                INSERT INTO package_information (
                    order_id, order_number, weight, width, height, length, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['order_id'],
                data['order_number'],
                data.get('weight'),
                data.get('width'),
                data.get('height'), 
                data.get('length'),
                data['timestamp']
            ))
            message = 'Package information created successfully'
        
        conn.commit()
        conn.close()
        
        # Emit update via WebSocket to notify clients
        socketio.emit('package_information_updated', {
            'order_id': data['order_id'],
            'order_number': data['order_number'],
            'weight': data.get('weight'),
            'width': data.get('width'),
            'height': data.get('height'),
            'length': data.get('length'),
            'timestamp': data['timestamp']
        })
        
        return jsonify({
            'message': message,
            'order_id': data['order_id'],
            'order_number': data['order_number']
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to store package information',
            'details': str(e)
        }), 500

@app.route('/api/package-information/<int:order_id>', methods=['GET'])
def get_package_information(order_id):
    """Get package information for a specific order"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute('SELECT * FROM package_information WHERE order_id = ?', (order_id,))
        package_info = c.fetchone()
        
        conn.close()
        
        if package_info:
            return jsonify(package_info)
        else:
            return jsonify({'message': 'No package information found for this order'}), 404
            
    except Exception as e:
        return jsonify({
            'error': 'Failed to get package information',
            'details': str(e)
        }), 500

@app.route('/api/package-information', methods=['GET'])
def get_all_package_information():
    """Get all package information records"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute('''
            SELECT pi.*, o.customer_name, o.product_name 
            FROM package_information pi
            LEFT JOIN orders o ON pi.order_id = o.id
            ORDER BY pi.created_at DESC
            LIMIT 50
        ''')
        package_info = c.fetchall()
        
        conn.close()
        
        return jsonify({
            'packages': package_info,
            'count': len(package_info),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get package information',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes/<int:order_id>', methods=['DELETE'])
def delete_scanned_code(order_id):
    """Delete a scanned code entry to allow rescanning"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check if the scanned code exists
        c.execute('SELECT * FROM scanned_codes WHERE order_id = ?', (order_id,))
        scanned_code = c.fetchone()
        
        if not scanned_code:
            conn.close()
            return jsonify({'error': 'Scanned code not found'}), 404
        
        # Delete the scanned code
        c.execute('DELETE FROM scanned_codes WHERE order_id = ?', (order_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Scanned code deleted successfully',
            'order_id': order_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to delete scanned code',
            'details': str(e)
        }), 500

@app.route('/api/validate-qr', methods=['POST'])
def validate_qr_code():
    """Validate QR code against orders database and record in scanned_codes table"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        source = data.get('source', 'web')  # Default to 'web' if not specified
        skip_print = data.get('skip_print', False)  # Default to False if not specified
        
        if not qr_data:
            return jsonify({'error': 'No QR data provided'}), 400
        
        # Clean the QR data
        qr_data = str(qr_data).strip()
        
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        # Check if QR data matches any order number
        c.execute('SELECT * FROM orders WHERE order_number = ?', (qr_data,))
        order = c.fetchone()
        
        if order:
            # Valid order found - Check if this order is already scanned
            # Use a more comprehensive check to prevent any duplicates
            c.execute('SELECT * FROM scanned_codes WHERE order_id = ?', (order['id'],))
            already_scanned = c.fetchone()
            
            if already_scanned:
                # Order already scanned - return existing scan info
                logger.info(f"QR code {qr_data} already scanned at {already_scanned['scanned_at']}")
                response_data = {
                    'valid': True,
                    'already_scanned': True,
                    'order_id': order['id'],
                    'order_number': order['order_number'],
                    'customer_name': order['customer_name'],
                    'product_name': order['product_name'],
                    'amount': order['amount'],
                    'date': order['date'],
                    'address': order.get('address', 'N/A'),
                    'contact_number': order.get('contact_number', 'N/A'),
                    'email': order.get('email', ''),
                    'message': f'Order {qr_data} already scanned successfully',
                    'scanned_at': already_scanned['scanned_at']
                }
            else:
                # Valid order, not yet scanned - process it
                # Double-check one more time to prevent race conditions
                c.execute('SELECT COUNT(*) as count FROM scanned_codes WHERE order_id = ?', (order['id'],))
                existing_count = c.fetchone()['count']
                
                if existing_count > 0:
                    # Another process already scanned this while we were processing
                    logger.warning(f"Race condition: QR code {qr_data} was scanned by another process")
                    c.execute('SELECT * FROM scanned_codes WHERE order_id = ?', (order['id'],))
                    existing_scan = c.fetchone()
                    response_data = {
                        'valid': True,
                        'already_scanned': True,
                        'order_id': order['id'],
                        'order_number': order['order_number'],
                        'customer_name': order['customer_name'],
                        'product_name': order['product_name'],
                        'amount': order['amount'],
                        'date': order['date'],
                        'message': f'Order {qr_data} was already scanned successfully',
                        'scanned_at': existing_scan['scanned_at']
                    }
                else:
                    # Safe to insert - Get sensor data if available
                    c.execute('SELECT * FROM loaded_sensor_data ORDER BY created_at DESC LIMIT 1')
                    sensor_data = c.fetchone()
                    
                    # Insert into scanned_codes table as verified to prevent duplicates
                    try:
                        c.execute('''
                            INSERT INTO scanned_codes (order_id, order_number, isverified, device)
                            VALUES (?, ?, ?, ?)
                        ''', (order['id'], order['order_number'], 'yes', 'raspberry_pi'))
                        
                        # If sensor data exists, create package information and then clear sensor data
                        package_info = None
                        if sensor_data:
                            # Create package information record
                            c.execute('''
                                INSERT INTO package_information 
                                (order_id, order_number, weight, width, height, length, package_size, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                order['id'],
                                order['order_number'],
                                sensor_data['weight'],
                                sensor_data['width'],
                                sensor_data['height'],
                                sensor_data['length'],
                                sensor_data.get('package_size', 'Unknown'),
                                datetime.now().isoformat()
                            ))
                            
                            # Get the created package info
                            c.execute('SELECT * FROM package_information WHERE order_id = ? ORDER BY created_at DESC LIMIT 1', (order['id'],))
                            package_info = c.fetchone()
                            
                            # Clear sensor data after successful validation
                            c.execute('DELETE FROM loaded_sensor_data')
                            logger.info(f"Applied sensor data to order {qr_data} and cleared sensor buffer")
                        
                        conn.commit()
                        logger.info(f"Successfully scanned QR code {qr_data} for order {order['order_number']}")
                        
                        # Send print request to Raspberry Pi for successful scan (only if not skipped)
                        if not skip_print:
                            logger.info(f"Attempting to send print request for order {order['order_number']}")
                            try:
                                print_success, print_message = send_print_request_to_raspi(order)
                                if print_success:
                                    logger.info(f"Print request sent successfully for order {order['order_number']}")
                                else:
                                    logger.warning(f"Print request failed for order {order['order_number']}: {print_message}")
                            except Exception as e:
                                print_success, print_message = False, f"Print function error: {str(e)}"
                                logger.error(f"Exception in print request for order {order['order_number']}: {e}")
                        else:
                            # Skip print request as requested (likely handled by local camera system)
                            print_success, print_message = True, "Print request skipped (handled locally)"
                            logger.info(f"Print request skipped for order {order['order_number']} - handled by {source}")
                        
                        response_data = {
                            'valid': True,
                            'already_scanned': False,
                            'order_id': order['id'],
                            'order_number': order['order_number'],
                            'customer_name': order['customer_name'],
                            'product_name': order['product_name'],
                            'amount': order['amount'],
                            'date': order['date'],
                            'address': order.get('address', 'N/A'),
                            'contact_number': order.get('contact_number', 'N/A'),
                            'email': order.get('email', ''),
                            'message': f'Order {qr_data} scanned successfully!',
                            'package_information': package_info,
                            'sensor_data_applied': sensor_data is not None,
                            'print_requested': print_success,
                            'print_message': print_message
                        }
                    except sqlite3.IntegrityError as ie:
                        # Handle UNIQUE constraint violation
                        logger.warning(f"UNIQUE constraint violation for QR code {qr_data}: {ie}")
                        c.execute('SELECT * FROM scanned_codes WHERE order_id = ?', (order['id'],))
                        existing_scan = c.fetchone()
                        response_data = {
                            'valid': True,
                            'already_scanned': True,
                            'order_id': order['id'],
                            'order_number': order['order_number'],
                            'customer_name': order['customer_name'],
                            'product_name': order['product_name'],
                            'amount': order['amount'],
                            'date': order['date'],
                            'address': order.get('address', 'N/A'),
                            'contact_number': order.get('contact_number', 'N/A'),
                            'email': order.get('email', ''),
                            'message': f'Order {qr_data} was already scanned successfully',
                            'scanned_at': existing_scan['scanned_at'] if existing_scan else 'Unknown'
                        }
        else:
            # Invalid QR code - order not found in database
            logger.warning(f"QR code {qr_data} not found in orders database")
            response_data = {
                'valid': False, 
                'already_scanned': False,
                'message': f'QR code {qr_data} not found in orders database'
            }
        
        conn.close()
        return jsonify(response_data), 200
            
    except Exception as e:
        logger.error(f"Error validating QR code {qr_data if 'qr_data' in locals() else 'Unknown'}: {e}")
        return jsonify({
            'valid': False, 
            'already_scanned': False,
            'message': f'Database error: {str(e)}'
        }), 500

@app.route('/api/sensor-data', methods=['POST'])
def store_sensor_data():
    """Store sensor data from MQTT (loadcell and box dimensions)"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Clear any existing sensor data first (overwrite behavior)
        c.execute('DELETE FROM loaded_sensor_data')
        
        # Insert new sensor data
        c.execute('''
            INSERT INTO loaded_sensor_data 
            (weight, width, height, length, package_size, loadcell_timestamp, box_dimensions_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('weight'),
            data.get('width'),
            data.get('height'),
            data.get('length'),
            data.get('package_size'),
            data.get('loadcell_timestamp'),
            data.get('box_dimensions_timestamp')
        ))
        
        conn.commit()
        conn.close()
        
        # Log the storage operation
        weight = data.get('weight', 'N/A')
        width = data.get('width', 'N/A') 
        height = data.get('height', 'N/A')
        length = data.get('length', 'N/A')
        package_size = data.get('package_size', 'N/A')
        
        if data.get('width') is None:
            logger.info(f"STEP 3: Weight-only data stored: {weight}kg")
        else:
            logger.info(f"STEP 5: Complete package data stored: {weight}kg, {width}x{height}x{length}cm ({package_size})")
        
        return jsonify({
            'message': 'Sensor data stored successfully',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'weight': data.get('weight'),
                'dimensions': f"{width}x{height}x{length}cm" if data.get('width') else None,
                'package_size': package_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error storing sensor data: {e}")
        return jsonify({
            'error': 'Failed to store sensor data',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes', methods=['GET'])
def get_scanned_codes():
    """Get all scanned QR codes with their order information"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        # Get all scanned codes with order details and package information
        c.execute('''
            SELECT 
                sc.id as scan_id,
                sc.order_id,
                sc.order_number,
                sc.isverified,
                sc.scanned_at,
                sc.device,
                o.customer_name,
                o.product_name,
                o.amount,
                o.date as order_date,
                pi.weight,
                pi.width,
                pi.height,
                pi.length,
                pi.timestamp as package_timestamp
            FROM scanned_codes sc
            LEFT JOIN orders o ON sc.order_id = o.id
            LEFT JOIN package_information pi ON sc.order_id = pi.order_id
            ORDER BY sc.scanned_at DESC
        ''')
        
        scanned_codes = c.fetchall()
        conn.close()
        
        return jsonify({
            'scanned_codes': scanned_codes,
            'total_count': len(scanned_codes)
        })
        
    except Exception as e:
        logger.error(f"Error getting scanned codes: {e}")
        return jsonify({
            'error': 'Failed to get scanned codes',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes/reset', methods=['POST'])
def reset_scanned_codes():
    """Reset/clear all scanned codes (for testing or restart)"""
    try:
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'error': 'Confirmation required',
                'message': 'Set confirm=true to reset all scanned codes'
            }), 400
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Count before deletion
        c.execute('SELECT COUNT(*) FROM scanned_codes')
        count_before = c.fetchone()[0]
        
        # Clear all scanned codes
        c.execute('DELETE FROM scanned_codes')
        conn.commit()
        conn.close()
        
        logger.info(f"Reset {count_before} scanned codes")
        
        return jsonify({
            'message': f'Successfully reset {count_before} scanned codes',
            'cleared_count': count_before
        })
        
    except Exception as e:
        logger.error(f"Error resetting scanned codes: {e}")
        return jsonify({
            'error': 'Failed to reset scanned codes',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes/<order_number>', methods=['DELETE'])
def remove_scanned_code(order_number):
    """Remove a specific scanned code to allow re-scanning"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check if the order exists in scanned codes
        c.execute('SELECT * FROM scanned_codes WHERE order_number = ?', (order_number,))
        existing = c.fetchone()
        
        if not existing:
            return jsonify({
                'error': 'Order not found in scanned codes',
                'order_number': order_number
            }), 404
        
        # Remove the scanned code
        c.execute('DELETE FROM scanned_codes WHERE order_number = ?', (order_number,))
        conn.commit()
        conn.close()
        
        logger.info(f"Removed scanned code for order {order_number}")
        
        return jsonify({
            'message': f'Successfully removed scanned code for order {order_number}',
            'order_number': order_number
        })
        
    except Exception as e:
        logger.error(f"Error removing scanned code for {order_number}: {e}")
        return jsonify({
            'error': 'Failed to remove scanned code',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes/check-duplicates', methods=['GET'])
def check_duplicates():
    """Check for duplicate scanned codes"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        # Find duplicates
        c.execute('''
            SELECT order_id, COUNT(*) as count
            FROM scanned_codes 
            GROUP BY order_id 
            HAVING COUNT(*) > 1
        ''')
        duplicates = c.fetchall()
        
        # Get detailed info about duplicates
        duplicate_details = []
        for dup in duplicates:
            c.execute('SELECT * FROM scanned_codes WHERE order_id = ? ORDER BY scanned_at', (dup['order_id'],))
            details = c.fetchall()
            duplicate_details.append({
                'order_id': dup['order_id'],
                'count': dup['count'],
                'entries': details
            })
        
        conn.close()
        
        return jsonify({
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'duplicates': duplicate_details
        })
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return jsonify({
            'error': 'Failed to check duplicates',
            'details': str(e)
        }), 500

@app.route('/api/scanned-codes/clean-duplicates', methods=['POST'])
def clean_duplicates():
    """Remove duplicate scanned codes, keeping only the oldest entry for each order"""
    try:
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'error': 'Confirmation required',
                'message': 'Set confirm=true to clean duplicates'
            }), 400
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Count duplicates before cleaning
        c.execute('''
            SELECT COUNT(*) FROM scanned_codes 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM scanned_codes 
                GROUP BY order_id
            )
        ''')
        duplicate_count = c.fetchone()[0]
        
        # Remove duplicates (keep the oldest scan for each order)
        c.execute('''
            DELETE FROM scanned_codes 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM scanned_codes 
                GROUP BY order_id
            )
        ''')
        
        removed_count = c.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {removed_count} duplicate scanned codes")
        
        return jsonify({
            'message': f'Successfully removed {removed_count} duplicate entries',
            'removed_count': removed_count,
            'duplicate_count_before': duplicate_count
        })
        
    except Exception as e:
        logger.error(f"Error cleaning duplicates: {e}")
        return jsonify({
            'error': 'Failed to clean duplicates',
            'details': str(e)
        }), 500

@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    """Get current sensor data"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute('SELECT * FROM loaded_sensor_data ORDER BY created_at DESC LIMIT 1')
        sensor_data = c.fetchone()
        
        conn.close()
        
        return jsonify({
            'sensor_data': sensor_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting sensor data: {e}")
        return jsonify({
            'error': 'Failed to get sensor data',
            'details': str(e)
        }), 500

@app.route('/api/sensor-data', methods=['DELETE'])
def clear_sensor_data():
    """Clear all sensor data"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        c.execute('DELETE FROM loaded_sensor_data')
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Sensor data cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing sensor data: {e}")
        return jsonify({
            'error': 'Failed to clear sensor data',
            'details': str(e)
        }), 500

@app.route('/api/sensor-data/all', methods=['GET'])
def get_all_sensor_data():
    """Get all sensor data records for package display"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        # Get all sensor data records, ordered by most recent first
        c.execute('''
            SELECT id, weight, width, height, length, package_size, 
                   loadcell_timestamp, box_dimensions_timestamp, created_at
            FROM loaded_sensor_data 
            ORDER BY created_at DESC 
            LIMIT 50
        ''')
        sensor_records = c.fetchall()
        
        # Format the data to match what the frontend expects
        packages = []
        for i, record in enumerate(sensor_records):
            packages.append({
                'id': record['id'],
                'order_number': f"ORD-{str(i + 1).zfill(3)}",  # Generate order numbers like ORD-001, ORD-002
                'order_id': f"ORD-{str(i + 1).zfill(3)}",
                'weight': record['weight'],
                'width': record['width'],
                'height': record['height'],
                'length': record['length'],
                'package_size': record['package_size'],
                'size': record['package_size'],  # Alias for compatibility
                'created_at': record['created_at'],
                'scanned_at': record['created_at'],  # Alias for compatibility
                'timestamp': record['created_at']  # Alias for compatibility
            })
        
        conn.close()
        
        return jsonify({
            'packages': packages,
            'count': len(packages),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting all sensor data: {e}")
        return jsonify({
            'error': 'Failed to get sensor data',
            'details': str(e)
        }), 500

@app.route('/api/workflow-status', methods=['GET'])
def get_workflow_status():
    """Get current workflow status based on sensor data"""
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute('SELECT * FROM loaded_sensor_data ORDER BY created_at DESC LIMIT 1')
        sensor_data = c.fetchone()
        
        conn.close()
        
        if not sensor_data:
            return jsonify({
                'step': 0,
                'status': 'waiting',
                'message': 'Waiting for QR scan to start workflow',
                'timestamp': datetime.now().isoformat()
            })
        
        # Determine workflow step based on available data
        has_weight = sensor_data.get('weight') is not None
        has_dimensions = all([
            sensor_data.get('width') is not None,
            sensor_data.get('height') is not None,
            sensor_data.get('length') is not None
        ])
        
        if has_weight and not has_dimensions:
            return jsonify({
                'step': 3,
                'status': 'weight_captured',
                'message': f"Weight captured: {sensor_data['weight']}kg. Ready for grabber to move package.",
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
        elif has_weight and has_dimensions:
            package_size = sensor_data.get('package_size', 'Unknown')
            return jsonify({
                'step': 5,
                'status': 'complete',
                'message': f"Package complete: {sensor_data['weight']}kg, {sensor_data['width']}x{sensor_data['height']}x{sensor_data['length']}cm ({package_size})",
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'step': 1,
                'status': 'incomplete',
                'message': 'Sensor data incomplete',
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        return jsonify({
            'error': 'Failed to get workflow status',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting Flask application with SocketIO...")
    socketio.run(app, debug=False, 
                host=os.getenv('BACKEND_HOST', '0.0.0.0'), 
                port=int(os.getenv('BACKEND_PORT', '5000')))