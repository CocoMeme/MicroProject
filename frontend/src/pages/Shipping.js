import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Grid,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  LocalShipping,
  LocationOn,
  Schedule,
  Warning,
  Person,
  Sort,
  FilterList,
  Refresh,
  Speed,
  LocalShippingOutlined,
  MoreVert,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from '@mui/lab';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

// Sample sorting zones data
const sortingZones = [
  { id: 'Z1', name: 'Zone A', capacity: 100, current: 65, status: 'Operational' },
  { id: 'Z2', name: 'Zone B', capacity: 80, current: 75, status: 'Near Capacity' },
  { id: 'Z3', name: 'Zone C', capacity: 120, current: 40, status: 'Operational' },
  { id: 'Z4', name: 'Zone D', capacity: 90, current: 88, status: 'Critical' },
];

// Sample routes data with sorting zone information
const sampleRoutes = [
  {
    id: 'RT001',
    name: 'Route A',
    destination: 'Warehouse 1',
    status: 'Active',
    parcels: 15,
    estimatedTime: '2 hours',
    distance: '25 km',
    driver: 'John Doe',
    sortingZone: 'Zone A',
    efficiency: 92,
    timeline: [
      { time: '08:00', status: 'Sorting Started', completed: true },
      { time: '08:30', status: 'Loading', completed: true },
      { time: '09:00', status: 'In Transit', completed: false },
      { time: '11:00', status: 'Delivery', completed: false },
    ],
  },
  {
    id: 'RT002',
    name: 'Route B',
    destination: 'Distribution Center',
    status: 'In Transit',
    parcels: 8,
    estimatedTime: '1.5 hours',
    distance: '18 km',
    driver: 'Jane Smith',
    sortingZone: 'Zone B',
    efficiency: 88,
    timeline: [
      { time: '09:00', status: 'Sorting Started', completed: true },
      { time: '09:30', status: 'Loading', completed: true },
      { time: '10:00', status: 'In Transit', completed: true },
      { time: '11:30', status: 'Delivery', completed: false },
    ],
  },
  {
    id: 'RT003',
    name: 'Route C',
    destination: 'Local Hub',
    status: 'Delayed',
    parcels: 12,
    estimatedTime: '3 hours',
    distance: '30 km',
    driver: 'Mike Johnson',
    sortingZone: 'Zone C',
    efficiency: 75,
    timeline: [
      { time: '10:00', status: 'Sorting Started', completed: true },
      { time: '10:45', status: 'Loading', completed: false },
      { time: '11:30', status: 'In Transit', completed: false },
      { time: '13:00', status: 'Delivery', completed: false },
    ],
  },
];

// Performance data for the chart
const performanceData = [
  { name: 'Zone A', efficiency: 92, capacity: 65, throughput: 85 },
  { name: 'Zone B', efficiency: 88, capacity: 75, throughput: 70 },
  { name: 'Zone C', efficiency: 75, capacity: 40, throughput: 60 },
  { name: 'Zone D', efficiency: 95, capacity: 88, throughput: 90 },
];

function ZoneStatusCard({ zone }) {
  const getStatusColor = (status, current, capacity) => {
    const percentage = (current / capacity) * 100;
    if (percentage > 90) return 'error';
    if (percentage > 75) return 'warning';
    return 'success';
  };

  const statusColor = getStatusColor(zone.status, zone.current, zone.capacity);
  const percentage = Math.round((zone.current / zone.capacity) * 100);

  return (
    <Card
      component={motion.div}
      whileHover={{ y: -4 }}
      sx={{
        height: '100%',
        background: 'linear-gradient(145deg, #ffffff 0%, #f5f5f5 100%)',
        boxShadow: '0 4px 20px 0 rgba(0,0,0,0.1)',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">{zone.name}</Typography>
          <Chip
            label={zone.status}
            color={statusColor}
            size="small"
            sx={{ fontWeight: 500 }}
          />
        </Box>
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">Capacity Usage</Typography>
            <Typography variant="body2" color="text.primary">{percentage}%</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={percentage}
            color={statusColor}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
        <Typography variant="body2" color="text.secondary">
          {zone.current} / {zone.capacity} packages
        </Typography>
      </CardContent>
    </Card>
  );
}

function ShippingCard({ route, onEdit }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'success';
      case 'in transit':
        return 'primary';
      case 'delayed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Card
      component={motion.div}
      whileHover={{ y: -4 }}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(145deg, #ffffff 0%, #f5f5f5 100%)',
        boxShadow: '0 4px 20px 0 rgba(0,0,0,0.1)',
      }}
    >
      <CardContent>
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="div">
            {route.name}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={route.status}
              color={getStatusColor(route.status)}
              size="small"
              sx={{ fontWeight: 500 }}
            />
            <IconButton
              size="small"
              onClick={(e) => setAnchorEl(e.currentTarget)}
            >
              <MoreVert fontSize="small" />
            </IconButton>
          </Box>
        </Box>

        <Timeline sx={{ m: 0, p: 0 }}>
          {route.timeline.map((item, index) => (
            <TimelineItem key={index} sx={{ minHeight: 40 }}>
              <TimelineSeparator>
                <TimelineDot color={item.completed ? 'success' : 'grey'} />
                {index < route.timeline.length - 1 && <TimelineConnector />}
              </TimelineSeparator>
              <TimelineContent>
                <Typography variant="body2" component="span">
                  {item.time}
                </Typography>
                <Typography variant="caption" display="block" color="text.secondary">
                  {item.status}
                </Typography>
              </TimelineContent>
            </TimelineItem>
          ))}
        </Timeline>

        <Box sx={{ mt: 2 }}>
          <Tooltip title="Sorting Zone">
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <LocalShippingOutlined sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                {route.sortingZone} • {route.parcels} parcels
              </Typography>
            </Box>
          </Tooltip>

          <Tooltip title="Efficiency Score">
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Speed sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                {route.efficiency}% efficiency
              </Typography>
            </Box>
          </Tooltip>
        </Box>
      </CardContent>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem onClick={() => {
          onEdit(route);
          setAnchorEl(null);
        }}>
          Edit Route
        </MenuItem>
        <MenuItem onClick={() => setAnchorEl(null)}>View Details</MenuItem>
        <Divider />
        <MenuItem onClick={() => setAnchorEl(null)} sx={{ color: 'error.main' }}>
          Report Issue
        </MenuItem>
      </Menu>
    </Card>
  );
}

