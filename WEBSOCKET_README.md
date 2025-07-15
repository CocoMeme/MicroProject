# WebSocket Implementation for Slow WiFi Support

This implementation adds WebSocket support to your project to improve performance and user experience when dealing with slow WiFi connections.

## Features

- **Real-time communication**: WebSocket connections provide instant updates for QR code detection and system status
- **Automatic fallback**: If WebSocket connection fails, the system automatically falls back to HTTP polling
- **Connection monitoring**: Real-time connection quality monitoring with ping times and transport information
- **Reconnection handling**: Automatic reconnection with exponential backoff when connections are lost
- **Background tasks**: Efficient background polling for QR codes without blocking the UI

## Architecture

### Backend (Flask + SocketIO)
- **Flask-SocketIO**: Provides WebSocket support with automatic fallback to long polling
- **Background tasks**: Handles QR code polling in separate threads
- **Event-driven**: Emits real-time events for camera status, QR detection, and system updates

### Frontend (React + Socket.IO Client)
- **Socket.IO Client**: Handles WebSocket connections with automatic reconnection
- **Service Layer**: Centralized WebSocket management with event handling
- **React Hooks**: Custom hooks for easy WebSocket integration in components
- **Connection Monitoring**: Visual indicators for connection status and quality

## Components

### Backend Files
- `backend/app.py` - Main Flask application with SocketIO integration
- `backend/requirements.txt` - Updated with flask-socketio and flask-cors

### Frontend Files
- `frontend/src/services/websocketService.js` - WebSocket service singleton
- `frontend/src/hooks/useWebSocket.js` - React hook for WebSocket functionality
- `frontend/src/components/ConnectionMonitor.js` - Connection status monitoring component
- `frontend/src/pages/Scanner.js` - Updated scanner with WebSocket support
- `frontend/src/pages/WebSocketTest.js` - Test page for WebSocket functionality

## Usage

### Starting the Services

1. **Backend**:
   ```bash
   cd backend
   pip install flask-socketio flask-cors
   python app.py
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install socket.io-client
   npm start
   ```

### WebSocket Events

#### Server → Client Events
- `status` - Server connection status
- `camera_status` - Camera start/stop status
- `camera_error` - Camera error messages
- `qr_detected` - Real-time QR code detection
- `system_status` - System status updates

#### Client → Server Events
- `start_camera_stream` - Start camera and QR polling
- `stop_camera_stream` - Stop camera
- `get_system_status` - Request system status update

### Using the WebSocket Service

```javascript
import websocketService from '../services/websocketService';

// Connect to WebSocket
await websocketService.connect('http://192.168.100.61:5000');

// Listen for events
websocketService.on('qr_detected', (data) => {
  console.log('QR Code detected:', data);
});

// Emit events
websocketService.startCamera();
websocketService.stopCamera();
websocketService.getSystemStatus();

// Check connection status
const isConnected = websocketService.isConnectedToServer();
const connectionInfo = websocketService.getConnectionInfo();
```

### Using the React Hook

```javascript
import useWebSocket from '../hooks/useWebSocket';

function MyComponent() {
  const {
    isConnected,
    isConnecting,
    connectionInfo,
    error,
    connect,
    emit,
    on,
    startCamera,
    stopCamera,
    getSystemStatus
  } = useWebSocket('http://192.168.100.61:5000');

  useEffect(() => {
    connect();
    
    const cleanup = on('qr_detected', (data) => {
      console.log('QR detected:', data);
    });
    
    return cleanup;
  }, []);

  return (
    <div>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <button onClick={startCamera}>Start Camera</button>
    </div>
  );
}
```

## Benefits for Slow WiFi

1. **Reduced HTTP Overhead**: WebSocket connections eliminate HTTP headers for each request
2. **Real-time Updates**: Instant notifications without polling delays
3. **Efficient Reconnection**: Smart reconnection logic with exponential backoff
4. **Transport Fallback**: Automatic fallback to long polling if WebSocket fails
5. **Connection Quality Monitoring**: Visual feedback on connection performance
6. **Background Processing**: Server-side background tasks reduce client-side polling

## Testing

Visit `/admin/websocket-test` to access the WebSocket test page where you can:
- Monitor connection status and quality
- Test message sending/receiving
- View real-time event logs
- Check system status updates

## Configuration

### Backend Configuration
```python
# In app.py
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
```

### Frontend Configuration
```javascript
// In websocketService.js
const socket = io(url, {
  transports: ['websocket', 'polling'], // Fallback order
  timeout: 10000,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  pingTimeout: 60000,
  pingInterval: 25000
});
```

## Troubleshooting

1. **Connection Issues**: Check the WebSocket test page for detailed connection information
2. **Firewall**: Ensure WebSocket ports are not blocked
3. **CORS**: Make sure CORS is properly configured for your domain
4. **Browser Support**: All modern browsers support WebSockets, but some corporate networks may block them

## Performance Monitoring

The connection monitor provides real-time information about:
- Connection status (Connected/Disconnected)
- Transport method (WebSocket/Polling)
- Ping times and connection quality
- Reconnection attempts
- Signal strength indicators
