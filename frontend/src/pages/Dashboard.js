import React, { useState } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Paper,
  Divider,
  Switch,
  Chip
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Power as PowerIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const Dashboard = () => {
  const [systemStatus, setSystemStatus] = useState({
    main: true,
    sorting: false,
    camera: true,
    mqtt: true,
    database: true
  });

  // Enhanced sample chart data with more realistic values
  const barChartData = {
    labels: ['Zone A', 'Zone B', 'Zone C', 'Zone D', 'Zone E'],
    datasets: [
      {
        label: 'Packages Processed Today',
        data: [145, 123, 98, 167, 134],
        backgroundColor: [
          'rgba(37, 99, 235, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(239, 68, 68, 0.8)'
        ],
        borderColor: [
          'rgb(37, 99, 235)',
          'rgb(16, 185, 129)',
          'rgb(245, 158, 11)',
          'rgb(139, 92, 246)',
          'rgb(239, 68, 68)'
        ],
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      },
    ],
  };

  const lineChartData = {
    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
    datasets: [
      {
        label: 'Processing Rate (packages/hour)',
        data: [12, 19, 35, 58, 45, 38, 15],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 3,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8,
      },
      {
        label: 'Target Rate',
        data: [40, 40, 40, 40, 40, 40, 40],
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0,
        fill: false,
        pointRadius: 0,
      },
    ],
  };

  const doughnutData = {
    labels: ['Small Packages', 'Medium Packages', 'Large Packages', 'Extra Large'],
    datasets: [
      {
        data: [45, 35, 15, 5],
        backgroundColor: [
          '#3b82f6',
          '#8b5cf6',
          '#f59e0b',
          '#ef4444'
        ],
        borderColor: [
          '#1e40af',
          '#7c3aed',
          '#d97706',
          '#dc2626'
        ],
        borderWidth: 3,
        hoverOffset: 10,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12,
            family: 'Inter, sans-serif'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
      }
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
            family: 'Inter, sans-serif'
          }
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          font: {
            size: 11,
            family: 'Inter, sans-serif'
          }
        }
      }
    }
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12,
            family: 'Inter, sans-serif'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
      }
    },
    cutout: '60%',
    elements: {
      arc: {
        borderWidth: 3,
      }
    }
  };

  const handleSystemToggle = (system) => {
    setSystemStatus(prev => ({
      ...prev,
      [system]: !prev[system]
    }));
  };

  const handleControlAction = (action) => {
    console.log(`Executing action: ${action}`);
    // Add your control logic here
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <DashboardIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" fontWeight="bold">
          System Dashboard
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Left Grid - Charts */}
        <Grid item xs={12} md={6}>
          <Paper 
            elevation={3} 
            sx={{ 
              p: 3, 
              height: 'fit-content',
              background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)'
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <AssessmentIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h5" fontWeight="bold">
                Analytics Dashboard
              </Typography>
            </Box>

            {/* Package Distribution Chart */}
            <Card sx={{ mb: 3, boxShadow: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Package Distribution by Zone
                  </Typography>
                  <Chip label="Live Data" color="success" size="small" />
                </Box>
                <Box sx={{ height: 300 }}>
                  <Bar data={barChartData} options={chartOptions} />
                </Box>
              </CardContent>
            </Card>

            {/* Processing Rate Chart */}
            <Card sx={{ mb: 3, boxShadow: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Processing Rate (24h)
                  </Typography>
                  <Chip label="Real-time" color="primary" size="small" />
                </Box>
                <Box sx={{ height: 250 }}>
                  <Line data={lineChartData} options={chartOptions} />
                </Box>
              </CardContent>
            </Card>

            {/* Package Size Distribution */}
            <Card sx={{ boxShadow: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Package Size Distribution
                  </Typography>
                  <Chip label="Today" color="warning" size="small" />
                </Box>
                <Box sx={{ height: 250, display: 'flex', justifyContent: 'center' }}>
                  <Doughnut data={doughnutData} options={doughnutOptions} />
                </Box>
              </CardContent>
            </Card>
          </Paper>
        </Grid>

        {/* Right Grid - Master Control */}
        <Grid item xs={12} md={6}>
          <Paper 
            elevation={3} 
            sx={{ 
              p: 3, 
              height: 'fit-content',
              background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)'
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <SettingsIcon sx={{ mr: 2, color: 'secondary.main' }} />
              <Typography variant="h5" fontWeight="bold">
                Master Control Panel
              </Typography>
            </Box>

            {/* System Status */}
            <Card sx={{ mb: 3, boxShadow: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Status
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {Object.entries(systemStatus).map(([system, status]) => (
                    <Box key={system} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body1" sx={{ textTransform: 'capitalize', mr: 2 }}>
                          {system === 'mqtt' ? 'MQTT Service' : `${system} System`}
                        </Typography>
                        <Chip 
                          label={status ? 'Online' : 'Offline'} 
                          color={status ? 'success' : 'error'}
                          size="small"
                        />
                      </Box>
                      <Switch 
                        checked={status} 
                        onChange={() => handleSystemToggle(system)}
                        color="primary"
                      />
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>

            {/* Control Buttons */}
            <Card sx={{ boxShadow: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Master Controls
                </Typography>
                <Divider sx={{ mb: 3 }} />
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      color="success"
                      fullWidth
                      size="large"
                      startIcon={<PlayArrowIcon />}
                      onClick={() => handleControlAction('start')}
                      sx={{ 
                        py: 2,
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        boxShadow: 3,
                        '&:hover': { boxShadow: 6 }
                      }}
                    >
                      Start System
                    </Button>
                  </Grid>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      color="error"
                      fullWidth
                      size="large"
                      startIcon={<StopIcon />}
                      onClick={() => handleControlAction('stop')}
                      sx={{ 
                        py: 2,
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        boxShadow: 3,
                        '&:hover': { boxShadow: 6 }
                      }}
                    >
                      Stop System
                    </Button>
                  </Grid>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      color="primary"
                      fullWidth
                      size="large"
                      startIcon={<RefreshIcon />}
                      onClick={() => handleControlAction('restart')}
                      sx={{ 
                        py: 2,
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        boxShadow: 3,
                        '&:hover': { boxShadow: 6 }
                      }}
                    >
                      Restart
                    </Button>
                  </Grid>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      color="warning"
                      fullWidth
                      size="large"
                      startIcon={<PowerIcon />}
                      onClick={() => handleControlAction('emergency')}
                      sx={{ 
                        py: 2,
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        boxShadow: 3,
                        '&:hover': { boxShadow: 6 }
                      }}
                    >
                      Emergency
                    </Button>
                  </Grid>
                  <Grid item xs={12}>
                    <Button
                      variant="outlined"
                      color="secondary"
                      fullWidth
                      size="large"
                      startIcon={<TrendingUpIcon />}
                      onClick={() => handleControlAction('calibrate')}
                      sx={{ 
                        py: 2,
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        borderWidth: 2,
                        '&:hover': { borderWidth: 2 }
                      }}
                    >
                      System Calibration
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card sx={{ mt: 3, boxShadow: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Statistics
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 2 }}>
                      <Typography variant="h4" fontWeight="bold" color="white">
                        143
                      </Typography>
                      <Typography variant="body2" color="white">
                        Total Packages
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 2 }}>
                      <Typography variant="h4" fontWeight="bold" color="white">
                        98%
                      </Typography>
                      <Typography variant="body2" color="white">
                        Success Rate
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 2 }}>
                      <Typography variant="h4" fontWeight="bold" color="white">
                        5.2s
                      </Typography>
                      <Typography variant="body2" color="white">
                        Avg Process Time
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'error.light', borderRadius: 2 }}>
                      <Typography variant="h4" fontWeight="bold" color="white">
                        2
                      </Typography>
                      <Typography variant="body2" color="white">
                        Active Errors
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;
