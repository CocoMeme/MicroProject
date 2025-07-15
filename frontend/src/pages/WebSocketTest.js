import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Alert,
  TextField,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import { Send, Refresh } from '@mui/icons-material';
import ConnectionMonitor from '../components/ConnectionMonitor';
import ErrorBoundary from '../components/ErrorBoundary';
import useWebSocket from '../hooks/useWebSocket';

const WebSocketTest = () => {
  const [testMessage, setTestMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  
  const {
    isConnected,
    isConnecting,
    error,
    connect,
    emit,
    on,
    getSystemStatus
  } = useWebSocket('http://192.168.100.61:5000');

  useEffect(() => {
    // Auto-connect on component mount
    connect();

    // Set up event listeners
    const cleanupFunctions = [
      on('status', (data) => {
        setMessages(prev => [...prev, { type: 'status', data, timestamp: new Date() }]);
      }),
      on('system_status', (data) => {
        setSystemStatus(data);
        setMessages(prev => [...prev, { type: 'system_status', data, timestamp: new Date() }]);
      }),
      on('camera_status', (data) => {
        setMessages(prev => [...prev, { type: 'camera_status', data, timestamp: new Date() }]);
      }),
      on('qr_detected', (data) => {
        setMessages(prev => [...prev, { type: 'qr_detected', data, timestamp: new Date() }]);
      }),
      on('test_response', (data) => {
        setMessages(prev => [...prev, { type: 'test_response', data, timestamp: new Date() }]);
      }),
    ];

    return () => {
      cleanupFunctions.forEach(cleanup => cleanup());
    };
  }, [connect, on]);

  const handleTestMessage = () => {
    if (testMessage.trim()) {
      emit('test_message', { message: testMessage });
      setMessages(prev => [...prev, { 
        type: 'sent', 
        data: { message: testMessage }, 
        timestamp: new Date() 
      }]);
      setTestMessage('');
    }
  };

  const handleGetSystemStatus = () => {
    getSystemStatus();
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        WebSocket Test & Monitoring
      </Typography>

      <Grid container spacing={3}>
        {/* Connection Monitor */}
        <Grid item xs={12} md={6}>
          <ErrorBoundary>
            <ConnectionMonitor />
          </ErrorBoundary>
        </Grid>

        {/* Controls */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Controls
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {!isConnected && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                WebSocket not connected. Some features may not work.
              </Alert>
            )}

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                label="Test Message"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleTestMessage()}
                size="small"
                fullWidth
                disabled={!isConnected}
              />
              <Button
                variant="contained"
                onClick={handleTestMessage}
                disabled={!isConnected || !testMessage.trim()}
                startIcon={<Send />}
              >
                Send
              </Button>
            </Box>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Button
                variant="outlined"
                onClick={handleGetSystemStatus}
                disabled={!isConnected}
                startIcon={<Refresh />}
              >
                Get System Status
              </Button>
              <Button
                variant="outlined"
                onClick={clearMessages}
              >
                Clear Messages
              </Button>
            </Box>

            <Button
              variant={isConnected ? 'outlined' : 'contained'}
              onClick={connect}
              disabled={isConnecting}
              fullWidth
            >
              {isConnecting ? 'Connecting...' : isConnected ? 'Reconnect' : 'Connect'}
            </Button>
          </Paper>
        </Grid>

        {/* System Status */}
        {systemStatus && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Latest System Status
              </Typography>
              <pre>{JSON.stringify(systemStatus, null, 2)}</pre>
            </Paper>
          </Grid>
        )}

        {/* Message Log */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Message Log ({messages.length})
            </Typography>
            
            <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
              {messages.length === 0 ? (
                <Typography color="text.secondary">
                  No messages yet. Connect to WebSocket and interact with the system.
                </Typography>
              ) : (
                messages.slice(-20).reverse().map((message, index) => (
                  <Card key={index} sx={{ mb: 1 }}>
                    <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2" color="primary">
                          {message.type}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {message.timestamp.toLocaleTimeString()}
                        </Typography>
                      </Box>
                      <Divider sx={{ my: 0.5 }} />
                      <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                        {JSON.stringify(message.data, null, 2)}
                      </Typography>
                    </CardContent>
                  </Card>
                ))
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default WebSocketTest;
