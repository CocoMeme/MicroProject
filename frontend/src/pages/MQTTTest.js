import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Alert,
  Card,
  CardContent,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import { 
  Refresh, 
  RestartAlt, 
  Wifi as WifiIcon, 
  WifiOff as WifiOffIcon,
  CheckCircle,
  Error as ErrorIcon,
  Warning 
} from '@mui/icons-material';
import ConnectionMonitor from '../components/ConnectionMonitor';
import ErrorBoundary from '../components/ErrorBoundary';
import raspberryPiWebSocketService from '../services/raspberryPiWebSocketService';

const RASPI_SERVER = 'http://192.168.100.63:5001'; // Your Raspberry Pi server

const MQTTTest = () => {
  const [mqttStatus, setMqttStatus] = useState(null);
  const [mqttMessages, setMqttMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [restarting, setRestarting] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // Initialize WebSocket connection
  useEffect(() => {
    const initializeWebSocket = async () => {
      setConnecting(true);
      try {
        await raspberryPiWebSocketService.connect(RASPI_SERVER);
        setWsConnected(true);
        
        // Set up event listeners for MQTT messages
        raspberryPiWebSocketService.on('mqtt_message', (data) => {
          console.log('Received MQTT message:', data);
          console.log('Message structure:', {
            topic: data.topic,
            message: data.message,
            timestamp: data.timestamp
          });
          
          setMqttMessages(prev => {
            const newMessage = {
              ...data,
              id: Date.now() + Math.random()
            };
            const newMessages = [...prev, newMessage];
            // Keep only last 50 messages
            return newMessages.slice(-50);
          });
        });

        raspberryPiWebSocketService.on('mqtt_status', (data) => {
          console.log('Received MQTT status:', data);
          setMqttStatus(data);
          setLastUpdate(new Date());
        });

        raspberryPiWebSocketService.on('system_status', (data) => {
          console.log('Received system status:', data);
          if (data.mqtt_system) {
            setMqttStatus(data.mqtt_system);
            setLastUpdate(new Date());
          }
        });

      } catch (error) {
        console.error('WebSocket connection failed:', error);
        setWsConnected(false);
        setError(`WebSocket connection failed: ${error.message}`);
      } finally {
        setConnecting(false);
      }
    };

    initializeWebSocket();

    return () => {
      // Cleanup listeners if needed
      raspberryPiWebSocketService.disconnect();
    };
  }, []);

  // Monitor WebSocket connection status
  useEffect(() => {
    const checkConnection = () => {
      const connected = raspberryPiWebSocketService.isConnectedToServer();
      setWsConnected(connected);
    };

    const interval = setInterval(checkConnection, 2000);
    return () => clearInterval(interval);
  }, []);

  // Fetch MQTT status from Raspberry Pi server
  const fetchMqttStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${RASPI_SERVER}/mqtt/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setMqttStatus(data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      console.error('Error fetching MQTT status:', err);
      setError(`Failed to connect to Raspberry Pi server: ${err.message}`);
      setMqttStatus(null);
    } finally {
      setLoading(false);
    }
  };

  // Restart MQTT listener
  const restartMqtt = async () => {
    try {
      setRestarting(true);
      const response = await fetch(`${RASPI_SERVER}/mqtt/restart`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setMqttStatus(data.status);
      setError(null);
      
      // Refresh status after restart
      setTimeout(() => {
        fetchMqttStatus();
      }, 2000);
      
    } catch (err) {
      console.error('Error restarting MQTT:', err);
      setError(`Failed to restart MQTT: ${err.message}`);
    } finally {
      setRestarting(false);
    }
  };

  // Auto-refresh MQTT status
  useEffect(() => {
    fetchMqttStatus();
    
    const interval = setInterval(() => {
      fetchMqttStatus();
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (connected) => {
    if (connected) {
      return <CheckCircle sx={{ color: 'success.main' }} />;
    }
    return <ErrorIcon sx={{ color: 'error.main' }} />;
  };

  const getStatusColor = (connected) => {
    return connected ? 'success' : 'error';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          MQTT Test & Monitoring
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Monitor and test MQTT communication with ESP32 devices on Raspberry Pi server
        </Typography>

        <Grid container spacing={3}>
          {/* Connection Status */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Connection Status
                </Typography>
                <ConnectionMonitor />
                <Divider sx={{ my: 2 }} />
                
                {error && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                  </Alert>
                )}

                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <Typography variant="body2">WebSocket:</Typography>
                  {connecting ? (
                    <Chip 
                      icon={<CircularProgress size={16} />} 
                      label="Connecting..." 
                      color="info" 
                      size="small" 
                    />
                  ) : wsConnected ? (
                    <Chip 
                      icon={<WifiIcon />} 
                      label="Connected" 
                      color="success" 
                      size="small" 
                    />
                  ) : (
                    <Chip 
                      icon={<WifiOffIcon />} 
                      label="Disconnected" 
                      color="error" 
                      size="small" 
                    />
                  )}
                </Box>

                {mqttStatus && (
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body2">MQTT:</Typography>
                    <Chip 
                      icon={getStatusIcon(mqttStatus.connected)}
                      label={mqttStatus.connected ? 'Connected' : 'Disconnected'} 
                      color={getStatusColor(mqttStatus.connected)}
                      size="small" 
                    />
                  </Box>
                )}

                {lastUpdate && (
                  <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                    Last updated: {formatTimestamp(lastUpdate)}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* MQTT Status Details */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    MQTT Server Status
                  </Typography>
                  <Box>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={fetchMqttStatus}
                      disabled={loading}
                      startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
                      sx={{ mr: 1 }}
                    >
                      Refresh
                    </Button>
                    <Button
                      variant="contained"
                      size="small"
                      onClick={restartMqtt}
                      disabled={restarting}
                      startIcon={restarting ? <CircularProgress size={16} /> : <RestartAlt />}
                      color="warning"
                    >
                      Restart MQTT
                    </Button>
                  </Box>
                </Box>

                {mqttStatus ? (
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell><strong>Status</strong></TableCell>
                        <TableCell>
                          <Chip 
                            label={mqttStatus.connected ? 'Connected' : 'Disconnected'}
                            color={getStatusColor(mqttStatus.connected)}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Broker</strong></TableCell>
                        <TableCell>{mqttStatus.broker_host}:{mqttStatus.broker_port}</TableCell>
                      </TableRow>
                      {mqttStatus.last_message && (
                        <TableRow>
                          <TableCell><strong>Last Message</strong></TableCell>
                          <TableCell>{formatTimestamp(mqttStatus.last_message)}</TableCell>
                        </TableRow>
                      )}
                      <TableRow>
                        <TableCell><strong>Subscribed Topics</strong></TableCell>
                        <TableCell>
                          {mqttStatus.subscribed_topics?.map((topic, index) => (
                            <Chip key={index} label={topic} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                          )) || 'esp32/#'}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                ) : (
                  <Alert severity="warning">
                    Unable to connect to MQTT server. Check if the Raspberry Pi server is running.
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* ESP32 Integration Info */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  ESP32 Integration
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Your MQTT system is configured to listen for ESP32 messages on the following topics:
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <Typography variant="subtitle2" color="primary" gutterBottom>
                        QR Scanning
                      </Typography>
                      <Typography variant="body2" fontFamily="monospace">
                        esp32/qr_scanned
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Payload: {"{"}"qr_code": "ORD-001234"{"}"} 
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <Typography variant="subtitle2" color="primary" gutterBottom>
                        Sensor Data
                      </Typography>
                      <Typography variant="body2" fontFamily="monospace">
                        esp32/sensor_data
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Payload: {"{"}"temperature": 25.6, "humidity": 60.2{"}"}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <Typography variant="subtitle2" color="primary" gutterBottom>
                        Device Status
                      </Typography>
                      <Typography variant="body2" fontFamily="monospace">
                        esp32/status
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Payload: {"{"}"status": "online", "device_id": "ESP32_001"{"}"}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Real-time MQTT Messages */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Real-time MQTT Messages
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Live messages received from MQTT broker via WebSocket
                </Typography>
                
                <Paper sx={{ maxHeight: 300, overflow: 'auto', bgcolor: 'grey.900', p: 2 }}>
                  {mqttMessages.length > 0 ? (
                    <List dense>
                      {mqttMessages.slice().reverse().map((message, index) => (
                        <ListItem key={index} sx={{ py: 0.5 }}>
                          <ListItemText
                            primary={
                              <Typography variant="body2" sx={{ color: 'common.white', fontFamily: 'monospace' }}>
                                [{formatTimestamp(message.timestamp)}] {message.topic} → {message.message}
                              </Typography>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" sx={{ color: 'grey.400', textAlign: 'center', py: 2 }}>
                      Waiting for MQTT messages...
                    </Typography>
                  )}
                </Paper>
              </CardContent>
            </Card>
          </Grid>

          {/* Implementation Notes */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Implementation Notes
                </Typography>
                <Typography variant="body2" paragraph>
                  Your MQTT system on the Raspberry Pi includes:
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="🚀 MQTT Listener Service"
                      secondary="Running on port 1883 with automatic reconnection"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="📨 Message Logging"
                      secondary="All MQTT messages are logged to mqtt_messages.log"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="🔌 WebSocket Integration"
                      secondary="Real-time message broadcasting to frontend clients"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="🔄 Auto-restart"
                      secondary="Automatic reconnection on connection loss"
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </ErrorBoundary>
  );
};

export default MQTTTest;
