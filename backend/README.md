# Backend for Parcel Sorting Machine

This is the Flask backend for the Parcel Sorting Machine project using Raspberry Pi 5 and ESP32.

## Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

1. Make sure your virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## Project Structure

```
backend/
├── venv/               # Virtual environment
├── app.py             # Main Flask application
├── requirements.txt   # Python dependencies
├── .gitignore        # Git ignore file
└── README.md         # This file
```

## Development

- The Flask app will run in debug mode for development
- API endpoints will be added for communication with the ESP32 and frontend
- Database integration will be added as needed

## API Endpoints

*To be documented as endpoints are implemented*
