import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import {
  Inventory as InventoryIcon,
  CheckCircle as CheckCircleIcon,
  Pending as PendingIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';

const iconMap = {
  total: InventoryIcon,
  processed: CheckCircleIcon,
  pending: PendingIcon,
  rate: SpeedIcon,
};

const iconColors = {
  total: '#1976d2',
  processed: '#2e7d32',
  pending: '#ed6c02',
  rate: '#9c27b0',
};

function StatCard({ title, value, icon }) {
  const Icon = iconMap[icon] || InventoryIcon;
  const iconColor = iconColors[icon] || '#1976d2';

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        height: 140,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          position: 'absolute',
          right: -20,
          top: -20,
          opacity: 0.1,
          transform: 'rotate(15deg)',
        }}
      >
        <Icon sx={{ fontSize: 140, color: iconColor }} />
      </Box>
      
      <Typography
        component="h2"
        variant="h6"
        color="text.secondary"
        gutterBottom
      >
        {title}
      </Typography>
      
      <Typography
        component="p"
        variant="h3"
        sx={{
          mt: 2,
          color: iconColor,
          fontWeight: 'medium',
        }}
      >
        {value}
      </Typography>
    </Paper>
  );
}

export default StatCard; 