### MicroProject

### Architecture Components

#### 🖥️ **Raspberry Pi 5 (Main Controller)**
- **Role**: Central processing hub and MQTT broker
- **Services**: Flask web server, database management, camera processing
- **Hardware**: 4GB+ RAM, WiFi connectivity, GPIO pins
- **Software**: Python Flask, OpenCV, SQLite, MQTT broker

#### 💻 **React Web Dashboard**
- **Role**: User interface and real-time monitoring
- **Features**: Live workflow visualization, system control, log monitoring
- **Technology**: React 18, Material-UI, Socket.IO client
- **Access**: Web browser interface with responsive design

#### 🔧 **ESP32 Microcontroller**
- **Role**: Hardware interface and sensor management
- **Functions**: MQTT communication, sensor data collection, actuator control
- **Connectivity**: WiFi connection to Raspberry Pi MQTT broker
- **Programming**: Arduino IDE with custom firmware

#### 🔗 **MQTT Communication Layer**
- **Role**: Real-time messaging between Raspberry Pi and ESP32
- **Protocol**: Publish/Subscribe messaging pattern
- **Topics**: Organized sensor data and control commands
- **Reliability**: QoS levels for critical operationsing System

## 🌟 Overview

The Automated Parcel Processing System is a comprehensive IoT solution that combines hardware automation with modern web technologies to create a seamless parcel processing workflow. The system automatically weighs, measures, validates, and processes packages through an 8-step automated cycle.

