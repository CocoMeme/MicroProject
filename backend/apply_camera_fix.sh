#!/bin/bash
# Camera Fix Update Script for Raspberry Pi
# This script applies the camera allocator error fix

echo "========================================"
echo "Camera Allocator Error Fix Script"
echo "========================================"

# Check if we're on a Raspberry Pi
if ! command -v vcgencmd &> /dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi"
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup current requirements
echo "Backing up current requirements..."
cp requirements.txt requirements.txt.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
cp requirements-raspi-websocket.txt requirements-raspi-websocket.txt.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Check current picamera2 version
echo "Checking current picamera2 version..."
python3 -c "import picamera2; print(f'Current version: {getattr(picamera2, \"__version__\", \"Unknown\")}')" 2>/dev/null || echo "PiCamera2 not installed or import failed"

# Upgrade picamera2
echo "Upgrading picamera2 to compatible version..."
pip3 install --upgrade "picamera2>=0.3.17,<0.4.0"

if [ $? -eq 0 ]; then
    echo "✅ PiCamera2 upgrade successful"
else
    echo "❌ PiCamera2 upgrade failed"
    exit 1
fi

# Verify new version
echo "Verifying new picamera2 version..."
python3 -c "import picamera2; print(f'New version: {getattr(picamera2, \"__version__\", \"Unknown\")}')"

# Run diagnostics if available
if [ -f "camera_diagnostics.py" ]; then
    echo "Running camera diagnostics..."
    python3 camera_diagnostics.py
else
    echo "Camera diagnostics script not found - skipping diagnostics"
fi

echo "========================================"
echo "Fix application complete!"
echo "Please restart your application:"
echo "  sudo systemctl restart your-app-service"
echo "  OR"
echo "  python3 app.py"
echo "========================================"
