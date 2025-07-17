import { io } from 'socket.io-client';

class RaspberryPiWebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.printPromises = new Map(); // Track print requests
  }

  connect(url = 'http://192.168.100.63:5001') {
    if (this.socket?.connected) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        transports: ['websocket', 'polling'], // Better for slow connections
        timeout: 15000, // Increased timeout for Raspberry Pi
        forceNew: true,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
        reconnectionDelayMax: 10000,
        maxHttpBufferSize: 1e6,
        pingTimeout: 60000,
        pingInterval: 25000
      });

      this.socket.on('connect', () => {
        console.log('Raspberry Pi WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.setupPrintHandlers();
        resolve();
      });

      this.socket.on('disconnect', () => {
        console.log('Raspberry Pi WebSocket disconnected');
        this.isConnected = false;
      });

      this.socket.on('connect_error', (error) => {
        console.error('Raspberry Pi WebSocket connection error:', error);
        this.isConnected = false;
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          reject(new Error(`Failed to connect after ${this.maxReconnectAttempts} attempts`));
        } else {
          // Exponential backoff
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
        }
      });

      // Connection timeout
      setTimeout(() => {
        if (!this.isConnected) {
          reject(new Error('Connection timeout'));
        }
      }, 15000);
    });
  }

  setupPrintHandlers() {
    // Handle print status updates
    this.socket.on('print_status', (data) => {
      console.log('Print status:', data);
      this.emit('print_status', data);
    });

    // Handle print success
    this.socket.on('print_success', (data) => {
      console.log('Print success:', data);
      this.emit('print_success', data);
      
      // Resolve promise if exists
      const promise = this.printPromises.get(data.order_number);
      if (promise) {
        promise.resolve(data);
        this.printPromises.delete(data.order_number);
      }
    });

    // Handle print errors
    this.socket.on('print_error', (data) => {
      console.error('Print error:', data);
      this.emit('print_error', data);
      
      // Reject promise if exists
      const promise = this.printPromises.get(data.order_number);
      if (promise) {
        promise.reject(new Error(data.error));
        this.printPromises.delete(data.order_number);
      }
    });

    // Handle printer status
    this.socket.on('printer_status', (data) => {
      console.log('Printer status:', data);
      this.emit('printer_status', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    const listeners = this.listeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${event} listener:`, error);
        }
      });
    }
  }

  // Print QR code via WebSocket with promise-based interface
  printQRCode(orderData) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected) {
        reject(new Error('Raspberry Pi WebSocket not connected'));
        return;
      }

      const orderNumber = orderData.orderNumber;
      
      // Store promise for this print request
      this.printPromises.set(orderNumber, { resolve, reject });

      // Set timeout for print request
      const timeout = setTimeout(() => {
        if (this.printPromises.has(orderNumber)) {
          this.printPromises.delete(orderNumber);
          reject(new Error('Print request timeout'));
        }
      }, 30000); // 30 second timeout

      // Clear timeout when promise resolves/rejects
      const originalResolve = resolve;
      const originalReject = reject;
      
      this.printPromises.set(orderNumber, {
        resolve: (data) => {
          clearTimeout(timeout);
          originalResolve(data);
        },
        reject: (error) => {
          clearTimeout(timeout);
          originalReject(error);
        }
      });

      // Send print request
      this.socket.emit('print_qr', orderData);
    });
  }

  // Check printer status
  checkPrinterStatus() {
    if (this.isConnected) {
      this.socket.emit('check_printer_status');
    }
  }

  // Get connection info
  getConnectionInfo() {
    if (!this.socket) return null;
    
    return {
      connected: this.isConnected,
      transport: this.socket.io.engine?.transport?.name || 'unknown',
      ping: this.socket.ping || 0,
      id: this.socket.id
    };
  }

  isConnectedToServer() {
    return this.isConnected && this.socket?.connected;
  }
}

// Create and export singleton instance
const raspberryPiWebSocketService = new RaspberryPiWebSocketService();
export default raspberryPiWebSocketService;
