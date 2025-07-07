import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
} from '@mui/icons-material';

const summaryData = [
  {
    title: 'Total Processed',
    value: '426',
    change: '+8.2%',
    trend: 'up',
  },
  {
    title: 'Delivery Success Rate',
    value: '94.5%',
    change: '+2.1%',
    trend: 'up',
  },
  {
    title: 'Average Processing Time',
    value: '2.3 hrs',
    change: '-12.5%',
    trend: 'down',
  },
  {
    title: 'Active Routes',
    value: '8',
    change: '0%',
    trend: 'neutral',
  },
];

const recentActivity = [
  { time: '09:45', event: 'Large batch processed', details: '45 parcels sorted to Zone B' },
  { time: '09:30', event: 'Route optimization completed', details: '3 routes adjusted' },
  { time: '09:15', event: 'System maintenance', details: 'Routine check completed' },
  { time: '09:00', event: 'Shift started', details: 'Morning shift began operations' },
];

export default function Reports() {
  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'up':
        return <TrendingUp sx={{ color: 'success.main' }} />;
      case 'down':
        return <TrendingDown sx={{ color: 'error.main' }} />;
      default:
        return null;
    }
  };

  return (
    <Box className="fade-in">
      <Typography variant="h4" sx={{ mb: 4, fontWeight: 600 }}>
        Reports
      </Typography>
      
      <Grid container spacing={3}>
        {/* Summary Cards */}
        {summaryData.map((item, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Paper className="hover-card" sx={{ p: 2 }}>
              <Typography color="text.secondary" variant="subtitle2">
                {item.title}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                <Typography variant="h4" component="div" sx={{ flexGrow: 1 }}>
                  {item.value}
                </Typography>
                {getTrendIcon(item.trend)}
              </Box>
              <Typography
                variant="body2"
                sx={{
                  color: item.trend === 'up' ? 'success.main' :
                    item.trend === 'down' ? 'error.main' : 'text.secondary',
                  mt: 1,
                }}
              >
                {item.change} from last period
              </Typography>
            </Paper>
          </Grid>
        ))}

        {/* Recent Activity Table */}
        <Grid item xs={12}>
          <TableContainer component={Paper} sx={{ mt: 3 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Event</TableCell>
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentActivity.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell>{row.time}</TableCell>
                    <TableCell>{row.event}</TableCell>
                    <TableCell>{row.details}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Box>
  );
} 