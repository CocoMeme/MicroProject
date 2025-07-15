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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import HistoryIcon from '@mui/icons-material/History';
import QrCodeIcon from '@mui/icons-material/QrCode';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import websocketService from '../services/websocketService';

const RASPI_SERVER = 'http://192.168.100.63:5001'; // Your Raspberry Pi address
const BACKEND_SERVER = 'http://192.168.100.61:5000'; // Your Flask backend

export default function Scanner() {
  const [isStreaming, setIsStreaming] = useState(true); // Auto-start camera
  const [qrHistory, setQrHistory] = useState([]);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState({ online: false, camera_running: false });
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Modal states
  const [historyModalOpen, setHistoryModalOpen] = useState(false);

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
    console.log('QR detected via WebSocket:', data); // Debug log
    
    // Immediately refresh QR history when new scan is detected
    getQRHistory();
  }, []);

  const handleQRHistoryUpdated = useCallback((data) => {
    console.log('QR history updated via WebSocket:', data); // Debug log
    if (data.history) {
      setQrHistory(prevHistory => {
        // Merge new history with existing, removing duplicates
        const combined = [...data.history];
        const existingKeys = new Set(data.history.map(h => `${h.qr_data}-${h.timestamp}`));
        
        // Add any existing items that aren't in the new data
        const additionalItems = prevHistory.filter(h => 
          !existingKeys.has(`${h.qr_data}-${h.timestamp}`)
        );
        
        combined.push(...additionalItems);
        
        // Sort by timestamp and limit to 20 items
        return combined
          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
          .slice(0, 20);
      });
    }
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
      websocketService.off('qr_history_updated', handleQRHistoryUpdated);
      websocketService.off('system_status', handleSystemStatus);
    };
  }, [handleCameraStatus, handleCameraError, handleQRDetected, handleQRHistoryUpdated, handleSystemStatus]);

  // Set up WebSocket event listeners
  useEffect(() => {
    if (wsConnected) {
      websocketService.on('camera_status', handleCameraStatus);
      websocketService.on('camera_error', handleCameraError);
      websocketService.on('qr_detected', handleQRDetected);
      websocketService.on('qr_history_updated', handleQRHistoryUpdated);
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
        historyInterval = setInterval(getQRHistory, 5000); // Refresh history every 5 seconds
      }

      return () => {
        clearInterval(statusInterval);
        if (qrInterval) clearInterval(qrInterval);
        if (historyInterval) clearInterval(historyInterval);
      };
    }
  }, [wsConnected, isStreaming, handleCameraStatus, handleCameraError, handleQRDetected, handleQRHistoryUpdated, handleSystemStatus]);

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
      console.log('Fetching QR history...'); // Debug log
      // Get QR history from both Raspberry Pi (local) and main backend (stored)
      const [raspiResponse, backendResponse] = await Promise.allSettled([
        fetch(`${RASPI_SERVER}/camera/qr-history`, {
          cache: 'no-cache',
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        }),
        fetch(`${BACKEND_SERVER}/api/qr-scans?limit=50`, {
          cache: 'no-cache',
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        })
      ]);
      
      let combinedHistory = [];
      
      // Add Raspberry Pi local history
      if (raspiResponse.status === 'fulfilled' && raspiResponse.value.ok) {
        const raspiData = await raspiResponse.value.json();
        console.log('Raspi QR history:', raspiData); // Debug log
        if (raspiData.qr_history) {
          combinedHistory = [...raspiData.qr_history];
        }
      } else {
        console.log('Failed to fetch Raspi QR history:', raspiResponse); // Debug log
      }
      
      // Add backend stored history
      if (backendResponse.status === 'fulfilled' && backendResponse.value.ok) {
        const backendData = await backendResponse.value.json();
        console.log('Backend QR history:', backendData); // Debug log
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
      } else {
        console.log('Failed to fetch backend QR history:', backendResponse); // Debug log
      }
      
      // Sort by timestamp (newest first)
      combinedHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      
      console.log('Final combined history:', combinedHistory); // Debug log
      setQrHistory(combinedHistory.slice(0, 20)); // Keep only latest 20
    } catch (err) {
      console.error('Failed to get QR history:', err);
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
          {/* Action Buttons */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              QR Code Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<HistoryIcon />}
                onClick={() => setHistoryModalOpen(true)}
                disabled={qrHistory.length === 0}
                fullWidth
              >
                View Scan History ({qrHistory.length})
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  console.log('Force refreshing QR history...');
                  getQRHistory();
                }}
                fullWidth
                sx={{ mt: 1 }}
              >
                Force Refresh History
              </Button>
              <Button
                variant="outlined"
                onClick={async () => {
                  try {
                    const response = await fetch(`${RASPI_SERVER}/debug/test-qr-image`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ qr_code: 'ORD-001' })
                    });
                    if (response.ok) {
                      console.log('Test QR image created');
                      // History will update via WebSocket
                    } else {
                      console.error('Failed to create test QR image');
                    }
                  } catch (err) {
                    console.error('Error creating test QR image:', err);
                  }
                }}
                fullWidth
                sx={{ mt: 1 }}
              >
                Test QR Image
              </Button>
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

          {/* Latest Scan Display */}
          {qrHistory.length > 0 && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Latest Scan
              </Typography>
              <Box>
                <Typography variant="body1" gutterBottom>
                  <strong>Order ID:</strong> {qrHistory[0].validation?.valid && qrHistory[0].validation?.order_number 
                    ? qrHistory[0].validation.order_number 
                    : qrHistory[0].validation?.valid && qrHistory[0].qr_data
                    ? qrHistory[0].qr_data
                    : 'Invalid QR Code'
                  }
                </Typography>
                
                {/* Display QR Image if available */}
                {qrHistory[0].image_data && qrHistory[0].image_data.base64 && (
                  <Box sx={{ mb: 2, textAlign: 'center' }}>
                    <Paper sx={{ p: 1, bgcolor: 'grey.50', display: 'inline-block' }}>
                      <img 
                        src={`data:image/jpeg;base64,${qrHistory[0].image_data.base64}`}
                        alt="Latest QR Code"
                        style={{ 
                          maxWidth: '150px', 
                          maxHeight: '150px',
                          border: '1px solid #ddd',
                          borderRadius: '4px'
                        }}
                      />
                    </Paper>
                  </Box>
                )}
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  <strong>QR Data:</strong> {qrHistory[0].qr_data}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  <strong>Scanned:</strong> {new Date(qrHistory[0].timestamp).toLocaleString()}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Chip
                    label={qrHistory[0].validation?.valid ? 'Valid' : 'Not Valid'}
                    color={qrHistory[0].validation?.valid ? 'success' : 'error'}
                    size="small"
                  />
                  <Chip
                    label={qrHistory[0].device || 'unknown'}
                    size="small"
                    variant="outlined"
                    color="info"
                    sx={{ ml: 1 }}
                  />
                </Box>
              </Box>
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* History Modal */}
      <Dialog open={historyModalOpen} onClose={() => setHistoryModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <HistoryIcon />
            QR Code Scan History ({qrHistory.length})
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {qrHistory.map((scan, index) => (
              <div key={index}>
                <ListItem sx={{ py: 2 }}>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          Order ID: {scan.validation?.valid && scan.validation?.order_number 
                            ? scan.validation.order_number 
                            : scan.validation?.valid && scan.qr_data
                            ? scan.qr_data
                            : 'Invalid QR Code'
                          }
                        </Typography>
                        
                        {/* QR Code Image */}
                        {scan.image_data && scan.image_data.base64 && (
                          <Box sx={{ mb: 2, textAlign: 'center' }}>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              QR Code Image:
                            </Typography>
                            <Paper sx={{ p: 1, bgcolor: 'grey.50', display: 'inline-block' }}>
                              <img 
                                src={`data:image/jpeg;base64,${scan.image_data.base64}`}
                                alt="QR Code"
                                style={{ 
                                  maxWidth: '200px', 
                                  maxHeight: '200px',
                                  border: '1px solid #ddd',
                                  borderRadius: '4px'
                                }}
                              />
                            </Paper>
                          </Box>
                        )}
                        
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          QR Code Data:
                        </Typography>
                        <Paper sx={{ p: 1, bgcolor: 'grey.50', mb: 1 }}>
                          <Typography 
                            variant="body1" 
                            sx={{ 
                              fontFamily: 'monospace',
                              wordBreak: 'break-all'
                            }}
                          >
                            {scan.qr_data}
                          </Typography>
                        </Paper>
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1 }}>
                          <Chip
                            label={scan.validation?.valid ? 'Valid' : 'Not Valid'}
                            color={scan.validation?.valid ? 'success' : 'error'}
                            size="small"
                          />
                          <Chip
                            label={scan.device || 'unknown'}
                            size="small"
                            variant="outlined"
                            color="info"
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Scanned: {new Date(scan.timestamp).toLocaleString()}
                        </Typography>
                        {scan.validation?.valid && scan.validation?.customer_name && (
                          <Typography variant="caption" color="success.main" sx={{ display: 'block' }}>
                            Customer: {scan.validation.customer_name}
                          </Typography>
                        )}
                        {scan.validation?.valid && scan.validation?.product_name && (
                          <Typography variant="caption" color="success.main" sx={{ display: 'block' }}>
                            Product: {scan.validation.product_name}
                          </Typography>
                        )}
                        {!scan.validation?.valid && scan.validation?.message && (
                          <Typography variant="caption" color="error.main" sx={{ display: 'block' }}>
                            {scan.validation.message}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < qrHistory.length - 1 && <Divider />}
              </div>
            ))}
            {qrHistory.length === 0 && (
              <ListItem>
                <ListItemText primary="No scan history available" />
              </ListItem>
            )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}