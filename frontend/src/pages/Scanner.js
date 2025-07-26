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
  Card,
  CardContent,
  Avatar,
  Fade,
  Grow,
  useTheme,
  useMediaQuery,
  LinearProgress,
  Stack,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import HistoryIcon from '@mui/icons-material/History';
import QrCodeIcon from '@mui/icons-material/QrCode';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import PackageIcon from '@mui/icons-material/Inventory';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import RefreshIcon from '@mui/icons-material/Refresh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
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
  const [successMessage, setSuccessMessage] = useState(null);
  const [status, setStatus] = useState({ online: false, camera_running: false });
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [packageData, setPackageData] = useState([]);
  const [isLoadingPackages, setIsLoadingPackages] = useState(false);
  
  // Modal states
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  // Responsive design
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));

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
    
    // Show success/status message based on QR validation
    if (data.validation) {
      if (data.validation.valid && !data.validation.already_scanned) {
        setSuccessMessage(`✅ ${data.qr_data} scanned successfully!`);
        setError(null);
        
        // Reset camera position after successful scan
        setTimeout(async () => {
          console.log('Resetting camera position after successful scan...'); // Debug log
          try {
            // Stop camera briefly
            if (wsConnected) {
              websocketService.stopCamera();
            } else {
              await fetch(`${RASPI_SERVER}/camera/stop`, { method: 'POST' });
            }
            
            // Wait for a short moment
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Restart camera to reset to initial position
            if (wsConnected) {
              websocketService.startCamera();
            } else {
              await fetch(`${RASPI_SERVER}/camera/start`, { method: 'POST' });
            }
            
            console.log('Camera reset completed'); // Debug log
          } catch (err) {
            console.error('Failed to reset camera:', err);
            // If reset fails, just ensure camera is running
            setIsStreaming(true);
          }
        }, 1000); // 1 second delay to show success message
        
      } else if (data.validation.already_scanned) {
        setSuccessMessage(`⚠️ ${data.qr_data} was already scanned`);
        setError(null);
      } else {
        setError(`❌ ${data.qr_data} not found in orders database`);
        setSuccessMessage(null);
      }
      
      // Clear messages after 5 seconds
      setTimeout(() => {
        setSuccessMessage(null);
        setError(null);
      }, 5000);
    }
    
    // Immediately refresh QR history when new scan is detected
    getQRHistory();
    
    // Also refresh package information to get latest sensor data
    getPackageInformation();
  }, [wsConnected]);

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
      
      // Get initial package information
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
      if (isStreaming) {
        historyInterval = setInterval(() => {
          getQRHistory();
          getPackageInformation();
        }, 5000); // Refresh both history and package info every 5 seconds
      }

      return () => {
        clearInterval(statusInterval);
        if (historyInterval) clearInterval(historyInterval);
        if (qrInterval) clearInterval(qrInterval);
      };
    }
  }, [wsConnected, isStreaming, handleCameraStatus, handleCameraError, handleQRDetected, handleQRHistoryUpdated, handleSystemStatus]);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(prev => ({
          ...prev,
          online: true,
          camera_running: data.camera_running,
          has_camera: data.has_camera,
          initialization_error: data.initialization_error
        }));
        setIsStreaming(data.camera_running);
      } else {
        setStatus(prev => ({ ...prev, online: false }));
      }
    } catch (err) {
      console.warn('Status check failed:', err);
      setStatus(prev => ({ ...prev, online: false }));
    }
  };

  const getQRHistory = async () => {
    setIsLoadingHistory(true);
    try {
      console.log('Fetching QR history...'); // Debug log
      const response = await fetch(`${BACKEND_SERVER}/api/qr-history`, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('QR history retrieved:', data); // Debug log
        
        // Combine frontend and backend histories
        const combinedHistory = [...(data.frontend_history || []), ...(data.backend_history || [])];
        
        // Sort by timestamp (latest first)
        combinedHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        // Remove duplicates based on order number - keep only the latest scan for each order
        const uniqueScans = new Map();
        const deduplicatedHistory = [];
        
        for (const scan of combinedHistory) {
          // Determine the order identifier (prefer order_number from validation, fallback to qr_data)
          const orderIdentifier = scan.validation?.order_number || scan.qr_data;
          
          // Only keep the first occurrence (which is the latest due to sorting)
          if (!uniqueScans.has(orderIdentifier)) {
            uniqueScans.set(orderIdentifier, true);
            deduplicatedHistory.push(scan);
          }
        }
        
        console.log('Final combined history (before deduplication):', combinedHistory); // Debug log
        console.log('Deduplicated history:', deduplicatedHistory); // Debug log
        const removedCount = combinedHistory.length - deduplicatedHistory.length;
        console.log(`Removed ${removedCount} duplicate scans`); // Debug log
        
        setQrHistory(deduplicatedHistory.slice(0, 20)); // Keep only latest 20 unique scans
        setLastRefresh(new Date()); // Update last refresh time
      } else {
        console.error('Failed to fetch QR history:', response.status);
      }
    } catch (err) {
      console.error('Failed to get QR history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const getPackageInformation = async () => {
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
        console.log('Package information retrieved:', data); // Debug log
        setPackageData(data.packages || []);
      } else {
        console.error('Failed to fetch package information:', response.status);
      }
    } catch (err) {
      console.error('Failed to get package information:', err);
    } finally {
      setIsLoadingPackages(false);
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
    <Box sx={{ 
      p: { xs: 2, md: 3 }, 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Fade in timeout={1000}>
        <Box>
          {/* Header Section */}
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            mb: 4,
            p: 3,
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            border: '1px solid rgba(255, 255, 255, 0.2)',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: { xs: 2, sm: 0 }
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ 
                bgcolor: 'primary.main', 
                mr: 2, 
                width: 56, 
                height: 56,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
              }}>
                <QrCodeScannerIcon sx={{ fontSize: 28 }} />
              </Avatar>
              <Box>
                <Typography variant="h3" sx={{ 
                  fontWeight: 700, 
                  color: 'white',
                  background: 'linear-gradient(45deg, #fff, #e3f2fd)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontSize: { xs: '1.8rem', md: '3rem' }
                }}>
                  QR Code Scanner
                </Typography>
                <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 1 }}>
                  Real-time order validation system
                </Typography>
              </Box>
            </Box>
            
            {/* Connection Status & Actions */}
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Tooltip title="Refresh data">
                <IconButton 
                  onClick={() => {
                    getQRHistory();
                    getPackageInformation();
                    checkStatus();
                  }}
                  sx={{ 
                    color: 'white',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.2)' }
                  }}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              
              {isConnecting && (
                <Chip 
                  icon={<CircularProgress size={16} />}
                  label="Connecting..." 
                  size="small" 
                  sx={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: 'white'
                  }}
                />
              )}
              <Chip
                icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                label={wsConnected ? 'WebSocket Ready' : 'HTTP Fallback'}
                color={wsConnected ? 'success' : 'warning'}
                size="small"
                sx={{ 
                  backgroundColor: wsConnected ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 152, 0, 0.1)',
                  backdropFilter: 'blur(10px)'
                }}
              />
              <Chip
                icon={status.online ? <CheckCircleIcon /> : <ErrorIcon />}
                label={status.online ? 'Pi Online' : 'Pi Offline'}
                color={status.online ? 'success' : 'error'}
                size="small"
                sx={{ 
                  backgroundColor: status.online ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)',
                  backdropFilter: 'blur(10px)'
                }}
              />
            </Stack>
          </Box>

          {/* Stats Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1000}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <QrCodeScannerIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {qrHistory.length}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Total Scans
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1200}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <CameraAltIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {isStreaming ? 'ON' : 'OFF'}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Camera Status
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1400}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <PackageIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {packageData.length}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Packages
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1600}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
                  color: '#333',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.2)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <CheckCircleIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {qrHistory.filter(scan => scan.validation?.valid && !scan.validation?.already_scanned).length}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Valid Scans
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            {/* Camera Feed Section */}
            <Grid item xs={12} lg={8}>
              <Grow in timeout={1800}>
                <Paper 
                  elevation={8}
                  sx={{ 
                    background: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: 3,
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    overflow: 'hidden',
                    p: 3
                  }}
                >
                  {/* Camera Header */}
                  <Box sx={{ 
                    mb: 3, 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    flexDirection: { xs: 'column', sm: 'row' },
                    gap: { xs: 2, sm: 1 }
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                        <CameraAltIcon />
                      </Avatar>
                      <Box>
                        <Typography variant="h5" sx={{ fontWeight: 600, color: 'primary.main' }}>
                          Live Camera Feed
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Auto-detection enabled
                        </Typography>
                      </Box>
                    </Box>
                    
                    {/* Camera Controls */}
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Button
                        variant={isStreaming ? "outlined" : "contained"}
                        color={isStreaming ? "error" : "success"}
                        size="small"
                        startIcon={isStreaming ? <StopIcon /> : <PlayArrowIcon />}
                        onClick={isStreaming ? stopCamera : startCamera}
                        sx={{ 
                          borderRadius: 2,
                          textTransform: 'none',
                          fontWeight: 600 
                        }}
                      >
                        {isStreaming ? 'Stop' : 'Start'}
                      </Button>
                      
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<HistoryIcon />}
                        onClick={() => setHistoryModalOpen(true)}
                        sx={{ 
                          borderRadius: 2,
                          textTransform: 'none',
                          fontWeight: 600 
                        }}
                      >
                        History
                      </Button>
                    </Stack>
                  </Box>

                  {/* Connection Status Alerts */}
                  {!wsConnected && (
                    <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
                      Using HTTP fallback mode - WebSocket connection unavailable
                    </Alert>
                  )}

                  {successMessage && (
                    <Alert 
                      severity="success" 
                      sx={{ mb: 2, borderRadius: 2 }}
                      icon={<CheckCircleIcon />}
                    >
                      {successMessage}
                    </Alert>
                  )}

                  {error && (
                    <Alert 
                      severity="error" 
                      sx={{ mb: 2, borderRadius: 2 }}
                      icon={<ErrorIcon />}
                    >
                      {error}
                    </Alert>
                  )}

                  {!status.online && (
                    <Alert 
                      severity="warning" 
                      sx={{ mb: 2, borderRadius: 2 }}
                      icon={<WarningIcon />}
                    >
                      Raspberry Pi server is offline
                    </Alert>
                  )}

                  {status.initialization_error && (
                    <Alert 
                      severity="error" 
                      sx={{ mb: 2, borderRadius: 2 }}
                      icon={<ErrorIcon />}
                    >
                      Camera initialization error: {status.initialization_error}
                    </Alert>
                  )}

                  {/* Camera Display */}
                  <Box
                    sx={{
                      width: '100%',
                      height: { xs: 300, sm: 400, md: 480 },
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      bgcolor: 'black',
                      position: 'relative',
                      borderRadius: 2,
                      overflow: 'hidden',
                      border: '2px solid',
                      borderColor: isStreaming ? 'success.main' : 'grey.400'
                    }}
                  >
                    {/* Fullscreen Button */}
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
                      <>
                        <img
                          src={`${RASPI_SERVER}/video_feed`}
                          alt="Camera Feed"
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'contain',
                          }}
                        />
                        {/* Active indicator */}
                        <Box sx={{
                          position: 'absolute',
                          bottom: 8,
                          left: 8,
                          display: 'flex',
                          alignItems: 'center',
                          bgcolor: 'rgba(76, 175, 80, 0.9)',
                          color: 'white',
                          px: 1,
                          py: 0.5,
                          borderRadius: 1,
                          fontSize: '0.75rem'
                        }}>
                          <Box sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            bgcolor: 'white',
                            mr: 1,
                            animation: 'pulse 2s infinite'
                          }} />
                          LIVE
                        </Box>
                      </>
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
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                          Click start to begin scanning
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grow>
            </Grid>

            {/* Scan History Section */}
            <Grid item xs={12} lg={4}>
              <Stack spacing={3}>
                {/* Latest Scans */}
                <Grow in timeout={2000}>
                  <Paper 
                    elevation={8}
                    sx={{ 
                      background: 'rgba(255, 255, 255, 0.95)',
                      backdropFilter: 'blur(20px)',
                      borderRadius: 3,
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      overflow: 'hidden',
                      height: { xs: 300, sm: 400, md: 480 },
                      display: 'flex',
                      flexDirection: 'column'
                    }}
                  >
                    <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Avatar sx={{ bgcolor: 'secondary.main', mr: 2, width: 32, height: 32 }}>
                            <HistoryIcon sx={{ fontSize: 18 }} />
                          </Avatar>
                          <Box>
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              Recent Scans
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Last {qrHistory.length} unique scans
                            </Typography>
                          </Box>
                        </Box>
                        {isLoadingHistory && <CircularProgress size={20} />}
                      </Box>
                    </Box>

                    <Box sx={{ 
                      flexGrow: 1, 
                      overflow: 'auto',
                      p: 1
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
                          <QrCodeScannerIcon sx={{ fontSize: 48, mb: 2, opacity: 0.3 }} />
                          <Typography variant="body2" align="center">
                            No scans detected yet
                          </Typography>
                          <Typography variant="caption" align="center" sx={{ mt: 1 }}>
                            Point a QR code at the camera
                          </Typography>
                        </Box>
                      ) : (
                        qrHistory.slice(0, 5).map((scan, index) => (
                          <Card key={index} sx={{ mb: 1, border: '1px solid', borderColor: 'divider' }}>
                            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                                <Chip
                                  label={
                                    scan.validation?.valid 
                                      ? (scan.validation?.already_scanned ? 'Duplicate' : 'Valid') 
                                      : 'Invalid'
                                  }
                                  color={
                                    scan.validation?.valid 
                                      ? (scan.validation?.already_scanned ? 'warning' : 'success')
                                      : 'error'
                                  }
                                  size="small"
                                />
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(scan.timestamp).toLocaleTimeString()}
                                </Typography>
                              </Box>
                              <Typography variant="body2" sx={{ 
                                fontFamily: 'monospace',
                                fontSize: '0.75rem',
                                wordBreak: 'break-all',
                                color: 'text.primary'
                              }}>
                                {scan.validation?.order_number || scan.qr_data}
                              </Typography>
                              {scan.validation?.customer_name && (
                                <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 0.5 }}>
                                  {scan.validation.customer_name}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        ))
                      )}
                    </Box>

                    {qrHistory.length > 5 && (
                      <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Button
                          variant="outlined"
                          fullWidth
                          size="small"
                          startIcon={<HistoryIcon />}
                          onClick={() => setHistoryModalOpen(true)}
                          sx={{ borderRadius: 2, textTransform: 'none' }}
                        >
                          View All ({qrHistory.length})
                        </Button>
                      </Box>
                    )}
                  </Paper>
                </Grow>
              </Stack>
            </Grid>
          </Grid>

          {/* Package Information Section - Full Width */}
          <Grid container spacing={3} sx={{ mt: 2 }}>
            <Grid item xs={12}>
              <Grow in timeout={2400}>
                <Paper 
                  elevation={8}
                  sx={{ 
                    background: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: 3,
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    overflow: 'hidden'
                  }}
                >
                  <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'info.main', mr: 2, width: 32, height: 32 }}>
                          <PackageIcon sx={{ fontSize: 18 }} />
                        </Avatar>
                        <Box>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            Package Data
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Sensor measurements and order details
                          </Typography>
                        </Box>
                      </Box>
                      {isLoadingPackages && <CircularProgress size={20} />}
                    </Box>
                  </Box>

                  {packageData.length > 0 ? (
                    <TableContainer sx={{ maxHeight: 400 }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow sx={{ backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
                            <TableCell sx={{ fontWeight: 600 }}>Order ID</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Size</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Length</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Width</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Height</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Time of Scan</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {packageData.map((pkg, index) => (
                            <TableRow key={index} sx={{ '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.02)' } }}>
                              <TableCell>
                                <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                                  {pkg.order_number || pkg.order_id || `PKG-${index + 1}`}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Chip 
                                  label={pkg.size || pkg.weight ? `${pkg.size || pkg.weight} kg` : 'N/A'} 
                                  size="small" 
                                  color={pkg.size || pkg.weight ? 'primary' : 'default'}
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="body2" color="text.secondary">
                                  {pkg.length ? `${pkg.length} cm` : 'N/A'}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="body2" color="text.secondary">
                                  {pkg.width ? `${pkg.width} cm` : 'N/A'}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="body2" color="text.secondary">
                                  {pkg.height ? `${pkg.height} cm` : 'N/A'}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="caption" color="text.secondary">
                                  {pkg.timestamp || pkg.scanned_at || pkg.time_of_scan 
                                    ? new Date(pkg.timestamp || pkg.scanned_at || pkg.time_of_scan).toLocaleString()
                                    : 'N/A'
                                  }
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Box sx={{ p: 4, textAlign: 'center' }}>
                      <PackageIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                        {isLoadingPackages ? 'Loading package data...' : 'No package data available'}
                      </Typography>
                      <Typography variant="body2" color="text.disabled">
                        Package information will appear here when orders are scanned
                      </Typography>
                    </Box>
                  )}
                </Paper>
              </Grow>
            </Grid>
          </Grid>
        </Box>
      </Fade>

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
            {/* Exit Fullscreen Button */}
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
        fullScreen={isSmallScreen}
        sx={{
          '& .MuiDialog-paper': {
            margin: { xs: 0, sm: 2 },
            width: { xs: '100%', sm: 'auto' },
            maxHeight: { xs: '100vh', sm: '90vh' },
            borderRadius: { xs: 0, sm: 3 }
          }
        }}
      >
        <DialogTitle sx={{ 
          pb: 1,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white'
        }}>
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
                                  maxWidth: isSmallScreen ? '150px' : '200px',
                                  maxHeight: isSmallScreen ? '150px' : '200px',
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
                            label={
                              scan.validation?.valid 
                                ? (scan.validation?.already_scanned ? 'Already Scanned' : 'Scanned Successfully') 
                                : 'Not Found'
                            }
                            color={
                              scan.validation?.valid 
                                ? (scan.validation?.already_scanned ? 'warning' : 'success')
                                : 'error'
                            }
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
          <Button 
            onClick={() => setHistoryModalOpen(false)} 
            variant="contained" 
            fullWidth={isSmallScreen}
            sx={{ borderRadius: 2 }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
        `}
      </style>
    </Box>
  );
}
