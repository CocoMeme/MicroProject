import React from 'react';
import { Typography, Box } from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function ParcelChart({ data }) {
  if (!data || data.length === 0) return null;

  // Process data for visualization
  const zones = ['Zone A', 'Zone B', 'Zone C'];

  const zoneData = zones.map(zone => ({
    zone,
    small: data.filter(p => p.destination === zone && p.size === 'Small').length,
    medium: data.filter(p => p.destination === zone && p.size === 'Medium').length,
    large: data.filter(p => p.destination === zone && p.size === 'Large').length,
  }));

  const chartData = {
    labels: zones,
    datasets: [
      {
        label: 'Small',
        data: zoneData.map(z => z.small),
        backgroundColor: '#1976d2',
      },
      {
        label: 'Medium',
        data: zoneData.map(z => z.medium),
        backgroundColor: '#2e7d32',
      },
      {
        label: 'Large',
        data: zoneData.map(z => z.large),
        backgroundColor: '#ed6c02',
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: false,
      },
    },
    scales: {
      x: {
        stacked: true,
      },
      y: {
        stacked: true,
        beginAtZero: true,
        ticks: {
          stepSize: 1,
        },
      },
    },
  };

  return (
    <>
      <Typography component="h2" variant="h6" color="primary" gutterBottom>
        Parcel Distribution by Zone and Size
      </Typography>
      <Box sx={{ height: 300, mt: 2 }}>
        <Bar data={chartData} options={options} />
      </Box>
    </>
  );
}

export default ParcelChart; 