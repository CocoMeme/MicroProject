import React, { useState } from 'react';
import {
  Box,
  Drawer,
  IconButton,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon,
} from '@mui/icons-material';
import { Routes, Route, Navigate } from 'react-router-dom';
import AdminSidebar from './AdminSidebar';
import Dashboard from '../pages/Dashboard';
import Parcels from '../pages/Parcels';
import Shipping from '../pages/Shipping';
import Reports from '../pages/Reports';
import Settings from '../pages/Settings';
import Orders from '../pages/Orders';
import Scanner from '../pages/Scanner';
import MQTTTest from '../pages/MQTTTest';

const drawerWidth = 280;

export default function AdminLayout() {
  const [open, setOpen] = useState(true);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Drawer
        variant={isMobile ? 'temporary' : 'permanent'}
        open={open}
        onClose={handleDrawerToggle}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <AdminSidebar open={open} onDrawerToggle={handleDrawerToggle} />
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: 'background.default',
        }}
      >
        {/* Mobile menu toggle button */}
        <Box sx={{ display: { md: 'none' }, mb: 2 }}>
          <IconButton
            color="primary"
            onClick={handleDrawerToggle}
            sx={{ 
              backgroundColor: 'background.paper',
              boxShadow: 1,
              '&:hover': {
                backgroundColor: 'background.paper',
                boxShadow: 2,
              }
            }}
          >
            <MenuIcon />
          </IconButton>
        </Box>
        
        <Routes>
          <Route path="/" element={<Navigate to="/admin" replace />} />
          <Route path="" element={<Dashboard />} />
          <Route path="orders" element={<Orders />} />
          <Route path="scanner" element={<Scanner />} />
          <Route path="mqtt-test" element={<MQTTTest />} />
          <Route path="parcels" element={<Parcels />} />
          <Route path="shipping" element={<Shipping />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Routes>
      </Box>
    </Box>
  );
} 