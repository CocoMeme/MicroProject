import { io } from 'socket.io-client';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
  }

  connect(url = process.env.REACT_APP_WEBSOCKET_URL || 'http://192.168.100.61:5000') {
    if (this.socket?.connected) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        transports: ['websocket', 'polling'], // Fallback to polling for slow connections
        timeout: 10000,
        forceNew: true,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
        reconnectionDelayMax: 5000,
        maxHttpBufferSize: 1e6,
        pingTimeout: 60000,
        pingInterval: 25000
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Reset delay
        resolve();
      });

      this.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        this.isConnected = false;
      });

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        this.isConnected = false;
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          reject(new Error('Failed to connect after maximum attempts'));
        } else {
          // Exponential backoff
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        }
      });

      this.socket.on('reconnect', (attemptNumber) => {
        console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
        this.isConnected = true;
        this.reconnectAttempts = 0;
      });

      // Set up default event listeners
      this.setupDefaultListeners();
    });
  }

  setupDefaultListeners() {
    if (!this.socket) return;

    // Handle server status updates
    this.socket.on('status', (data) => {
      console.log('Server status:', data);
    });

    // Handle camera status updates
    this.socket.on('camera_status', (data) => {
      this.notifyListeners('camera_status', data);
    });

    // Handle camera errors
    this.socket.on('camera_error', (data) => {
      this.notifyListeners('camera_error', data);
    });

    // Handle QR code detection
    this.socket.on('qr_detected', (data) => {
      this.notifyListeners('qr_detected', data);
    });

    // Handle system status updates
    this.socket.on('system_status', (data) => {
      this.notifyListeners('system_status', data);
    });
  }

  // Add event listener
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  // Remove event listener
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  // Notify all listeners of an event
  notifyListeners(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${event} listener:`, error);
        }
      });
    }
  }

  // Emit events to server
  emit(event, data) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('Cannot emit - WebSocket not connected');
    }
  }

  // Camera control methods
  startCamera() {
    this.emit('start_camera_stream');
  }

  stopCamera() {
    this.emit('stop_camera_stream');
  }

  getSystemStatus() {
    this.emit('get_system_status');
  }

  // Connection status
  isConnectedToServer() {
    return this.isConnected && this.socket?.connected;
  }

  // Disconnect
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
    this.listeners.clear();
  }

  // Get connection quality info
  getConnectionInfo() {
    if (!this.socket) return null;
    
    return {
      connected: this.socket.connected,
      transport: this.socket.io.engine.transport.name,
      ping: this.socket.ping || 0,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