![System Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)
![Backend](https://img.shields.io/badge/Backend-Python%20Flask-green)
![IoT](https://img.shields.io/badge/IoT-ESP32%20MQTT-orange)
![Real--time](https://img.shields.io/badge/Real--time-WebSocket-yellow)


## 🔄 8-Step Automated Workflow

### Step 1: IR Detection & Motor Control
- **Trigger**: IR Sensor A detects incoming package
- **Action**: Stops Motor A, starts actuator with 5-second delay
- **Status**: `IR A triggered - Motor A stop requested`

### Step 2: Load Cell Weight Measurement
- **Trigger**: Motor A status confirmation
- **Action**: Activates load cell for weight measurement
- **Status**: `Weight captured X.Xg`

### Step 3: Package Dimensioning
- **Trigger**: Final weight received and stored
- **Action**: Box sensors measure width, height, length
- **Status**: `Dimensions captured W:X, H:Y, L:Zcm`

### Step 4: Grabber Operations
- **Trigger**: Weight stored in database
- **Action**: Activates Grabber1, then Grabber2 in sequence
- **Status**: `Grabber1/2 operations completed`

### Step 5: Size Calculation & Stepper
- **Trigger**: Grabber2 completion
- **Action**: Calculates package size (small/medium/large), positions stepper motor
- **Status**: `Size: X - Stepper positioned`

### Step 6: QR Code Validation
- **Trigger**: Stepper positioning complete
- **Action**: Camera captures and validates QR code
- **Status**: `QR code detected: XXXXX`

### Step 7: Receipt Printing
- **Trigger**: Valid QR code detected
- **Action**: Prints thermal receipt with package details
- **Status**: `Receipt printed successfully`

### Step 8: Cycle Completion
- **Trigger**: Receipt printing complete
- **Action**: Motor B cycle, GSM SMS notification, system reset
- **Status**: `SMS sent - Cycle completed`

## 🛠️ Technology Stack

### Backend (Python Flask)
- **Framework**: Flask 3.0.0 with SocketIO for real-time communication
- **MQTT**: Paho-MQTT for ESP32 hardware communication
- **Database**: SQLite for data persistence
- **Computer Vision**: OpenCV + PyZBar for QR code scanning
- **Hardware Integration**: 
  - Picamera2 for Raspberry Pi camera
  - Thermal printer support
  - GSM module for SMS notifications

### Frontend (React)
- **Framework**: React 18.2.0 with Material-UI components
- **Real-time**: Socket.IO client for live updates
- **State Management**: React hooks with WebSocket integration
- **UI Components**:
  - Live workflow monitoring dashboard
  - Real-time log display
  - System status indicators
  - Responsive design with animations

### Hardware (ESP32 IoT)
- **Microcontroller**: ESP32 with WiFi/Bluetooth
- **Sensors**: 
  - IR sensors (A & B) for object detection
  - Load cell for weight measurement
  - Box dimension sensors
- **Actuators**:
  - Stepper motors for positioning
  - DC motors for conveyor belts
  - Grabber mechanisms
- **Communication**: MQTT protocol over WiFi

## 📋 Prerequisites

### Hardware Requirements

#### 🖥️ **Raspberry Pi 5 (Main Controller)**
- **Model**: Raspberry Pi 4B with 4GB+ RAM (8GB recommended)
- **Storage**: 32GB+ microSD card (Class 10)
- **Connectivity**: WiFi/Ethernet, Bluetooth, USB ports
- **Camera**: Pi Camera Module v2 or compatible USB camera
- **Power**: 5V 3A USB-C power supply

#### 🔧 **ESP32 Microcontroller**
- **Model**: ESP32 DevKit v1 or similar
- **Features**: WiFi + Bluetooth, 30+ GPIO pins
- **Power**: 3.3V/5V compatible
- **Programming**: USB to Serial adapter included

#### 📟 **Peripheral Hardware**
- **Thermal Printer**: ESC/POS compatible thermal printer
- **Load Cell**: 0-20kg capacity with HX711 amplifier
- **IR Sensors**: Digital infrared object detection sensors
- **Stepper Motors**: NEMA 17 with A4988/DRV8825 drivers
- **DC Motors**: 12V motors for conveyor system with motor drivers
- **GSM Module**: SIM800L or similar for SMS notifications
- **Grabber Systems**: Servo-controlled mechanical grabbers

#### 🔌 **Supporting Components**
- **Power Supplies**: 12V for motors, 5V for electronics
- **Breadboards/PCBs**: For circuit connections
- **Jumper Wires**: Male-to-male, male-to-female connections
- **Resistors/Capacitors**: Basic electronic components

### Software Requirements
- Python 3.8+
- Node.js 16+
- MQTT broker (Mosquitto)
- Git

## 🚀 Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/CocoMeme/MicroProject.git
cd MicroProject
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your settings
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API endpoints
```

### 4. ESP32 Setup
```bash
cd backend/esp32files

# Upload the Arduino code to your ESP32
# Configure WiFi credentials and MQTT settings
# Install required libraries:
# - PubSubClient
# - WiFi
# - ArduinoJson
```

## ⚙️ Configuration

### Environment Variables

#### Backend (.env)
```env
FLASK_ENV=development
MQTT_BROKER=localhost
MQTT_PORT=1883
DATABASE_URL=sqlite:///database.db
GSM_PHONE_NUMBER=+1234567890
PRINTER_ENABLED=true
CAMERA_ENABLED=true
```

#### Frontend (.env)
```env
REACT_APP_API_ENDPOINT=http://localhost:5000/api
REACT_APP_WEBSOCKET_URL=http://localhost:5000
REACT_APP_RASPI_BASE_URL=http://localhost:5000
```

### MQTT Topics Configuration

#### Input Topics (from ESP32)
- `esp32/ir/status` - IR A sensor triggers
- `esp32/irsensorB/status` - IR B sensor status
- `esp32/motor/status` - Motor status updates
- `esp32/loadcell/data` - Weight measurements
- `esp32/box/status` - Dimension measurements
- `esp32/parcel1/status` - Grabber1 status
- `esp32/parcel2/status` - Grabber2 status
- `esp32/stepper/status` - Stepper position status

#### Output Topics (to ESP32)
- `esp32/proximity/request` - Start proximity sensor
- `esp32/motor/request` - Motor control (startA, stopA, startB, stopB)
- `esp32/irsensorB/request` - IR B sensor control
- `esp32/loadcell/request` - Load cell control
- `esp32/grabber1/request` - Grabber1 control
- `esp32/grabber2/request` - Grabber2 control
- `esp32/box/request` - Box system control
- `esp32/stepper/request` - Stepper positioning
- `esp32/gsm/send` - SMS notifications

## 🏃‍♂️ Running the System

### 1. Start MQTT Broker
```bash
# Install Mosquitto MQTT broker
sudo apt install mosquitto mosquitto-clients

# Start the broker
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### 2. Start Backend Server
```bash
cd backend
source venv/bin/activate
python server.py
```

The backend will start on `http://localhost:5000`

### 3. Start Frontend Dashboard
```bash
cd frontend
npm start
```

The dashboard will open on `http://localhost:3000`

### 4. Connect ESP32 Hardware
- Power on ESP32 with uploaded firmware
- Ensure WiFi connectivity
- Verify MQTT connection in backend logs

## 🖥️ Dashboard Features

### Master Control Panel
- **System Start/Stop**: Control the entire workflow
- **Emergency Stop**: Immediate system shutdown
- **Real-time Status**: Connection and component monitoring

### Live Workflow Monitoring
- **Step Progress**: Visual 1-8 step indicator
- **Real-time Logs**: Live display of system logs with color coding
- **Timeline View**: Chronological workflow progression
- **Status Indicators**: Component status with animations

### System Analytics
- **Package Statistics**: Daily processing counts
- **Weight Analysis**: Real-time weight measurements
- **Dimension Tracking**: Package size distributions
- **Performance Metrics**: System uptime and efficiency

## 📊 Database Schema

### Tables
- **`loaded_sensor_data`**: Weight and sensor measurements
- **`package_information`**: Complete package details
- **`system_logs`**: Audit trail and debugging information

### Key Fields
```sql
-- Package Information
CREATE TABLE package_information (
    id INTEGER PRIMARY KEY,
    weight REAL,
    dimensions TEXT,
    qr_code TEXT,
    package_size TEXT,
    timestamp DATETIME,
    status TEXT
);

-- Sensor Data
CREATE TABLE loaded_sensor_data (
    id INTEGER PRIMARY KEY,
    weight REAL,
    timestamp DATETIME,
    processed BOOLEAN DEFAULT FALSE
);
```

## 🔧 API Endpoints

### System Control
- `POST /api/system/start` - Start the workflow system
- `POST /api/system/stop` - Stop all system operations
- `GET /api/system/status` - Get current system status

### Data Access
- `GET /api/packages` - Retrieve package data
- `GET /api/sensors` - Get sensor readings
- `POST /api/packages` - Add package manually

### Hardware Control
- `POST /api/camera/start` - Start camera stream
- `POST /api/printer/test` - Test printer functionality
- `POST /api/gsm/send` - Send SMS notification

## 🔐 Security Features

- **CORS Protection**: Configured for specific origins
- **Input Validation**: Sanitized data inputs
- **Error Handling**: Comprehensive error management
- **Connection Security**: WebSocket authentication
- **Data Backup**: Automated database backups

## 🐛 Troubleshooting

### Common Issues

#### WebSocket Connection Failed
```bash
# Check if backend is running
curl http://localhost:5000/api/system/status

# Verify network connectivity
ping localhost
```

#### MQTT Connection Issues
```bash
# Test MQTT broker
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test

# Check ESP32 logs for WiFi/MQTT errors
```

#### Camera Not Working
```bash
# Test camera availability
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# Check permissions
sudo usermod -a -G video $USER
```

#### Database Errors
```bash
# Reset database
cd backend
rm database.db
python -c "import app; app.init_db()"
```

### Debug Mode
Enable detailed logging:
```python
# In server.py
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Optimization

### Backend Optimization
- **Threading**: Async processing for MQTT and WebSocket
- **Connection Pooling**: Efficient database connections
- **Caching**: Redis integration for high-performance scenarios

### Frontend Optimization
- **Code Splitting**: Lazy loading of components
- **State Management**: Optimized React updates
- **Bundle Size**: Minimized JavaScript payload

### Hardware Optimization
- **MQTT QoS**: Configured for reliability vs. speed
- **Sensor Timing**: Optimized polling intervals
- **Power Management**: Sleep modes for ESP32

## 🤝 Contributing

### Development Guidelines
1. Follow Python PEP 8 style guide
2. Use ESLint for JavaScript code
3. Write unit tests for new features
4. Document API changes
5. Test hardware integration thoroughly

### Code Structure
```
backend/
├── server.py              # Main Flask application
├── mqtt_listener.py       # MQTT communication
├── camera.py              # Camera management
├── print.py               # Printer operations
├── products_data.py       # Data models
└── esp32files/            # Arduino firmware

frontend/
├── src/
│   ├── components/        # Reusable UI components
│   ├── pages/            # Page components
│   ├── services/         # API and WebSocket services
│   └── utils/            # Utility functions
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Documentation](docs/api.md)
- [Hardware Setup Guide](docs/hardware.md)
- [Deployment Guide](docs/deployment.md)

### Community
- **Issues**: Report bugs and feature requests
- **Discussions**: Community forum for questions
- **Wiki**: Detailed setup and configuration guides

### Contact
- **Email**: support@microproject.com
- **Discord**: [Join our server](https://discord.gg/microproject)
- **Documentation**: [Full docs website](https://docs.microproject.com)

---

## 🏆 Features Highlights

✅ **Real-time Monitoring**: Live workflow visualization  
✅ **8-Step Automation**: Complete parcel processing cycle  
✅ **Hardware Integration**: ESP32 IoT sensor network  
✅ **QR Code Validation**: Computer vision integration  
✅ **Thermal Printing**: Receipt generation system  
✅ **SMS Notifications**: GSM module integration  
✅ **Web Dashboard**: Modern React interface  
✅ **Database Storage**: Persistent data management  
✅ **MQTT Communication**: Reliable IoT messaging  
✅ **Error Handling**: Comprehensive fault tolerance  

---

**Built with ❤️ by the MicroProject Team**

*Last updated: August 2025*
