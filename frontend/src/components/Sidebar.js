import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Typography,
  Avatar,
  Tooltip,
  Badge,
  Divider,
} from '@mui/material';
import {
  Dashboard,
  LocalShipping,
  Assessment,
  Settings,
  Menu as MenuIcon,
  Notifications,
  ChevronLeft,
  ViewInAr,
  Speed,
  Group,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const drawerWidth = 280;

const menuItems = [
  { name: 'Dashboard', icon: <Dashboard />, path: '/' },
  { name: 'Package Sorting', icon: <ViewInAr />, path: '/sorting' },
  { name: 'Shipping', icon: <LocalShipping />, path: '/shipping' },
  { name: 'Performance', icon: <Speed />, path: '/performance' },
  { name: 'Reports', icon: <Assessment />, path: '/reports' },
  { name: 'Team', icon: <Group />, path: '/team' },
  { name: 'Settings', icon: <Settings />, path: '/settings' },
];

export default function Sidebar() {
  const [open, setOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  const ListItemComponent = ({ item }) => {
    const isActive = location.pathname === item.path;
    
    return (
      <ListItem disablePadding sx={{ mb: 0.5 }}>
        <ListItemButton
          onClick={() => navigate(item.path)}
          sx={{
            borderRadius: 2,
            mx: 1,
            backgroundColor: isActive ? 'rgba(37, 99, 235, 0.08)' : 'transparent',
            color: isActive ? 'primary.main' : 'text.secondary',
            '&:hover': {
              backgroundColor: isActive ? 'rgba(37, 99, 235, 0.12)' : 'rgba(0, 0, 0, 0.04)',
            },
          }}
        >
          <ListItemIcon sx={{ color: isActive ? 'primary.main' : 'text.secondary', minWidth: 40 }}>
            {item.icon}
          </ListItemIcon>
          <ListItemText 
            primary={item.name}
            primaryTypographyProps={{
              fontSize: '0.875rem',
              fontWeight: isActive ? 600 : 500,
            }}
          />
          {item.badge && (
            <Badge color="error" badgeContent={item.badge} sx={{ ml: 1 }} />
          )}
        </ListItemButton>
      </ListItem>
    );
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: open ? drawerWidth : 72,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: open ? drawerWidth : 72,
          boxSizing: 'border-box',
          borderRight: '1px solid',
          borderColor: 'grey.200',
          backgroundColor: 'background.paper',
          transition: 'width 0.3s ease',
          overflowX: 'hidden',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {open ? (
          <Typography variant="h6" sx={{ fontWeight: 600, color: 'primary.main' }}>
            PackageSort Pro
          </Typography>
        ) : (
          <Box sx={{ width: 32, height: 32 }}>
            <img src="/logo192.png" alt="Logo" style={{ width: '100%', height: '100%' }} />
          </Box>
        )}
        <IconButton onClick={handleDrawerToggle} size="small">
          {open ? <ChevronLeft /> : <MenuIcon />}
        </IconButton>
      </Box>

      <Box sx={{ px: 2, py: 1.5 }}>
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: 'grey.50',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <Avatar
            src="/avatar.jpg"
            alt="User Avatar"
            sx={{ width: 40, height: 40 }}
          />
          {open && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                John Doe
              </Typography>
              <Typography variant="caption" color="text.secondary">
                System Admin
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      <Divider sx={{ mx: 2, my: 1 }} />

      <List sx={{ px: 1 }}>
        {menuItems.map((item) => (
          <motion.div
            key={item.name}
            initial={false}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            <ListItemComponent item={item} />
          </motion.div>
        ))}
      </List>

      <Box sx={{ flexGrow: 1 }} />

      <Box sx={{ p: 2 }}>
        {open && (
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              bgcolor: 'primary.main',
              color: 'white',
              textAlign: 'center',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              Need Help?
            </Typography>
            <Typography variant="caption">
              Check our documentation or contact support
            </Typography>
          </Box>
        )}
      </Box>
    </Drawer>
  );
} 