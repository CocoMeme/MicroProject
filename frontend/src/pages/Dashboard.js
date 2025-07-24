import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  useTheme,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Print as PrintIcon,
  Camera as CameraIcon,
  Router as RouterIcon,
  Memory as MemoryIcon,
  Thermostat as ThermostatIcon,
} from '@mui/icons-material';
import { useNotification } from '../components/Notification';

export default function Dashboard() {
  const theme = useTheme();
  const { showNotification, hideNotification, clearNotificationsBy, NotificationContainer } = useNotification();
  const [raspiStatus, setRaspiStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [startingSystem, setStartingSystem] = useState(false);
  const [stoppingSystem, setStoppingSystem] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(0);

  // Fetch Raspberry Pi status
  const fetchRaspiStatus = async (showLoadingNotification = false) => {
    if (loading && showLoadingNotification) return; // Prevent duplicate refresh calls
    
    // Additional debouncing for manual refresh calls
    if (showLoadingNotification) {
      const now = Date.now();
      if (now - lastActionTime < 1000) return; // Prevent rapid manual refreshes
      setLastActionTime(now);
    }
    
    try {
      setLoading(true);
      
      if (showLoadingNotification) {
        // Clear existing status notifications
        clearNotificationsBy({ title: 'Refreshing Status' });
        clearNotificationsBy({ title: 'Status Updated' });
        clearNotificationsBy({ title: 'Connection Failed' });
        
        showNotification({
          title: 'Refreshing Status',
          message: 'Fetching latest system information...',
          severity: 'info',
          duration: 4000,
        });
      }
      
      const response = await fetch(`${process.env.REACT_APP_RASPI_BASE_URL}/status`);
      if (response.ok) {
        const data = await response.json();
        setRaspiStatus(data);
        setLastUpdated(new Date().toLocaleString());
        
        if (showLoadingNotification) {
          showNotification({
            title: 'Status Updated',
            message: 'System status refreshed successfully.',
            severity: 'success',
            duration: 5000,
          });
        }
      } else {
        throw new Error('Failed to fetch status');
      }
    } catch (error) {
      console.error('Error fetching Raspberry Pi status:', error);
      setRaspiStatus({ error: 'Connection failed' });
      setLastUpdated(new Date().toLocaleString());
      
      if (showLoadingNotification) {
        showNotification({
          title: 'Connection Failed',
          message: 'Unable to fetch system status. Please check connection.',
          severity: 'error',
          duration: 5000,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Start the motor system
  const startSystem = async () => {
    const now = Date.now();
    if (startingSystem || (now - lastActionTime < 2000)) return; // Prevent rapid clicks
    
    try {
      setStartingSystem(true);
      setLastActionTime(now);
      
      // Clear any existing system-related notifications
      clearNotificationsBy({ title: '🚀 Starting System' });
      clearNotificationsBy({ title: '🚀 System Started Successfully' });
      clearNotificationsBy({ title: '❌ System Start Failed' });
      
      // Show loading notification
      const loadingNotificationId = showNotification({
        title: '🚀 Starting System',
        message: 'Initializing motor system components...',
        severity: 'info',
        type: 'system',
        persistent: true,
      });
      
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/system/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      // Hide loading notification
      if (loadingNotificationId) {
        setTimeout(() => hideNotification(loadingNotificationId), 300);
      }

      if (response.ok) {
        console.log('✅ Motor system started successfully:', data);
        showNotification({
          title: '🚀 System Started Successfully',
          message: `${data.message || 'Motor system is now running and ready for operation'}`,
          severity: 'success',
          type: 'system',
          duration: 10000,
        });
      } else {
        console.error('❌ Failed to start motor system:', data);
        showNotification({
          title: '❌ System Start Failed',
          message: `${data.message || data.error || 'Unable to start system - please check system status'}`,
          severity: 'error',
          type: 'system',
          duration: 10000,
        });
      }
    } catch (error) {
      console.error('❌ Error starting motor system:', error);
      showNotification({
        title: '🔌 Connection Error (Start)',
        message: `${error.message || 'Unable to connect to system - check network connection'}`,
        severity: 'error',
        type: 'system',
        duration: 10000,
      });
    } finally {
      setStartingSystem(false);
    }
  };

  // Stop the motor system
  const stopSystem = async () => {
    const now = Date.now();
    if (stoppingSystem || (now - lastActionTime < 2000)) return; // Prevent rapid clicks
    
    try {
      setStoppingSystem(true);
      setLastActionTime(now);
      
      // Clear any existing system-related notifications
      clearNotificationsBy({ title: '🛑 Stopping System' });
      clearNotificationsBy({ title: '🛑 System Stopped Successfully' });
      clearNotificationsBy({ title: '⚠️ System Stop Failed' });
      
      // Show loading notification
      const loadingNotificationId = showNotification({
        title: '🛑 Stopping System',
        message: 'Safely shutting down motor system...',
        severity: 'info',
        type: 'system',
        persistent: true,
      });
      
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/system/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      // Hide loading notification
      if (loadingNotificationId) {
        setTimeout(() => hideNotification(loadingNotificationId), 300);
      }

      if (response.ok) {
        console.log('✅ Motor system stopped successfully:', data);
        showNotification({
          title: '🛑 System Stopped Successfully',
          message: `${data.message || 'Motor system has been safely shut down'}`,
          severity: 'success',
          type: 'system',
          duration: 10000,
        });
      } else {
        console.error('❌ Failed to stop motor system:', data);
        showNotification({
          title: '⚠️ System Stop Failed',
          message: `${data.message || data.error || 'Unable to stop system - manual intervention may be required'}`,
          severity: 'error',
          type: 'system',
          duration: 10000,
        });
      }
    } catch (error) {
      console.error('❌ Error stopping motor system:', error);
      showNotification({
        title: '🔌 Connection Error (Stop)',
        message: `${error.message || 'Unable to connect to system - check network connection'}`,
        severity: 'error',
        type: 'system',
        duration: 10000,
      });
    } finally {
      setStoppingSystem(false);
    }
  };

  // Fetch status on component mount and set up auto-refresh
  useEffect(() => {
    fetchRaspiStatus();
    const interval = setInterval(fetchRaspiStatus, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    if (status === 'available' || status === 'running' || status?.connected || status === 'online' || status === 'connected' || status === true) return 'success';
    if (status === 'unavailable' || status === 'error' || !status?.connected || status === 'offline' || status === 'disconnected' || status === false) return 'error';
    return 'warning';
  };

  const getStatusIcon = (type, status) => {
    const isGood = status === 'available' || status === 'running' || status?.connected || status === 'online' || status === 'connected' || status === true;
    const iconProps = { 
      fontSize: 'small', 
      sx: { color: isGood ? 'success.main' : 'error.main' }
    };

    switch (type) {
      case 'printer':
        return <PrintIcon {...iconProps} />;
      case 'camera':
        return <CameraIcon {...iconProps} />;
      case 'mqtt':
        return <RouterIcon {...iconProps} />;
      case 'cpu':
        return <MemoryIcon {...iconProps} />;
      case 'temperature':
        return <ThermostatIcon {...iconProps} />;
      default:
        return isGood ? <CheckCircleIcon {...iconProps} /> : <ErrorIcon {...iconProps} />;
    }
  };

  const controlButtons = [
    { 
      label: 'Start System', 
      icon: <PlayIcon />, 
      color: 'success',
      variant: 'contained',
      action: startSystem,
      loading: startingSystem
    },
    { 
      label: 'Stop System', 
      icon: <StopIcon />, 
      color: 'error',
      variant: 'contained',
      action: stopSystem,
      loading: stoppingSystem
    }
  ];

  return (
    <Box sx={{ padding: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 600 }}>
        <DashboardIcon sx={{ mr: 2, fontSize: 'inherit' }} />
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Top Row - Charts (Grid 1 and Grid 2) */}
        <Grid item xs={12} md={6}>
          <Paper 
            elevation={3}
            sx={{ 
              p: 3, 
              height: '350px',
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
            }}
          >
            <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
              Analytics Chart 1
            </Typography>
            
            <Box sx={{ 
              height: 'calc(100% - 60px)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              border: `2px dashed ${theme.palette.divider}`,
              borderRadius: 1,
              backgroundColor: theme.palette.grey[50]
            }}>
              <Box textAlign="center">
                <Typography variant="h6" color="text.secondary">
                  Chart 1
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  (Chart placeholder)
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper 
            elevation={3}
            sx={{ 
              p: 3, 
              height: '350px',
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5" sx={{ fontWeight: 500 }}>
                Master Control
              </Typography>
            </Box>
            
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 1,
              height: 'calc(100% - 60px)'
            }}>
              {controlButtons.map((button, index) => (
                <Button
                  key={index}
                  variant={button.variant}
                  color={button.color}
                  size="small"
                  startIcon={button.loading ? <CircularProgress size={16} /> : button.icon}
                  fullWidth
                  disabled={button.loading}
                  sx={{
                    flex: 1,
                    py: 1,
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    borderRadius: 2,
                    textTransform: 'none',
                    minHeight: '40px',
                    maxHeight: '50px',
                    '&:hover': {
                      transform: button.loading ? 'none' : 'translateY(-1px)',
                      boxShadow: button.loading ? 'none' : theme.shadows[3],
                    },
                    transition: 'all 0.2s ease-in-out',
                  }}
                  onClick={() => {
                    if (button.action && !button.loading) {
                      button.action();
                    } else if (!button.action && !button.loading) {
                      console.log(`${button.label} clicked`);
                    }
                  }}
                >
                  {button.loading ? 
                    (button.label === 'Start System' ? 'Starting...' : 
                     button.label === 'Stop System' ? 'Stopping...' : 
                     button.label) : 
                    button.label
                  }
                </Button>
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Bottom Row - Raspberry Pi Status (Grid 3) */}
        <Grid item xs={12}>
          <Paper 
            elevation={3}
            sx={{ 
              p: 3, 
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5" sx={{ fontWeight: 500 }}>
                Raspberry Pi Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {loading && <CircularProgress size={20} />}
                {lastUpdated && (
                  <Typography variant="caption" color="text.secondary">
                    Last updated: {lastUpdated}
                  </Typography>
                )}
              </Box>
            </Box>
            
            {raspiStatus?.error ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                Failed to connect to Raspberry Pi: {raspiStatus.error}
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {raspiStatus && Object.entries(raspiStatus).map(([key, value], index) => {
                  if (key === 'error') return null;
                  
                  const isSystemInfo = typeof value === 'object' && value !== null;
                  const displayValue = isSystemInfo ? JSON.stringify(value, null, 2) : String(value);
                  const status = isSystemInfo ? 
                    (value.connected !== undefined ? value.connected : 'unknown') : 
                    value;

                  return (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                      <Card sx={{ height: '100%', minHeight: '120px' }}>
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            {getStatusIcon(key.toLowerCase(), status)}
                            <Typography variant="h6" sx={{ ml: 1, textTransform: 'capitalize' }}>
                              {key.replace(/_/g, ' ')}
                            </Typography>
                          </Box>
                          
                          <Chip 
                            label={isSystemInfo ? 
                              (value.connected !== undefined ? 
                                (value.connected ? 'Connected' : 'Disconnected') : 
                                'Status Unknown'
                              ) : 
                              displayValue
                            }
                            color={getStatusColor(status)}
                            size="small"
                            sx={{ mb: 1 }}
                          />
                          
                          {isSystemInfo && (
                            <Typography variant="body2" color="text.secondary" sx={{ 
                              fontSize: '0.75rem',
                              fontFamily: 'monospace',
                              whiteSpace: 'pre-wrap',
                              maxHeight: '60px',
                              overflow: 'auto'
                            }}>
                              {Object.entries(value).map(([k, v]) => `${k}: ${v}`).join('\n')}
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
                
                {!raspiStatus && !loading && (
                  <Grid item xs={12}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center', py: 4 }}>
                        <Typography variant="h6" color="text.secondary">
                          No status data available
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Click "Refresh Data" to fetch the latest status
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}
              </Grid>
            )}
          </Paper>
        </Grid>
      </Grid>
      
      {/* Custom Notifications */}
      <NotificationContainer />
    </Box>
  );
}
