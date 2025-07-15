import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Grid,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  Wifi,
  WifiOff,
  Speed,
  SignalWifi3Bar,
  SignalWifi2Bar,
  SignalWifi1Bar,
  SignalWifiOff,
} from '@mui/icons-material';
import websocketService from '../services/websocketService';

const ConnectionMonitor = () => {
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  // Helper function to ensure valid MUI colors
  const getValidMuiColor = (color) => {
    const validColors = ['primary', 'secondary', 'error', 'warning', 'info', 'success'];
    return validColors.includes(color) ? color : 'primary';
  };

  useEffect(() => {
    // Check initial connection status
    setIsConnected(websocketService.isConnectedToServer());
    
    // Set up periodic updates
    const updateInterval = setInterval(() => {
      const connected = websocketService.isConnectedToServer();
      const info = websocketService.getConnectionInfo();
      
      setIsConnected(connected);
      setConnectionInfo(info);
    }, 2000); // Update every 2 seconds

    return () => clearInterval(updateInterval);
  }, []);

  const getSignalIcon = (ping) => {
    if (!ping || ping === 0) return <SignalWifiOff />;
    if (ping < 50) return <SignalWifi3Bar />;
    if (ping < 150) return <SignalWifi2Bar />;
    if (ping < 300) return <SignalWifi1Bar />;
    return <SignalWifiOff />;
  };

  const getConnectionQuality = (ping) => {
    if (!ping || ping === 0) return { label: 'No Connection', color: 'error', value: 0 };
    if (ping < 50) return { label: 'Excellent', color: 'success', value: 100 };
    if (ping < 150) return { label: 'Good', color: 'success', value: 75 };
    if (ping < 300) return { label: 'Fair', color: 'warning', value: 50 };
    return { label: 'Poor', color: 'error', value: 25 };
  };

  const reconnectToWebSocket = async () => {
    setIsConnecting(true);
    try {
      await websocketService.connect();
      setIsConnected(true);
    } catch (error) {
      console.error('Reconnection failed:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const quality = connectionInfo ? getConnectionQuality(connectionInfo.ping) : { label: 'Unknown', color: 'primary', value: 0 };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Connection Monitor
      </Typography>
      
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            {isConnected ? <Wifi color="success" /> : <WifiOff color="error" />}
            <Typography variant="body1">
              WebSocket Status:
            </Typography>
            <Chip
              label={isConnected ? 'Connected' : 'Disconnected'}
              color={isConnected ? 'success' : 'error'}
              size="small"
            />
          </Box>
        </Grid>

        <Grid item xs={12} sm={6}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            {getSignalIcon(connectionInfo?.ping)}
            <Typography variant="body1">
              Signal Quality:
            </Typography>
            <Chip
              label={quality.label}
              color={getValidMuiColor(quality.color)}
              size="small"
            />
          </Box>
        </Grid>

        {connectionInfo && (
          <>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Transport: {connectionInfo.transport || 'Unknown'}
              </Typography>
            </Grid>

            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Ping: {connectionInfo.ping || 0}ms
              </Typography>
            </Grid>

            {connectionInfo.reconnectAttempts > 0 && (
              <Grid item xs={12}>
                <Alert severity="warning" size="small">
                  Reconnection attempts: {connectionInfo.reconnectAttempts}
                </Alert>
              </Grid>
            )}
          </>
        )}

        <Grid item xs={12}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Connection Quality
          </Typography>
          <LinearProgress
            variant="determinate"
            value={quality.value}
            color={getValidMuiColor(quality.color)}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Grid>

        {!isConnected && !isConnecting && (
          <Grid item xs={12}>
            <Alert 
              severity="info" 
              action={
                <Chip
                  label="Retry"
                  onClick={reconnectToWebSocket}
                  size="small"
                  clickable
                />
              }
            >
              WebSocket connection lost. Using HTTP fallback mode.
            </Alert>
          </Grid>
        )}

        {isConnecting && (
          <Grid item xs={12}>
            <Alert severity="info">
              Attempting to reconnect...
              <LinearProgress sx={{ mt: 1 }} />
            </Alert>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default ConnectionMonitor;
