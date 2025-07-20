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
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  PowerSettingsNew as PowerIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Print as PrintIcon,
  Camera as CameraIcon,
  Router as RouterIcon,
  Memory as MemoryIcon,
  Thermostat as ThermostatIcon,
} from '@mui/icons-material';

export default function Dashboard() {
  const theme = useTheme();
  const [raspiStatus, setRaspiStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [startingSystem, setStartingSystem] = useState(false);
  const [stoppingSystem, setStoppingSystem] = useState(false);

  // Fetch Raspberry Pi status
  const fetchRaspiStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${process.env.REACT_APP_RASPI_BASE_URL}/status`);
      if (response.ok) {
        const data = await response.json();
        setRaspiStatus(data);
        setLastUpdated(new Date().toLocaleString());
      } else {
        throw new Error('Failed to fetch status');
      }
    } catch (error) {
      console.error('Error fetching Raspberry Pi status:', error);
      setRaspiStatus({ error: 'Connection failed' });
      setLastUpdated(new Date().toLocaleString());
    } finally {
      setLoading(false);
    }
  };

  // Start the motor system
  const startSystem = async () => {
    try {
      setStartingSystem(true);
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/system/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok) {
        console.log('✅ Motor system started successfully:', data);
        alert(`Motor system started successfully!\n${data.message}`);
      } else {
        console.error('❌ Failed to start motor system:', data);
        alert(`Failed to start motor system:\n${data.message || data.error}`);
      }
    } catch (error) {
      console.error('❌ Error starting motor system:', error);
      alert(`Error starting motor system:\n${error.message}`);
    } finally {
      setStartingSystem(false);
    }
  };

  // Stop the motor system
  const stopSystem = async () => {
    try {
      setStoppingSystem(true);
      const response = await fetch(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/system/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok) {
        console.log('✅ Motor system stopped successfully:', data);
        alert(`Motor system stopped successfully!\n${data.message}`);
      } else {
        console.error('❌ Failed to stop motor system:', data);
        alert(`Failed to stop motor system:\n${data.message || data.error}`);
      }
    } catch (error) {
      console.error('❌ Error stopping motor system:', error);
      alert(`Error stopping motor system:\n${error.message}`);
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
    },
    { 
      label: 'Refresh Data', 
      icon: <RefreshIcon />, 
      color: 'primary',
      variant: 'contained',
      action: fetchRaspiStatus
    },
    { 
      label: 'System Settings', 
      icon: <SettingsIcon />, 
      color: 'secondary',
      variant: 'contained'
    },
    { 
      label: 'Power Control', 
      icon: <PowerIcon />, 
      color: 'warning',
      variant: 'contained'
    },
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
    </Box>
  );
}
