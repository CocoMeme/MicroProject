import React from 'react';
import {
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  Chip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  DeviceThermostat as TempIcon,
  Water as HumidityIcon,
  Timer as TimerIcon,
} from '@mui/icons-material';

const getStatusIcon = (status) => {
  switch (status.toLowerCase()) {
    case 'running':
    case 'operational':
    case 'active':
    case 'connected':
    case 'healthy':
      return <CheckCircleIcon sx={{ color: '#2e7d32' }} />;
    case 'warning':
      return <WarningIcon sx={{ color: '#ed6c02' }} />;
    case 'error':
    case 'disconnected':
      return <ErrorIcon sx={{ color: '#d32f2f' }} />;
    default:
      return <CheckCircleIcon sx={{ color: '#2e7d32' }} />;
  }
};

function SystemStatus({ status }) {
  if (!status) return null;

  const mainComponents = [
    { label: 'Conveyor Belt', value: status.conveyor_belt },
    { label: 'Sorting Arms', value: status.sorting_arms },
    { label: 'Sensors', value: status.sensors },
    { label: 'ESP32 Connection', value: status.esp32_connection },
    { label: 'Raspberry Pi', value: status.raspberry_pi },
  ];

  return (
    <>
      <Typography component="h2" variant="h6" color="primary" gutterBottom>
        System Status
      </Typography>

      <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
        {mainComponents.map((item) => (
          <ListItem key={item.label}>
            <ListItemIcon>{getStatusIcon(item.value)}</ListItemIcon>
            <ListItemText primary={item.label} secondary={item.value} />
          </ListItem>
        ))}
      </List>

      <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Chip
          icon={<TempIcon />}
          label={`Temperature: ${status.temperature}°C`}
          color="primary"
          variant="outlined"
        />
        <Chip
          icon={<HumidityIcon />}
          label={`Humidity: ${status.humidity}%`}
          color="primary"
          variant="outlined"
        />
        <Chip
          icon={<TimerIcon />}
          label={`Uptime: ${status.uptime}`}
          color="primary"
          variant="outlined"
        />
      </Box>
    </>
  );
}

export default SystemStatus; 