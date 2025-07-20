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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import HistoryIcon from '@mui/icons-material/History';
import QrCodeIcon from '@mui/icons-material/QrCode';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import websocketService from '../services/websocketService';

const RASPI_SERVER = process.env.REACT_APP_RASPI_BASE_URL || 'http://192.168.100.63:5001';
const BACKEND_SERVER = process.env.REACT_APP_API_BASE_URL || 'http://192.168.100.61:5000';

// Debug logging
console.log('Environment Variables:', {
  REACT_APP_RASPI_BASE_URL: process.env.REACT_APP_RASPI_BASE_URL,
  REACT_APP_API_BASE_URL: process.env.REACT_APP_API_BASE_URL,
  RASPI_SERVER,
  BACKEND_SERVER
});

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
  const [packageInformation, setPackageInformation] = useState([]);
  const [isLoadingPackages, setIsLoadingPackages] = useState(false);
  
  // Modal states
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  // Define utility functions first
  const getQRHistory = useCallback(async () => {
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
      
      // Add backend stored scans
      if (backendResponse.status === 'fulfilled' && backendResponse.value.ok) {
        const backendData = await backendResponse.value.json();
        console.log('Backend QR scans:', backendData); // Debug log
        if (backendData.scans) {
          // Transform backend scans to match local history format
          const backendScans = backendData.scans.map(scan => ({
            qr_data: scan.qr_data,
            timestamp: scan.timestamp,
            device: scan.device || 'backend',
            is_valid: scan.is_valid,
            validation_message: scan.validation_message,
            order_id: scan.order_id,
            source: 'backend'
          }));
          
          combinedHistory = [...combinedHistory, ...backendScans];
        }
      } else {
        console.log('Failed to fetch backend QR scans:', backendResponse); // Debug log
      }
      
      // Remove duplicates and sort by timestamp
      const uniqueHistory = combinedHistory.reduce((acc, current) => {
        const key = `${current.qr_data}-${current.timestamp}`;
        if (!acc.some(item => `${item.qr_data}-${item.timestamp}` === key)) {
          acc.push(current);
        }
        return acc;
      }, []);
      
      console.log('Final combined history:', uniqueHistory); // Debug log
      setQrHistory(uniqueHistory.slice(0, 20)); // Keep only latest 20
      setLastRefresh(new Date()); // Update last refresh time
    } catch (err) {
      console.error('Failed to get QR history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const getPackageInformation = useCallback(async () => {
    setIsLoadingPackages(true);
    try {
      console.log('Fetching package information...'); // Debug log
      const response = await fetch(`${BACKEND_SERVER}/api/package-information`, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Package information:', data); // Debug log
        if (data.packages) {
          setPackageInformation(data.packages);
        }
      } else {
        console.log('Failed to fetch package information:', response.status); // Debug log
      }
    } catch (err) {
      console.error('Error fetching package information:', err);
    } finally {
      setIsLoadingPackages(false);
    }
  }, []);

  // WebSocket event handlers (defined after utility functions)
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
    
    // Immediately refresh QR history and package information when new scan is detected
    getQRHistory();
    getPackageInformation();
  }, [getQRHistory, getPackageInformation]);

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
      getPackageInformation();

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
      let packageInterval;
      if (isStreaming) {
        historyInterval = setInterval(getQRHistory, 5000); // Refresh history every 5 seconds
        packageInterval = setInterval(getPackageInformation, 10000); // Refresh package info every 10 seconds
      }

      return () => {
        clearInterval(statusInterval);
        if (qrInterval) clearInterval(qrInterval);
        if (historyInterval) clearInterval(historyInterval);
        if (packageInterval) clearInterval(packageInterval);
      };
    }
  }, [wsConnected, isStreaming, handleCameraStatus, handleCameraError, handleQRDetected, handleQRHistoryUpdated, handleSystemStatus, getQRHistory, getPackageInformation]);

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
          getPackageInformation();
        } catch (err) {
          console.error('Failed to auto-start camera:', err);
        }
      }
    };

    // Delay auto-start to ensure server connection is ready
    const timer = setTimeout(autoStartCamera, 2000);
    return () => clearTimeout(timer);
  }, [wsConnected, getQRHistory, getPackageInformation]);

  // Initial data load when component mounts
  useEffect(() => {
    // Load QR history and package information immediately when component mounts
    getQRHistory();
    getPackageInformation();
    
    // Also check camera status
    checkStatus();
  }, [getQRHistory, getPackageInformation]); // Dependencies added

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
        
        if (response.ok) {
          setIsStreaming(true);
          setError(null);
          // Get QR history when camera starts
          getQRHistory();
        } else {
          setError('Failed to start camera');
        }
      } catch (err) {
        console.error('Failed to start camera:', err);
        setError('Failed to connect to Raspberry Pi server');
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
        
        if (response.ok) {
          setIsStreaming(false);
          setError(null);
        } else {
          setError('Failed to stop camera');
        }
      } catch (err) {
        console.error('Failed to stop camera:', err);
        setError('Failed to connect to Raspberry Pi server');
      }
    }
  };

  const refreshStatus = () => {
    if (wsConnected) {
      websocketService.getSystemStatus();
    } else {
      checkStatus();
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const isValidQR = (qr) => {
    return qr.is_valid === true || qr.is_valid === 'true';
  };

  const getQRStatusChip = (qr) => {
    if (isValidQR(qr)) {
      return <Chip label="Valid" color="success" size="small" />;
    } else {
      return <Chip label="Invalid" color="error" size="small" />;
    }
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 }, maxWidth: 1200, margin: '0 auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.75rem', sm: '2.125rem' } }}>
        📱 QR Scanner
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Camera Controls */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <QrCodeScannerIcon sx={{ mr: 1 }} />
              <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                Camera Control
              </Typography>
              <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
                {wsConnected ? (
                  <Tooltip title="WebSocket Connected">
                    <WifiIcon color="success" />
                  </Tooltip>
                ) : (
                  <Tooltip title="Using HTTP Polling">
                    <WifiOffIcon color="warning" />
                  </Tooltip>
                )}
                <Button size="small" variant="outlined" onClick={refreshStatus}>
                  Refresh
                </Button>
              </Box>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Status: {status.online ? 'Online' : 'Offline'}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Camera: {status.camera_running ? 'Running' : 'Stopped'}
              </Typography>
              {status.has_camera === false && (
                <Typography variant="body2" color="error" gutterBottom>
                  ⚠️ No camera detected on Raspberry Pi
                </Typography>
              )}
              {status.initialization_error && (
                <Typography variant="body2" color="error" gutterBottom>
                  ⚠️ {status.initialization_error}
                </Typography>
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                color="primary"
                onClick={startCamera}
                disabled={isStreaming || !status.online}
                startIcon={<QrCodeScannerIcon />}
                size="small"
              >
                Start Camera
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                onClick={stopCamera}
                disabled={!isStreaming || !status.online}
                size="small"
              >
                Stop Camera
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Camera Stream */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                Camera Feed
              </Typography>
              <IconButton
                sx={{ ml: 'auto' }}
                onClick={() => setFullscreenOpen(true)}
                disabled={!isStreaming}
              >
                <FullscreenIcon />
              </IconButton>
            </Box>
            
            <Box
              sx={{
                position: 'relative',
                width: '100%',
                paddingBottom: '56.25%', // 16:9 aspect ratio
                backgroundColor: '#000',
                borderRadius: 1,
                overflow: 'hidden',
              }}
            >
              {isStreaming ? (
                <img
                  src={`${RASPI_SERVER}/camera/stream`}
                  alt="Camera Stream"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                  onError={() => setError('Camera stream unavailable')}
                />
              ) : (
                <Box
                  sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    textAlign: 'center',
                    color: 'white',
                  }}
                >
                  <QrCodeScannerIcon sx={{ fontSize: 48, mb: 1 }} />
                  <Typography variant="body2">Camera not active</Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* QR History */}
        <Grid item xs={12}>
          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <HistoryIcon sx={{ mr: 1 }} />
                <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                  Recent Scans ({qrHistory.length})
                </Typography>
              </Box>
              <Button
                variant="outlined"
                size="small"
                onClick={getQRHistory}
                disabled={isLoadingHistory}
                startIcon={isLoadingHistory ? <CircularProgress size={16} /> : <HistoryIcon />}
              >
                Refresh
              </Button>
            </Box>

            {lastRefresh && (
              <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                Last updated: {lastRefresh.toLocaleTimeString()}
              </Typography>
            )}

            {isLoadingHistory ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress />
              </Box>
            ) : qrHistory.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                No QR codes scanned yet
              </Typography>
            ) : (
              <>
                <List sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {qrHistory.slice(0, 5).map((qr, index) => (
                    <React.Fragment key={`${qr.qr_data}-${qr.timestamp}-${index}`}>
                      <ListItem>
                        <QrCodeIcon sx={{ mr: 2, color: isValidQR(qr) ? 'success.main' : 'error.main' }} />
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                              <Typography variant="body1" sx={{ fontSize: { xs: '0.9rem', sm: '1rem' } }}>
                                {qr.qr_data}
                              </Typography>
                              {getQRStatusChip(qr)}
                              {qr.source === 'backend' && (
                                <Chip label="Stored" color="info" size="small" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="caption" color="text.secondary">
                                {formatTimestamp(qr.timestamp)} • {qr.device || 'Unknown Device'}
                              </Typography>
                              {qr.validation_message && (
                                <Typography variant="caption" display="block" color="text.secondary">
                                  {qr.validation_message}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < Math.min(qrHistory.length - 1, 4) && <Divider />}
                    </React.Fragment>
                  ))}
                </List>

                <Box sx={{ mt: 2, textAlign: 'center' }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setHistoryModalOpen(true)}
                    endIcon={<HistoryIcon />}
                  >
                    View All History
                  </Button>
                </Box>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Package Information Table */}
      <Paper sx={{ p: { xs: 2, sm: 3 }, mt: { xs: 2, sm: 3 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
            Package Information
          </Typography>
          <Button
            variant="outlined"
            size="small"
            onClick={getPackageInformation}
            disabled={isLoadingPackages}
            startIcon={isLoadingPackages ? <CircularProgress size={16} /> : null}
          >
            Refresh
          </Button>
        </Box>
        <TableContainer>
          <Table sx={{ minWidth: 650 }} aria-label="package information table">
            <TableHead>
              <TableRow>
                <TableCell>Order Id</TableCell>
                <TableCell>Order Number</TableCell>
                <TableCell>Package Weight</TableCell>
                <TableCell>Package Height</TableCell>
                <TableCell>Package Width</TableCell>
                <TableCell>Package Length</TableCell>
                <TableCell>Timestamp</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoadingPackages ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <CircularProgress size={24} />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Loading package information...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : packageInformation.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary">
                      No package information available
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                packageInformation.map((pkg, index) => (
                  <TableRow key={pkg.id || index}>
                    <TableCell>{pkg.order_id || 'N/A'}</TableCell>
                    <TableCell>{pkg.order_number || 'N/A'}</TableCell>
                    <TableCell>{pkg.weight ? `${pkg.weight} kg` : 'N/A'}</TableCell>
                    <TableCell>{pkg.height ? `${pkg.height} cm` : 'N/A'}</TableCell>
                    <TableCell>{pkg.width ? `${pkg.width} cm` : 'N/A'}</TableCell>
                    <TableCell>{pkg.length ? `${pkg.length} cm` : 'N/A'}</TableCell>
                    <TableCell>
                      {pkg.timestamp ? new Date(pkg.timestamp).toLocaleString() : 'N/A'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

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
            position: 'relative',
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <IconButton
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              color: 'white',
              zIndex: 1000,
              backgroundColor: 'rgba(0,0,0,0.5)',
              '&:hover': {
                backgroundColor: 'rgba(0,0,0,0.7)',
              },
            }}
            onClick={() => setFullscreenOpen(false)}
          >
            <FullscreenExitIcon />
          </IconButton>
          
          {isStreaming ? (
            <img
              src={`${RASPI_SERVER}/camera/stream`}
              alt="Camera Stream"
              style={{
                maxWidth: '100%',
                maxHeight: '100%',
                objectFit: 'contain',
              }}
              onError={() => setError('Camera stream unavailable')}
            />
          ) : (
            <Box sx={{ textAlign: 'center', color: 'white' }}>
              <QrCodeScannerIcon sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h6">Camera not active</Typography>
            </Box>
          )}
        </Box>
      </Dialog>

      {/* History Modal */}
      <Dialog open={historyModalOpen} onClose={() => setHistoryModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          QR Scan History
          <Typography variant="body2" color="text.secondary">
            All scanned QR codes
          </Typography>
        </DialogTitle>
        <DialogContent>
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {qrHistory.map((qr, index) => (
              <React.Fragment key={`${qr.qr_data}-${qr.timestamp}-${index}`}>
                <ListItem>
                  <QrCodeIcon sx={{ mr: 2, color: isValidQR(qr) ? 'success.main' : 'error.main' }} />
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="body1">
                          {qr.qr_data}
                        </Typography>
                        {getQRStatusChip(qr)}
                        {qr.source === 'backend' && (
                          <Chip label="Stored" color="info" size="small" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {formatTimestamp(qr.timestamp)} • {qr.device || 'Unknown Device'}
                        </Typography>
                        {qr.validation_message && (
                          <Typography variant="caption" display="block" color="text.secondary">
                            {qr.validation_message}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < qrHistory.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryModalOpen(false)}>Close</Button>
          <Button onClick={getQRHistory} variant="outlined" disabled={isLoadingHistory}>
            Refresh
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
