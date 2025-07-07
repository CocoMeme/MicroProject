import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Switch,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  FormControl,
  Select,
  MenuItem,
  Button,
  Alert,
  Snackbar,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';

export default function Settings() {
  const [settings, setSettings] = useState({
    notifications: true,
    autoOptimize: true,
    darkMode: false,
    refreshInterval: '5',
    language: 'en',
    timezone: 'UTC',
    sortingSpeed: 'medium',
    maintenanceMode: false,
  });

  const [showSaveSuccess, setShowSaveSuccess] = useState(false);

  const handleChange = (setting) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setSettings({ ...settings, [setting]: value });
  };

  const handleSave = () => {
    setShowSaveSuccess(true);
  };

  const systemSettings = [
    {
      title: 'Notifications',
      description: 'Enable system notifications',
      type: 'switch',
      value: settings.notifications,
      key: 'notifications',
    },
    {
      title: 'Auto-Optimize Routes',
      description: 'Automatically optimize delivery routes',
      type: 'switch',
      value: settings.autoOptimize,
      key: 'autoOptimize',
    },
    {
      title: 'Dark Mode',
      description: 'Enable dark mode interface',
      type: 'switch',
      value: settings.darkMode,
      key: 'darkMode',
    },
    {
      title: 'Refresh Interval',
      description: 'Data refresh interval (minutes)',
      type: 'select',
      value: settings.refreshInterval,
      key: 'refreshInterval',
      options: [
        { value: '1', label: '1 minute' },
        { value: '5', label: '5 minutes' },
        { value: '15', label: '15 minutes' },
        { value: '30', label: '30 minutes' },
      ],
    },
    {
      title: 'Language',
      description: 'Interface language',
      type: 'select',
      value: settings.language,
      key: 'language',
      options: [
        { value: 'en', label: 'English' },
        { value: 'es', label: 'Spanish' },
        { value: 'fr', label: 'French' },
        { value: 'de', label: 'German' },
      ],
    },
    {
      title: 'Timezone',
      description: 'System timezone',
      type: 'select',
      value: settings.timezone,
      key: 'timezone',
      options: [
        { value: 'UTC', label: 'UTC' },
        { value: 'EST', label: 'Eastern Time' },
        { value: 'CST', label: 'Central Time' },
        { value: 'PST', label: 'Pacific Time' },
      ],
    },
  ];

  return (
    <Box className="fade-in">
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Settings
        </Typography>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
        >
          Save Changes
        </Button>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <List>
          {systemSettings.map((setting, index) => (
            <React.Fragment key={setting.key}>
              <ListItem sx={{ py: 2 }}>
                <ListItemText
                  primary={setting.title}
                  secondary={setting.description}
                />
                <ListItemSecondaryAction>
                  {setting.type === 'switch' ? (
                    <Switch
                      edge="end"
                      checked={settings[setting.key]}
                      onChange={handleChange(setting.key)}
                    />
                  ) : setting.type === 'select' ? (
                    <FormControl sx={{ minWidth: 120 }}>
                      <Select
                        value={settings[setting.key]}
                        onChange={handleChange(setting.key)}
                        size="small"
                      >
                        {setting.options.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : null}
                </ListItemSecondaryAction>
              </ListItem>
              {index < systemSettings.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </List>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          System Information
        </Typography>
        <List dense>
          <ListItem>
            <ListItemText
              primary="Version"
              secondary="1.0.0"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Last Updated"
              secondary="2024-01-15 09:00 AM"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Server Status"
              secondary="Operational"
            />
          </ListItem>
        </List>
      </Paper>

      <Snackbar
        open={showSaveSuccess}
        autoHideDuration={3000}
        onClose={() => setShowSaveSuccess(false)}
      >
        <Alert
          onClose={() => setShowSaveSuccess(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          Settings saved successfully!
        </Alert>
      </Snackbar>
    </Box>
  );
} 