import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  PowerSettingsNew as PowerIcon,
} from '@mui/icons-material';

export default function Dashboard() {
  const theme = useTheme();

  const controlButtons = [
    { 
      label: 'Start System', 
      icon: <PlayIcon />, 
      color: 'success',
      variant: 'contained'
    },
    { 
      label: 'Stop System', 
      icon: <StopIcon />, 
      color: 'error',
      variant: 'contained'
    },
    { 
      label: 'Refresh Data', 
      icon: <RefreshIcon />, 
      color: 'primary',
      variant: 'contained'
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

      <Grid container spacing={4}>
        {/* First Grid - Charts Section */}
        <Grid item xs={12} md={8}>
          <Paper 
            elevation={3}
            sx={{ 
              p: 3, 
              height: '400px',
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
            }}
          >
            <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
              Analytics & Charts
            </Typography>
            
            <Grid container spacing={2} sx={{ height: 'calc(100% - 60px)' }}>
              <Grid item xs={12} sm={6}>
                <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" align="center">
                      Chart 1
                    </Typography>
                    <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                      (Chart placeholder)
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" align="center">
                      Chart 2
                    </Typography>
                    <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                      (Chart placeholder)
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" align="center">
                      Main Dashboard Chart
                    </Typography>
                    <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                      (Large chart placeholder)
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Second Grid - Master Control Buttons */}
        <Grid item xs={12} md={4}>
          <Paper 
            elevation={3}
            sx={{ 
              p: 3, 
              height: '400px',
              backgroundColor: theme.palette.background.paper,
              borderRadius: 2,
            }}
          >
            <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
              Master Control
            </Typography>
            
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 2,
              height: 'calc(100% - 60px)'
            }}>
              {controlButtons.map((button, index) => (
                <Button
                  key={index}
                  variant={button.variant}
                  color={button.color}
                  size="large"
                  startIcon={button.icon}
                  fullWidth
                  sx={{
                    flex: 1,
                    py: 2,
                    fontSize: '1rem',
                    fontWeight: 500,
                    borderRadius: 2,
                    textTransform: 'none',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: theme.shadows[4],
                    },
                    transition: 'all 0.2s ease-in-out',
                  }}
                  onClick={() => {
                    // Placeholder for future functionality
                    console.log(`${button.label} clicked`);
                  }}
                >
                  {button.label}
                </Button>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
