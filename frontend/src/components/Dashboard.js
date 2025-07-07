import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Box,
  CircularProgress,
} from '@mui/material';
import axios from 'axios';
import StatCard from './StatCard';
import SystemStatus from './SystemStatus';
import RecentParcels from './RecentParcels';
import ParcelChart from './ParcelChart';

const API_BASE_URL = 'http://localhost:5000/api';

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [recentParcels, setRecentParcels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashboardRes, statusRes, parcelsRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/dashboard`),
          axios.get(`${API_BASE_URL}/system-status`),
          axios.get(`${API_BASE_URL}/recent-parcels`),
        ]);

        setDashboardData(dashboardRes.data);
        setSystemStatus(statusRes.data);
        setRecentParcels(parcelsRes.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Stats Overview */}
        <Grid item xs={12} md={3}>
          <StatCard
            title="Total Parcels"
            value={dashboardData?.total_parcels || 0}
            icon="total"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Processed Today"
            value={dashboardData?.processed_today || 0}
            icon="processed"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Pending Parcels"
            value={dashboardData?.pending_parcels || 0}
            icon="pending"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Sorting Rate"
            value={`${dashboardData?.sorting_rate || 0}/hr`}
            icon="rate"
          />
        </Grid>

        {/* System Status */}
        <Grid item xs={12} md={4}>
          <Paper 
            sx={{ 
              p: 2, 
              display: 'flex', 
              flexDirection: 'column', 
              height: 400,
              transition: 'transform 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
              },
            }}
          >
            <SystemStatus status={systemStatus} />
          </Paper>
        </Grid>

        {/* Parcel Chart */}
        <Grid item xs={12} md={8}>
          <Paper 
            sx={{ 
              p: 2, 
              display: 'flex', 
              flexDirection: 'column', 
              height: 400,
              transition: 'transform 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
              },
            }}
          >
            <ParcelChart data={recentParcels} />
          </Paper>
        </Grid>

        {/* Recent Parcels */}
        <Grid item xs={12}>
          <Paper 
            sx={{ 
              p: 2, 
              display: 'flex', 
              flexDirection: 'column',
              transition: 'transform 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
              },
            }}
          >
            <RecentParcels parcels={recentParcels} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard; 