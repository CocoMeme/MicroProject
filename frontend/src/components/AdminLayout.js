import React, { useState } from 'react';
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
<<<<<<< HEAD
<<<<<<< HEAD
  Toolbar,
=======
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
  Avatar,
  Badge,
  Menu,
  MenuItem,
  Tooltip,
  useMediaQuery,
  useTheme,
<<<<<<< HEAD
<<<<<<< HEAD
  Typography,
=======
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  LocalShipping as ShippingIcon,
  Inventory as InventoryIcon,
  Assessment as ReportsIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Person as PersonIcon,
  ChevronLeft as ChevronLeftIcon,
  ShoppingCart as OrdersIcon,
} from '@mui/icons-material';
<<<<<<< HEAD
import { Routes, Route, Navigate } from 'react-router-dom';
import AdminSidebar from './AdminSidebar';
=======
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  LocalShipping as ShippingIcon,
  Inventory as InventoryIcon,
  Assessment as ReportsIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Person as PersonIcon,
  ChevronLeft as ChevronLeftIcon,
  ShoppingCart as OrdersIcon,
} from '@mui/icons-material';
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
import Dashboard from '../pages/Dashboard';
import Parcels from '../pages/Parcels';
import Shipping from '../pages/Shipping';
import Reports from '../pages/Reports';
import Settings from '../pages/Settings';
import Orders from '../pages/Orders';
<<<<<<< HEAD
<<<<<<< HEAD
import Scanner from '../pages/Scanner';

const drawerWidth = 280;

=======

const drawerWidth = 280;

=======

const drawerWidth = 280;

>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/admin' },
  { text: 'Orders', icon: <OrdersIcon />, path: '/admin/orders' },
  { text: 'Parcels', icon: <InventoryIcon />, path: '/admin/parcels' },
  { text: 'Shipping', icon: <ShippingIcon />, path: '/admin/shipping' },
  { text: 'Reports', icon: <ReportsIcon />, path: '/admin/reports' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/admin/settings' },
];

<<<<<<< HEAD
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
export default function AdminLayout() {
  const [open, setOpen] = useState(true);
  const [anchorEl, setAnchorEl] = useState(null);
  const [notificationAnchor, setNotificationAnchor] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
<<<<<<< HEAD
<<<<<<< HEAD
=======
  const navigate = useNavigate();
  const location = useLocation();
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
  const navigate = useNavigate();
  const location = useLocation();
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  const handleProfileClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileClose = () => {
    setAnchorEl(null);
  };

  const handleNotificationClick = (event) => {
    setNotificationAnchor(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };

<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" sx={{ fontWeight: 600, color: theme.palette.primary.main }}>
          Admin Dashboard
        </Typography>
        {open && (
          <IconButton onClick={handleDrawerToggle} sx={{ display: { md: 'flex', lg: 'none' } }}>
            <ChevronLeftIcon />
          </IconButton>
        )}
      </Box>
      <List sx={{ flex: 1, px: 2 }}>
        {menuItems.map((item) => (
          <ListItemButton
            key={item.text}
            selected={location.pathname === item.path}
            onClick={() => navigate(item.path)}
            sx={{
              mb: 1,
              '&.Mui-selected': {
                '& .MuiListItemIcon-root': {
                  color: 'inherit',
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
        <Box sx={{ display: 'flex', alignItems: 'center', p: 1 }}>
          <Avatar sx={{ width: 32, height: 32, mr: 2 }}>
            <PersonIcon />
          </Avatar>
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              John Doe
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Administrator
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );

<<<<<<< HEAD
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${open ? drawerWidth : 0}px)` },
          ml: { md: `${open ? drawerWidth : 0}px` },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, color: 'text.primary' }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title="Notifications">
              <IconButton
                size="large"
                onClick={handleNotificationClick}
                sx={{ color: 'text.primary' }}
              >
                <Badge badgeContent={4} color="error">
                  <NotificationsIcon />
                </Badge>
              </IconButton>
            </Tooltip>
            <Tooltip title="Profile">
              <IconButton
                size="large"
                onClick={handleProfileClick}
                sx={{ color: 'text.primary' }}
              >
                <Avatar sx={{ width: 32, height: 32 }}>
                  <PersonIcon />
                </Avatar>
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

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
        {drawer}
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: 'background.default',
          marginTop: '64px',
        }}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/admin" replace />} />
          <Route path="" element={<Dashboard />} />
          <Route path="orders" element={<Orders />} />
<<<<<<< HEAD
<<<<<<< HEAD
          <Route path="scanner" element={<Scanner />} />
=======
>>>>>>> 5ee4dd2bd6d9e84866d9a58f5e54dfdb6ce6d359
=======
>>>>>>> parent of e909c783 (cam in webserver (no qr code yet))
          <Route path="parcels" element={<Parcels />} />
          <Route path="shipping" element={<Shipping />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Routes>
      </Box>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleProfileClose}
        sx={{ mt: 1 }}
      >
        <MenuItem onClick={handleProfileClose}>Profile</MenuItem>
        <MenuItem onClick={handleProfileClose}>My account</MenuItem>
        <MenuItem onClick={handleProfileClose}>Logout</MenuItem>
      </Menu>

      <Menu
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
        sx={{ mt: 1 }}
      >
        <MenuItem onClick={handleNotificationClose}>
          <Typography variant="subtitle2">New parcel arrived</Typography>
        </MenuItem>
        <MenuItem onClick={handleNotificationClose}>
          <Typography variant="subtitle2">Shipping route updated</Typography>
        </MenuItem>
        <MenuItem onClick={handleNotificationClose}>
          <Typography variant="subtitle2">System maintenance scheduled</Typography>
        </MenuItem>
      </Menu>
    </Box>
  );
} 