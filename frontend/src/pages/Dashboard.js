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
  Avatar,
  LinearProgress,
  Fade,
  Grow,
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
  Speed as SpeedIcon,
  TrendingUp as TrendingIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
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
      
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://10.194.125.225:5000/api'}/system/start`, {
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

  // Stop all systems
  const stopSystem = async () => {
    const now = Date.now();
    if (stoppingSystem || (now - lastActionTime < 2000)) return; // Prevent rapid clicks
    
    try {
      setStoppingSystem(true);
      setLastActionTime(now);
      
      // Clear any existing system-related notifications
      clearNotificationsBy({ title: '🛑 Stopping All Systems' });
      clearNotificationsBy({ title: '🛑 All Systems Stopped Successfully' });
      clearNotificationsBy({ title: '⚠️ System Stop Failed' });
      
      // Show loading notification
      const loadingNotificationId = showNotification({
        title: '🛑 Stopping All Systems',
        message: 'Emergency stop - Shutting down all MQTT systems...',
        severity: 'warning',
        type: 'system',
        persistent: true,
      });
      
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://10.194.125.225:5000/api'}/system/stop`, {
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
        console.log('✅ All systems stopped successfully:', data);
        showNotification({
          title: '🛑 All Systems Stopped Successfully',
          message: `${data.message || 'All MQTT systems have been safely shut down'}`,
          severity: 'success',
          type: 'system',
          duration: 12000,
        });
      } else {
        console.error('❌ Failed to stop all systems:', data);
        showNotification({
          title: '⚠️ System Stop Failed',
          message: `${data.message || data.error || 'Unable to stop systems - manual intervention may be required'}`,
          severity: 'error',
          type: 'system',
          duration: 15000,
        });
      }
    } catch (error) {
      console.error('❌ Error stopping all systems:', error);
      showNotification({
        title: '🔌 Connection Error (Emergency Stop)',
        message: `${error.message || 'Unable to connect to system - check network connection'}`,
        severity: 'error',
        type: 'system',
        duration: 15000,
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
      label: 'Emergency Stop', 
      icon: <StopIcon />, 
      color: 'error',
      variant: 'contained',
      action: stopSystem,
      loading: stoppingSystem
    }
  ];

  return (
    <Box sx={{ padding: 3, minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Fade in timeout={1000}>
        <Box>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            mb: 4, 
            p: 3,
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <Avatar sx={{ 
              bgcolor: 'primary.main', 
              mr: 2, 
              width: 56, 
              height: 56,
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
            }}>
              <DashboardIcon sx={{ fontSize: 28 }} />
            </Avatar>
            <Box>
              <Typography variant="h3" sx={{ 
                fontWeight: 700, 
                color: 'white',
                background: 'linear-gradient(45deg, #fff, #e3f2fd)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                System Dashboard
              </Typography>
              <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 1 }}>
                Monitor and control your QR scanning system
              </Typography>
            </Box>
          </Box>

          <Grid container spacing={3}>
            {/* System Metrics Row */}
            <Grid item xs={12} md={3}>
              <Grow in timeout={1000}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  height: '160px',
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
                  <CardContent sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <SpeedIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        98%
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        System Health
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={98} 
                        sx={{ 
                          mt: 1, 
                          backgroundColor: 'rgba(255, 255, 255, 0.3)',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: '#4caf50'
                          }
                        }} 
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} md={3}>
              <Grow in timeout={1200}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  color: 'white',
                  height: '160px',
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
                  <CardContent sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <TrendingIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        156
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Scans Today
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>
                        +12% from yesterday
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} md={3}>
              <Grow in timeout={1400}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  color: 'white',
                  height: '160px',
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
                  <CardContent sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <AssessmentIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        24h
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Uptime
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>
                        System running smoothly
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} md={3}>
              <Grow in timeout={1600}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
                  color: '#333',
                  height: '160px',
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
                  <CardContent sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <PrintIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        42
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Prints Today
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>
                        Thermal printer active
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            {/* Master Control Panel */}
            <Grid item xs={12} md={8}>
              <Grow in timeout={1800}>
                <Paper 
                  elevation={8}
                  sx={{ 
                    p: 4, 
                    height: '400px',
                    background: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: 3,
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    position: 'relative',
                    overflow: 'hidden',
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)',
                      backdropFilter: 'blur(10px)',
                    }
                  }}
                >
                  <Box sx={{ position: 'relative', zIndex: 1, height: '100%' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 48, height: 48 }}>
                          <SettingsIcon />
                        </Avatar>
                        <Box>
                          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
                            Master Control Panel
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            System operations and monitoring
                          </Typography>
                        </Box>
                      </Box>
                      {loading && <CircularProgress size={24} />}
                    </Box>
                    
                    <Grid container spacing={3} sx={{ height: 'calc(100% - 100px)' }}>
                      {controlButtons.map((button, index) => (
                        <Grid item xs={12} sm={6} key={index}>
                          <Button
                            variant={button.variant}
                            color={button.color}
                            size="large"
                            startIcon={button.loading ? <CircularProgress size={20} /> : button.icon}
                            fullWidth
                            disabled={button.loading}
                            sx={{
                              height: '80px',
                              fontSize: '1.1rem',
                              fontWeight: 600,
                              borderRadius: 3,
                              textTransform: 'none',
                              background: button.color === 'success' 
                                ? 'linear-gradient(135deg, #4caf50 0%, #81c784 100%)'
                                : 'linear-gradient(135deg, #f44336 0%, #e57373 100%)',
                              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
                              '&:hover': {
                                transform: button.loading ? 'none' : 'translateY(-2px)',
                                boxShadow: button.loading ? 'none' : '0 8px 30px rgba(0, 0, 0, 0.15)',
                              },
                              transition: 'all 0.3s ease-in-out',
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
                              (button.label === 'Start System' ? 'Starting System...' : 
                               button.label === 'Emergency Stop' ? 'Stopping All Systems...' : 
                               button.label) : 
                              button.label
                            }
                          </Button>
                        </Grid>
                      ))}
                      
                      {/* Quick Actions */}
                      <Grid item xs={12}>
                        <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(0, 0, 0, 0.02)', borderRadius: 2 }}>
                          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                            Quick Actions
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Chip 
                              icon={<CameraIcon />} 
                              label="Camera Status" 
                              variant="outlined" 
                              size="small"
                              sx={{ borderRadius: 2 }}
                            />
                            <Chip 
                              icon={<PrintIcon />} 
                              label="Printer Ready" 
                              variant="outlined" 
                              size="small"
                              sx={{ borderRadius: 2 }}
                            />
                            <Chip 
                              icon={<RouterIcon />} 
                              label="Network OK" 
                              variant="outlined" 
                              size="small"
                              sx={{ borderRadius: 2 }}
                            />
                          </Box>
                        </Box>
                      </Grid>
                    </Grid>
                  </Box>
                </Paper>
              </Grow>
            </Grid>

            {/* System Status Panel */}
            <Grid item xs={12} md={4}>
              <Grow in timeout={2000}>
                <Paper 
                  elevation={8}
                  sx={{ 
                    p: 4, 
                    height: '400px',
                    background: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: 3,
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    position: 'relative',
                    overflow: 'hidden',
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)',
                      backdropFilter: 'blur(10px)',
                    }
                  }}
                >
                  <Box sx={{ position: 'relative', zIndex: 1, height: '100%' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'success.main', mr: 2, width: 48, height: 48 }}>
                          <CheckCircleIcon />
                        </Avatar>
                        <Box>
                          <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
                            System Status
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Real-time monitoring
                          </Typography>
                        </Box>
                      </Box>
                      {loading && <CircularProgress size={20} />}
                      {lastUpdated && (
                        <Typography variant="caption" color="text.secondary">
                          {lastUpdated}
                        </Typography>
                      )}
                    </Box>
                    
                    {raspiStatus?.error ? (
                      <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
                        Failed to connect: {raspiStatus.error}
                      </Alert>
                    ) : (
                      <Box sx={{ height: 'calc(100% - 80px)', overflowY: 'auto' }}>
                        {raspiStatus && Object.entries(raspiStatus).map(([key, value], index) => {
                          if (key === 'error') return null;
                          
                          const isSystemInfo = typeof value === 'object' && value !== null;
                          const status = isSystemInfo ? 
                            (value.connected !== undefined ? value.connected : 'unknown') : 
                            value;

                          return (
                            <Card key={index} sx={{ mb: 2, backgroundColor: 'rgba(0, 0, 0, 0.02)', border: 'none' }}>
                              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    {getStatusIcon(key.toLowerCase(), status)}
                                    <Typography variant="subtitle2" sx={{ ml: 1, textTransform: 'capitalize', fontWeight: 600 }}>
                                      {key.replace(/_/g, ' ')}
                                    </Typography>
                                  </Box>
                                  
                                  <Chip 
                                    label={isSystemInfo ? 
                                      (value.connected !== undefined ? 
                                        (value.connected ? 'Online' : 'Offline') : 
                                        'Unknown'
                                      ) : 
                                      String(value)
                                    }
                                    color={getStatusColor(status)}
                                    size="small"
                                    sx={{ borderRadius: 2, fontWeight: 500 }}
                                  />
                                </Box>
                                
                                {isSystemInfo && (
                                  <Typography variant="caption" color="text.secondary" sx={{ 
                                    mt: 1,
                                    display: 'block',
                                    fontFamily: 'monospace',
                                    fontSize: '0.7rem'
                                  }}>
                                    {Object.entries(value).slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                                  </Typography>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })}
                        
                        {!raspiStatus && !loading && (
                          <Card sx={{ textAlign: 'center', py: 4, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
                            <CardContent>
                              <Typography variant="h6" color="text.secondary">
                                No Status Data
                              </Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                System information unavailable
                              </Typography>
                            </CardContent>
                          </Card>
                        )}
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grow>
            </Grid>
          </Grid>
        </Box>
      </Fade>
      
      {/* Custom Notifications */}
      <NotificationContainer />
    </Box>
  );
}
