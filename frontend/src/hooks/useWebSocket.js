import { useState, useEffect, useCallback } from 'react';
import websocketService from '../services/websocketService';

export const useWebSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);

  const connect = useCallback(async () => {
    if (websocketService.isConnectedToServer()) {
      setIsConnected(true);
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      await websocketService.connect(url);
      setIsConnected(true);
    } catch (err) {
      setError(err.message);
      setIsConnected(false);
    } finally {
      setIsConnecting(false);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
    setConnectionInfo(null);
  }, []);

  const emit = useCallback((event, data) => {
    if (isConnected) {
      websocketService.emit(event, data);
    } else {
      console.warn(`Cannot emit ${event} - WebSocket not connected`);
    }
  }, [isConnected]);

  const on = useCallback((event, callback) => {
    websocketService.on(event, callback);
    
    // Return cleanup function
    return () => websocketService.off(event, callback);
  }, []);

  useEffect(() => {
    // Check connection status periodically
    const statusInterval = setInterval(() => {
      const connected = websocketService.isConnectedToServer();
      const info = websocketService.getConnectionInfo();
      
      setIsConnected(connected);
      setConnectionInfo(info);
    }, 2000);

    return () => clearInterval(statusInterval);
  }, []);

  return {
    isConnected,
    isConnecting,
    connectionInfo,
    error,
    connect,
    disconnect,
    emit,
    on,
    // Convenience methods
    startCamera: () => emit('start_camera_stream'),
    stopCamera: () => emit('stop_camera_stream'),
    getSystemStatus: () => emit('get_system_status'),
  };
};

export default useWebSocket;
