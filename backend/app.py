from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
