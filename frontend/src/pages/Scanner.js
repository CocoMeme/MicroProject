import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Alert,
  Chip,
  CircularProgress,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import websocketService from '../services/websocketService';

const RASPI_SERVER = 'http://192.168.100.63:5001'; // Your Raspberry Pi address
const BACKEND_SERVER = 'http://192.168.100.61:5000'; // Your Flask backend

export default function Scanner() {
  const [isStreaming, setIsStreaming] = useState(true); // Auto-start camera
  const [lastScan, setLastScan] = useState(null);
  const [qrHistory, setQrHistory] = useState([]);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState({ online: false, camera_running: false });
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);

  // WebSocket event handlers
  const handleCameraStatus = useCallback((data) => {
    if (data.status === 'started') {
      setIsStreaming(true);
      setError(null);
    } else if (data.status === 'stopped') {
      setIsStreaming(false);
    }
  }, []);

  const handleCameraError = useCallback((data) => {
    setError(data.error);
    setIsStreaming(false);
  }, []);

  const handleQRDetected = useCallback((data) => {
    setLastScan({
      data: data.data,
      timestamp: new Date(data.timestamp).toLocaleString(),
      type: data.type || 'QR Code',
      validation: data.validation || { valid: false, message: 'Unknown validation status' }
    });
  }, []);

  const handleSystemStatus = useCallback((data) => {
    if (data.camera_system) {
      setStatus(prev => ({
        ...prev,
        online: true,
        camera_running: data.camera_system.camera_running || false,
        has_camera: data.camera_system.has_camera,
        initialization_error: data.camera_system.initialization_error
      }));
    }
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    let mounted = true;
    
    const initializeWebSocket = async () => {
      setIsConnecting(true);
      try {
        await websocketService.connect(BACKEND_SERVER);
        if (mounted) {
          setWsConnected(true);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError('Failed to connect to WebSocket server. Falling back to HTTP polling.');
          setWsConnected(false);
        }
      } finally {
        if (mounted) {
          setIsConnecting(false);
        }
      }
    };

    initializeWebSocket();

    return () => {
      mounted = false;
      websocketService.off('camera_status', handleCameraStatus);
      websocketService.off('camera_error', handleCameraError);
      websocketService.off('qr_detected', handleQRDetected);
      websocketService.off('system_status', handleSystemStatus);
    };
  }, [handleCameraStatus, handleCameraError, handleQRDetected, handleSystemStatus]);

  // Set up WebSocket event listeners
  useEffect(() => {
    if (wsConnected) {
      websocketService.on('camera_status', handleCameraStatus);
      websocketService.on('camera_error', handleCameraError);
      websocketService.on('qr_detected', handleQRDetected);
      websocketService.on('system_status', handleSystemStatus);

      // Get initial system status
      websocketService.getSystemStatus();

      // Update connection info periodically
      const connectionInterval = setInterval(() => {
        setConnectionInfo(websocketService.getConnectionInfo());
      }, 5000);

      return () => {
        clearInterval(connectionInterval);
      };
    } else {
      // Fallback to HTTP polling if WebSocket fails
      checkStatus();
      const statusInterval = setInterval(checkStatus, 5000);
      
      let qrInterval;
      let historyInterval;
      if (isStreaming) {
        qrInterval = setInterval(getLastQR, 1000);
        historyInterval = setInterval(getQRHistory, 5000); // Refresh history every 5 seconds
      }

      return () => {
        clearInterval(statusInterval);
        if (qrInterval) clearInterval(qrInterval);
        if (historyInterval) clearInterval(historyInterval);
      };
    }
  }, [wsConnected, isStreaming, handleCameraStatus, handleCameraError, handleQRDetected, handleSystemStatus]);

  // Auto-start camera on component mount
  useEffect(() => {
    const autoStartCamera = async () => {
      if (!wsConnected) {
        // Auto-start camera using HTTP
        try {
          const statusResponse = await fetch(`${RASPI_SERVER}/camera/status`);
          const statusData = await statusResponse.json();

          if (!statusData.camera_running) {
            const response = await fetch(`${RASPI_SERVER}/camera/start`, {
              method: 'POST',
            });
            
            if (response.ok) {
              setIsStreaming(true);
              setError(null);
            }
          } else {
            setIsStreaming(true);
          }
          
          // Get initial QR history
          getQRHistory();
        } catch (err) {
          console.error('Failed to auto-start camera:', err);
        }
      }
    };

    // Delay auto-start to ensure server connection is ready
    const timer = setTimeout(autoStartCamera, 2000);
    return () => clearTimeout(timer);
  }, [wsConnected]);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/status`);
      const data = await response.json();
      
      // Update streaming state based on camera status
      setIsStreaming(data.camera_running);
      
      setStatus({
        online: true,
        camera_running: data.camera_running,
        has_camera: data.has_camera,
        initialization_error: data.initialization_error
      });

      // Clear any previous errors if the status check is successful
      setError(null);
    } catch (err) {
      console.error('Failed to check camera status:', err);
      setError('Failed to connect to Raspberry Pi server');
      setStatus({ online: false, camera_running: false });
    }
  };

  const getQRHistory = async () => {
    try {
      // Get QR history from both Raspberry Pi (local) and main backend (stored)
      const [raspiResponse, backendResponse] = await Promise.allSettled([
        fetch(`${RASPI_SERVER}/camera/qr-history`),
        fetch(`${BACKEND_SERVER}/api/qr-scans?limit=20`)
      ]);
      
      let combinedHistory = [];
      
      // Add Raspberry Pi local history
      if (raspiResponse.status === 'fulfilled' && raspiResponse.value.ok) {
        const raspiData = await raspiResponse.value.json();
        if (raspiData.qr_history) {
          combinedHistory = [...raspiData.qr_history];
        }
      }
      
      // Add backend stored history
      if (backendResponse.status === 'fulfilled' && backendResponse.value.ok) {
        const backendData = await backendResponse.value.json();
        if (Array.isArray(backendData)) {
          // Convert backend format to match frontend format
          const backendHistory = backendData.map(scan => ({
            qr_data: scan.qr_data,
            timestamp: scan.timestamp,
            validation: {
              valid: scan.is_valid,
              order_id: scan.order_id,
              message: scan.validation_message
            },
            device: scan.device || 'backend'
          }));
          
          // Merge and remove duplicates based on qr_data and timestamp
          const existingKeys = new Set(combinedHistory.map(h => `${h.qr_data}-${h.timestamp}`));
          const newBackendHistory = backendHistory.filter(h => 
            !existingKeys.has(`${h.qr_data}-${h.timestamp}`)
          );
          
          combinedHistory = [...combinedHistory, ...newBackendHistory];
        }
      }
      
      // Sort by timestamp (newest first)
      combinedHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      
      setQrHistory(combinedHistory.slice(0, 20)); // Keep only latest 20
    } catch (err) {
      console.error('Failed to get QR history:', err);
    }
  };

  const getLastQR = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/last-qr`);
      const data = await response.json();
      if (data.last_qr_data && (!lastScan || data.last_qr_data !== lastScan.data)) {
        // Try to validate the QR code against backend
        let validation = { valid: false, message: 'Validation pending...' };
        try {
          const validationResponse = await fetch(`${BACKEND_SERVER}/api/validate-qr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qr_data: data.last_qr_data })
          });
          if (validationResponse.ok) {
            validation = await validationResponse.json();
          }
        } catch (validationError) {
          console.error('Validation error:', validationError);
        }

        setLastScan({
          data: data.last_qr_data,
          timestamp: new Date().toLocaleString(),
          type: 'QR Code',
          validation: validation
        });
        
        // Refresh QR history when new scan is detected
        getQRHistory();
      }
    } catch (err) {
      console.error('Failed to get last QR code:', err);
    }
  };

  const startCamera = async () => {
    if (wsConnected) {
      // Use WebSocket
      websocketService.startCamera();
    } else {
      // Fallback to HTTP
      try {
        const statusResponse = await fetch(`${RASPI_SERVER}/camera/status`);
        const statusData = await statusResponse.json();

        if (statusData.camera_running) {
          setIsStreaming(true);
          setError(null);
          return;
        }

        const response = await fetch(`${RASPI_SERVER}/camera/start`, {
          method: 'POST',
        });
        const data = await response.json();

        if (response.ok) {
          setIsStreaming(true);
          setError(null);
        } else {
          throw new Error(data.error || 'Failed to start camera');
        }
      } catch (err) {
        console.error('Failed to start camera:', err);
        setError(err.message || 'Failed to start camera');
        setIsStreaming(false);
      }
    }
  };

  const stopCamera = async () => {
    if (wsConnected) {
      // Use WebSocket
      websocketService.stopCamera();
    } else {
      // Fallback to HTTP
      try {
        const response = await fetch(`${RASPI_SERVER}/camera/stop`, {
          method: 'POST',
        });
        const data = await response.json();
        
        if (response.ok) {
          setIsStreaming(false);
          setError(null);
        } else {
          throw new Error(data.error || 'Failed to stop camera');
        }
      } catch (err) {
        console.error('Failed to stop camera:', err);
        setError(err.message || 'Failed to stop camera');
      }
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        QR Code Scanner
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
              <Typography variant="h6">Camera Feed (Auto-Active)</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {/* Connection Status */}
                <Chip
                  icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                  label={wsConnected ? 'WebSocket' : 'HTTP Fallback'}
                  color={wsConnected ? 'success' : 'warning'}
                  size="small"
                />
                
                {/* Connection Info */}
                {connectionInfo && (
                  <Chip
                    label={`Ping: ${connectionInfo.ping}ms`}
                    size="small"
                    variant="outlined"
                  />
                )}

                {/* Loading indicator */}
                {(isConnecting) && (
                  <CircularProgress size={20} />
                )}

                {/* Camera Status Indicator */}
                <Chip
                  label={isStreaming ? 'Camera Active' : 'Camera Inactive'}
                  color={isStreaming ? 'success' : 'error'}
                  size="small"
                />
              </Box>
            </Box>

            {!wsConnected && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Using HTTP fallback mode - WebSocket connection unavailable
              </Alert>
            )}

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {!status.online && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Raspberry Pi server is offline
              </Alert>
            )}

            {status.initialization_error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Camera initialization error: {status.initialization_error}
              </Alert>
            )}

            <Box
              sx={{
                width: '100%',
                height: 480,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                bgcolor: 'black',
                position: 'relative',
              }}
            >
              {isStreaming ? (
                <img
                  src={`${RASPI_SERVER}/video_feed`}
                  alt="Camera Feed"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                  }}
                />
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    color: 'grey.500',
                  }}
                >
                  <QrCodeScannerIcon sx={{ fontSize: 60, mb: 2 }} />
                  <Typography>Camera is stopped</Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Last Scan
            </Typography>
            {lastScan ? (
              <Box>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  Data: {lastScan.data}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Type: {lastScan.type}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Time: {lastScan.timestamp}
                </Typography>
                {lastScan.validation && (
                  <Box sx={{ mt: 1 }}>
                    <Chip
                      label={lastScan.validation.valid ? 'Valid' : 'Not Valid'}
                      color={lastScan.validation.valid ? 'success' : 'error'}
                      size="small"
                    />
                    {lastScan.validation.valid && lastScan.validation.order_number && (
                      <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 0.5 }}>
                        Order: {lastScan.validation.order_number}
                      </Typography>
                    )}
                    {!lastScan.validation.valid && lastScan.validation.message && (
                      <Typography variant="caption" color="error.main" sx={{ display: 'block', mt: 0.5 }}>
                        {lastScan.validation.message}
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
            ) : (
              <Typography color="text.secondary">No QR codes scanned yet</Typography>
            )}
          </Paper>

          {/* QR History Panel */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Scan History ({qrHistory.length})
            </Typography>
            <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>
              {qrHistory.length > 0 ? (
                qrHistory.slice(0, 15).map((scan, index) => (
                  <Box key={index} sx={{ mb: 1, p: 1, border: '1px solid #eee', borderRadius: 1 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {scan.qr_data}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(scan.timestamp).toLocaleTimeString()}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                        <Chip
                          label={scan.device || 'unknown'}
                          size="small"
                          variant="outlined"
                          color="info"
                          sx={{ fontSize: '0.6rem', height: 18 }}
                        />
                        <Chip
                          label={scan.validation.valid ? 'Valid' : 'Not Valid'}
                          color={scan.validation.valid ? 'success' : 'error'}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                    {scan.validation.valid && scan.validation.order_number && (
                      <Typography variant="caption" color="success.main">
                        Order: {scan.validation.order_number}
                      </Typography>
                    )}
                    {!scan.validation.valid && scan.validation.message && (
                      <Typography variant="caption" color="error.main">
                        {scan.validation.message}
                      </Typography>
                    )}
                  </Box>
                ))
              ) : (
                <Typography color="text.secondary">No scans in history</Typography>
              )}
            </Box>
          </Paper>

          {/* Connection Status Panel */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Connection Status
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">WebSocket:</Typography>
                <Chip 
                  label={wsConnected ? 'Connected' : 'Disconnected'} 
                  color={wsConnected ? 'success' : 'error'} 
                  size="small" 
                />
              </Box>
              
              {connectionInfo && (
                <>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Transport:</Typography>
                    <Typography variant="body2">{connectionInfo.transport}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Ping:</Typography>
                    <Typography variant="body2">{connectionInfo.ping}ms</Typography>
                  </Box>
                  {connectionInfo.reconnectAttempts > 0 && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Reconnects:</Typography>
                      <Typography variant="body2">{connectionInfo.reconnectAttempts}</Typography>
                    </Box>
                  )}
                </>
              )}
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Raspberry Pi:</Typography>
                <Chip 
                  label={status.online ? 'Online' : 'Offline'} 
                  color={status.online ? 'success' : 'error'} 
                  size="small" 
                />
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}