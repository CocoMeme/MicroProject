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
  IconButton,
  Tooltip,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import HistoryIcon from '@mui/icons-material/History';
import QrCodeIcon from '@mui/icons-material/QrCode';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import websocketService from '../services/websocketService';

const RASPI_SERVER = process.env.REACT_APP_RASPBERRY_PI_URL || 'http://192.168.100.63:5001'; // Your Raspberry Pi address
const BACKEND_SERVER = process.env.REACT_APP_BACKEND_URL || 'http://192.168.100.61:5000'; // Your Flask backend

export default function Scanner() {
  const [isStreaming, setIsStreaming] = useState(true); // Auto-start camera
  const [qrHistory, setQrHistory] = useState([]);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState({ online: false, camera_running: false });
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  // Modal states
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

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
      
      // Get initial QR history when WebSocket connects
      getQRHistory();

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

  // Initial data load when component mounts
  useEffect(() => {
    // Load QR history immediately when component mounts
    getQRHistory();
    
    // Also check camera status
    checkStatus();
  }, []); // Empty dependency array means this runs once on mount

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
    setIsLoadingHistory(true);
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
      setLastRefresh(new Date()); // Update last refresh time
    } catch (err) {
      console.error('Failed to get QR history:', err);
    } finally {
      setIsLoadingHistory(false);
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

  // Auto-refresh QR history with smart intervals
  useEffect(() => {
    // Fetch immediately when effect runs
    getQRHistory();
    
    const autoRefreshInterval = setInterval(() => {
      // Auto-refresh at different intervals based on connection type
      if (!wsConnected) {
        // More frequent refresh when no WebSocket (5 seconds)
        getQRHistory();
      } else {
        // Less frequent backup refresh even with WebSocket (15 seconds)
        // This ensures we don't miss anything if WebSocket has issues
        getQRHistory();
      }
    }, wsConnected ? 15000 : 5000); // 15s with WebSocket, 5s without

    return () => clearInterval(autoRefreshInterval);
  }, [wsConnected]);

  // Handle ESC key for fullscreen exit
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && fullscreenOpen) {
        setFullscreenOpen(false);
      }
    };

    if (fullscreenOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [fullscreenOpen]);

  return (
    <Box sx={{ p: { xs: 1, sm: 0 } }}>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>
        QR Code Scanner
      </Typography>

      <Grid container spacing={{ xs: 2, sm: 3 }}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: { xs: 2, sm: 3 }, mb: { xs: 2, sm: 3 } }}>
            <Box sx={{ 
              mb: 2, 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start',
              flexDirection: { xs: 'column', sm: 'row' },
              gap: { xs: 2, sm: 1 }
            }}>
              <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                Camera Feed (Auto-Active)
              </Typography>
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                flexWrap: 'wrap',
                width: { xs: '100%', sm: 'auto' },
                justifyContent: { xs: 'flex-start', sm: 'flex-end' }
              }}>
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
              <Alert severity="info" sx={{ mb: 2, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                Using HTTP fallback mode - WebSocket connection unavailable
              </Alert>
            )}

            {error && (
              <Alert severity="error" sx={{ mb: 2, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                {error}
              </Alert>
            )}

            {!status.online && (
              <Alert severity="warning" sx={{ mb: 2, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                Raspberry Pi server is offline
              </Alert>
            )}

            {status.initialization_error && (
              <Alert severity="error" sx={{ mb: 2, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                Camera initialization error: {status.initialization_error}
              </Alert>
            )}

            <Box
              sx={{
                width: '100%',
                height: { xs: 300, sm: 400, md: 480 },
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                bgcolor: 'black',
                position: 'relative',
                borderRadius: 1,
                overflow: 'hidden',
              }}
            >
              {/* Fullscreen Button - Always visible */}
              <Tooltip title="Fullscreen">
                <IconButton
                  onClick={() => setFullscreenOpen(true)}
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    color: 'white',
                    bgcolor: 'rgba(0, 0, 0, 0.6)',
                    zIndex: 1,
                    '&:hover': {
                      bgcolor: 'rgba(0, 0, 0, 0.8)',
                    },
                    transition: 'all 0.2s ease-in-out',
                  }}
                >
                  <FullscreenIcon />
                </IconButton>
              </Tooltip>

              {isStreaming ? (
                <img
                  src={`${RASPI_SERVER}/video_feed`}
                  alt="Camera Feed"
                  style={{
                    width: '100%',
                    height: '100%',
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
                  <QrCodeScannerIcon sx={{ fontSize: { xs: 40, sm: 60 }, mb: 2 }} />
                  <Typography variant="body1" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                    Camera is stopped
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} lg={4}>
          {/* Latest Scans List - Auto-refreshing */}
          <Paper sx={{ 
            p: { xs: 2, sm: 3 }, 
            height: { xs: '60vh', sm: '70vh', lg: 'calc(100vh - 200px)' },
            display: 'flex', 
            flexDirection: 'column',
            minHeight: { xs: '400px', sm: '500px' }
          }}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              flexWrap: 'wrap',
              gap: 1,
              mb: 1
            }}>
              <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                Latest Scans
              </Typography>
              <Chip 
                label={`${qrHistory.length} scans`} 
                size="small" 
                color={qrHistory.length > 0 ? 'primary' : 'default'}
              />
              {isLoadingHistory && (
                <CircularProgress size={16} />
              )}
            </Box>
            
            {/* Last refresh indicator */}
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              mb: 1,
              flexWrap: 'wrap',
              gap: 1
            }}>
              {lastRefresh && (
                <Typography variant="caption" color="text.secondary">
                  Last updated: {lastRefresh.toLocaleTimeString()}
                </Typography>
              )}
              {isLoadingHistory && (
                <Typography variant="caption" color="primary">
                  Refreshing...
                </Typography>
              )}
            </Box>
            
            {/* Connection Status Indicator */}
            <Box sx={{ 
              display: 'flex', 
              gap: 1, 
              mb: 2,
              flexWrap: 'wrap'
            }}>
              <Chip 
                icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                label={wsConnected ? 'Live (15s backup)' : 'Auto-refresh (5s)'} 
                color={wsConnected ? 'success' : 'info'} 
                size="small" 
              />
              <Chip 
                label={status.online ? 'Pi Online' : 'Pi Offline'} 
                color={status.online ? 'success' : 'error'} 
                size="small" 
              />
            </Box>

            {/* Scrollable scan list */}
            <Box sx={{ 
              flexGrow: 1, 
              overflow: 'auto',
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              bgcolor: 'background.paper'
            }}>
              {qrHistory.length === 0 ? (
                <Box sx={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  height: '100%',
                  color: 'text.secondary',
                  p: 3
                }}>
                  <QrCodeScannerIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                  <Typography variant="body2" align="center" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                    No scans detected yet
                  </Typography>
                  <Typography variant="caption" align="center" sx={{ mt: 1, fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
                    Point a QR code at the camera
                  </Typography>
                </Box>
              ) : (
                <List sx={{ p: 0 }}>
                  {qrHistory.map((scan, index) => (
                    <React.Fragment key={`${scan.qr_data}-${scan.timestamp}-${index}`}>
                      <ListItem 
                        sx={{ 
                          py: { xs: 1.5, sm: 2 },
                          px: { xs: 1, sm: 2 },
                          bgcolor: index === 0 ? 'action.hover' : 'transparent',
                          borderLeft: index === 0 ? '4px solid' : 'none',
                          borderLeftColor: index === 0 ? 'primary.main' : 'transparent'
                        }}
                      >
                        <Box sx={{ width: '100%' }}>
                          {/* QR Data and Status */}
                          <Box sx={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'flex-start',
                            mb: 1,
                            flexWrap: 'wrap',
                            gap: 1
                          }}>
                            <Typography 
                              variant="subtitle2" 
                              sx={{ 
                                fontWeight: 'bold',
                                fontSize: { xs: '0.875rem', sm: '1rem' },
                                wordBreak: 'break-word',
                                maxWidth: { xs: '60%', sm: '70%' }
                              }}
                            >
                              {scan.validation?.valid && scan.validation?.order_number 
                                ? scan.validation.order_number 
                                : scan.qr_data}
                            </Typography>
                            <Chip
                              label={scan.validation?.valid ? 'Valid' : 'Invalid'}
                              color={scan.validation?.valid ? 'success' : 'error'}
                              size="small"
                            />
                          </Box>
                          
                          {/* Order Details if valid */}
                          {scan.validation?.valid && (
                            <Box sx={{ mb: 1 }}>
                              {scan.validation.customer_name && (
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
                                  Customer: {scan.validation.customer_name}
                                </Typography>
                              )}
                              {scan.validation.product_name && (
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
                                  Product: {scan.validation.product_name}
                                </Typography>
                              )}
                              {scan.validation.amount && (
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
                                  Amount: ₱{parseFloat(scan.validation.amount).toFixed(2)}
                                </Typography>
                              )}
                            </Box>
                          )}
                          
                          {/* Timestamp */}
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.6rem', sm: '0.75rem' } }}>
                            {new Date(scan.timestamp).toLocaleString()}
                          </Typography>
                          
                          {/* QR Image if available */}
                          {scan.image_data && scan.image_data.base64 && (
                            <Box sx={{ mt: 1, textAlign: 'center' }}>
                              <img 
                                src={`data:image/jpeg;base64,${scan.image_data.base64}`}
                                alt="QR Code"
                                style={{ 
                                  maxWidth: '60px', 
                                  maxHeight: '60px',
                                  border: '1px solid #ddd',
                                  borderRadius: '4px'
                                }}
                              />
                            </Box>
                          )}
                        </Box>
                      </ListItem>
                      {index < qrHistory.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Box>

            {/* Quick Actions */}
            <Box sx={{ 
              mt: 2, 
              display: 'flex', 
              justifyContent: 'center',
              gap: 1,
              flexWrap: 'wrap'
            }}>
              <Button
                variant="outlined"
                size="small"
                onClick={() => setHistoryModalOpen(true)}
                disabled={qrHistory.length === 0}
                sx={{ minWidth: { xs: '120px', sm: 'auto' } }}
              >
                View All History
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Fullscreen Camera Modal */}
      <Dialog
        open={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        maxWidth={false}
        fullScreen
        PaperProps={{
          style: {
            backgroundColor: 'black',
            margin: 0,
            padding: 0,
            borderRadius: 0,
            maxHeight: '100vh',
            maxWidth: '100vw',
            height: '100vh',
            width: '100vw',
          },
        }}
        sx={{
          '& .MuiDialog-container': {
            height: '100vh',
            width: '100vw',
          },
          '& .MuiBackdrop-root': {
            backgroundColor: 'black',
          },
        }}
      >
        <Box
          sx={{
            width: '100vw',
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'black',
            position: 'relative',
            margin: 0,
            padding: 0,
            overflow: 'hidden',
          }}
        >
          {/* Status Bar */}
          <Box
            sx={{
              position: 'absolute',
              top: 16,
              left: 16,
              zIndex: 10,
              display: 'flex',
              gap: 1,
              flexWrap: 'wrap',
            }}
          >
            <Chip
              icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
              label={wsConnected ? 'WebSocket' : 'HTTP'}
              color={wsConnected ? 'success' : 'warning'}
              size="small"
            />
            <Chip
              label={isStreaming ? 'Camera Active' : 'Camera Inactive'}
              color={isStreaming ? 'success' : 'error'}
              size="small"
            />
          </Box>

          {/* Camera Feed */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              bgcolor: 'black',
            }}
          >
            {/* Exit Fullscreen Button - Always visible */}
            <Tooltip title="Exit Fullscreen">
              <IconButton
                onClick={() => setFullscreenOpen(false)}
                sx={{
                  position: 'absolute',
                  top: 16,
                  right: 16,
                  color: 'white',
                  bgcolor: 'rgba(0, 0, 0, 0.6)',
                  zIndex: 10,
                  '&:hover': {
                    bgcolor: 'rgba(0, 0, 0, 0.8)',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                <FullscreenExitIcon />
              </IconButton>
            </Tooltip>

            {isStreaming ? (
              <img
                src={`${RASPI_SERVER}/video_feed`}
                alt="Camera Feed - Fullscreen"
                style={{
                  width: '100vw',
                  height: '100vh',
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
                <QrCodeScannerIcon sx={{ fontSize: 120, mb: 2 }} />
                <Typography variant="h5" sx={{ color: 'grey.400' }}>
                  Camera is stopped
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      </Dialog>

      {/* History Modal */}
      <Dialog 
        open={historyModalOpen} 
        onClose={() => setHistoryModalOpen(false)} 
        maxWidth="md" 
        fullWidth
        fullScreen={{ xs: true, sm: false }}
        sx={{
          '& .MuiDialog-paper': {
            margin: { xs: 0, sm: 2 },
            width: { xs: '100%', sm: 'auto' },
            maxHeight: { xs: '100vh', sm: '90vh' }
          }
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <HistoryIcon />
            <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
              QR Code Scan History ({qrHistory.length})
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          <List sx={{ maxHeight: { xs: 'none', sm: 400 }, overflow: 'auto' }}>
            {qrHistory.map((scan, index) => (
              <div key={index}>
                <ListItem sx={{ py: { xs: 1.5, sm: 2 }, px: { xs: 2, sm: 3 } }}>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography variant="h6" gutterBottom sx={{ fontSize: { xs: '1rem', sm: '1.25rem' } }}>
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
                                  maxWidth: window.innerWidth < 600 ? '150px' : '200px',
                                  maxHeight: window.innerWidth < 600 ? '150px' : '200px',
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
                              wordBreak: 'break-all',
                              fontSize: { xs: '0.75rem', sm: '0.875rem' }
                            }}
                          >
                            {scan.qr_data}
                          </Typography>
                        </Paper>
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Box sx={{ 
                          display: 'flex', 
                          gap: 1, 
                          alignItems: 'center', 
                          mb: 1,
                          flexWrap: 'wrap'
                        }}>
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
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>
                          Scanned: {new Date(scan.timestamp).toLocaleString()}
                        </Typography>
                        {scan.validation?.valid && scan.validation?.customer_name && (
                          <Typography variant="caption" color="success.main" sx={{ display: 'block', fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>
                            Customer: {scan.validation.customer_name}
                          </Typography>
                        )}
                        {scan.validation?.valid && scan.validation?.product_name && (
                          <Typography variant="caption" color="success.main" sx={{ display: 'block', fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>
                            Product: {scan.validation.product_name}
                          </Typography>
                        )}
                        {!scan.validation?.valid && scan.validation?.message && (
                          <Typography variant="caption" color="error.main" sx={{ display: 'block', fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>
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
              <ListItem sx={{ py: 4 }}>
                <ListItemText 
                  primary={
                    <Box sx={{ textAlign: 'center' }}>
                      <QrCodeScannerIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                      <Typography variant="body1">No scan history available</Typography>
                    </Box>
                  }
                />
              </ListItem>
            )}
          </List>
        </DialogContent>
        <DialogActions sx={{ p: { xs: 2, sm: 3 } }}>
          <Button onClick={() => setHistoryModalOpen(false)} variant="outlined" fullWidth={{ xs: true, sm: false }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}