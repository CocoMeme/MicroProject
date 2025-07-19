import React, { useState } from 'react';
import {
  AppBar,
  Box,
  Toolbar,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Typography,
  InputBase,
  Tooltip,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
} from '@mui/material';
import {
  Notifications,
  Search,
  Person,
  ExitToApp,
  LocalShipping,
  Warning,
  CheckCircle,
} from '@mui/icons-material';
import { alpha } from '@mui/material/styles';

const notifications = [
  {
    id: 1,
    type: 'success',
    message: 'Route A completed successfully',
    time: '5 minutes ago',
    icon: <CheckCircle color="success" />,
  },
  {
    id: 2,
    type: 'warning',
    message: 'Zone B approaching capacity',
    time: '10 minutes ago',
    icon: <Warning color="warning" />,
  },
  {
    id: 3,
    type: 'info',
    message: 'New shipment arrived at Zone C',
    time: '15 minutes ago',
    icon: <LocalShipping color="info" />,
  },
];

export default function Header() {
  const [anchorEl, setAnchorEl] = useState(null);
  const [notificationEl, setNotificationEl] = useState(null);

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleNotificationMenuOpen = (event) => {
    setNotificationEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setNotificationEl(null);
  };

  return (
    <AppBar 
      position="fixed" 
      color="inherit" 
      elevation={0}
      sx={{
        borderBottom: '1px solid',
        borderColor: 'grey.200',
        backdropFilter: 'blur(8px)',
        backgroundColor: alpha('#fff', 0.9),
      }}
    >
      <Toolbar sx={{ justifyContent: 'flex-end' }}>
        <Box sx={{ flexGrow: 1 }} />

        {/* Search Bar */}
        <Box
          sx={{
            position: 'relative',
            borderRadius: 2,
            backgroundColor: (theme) => alpha(theme.palette.grey[100], 0.5),
            '&:hover': {
              backgroundColor: (theme) => alpha(theme.palette.grey[100], 0.8),
            },
            marginRight: 2,
            width: 'auto',
          }}
        >
          <Box sx={{ padding: '0 12px', height: '100%', position: 'absolute', display: 'flex', alignItems: 'center' }}>
            <Search sx={{ color: 'text.secondary' }} />
          </Box>
          <InputBase
            placeholder="Search packages, routes..."
            sx={{
              color: 'inherit',
              '& .MuiInputBase-input': {
                padding: '8px 8px 8px 40px',
                width: '20ch',
                '&:focus': {
                  width: '30ch',
                },
                transition: 'width 0.2s',
              },
            }}
          />
        </Box>

        {/* Notifications */}
        <Tooltip title="Notifications">
          <IconButton
            size="large"
            color="inherit"
            onClick={handleNotificationMenuOpen}
          >
            <Badge badgeContent={notifications.length} color="error">
              <Notifications />
            </Badge>
          </IconButton>
        </Tooltip>

        {/* Profile */}
        <Tooltip title="Account">
          <IconButton
            size="large"
            edge="end"
            onClick={handleProfileMenuOpen}
            color="inherit"
          >
            <Avatar
              sx={{ width: 32, height: 32 }}
              src="/avatar.jpg"
            />
          </IconButton>
        </Tooltip>

        {/* Profile Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          onClick={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          PaperProps={{
            sx: {
              mt: 1.5,
              borderRadius: 2,
              minWidth: 200,
            },
          }}
        >
          <MenuItem>
            <Person sx={{ mr: 2 }} /> Profile
          </MenuItem>
          <Divider />
          <MenuItem sx={{ color: 'error.main' }}>
            <ExitToApp sx={{ mr: 2 }} /> Logout
          </MenuItem>
        </Menu>

        {/* Notifications Menu */}
        <Menu
          anchorEl={notificationEl}
          open={Boolean(notificationEl)}
          onClose={handleMenuClose}
          onClick={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          PaperProps={{
            sx: {
              mt: 1.5,
              borderRadius: 2,
              minWidth: 360,
            },
          }}
        >
          <Box sx={{ p: 2, pb: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Notifications
            </Typography>
          </Box>
          <List sx={{ p: 0 }}>
            {notifications.map((notification) => (
              <ListItem 
                key={notification.id}
                sx={{
                  py: 1.5,
                  px: 2,
                  '&:hover': {
                    backgroundColor: 'grey.50',
                  },
                }}
              >
                <ListItemAvatar>
                  {notification.icon}
                </ListItemAvatar>
                <ListItemText
                  primary={notification.message}
                  secondary={notification.time}
                  primaryTypographyProps={{
                    variant: 'body2',
                    fontWeight: 500,
                  }}
                  secondaryTypographyProps={{
                    variant: 'caption',
                  }}
                />
              </ListItem>
            ))}
          </List>
          <Divider />
          <Box sx={{ p: 1 }}>
            <MenuItem sx={{ borderRadius: 1 }}>
              <Typography
                variant="body2"
                sx={{ fontWeight: 500, textAlign: 'center', width: '100%' }}
              >
                View All Notifications
              </Typography>
            </MenuItem>
          </Box>
        </Menu>
      </Toolbar>
    </AppBar>
  );
} 