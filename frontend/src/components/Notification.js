import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  IconButton,
  Box,
  Typography,
  Paper,
  Slide,
  useTheme,
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

const SlideTransition = (props) => {
  return <Slide {...props} direction="down" />;
};

const CustomNotification = ({ 
  open, 
  message, 
  title, 
  severity = 'info', 
  duration = 5000, 
  onClose,
  action,
  persistent = false,
  type = 'normal' // 'normal' or 'system'
}) => {
  const [isOpen, setIsOpen] = useState(open);

  useEffect(() => {
    setIsOpen(open);
    
    // Handle auto-hide for non-persistent notifications
    if (open && !persistent && duration > 0) {
      const timer = setTimeout(() => {
        setIsOpen(false);
        if (onClose) onClose();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [open, persistent, duration, onClose]);

  const handleClose = (event, reason) => {
    if (reason === 'clickaway' && persistent) {
      return;
    }
    setIsOpen(false);
    if (onClose) onClose();
  };

  const getIcon = () => {
    switch (severity) {
      case 'success':
        return <SuccessIcon sx={{ fontSize: 20 }} />;
      case 'error':
        return <ErrorIcon sx={{ fontSize: 20 }} />;
      case 'warning':
        return <WarningIcon sx={{ fontSize: 20 }} />;
      default:
        return <InfoIcon sx={{ fontSize: 20 }} />;
    }
  };

  const getColors = () => {
    switch (severity) {
      case 'success':
        return {
          bg: '#f0f9f0', // Light green background
          border: '#4caf50', // Green border
          text: '#2e7d32', // Dark green text
        };
      case 'error':
        return {
          bg: '#fef5f5', // Light red background
          border: '#f44336', // Red border
          text: '#c62828', // Dark red text
        };
      case 'warning':
        return {
          bg: '#fff8e1', // Light amber background
          border: '#ff9800', // Orange border
          text: '#e65100', // Dark orange text
        };
      default:
        return {
          bg: '#e3f2fd', // Light blue background
          border: '#2196f3', // Blue border
          text: '#1565c0', // Dark blue text
        };
    }
  };

  const colors = getColors();

  // Special styling for system notifications
  const isSystemNotification = type === 'system';
  
  return (
    <Snackbar
      open={isOpen}
      autoHideDuration={null}
      onClose={handleClose}
      TransitionComponent={SlideTransition}
      anchorOrigin={{ 
        vertical: isSystemNotification ? 'top' : 'top', 
        horizontal: isSystemNotification ? 'center' : 'right' 
      }}
      sx={{ 
        '& .MuiSnackbar-root': {
          top: isSystemNotification ? '50px !important' : '24px !important',
        },
        zIndex: isSystemNotification ? 2000 : 1400,
      }}
    >
      <Paper
        elevation={isSystemNotification ? 8 : 3}
        sx={{
          minWidth: isSystemNotification ? 400 : 280,
          maxWidth: isSystemNotification ? 600 : 400,
          bgcolor: colors.bg,
          borderLeft: `${isSystemNotification ? 5 : 3}px solid ${colors.border}`,
          borderRadius: isSystemNotification ? 2 : 1,
          overflow: 'hidden',
          ...(isSystemNotification && {
            transform: 'scale(1.05)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: `2px solid ${colors.border}`,
            background: `linear-gradient(135deg, ${colors.bg} 0%, ${colors.bg}ee 100%)`,
          })
        }}
      >
        <Box sx={{ p: isSystemNotification ? 2.5 : 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
            <Box sx={{ 
              color: colors.text, 
              mt: 0.5,
              ...(isSystemNotification && {
                transform: 'scale(1.3)',
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
              })
            }}>
              {getIcon()}
            </Box>
            
            <Box sx={{ flex: 1, minWidth: 0 }}>
              {title && (
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: isSystemNotification ? 700 : 600,
                    color: colors.text,
                    mb: 0.5,
                    fontSize: isSystemNotification ? '1.1rem' : '0.9rem',
                    textShadow: isSystemNotification ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                  }}
                >
                  {title}
                </Typography>
              )}
              
              <Typography
                variant="body2"
                sx={{
                  color: colors.text,
                  fontSize: isSystemNotification ? '0.95rem' : '0.8rem',
                  lineHeight: 1.3,
                  whiteSpace: 'pre-line',
                  fontWeight: isSystemNotification ? 500 : 400,
                }}
              >
                {message}
              </Typography>
              
              {action && (
                <Box sx={{ mt: 1 }}>
                  {action}
                </Box>
              )}
            </Box>
            
            <IconButton
              size="small"
              onClick={handleClose}
              sx={{
                color: colors.text,
                opacity: 0.7,
                '&:hover': {
                  opacity: 1,
                  bgcolor: 'rgba(0, 0, 0, 0.04)',
                },
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </Paper>
    </Snackbar>
  );
};

// Notification Hook for easy usage
export const useNotification = () => {
  const [notifications, setNotifications] = useState([]);
  const [nextId, setNextId] = useState(1);

  const showNotification = ({
    message,
    title,
    severity = 'info',
    duration = 5000,
    persistent = false,
    action = null,
    type = 'normal'
  }) => {
    const id = nextId;
    setNextId(prev => prev + 1);
    
    // Check for duplicate notifications (same title and message)
    const isDuplicate = notifications.some(n => 
      n.title === title && n.message === message && n.severity === severity
    );
    
    if (isDuplicate) {
      console.log('Preventing duplicate notification:', { title, message });
      return null;
    }

    const newNotification = {
      id,
      message,
      title,
      severity,
      duration,
      persistent,
      action,
      type,
      open: true,
    };

    setNotifications(prev => [...prev, newNotification]);

    return id; // Return ID for manual removal
  };

  const hideNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const hideAllNotifications = () => {
    setNotifications([]);
  };

  // Clear notifications of specific type or title to prevent buildup
  const clearNotificationsBy = (criteria) => {
    setNotifications(prev => prev.filter(n => {
      if (criteria.title && n.title === criteria.title) return false;
      if (criteria.severity && n.severity === criteria.severity) return false;
      return true;
    }));
  };

  const NotificationContainer = () => (
    <>
      {notifications.map((notification) => (
        <CustomNotification
          key={notification.id}
          open={notification.open}
          message={notification.message}
          title={notification.title}
          severity={notification.severity}
          duration={notification.duration}
          persistent={notification.persistent}
          action={notification.action}
          type={notification.type}
          onClose={() => hideNotification(notification.id)}
        />
      ))}
    </>
  );

  return {
    showNotification,
    hideNotification,
    hideAllNotifications,
    clearNotificationsBy,
    NotificationContainer,
    notifications,
  };
};

export default CustomNotification;
