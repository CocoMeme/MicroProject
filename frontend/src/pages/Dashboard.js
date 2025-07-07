import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  IconButton,
  LinearProgress,
} from '@mui/material';
import {
  LocalShipping,
  Inventory,
  Speed,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';

const StatCard = ({ title, value, icon, color, progress }) => (
  <Card className="hover-card">
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box
            sx={{
              backgroundColor: `${color}15`,
              borderRadius: '8px',
              p: 1,
              mr: 2,
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {icon}
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              {value}
            </Typography>
          </Box>
        </Box>
        <IconButton size="small">
          <MoreVertIcon />
        </IconButton>
      </Box>
      {progress && (
        <Box sx={{ width: '100%' }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: `${color}15`,
              '& .MuiLinearProgress-bar': {
                backgroundColor: color,
              },
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {progress}% of daily goal
          </Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

export default function Dashboard() {
  const stats = [
    {
      title: 'Total Parcels',
      value: '1,284',
      icon: <Inventory sx={{ color: '#2563eb' }} />,
      color: '#2563eb',
      progress: 75,
    },
    {
      title: 'Active Shipments',
      value: '342',
      icon: <LocalShipping sx={{ color: '#7c3aed' }} />,
      color: '#7c3aed',
      progress: 68,
    },
    {
      title: 'System Performance',
      value: '98.2%',
      icon: <Speed sx={{ color: '#10b981' }} />,
      color: '#10b981',
      progress: 98,
    },
  ];

  return (
    <Box className="fade-in">
      <Typography variant="h4" sx={{ mb: 4, fontWeight: 600 }}>
        Dashboard
      </Typography>
      <Grid container spacing={3}>
        {stats.map((stat, index) => (
          <Grid item xs={12} md={4} key={index}>
            <StatCard {...stat} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
} 