export default function Shipping() {
  const [routes, setRoutes] = useState(sampleRoutes);
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    destination: '',
    driver: '',
    parcels: '',
    distance: '',
    estimatedTime: '',
    sortingZone: '',
  });

  const handleOpenDialog = (route = null) => {
    if (route) {
      setSelectedRoute(route);
      setFormData({
        name: route.name,
        destination: route.destination,
        driver: route.driver,
        parcels: route.parcels,
        distance: route.distance,
        estimatedTime: route.estimatedTime,
        sortingZone: route.sortingZone,
      });
    } else {
      setSelectedRoute(null);
      setFormData({
        name: '',
        destination: '',
        driver: '',
        parcels: '',
        distance: '',
        estimatedTime: '',
        sortingZone: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedRoute(null);
  };

  const handleSubmit = () => {
    if (selectedRoute) {
      setRoutes(routes.map(r =>
        r.id === selectedRoute.id
          ? { ...r, ...formData }
          : r
      ));
    } else {
      const newRoute = {
        id: `RT${Math.floor(Math.random() * 1000)}`,
        ...formData,
        status: 'Active',
        efficiency: 100,
        timeline: [
          { time: new Date().toLocaleTimeString(), status: 'Created', completed: true },
          { time: '--:--', status: 'Sorting', completed: false },
          { time: '--:--', status: 'Loading', completed: false },
          { time: '--:--', status: 'Delivery', completed: false },
        ],
      };
      setRoutes([...routes, newRoute]);
    }
    handleCloseDialog();
  };

  return (
    <Box className="fade-in" sx={{ pb: 4 }}>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>
            Package Sorting & Shipping
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<FilterList />}
              sx={{ borderRadius: 2 }}
            >
              Filter
            </Button>
            <Button
              variant="outlined"
              startIcon={<Sort />}
              sx={{ borderRadius: 2 }}
            >
              Sort
            </Button>
            <Button
              variant="contained"
              startIcon={<LocalShipping />}
              onClick={() => handleOpenDialog()}
              sx={{ borderRadius: 2 }}
            >
              New Route
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Sorting Zones Overview */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 500 }}>
        Sorting Zones Status
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {sortingZones.map((zone) => (
          <Grid item xs={12} sm={6} md={3} key={zone.id}>
            <ZoneStatusCard zone={zone} />
          </Grid>
        ))}
      </Grid>

      {/* Performance Chart */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Zone Performance</Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={performanceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <RechartsTooltip />
            <Bar dataKey="efficiency" fill="#2563eb" name="Efficiency %" />
            <Bar dataKey="capacity" fill="#7c3aed" name="Capacity %" />
            <Bar dataKey="throughput" fill="#059669" name="Throughput %" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Active Routes */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" sx={{ fontWeight: 500 }}>
          Active Routes
        </Typography>
        <Tooltip title="Refresh Data">
          <IconButton>
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        <AnimatePresence>
          {routes.map((route) => (
            <Grid item xs={12} sm={6} md={4} key={route.id}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <ShippingCard route={route} onEdit={handleOpenDialog} />
              </motion.div>
            </Grid>
          ))}
        </AnimatePresence>
      </Grid>

      {/* Add/Edit Route Dialog */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {selectedRoute ? 'Edit Route' : 'Add New Route'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Route Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            <TextField
              fullWidth
              label="Destination"
              value={formData.destination}
              onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
            />
            <TextField
              fullWidth
              label="Driver"
              value={formData.driver}
              onChange={(e) => setFormData({ ...formData, driver: e.target.value })}
            />
            <TextField
              fullWidth
              label="Number of Parcels"
              type="number"
              value={formData.parcels}
              onChange={(e) => setFormData({ ...formData, parcels: e.target.value })}
            />
            <TextField
              fullWidth
              label="Sorting Zone"
              select
              value={formData.sortingZone}
              onChange={(e) => setFormData({ ...formData, sortingZone: e.target.value })}
            >
              {sortingZones.map((zone) => (
                <MenuItem key={zone.id} value={zone.name}>
                  {zone.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              fullWidth
              label="Distance"
              value={formData.distance}
              onChange={(e) => setFormData({ ...formData, distance: e.target.value })}
            />
            <TextField
              fullWidth
              label="Estimated Time"
              value={formData.estimatedTime}
              onChange={(e) => setFormData({ ...formData, estimatedTime: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2, pt: 0 }}>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            color="primary"
          >
            {selectedRoute ? 'Update Route' : 'Add Route'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
} 