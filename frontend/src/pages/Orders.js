import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  CircularProgress,
  Alert,
  Snackbar,
  Button,
  Stack,
  Chip,
  useTheme,
  useMediaQuery,
  Card,
  CardContent,
  Grid,
  Avatar,
  Fade,
  Grow,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import { 
  QrCode2 as QrCodeIcon, 
  Print as PrintIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  ShoppingCart as OrdersIcon,
  Person as PersonIcon,
  AttachMoney as MoneyIcon,
  CalendarToday as CalendarIcon,
  Phone as PhoneIcon,
  Email as EmailIcon,
  LocationOn as LocationIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import axios from 'axios';
import raspberryPiWebSocketService from '../services/raspberryPiWebSocketService';

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  // Responsive design
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));

  // WebSocket and printing states
  const [wsConnected, setWsConnected] = useState(false);
  const [connectingWs, setConnectingWs] = useState(false);
  const [printingOrders, setPrintingOrders] = useState(new Set());

  // Initialize WebSocket connection
  useEffect(() => {
    const initializeWebSocket = async () => {
      setConnectingWs(true);
      try {
        await raspberryPiWebSocketService.connect();
        setWsConnected(true);
        
        // Set up event listeners
        raspberryPiWebSocketService.on('print_status', handlePrintStatus);
        raspberryPiWebSocketService.on('print_success', handlePrintSuccess);
        raspberryPiWebSocketService.on('print_error', handlePrintError);
        
      } catch (error) {
        console.warn('WebSocket connection failed, will use HTTP fallback:', error);
        setWsConnected(false);
      } finally {
        setConnectingWs(false);
      }
    };

    initializeWebSocket();

    // Cleanup
    return () => {
      raspberryPiWebSocketService.off('print_status', handlePrintStatus);
      raspberryPiWebSocketService.off('print_success', handlePrintSuccess);
      raspberryPiWebSocketService.off('print_error', handlePrintError);
    };
  }, []);

  // WebSocket event handlers
  const handlePrintStatus = (data) => {
    console.log('Print status:', data.message);
  };

  const handlePrintSuccess = (data) => {
    setPrintingOrders(prev => {
      const newSet = new Set(prev);
      newSet.delete(data.order_number);
      return newSet;
    });

    setSnackbar({
      open: true,
      message: `QR code printed successfully for order ${data.order_number}`,
      severity: 'success'
    });

    setTimeout(() => {
      window.location.reload();
    }, 1000);
  };

  const handlePrintError = (data) => {
    setPrintingOrders(prev => {
      const newSet = new Set(prev);
      newSet.delete(data.order_number);
      return newSet;
    });
    
    setSnackbar({
      open: true,
      message: data.error || 'Failed to print QR code',
      severity: 'error'
    });
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/orders`);
      setOrders(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching orders:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load orders. Please try again later.',
        severity: 'error'
      });
      setLoading(false);
    }
  };

  const handlePrintQRCode = async (orderId) => {
    if (printingOrders.has(orderId)) {
      setSnackbar({
        open: true,
        message: 'Print already in progress for this order',
        severity: 'warning'
      });
      return;
    }

    const order = orders.find(o => o.id === orderId);
    if (!order) {
      setSnackbar({
        open: true,
        message: 'Order not found',
        severity: 'error'
      });
      return;
    }

    setPrintingOrders(prev => new Set([...prev, orderId]));

    try {
      if (wsConnected) {
        console.log('Using WebSocket for printing');
        
        const orderData = {
          orderNumber: order.order_number,
          customerName: order.customer_name,
          productName: order.product_name,
          amount: `₱${order.amount.toFixed(2)}`,
          date: order.date,
          address: order.address,
          contactNumber: order.contact_number,
          email: order.email || ''
        };

        await raspberryPiWebSocketService.printQRCode(orderData);
        
      } else {
        console.log('Using HTTP fallback for printing');
        
        const response = await axios.post(`${process.env.REACT_APP_API_ENDPOINT || 'http://192.168.100.61:5000/api'}/print-qr`, {
          orderId: orderId.toString()
        }, {
          timeout: 15000
        });
        
        setPrintingOrders(prev => {
          const newSet = new Set(prev);
          newSet.delete(orderId);
          return newSet;
        });
        
        setSnackbar({
          open: true,
          message: 'QR code print request sent successfully (HTTP)',
          severity: 'success'
        });

        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
    } catch (error) {
      console.error('Error printing QR code:', error);
      
      setPrintingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });

      let errorMessage = 'Failed to print QR code';
      
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.message) {
        errorMessage = error.message;
      } else if (error.code === 'ECONNABORTED') {
        errorMessage = 'Print request timed out - please try again';
      }
      
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ 
      p: { xs: 2, md: 3 }, 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Fade in timeout={1000}>
        <Box>
          {/* Header Section */}
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            mb: 4,
            p: 3,
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            border: '1px solid rgba(255, 255, 255, 0.2)',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: { xs: 2, sm: 0 }
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ 
                bgcolor: 'primary.main', 
                mr: 2, 
                width: 56, 
                height: 56,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
              }}>
                <OrdersIcon sx={{ fontSize: 28 }} />
              </Avatar>
              <Box>
                <Typography variant="h3" sx={{ 
                  fontWeight: 700, 
                  color: 'white',
                  background: 'linear-gradient(45deg, #fff, #e3f2fd)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontSize: { xs: '1.8rem', md: '3rem' }
                }}>
                  Order Management
                </Typography>
                <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 1 }}>
                  Track and print order receipts
                </Typography>
              </Box>
            </Box>
            
            {/* Connection Status & Actions */}
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Tooltip title="Refresh orders">
                <IconButton 
                  onClick={fetchOrders}
                  sx={{ 
                    color: 'white',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.2)' }
                  }}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              
              {connectingWs && (
                <Chip 
                  icon={<CircularProgress size={16} />}
                  label="Connecting..." 
                  size="small" 
                  sx={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: 'white'
                  }}
                />
              )}
              <Chip
                icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                label={wsConnected ? 'WebSocket Ready' : 'HTTP Fallback'}
                color={wsConnected ? 'success' : 'warning'}
                size="small"
                sx={{ 
                  backgroundColor: wsConnected ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 152, 0, 0.1)',
                  backdropFilter: 'blur(10px)'
                }}
              />
              <Chip
                icon={<PrintIcon />}
                label={`${printingOrders.size} printing`}
                color={printingOrders.size > 0 ? 'primary' : 'default'}
                size="small"
                sx={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  backdropFilter: 'blur(10px)',
                  color: 'white'
                }}
              />
            </Stack>
          </Box>

          {/* Stats Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1000}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <OrdersIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {orders.length}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Total Orders
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1200}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <PrintIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {printingOrders.size}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Printing Queue
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1400}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  color: 'white',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <MoneyIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        ₱{orders.reduce((sum, order) => sum + (order.amount || 0), 0).toLocaleString()}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Total Revenue
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Grow in timeout={1600}>
                <Card sx={{ 
                  background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
                  color: '#333',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.2)',
                    backdropFilter: 'blur(10px)',
                  }
                }}>
                  <CardContent sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <CalendarIcon sx={{ fontSize: 32, opacity: 0.8 }} />
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {new Date().toLocaleDateString()}
                      </Typography>
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                      Today's Date
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>
          </Grid>

          {/* Orders Table */}
          <Grow in timeout={1800}>
            <Paper 
              elevation={8}
              sx={{ 
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(20px)',
                borderRadius: 3,
                border: '1px solid rgba(255, 255, 255, 0.2)',
                overflow: 'hidden'
              }}
            >
              {isMobile ? (
                // Mobile Card View
                <Box sx={{ p: 2 }}>
                  {orders.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((order) => (
                    <Card key={order.id} sx={{ mb: 2, position: 'relative' }}>
                      <CardContent sx={{ p: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 40, height: 40 }}>
                              <PersonIcon />
                            </Avatar>
                            <Box>
                              <Typography variant="h6" sx={{ fontWeight: 600, color: 'primary.main' }}>
                                {order.order_number}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Order #{order.id}
                              </Typography>
                            </Box>
                          </Box>
                          <Button
                            variant="contained"
                            color="primary"
                            size="small"
                            startIcon={printingOrders.has(order.id) ? <CircularProgress size={16} /> : <PrintIcon />}
                            onClick={() => handlePrintQRCode(order.id)}
                            disabled={printingOrders.has(order.id)}
                            sx={{
                              minWidth: '100px',
                              borderRadius: 2,
                              textTransform: 'none',
                              fontWeight: 600
                            }}
                          >
                            {printingOrders.has(order.id) ? 'Printing...' : 'Print'}
                          </Button>
                        </Box>

                        <Grid container spacing={2}>
                          <Grid item xs={12}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <PersonIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} />
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {order.customer_name}
                              </Typography>
                            </Box>
                          </Grid>
                          
                          <Grid item xs={12}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <QrCodeIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} />
                              <Typography variant="body2">
                                {order.product_name}
                              </Typography>
                            </Box>
                          </Grid>

                          <Grid item xs={6}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <MoneyIcon sx={{ mr: 1, color: 'success.main', fontSize: 18 }} />
                              <Typography variant="body2" sx={{ fontWeight: 600, color: 'success.main' }}>
                                ₱{order.amount?.toFixed(2)}
                              </Typography>
                            </Box>
                          </Grid>

                          <Grid item xs={6}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <CalendarIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} />
                              <Typography variant="body2">
                                {order.date}
                              </Typography>
                            </Box>
                          </Grid>

                          {order.contact_number && (
                            <Grid item xs={12}>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <PhoneIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} />
                                <Typography variant="body2">
                                  {order.contact_number}
                                </Typography>
                              </Box>
                            </Grid>
                          )}

                          {order.email && (
                            <Grid item xs={12}>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <EmailIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} />
                                <Typography variant="body2">
                                  {order.email}
                                </Typography>
                              </Box>
                            </Grid>
                          )}

                          {order.address && (
                            <Grid item xs={12}>
                              <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                                <LocationIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 18, mt: 0.2 }} />
                                <Typography variant="body2">
                                  {order.address}
                                </Typography>
                              </Box>
                            </Grid>
                          )}
                        </Grid>

                        {printingOrders.has(order.id) && (
                          <Box sx={{ mt: 2 }}>
                            <LinearProgress sx={{ borderRadius: 1 }} />
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                              Sending to printer...
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              ) : (
                // Desktop Table View
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow sx={{ backgroundColor: 'rgba(0, 0, 0, 0.04)' }}>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Order #</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Customer</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Product</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Amount</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Date</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Contact</TableCell>
                        <TableCell sx={{ fontWeight: 700, fontSize: '0.9rem' }}>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {orders.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((order, index) => (
                        <TableRow 
                          key={order.id} 
                          sx={{ 
                            '&:hover': { 
                              backgroundColor: 'rgba(0, 0, 0, 0.02)',
                              transform: 'scale(1.001)',
                              transition: 'all 0.2s ease-in-out'
                            },
                            position: 'relative'
                          }}
                        >
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 32, height: 32 }}>
                                <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                  {index + 1 + page * rowsPerPage}
                                </Typography>
                              </Avatar>
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                                  {order.order_number}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  ID: {order.id}
                                </Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {order.customer_name}
                              </Typography>
                              {order.email && (
                                <Typography variant="caption" color="text.secondary">
                                  {order.email}
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{order.product_name}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`₱${order.amount?.toFixed(2)}`}
                              color="success"
                              variant="outlined"
                              size="small"
                              sx={{ fontWeight: 600, borderRadius: 2 }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{order.date}</Typography>
                          </TableCell>
                          <TableCell>
                            <Box>
                              {order.contact_number && (
                                <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                                  📞 {order.contact_number}
                                </Typography>
                              )}
                              {order.address && (
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                  📍 {order.address.length > 30 ? `${order.address.substring(0, 30)}...` : order.address}
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="contained"
                              color="primary"
                              size="small"
                              startIcon={printingOrders.has(order.id) ? <CircularProgress size={16} /> : <PrintIcon />}
                              onClick={() => handlePrintQRCode(order.id)}
                              disabled={printingOrders.has(order.id)}
                              sx={{
                                minWidth: '100px',
                                borderRadius: 2,
                                textTransform: 'none',
                                fontWeight: 600,
                                background: printingOrders.has(order.id) 
                                  ? 'linear-gradient(45deg, #ff9800, #ffc107)' 
                                  : 'linear-gradient(45deg, #2196f3, #21cbf3)',
                                '&:hover': {
                                  background: printingOrders.has(order.id)
                                    ? 'linear-gradient(45deg, #ff9800, #ffc107)'
                                    : 'linear-gradient(45deg, #1976d2, #1cb5e0)',
                                }
                              }}
                            >
                              {printingOrders.has(order.id) ? 'Printing...' : 'Print QR'}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}

              <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={orders.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                sx={{ 
                  borderTop: '1px solid rgba(0, 0, 0, 0.12)',
                  backgroundColor: 'rgba(0, 0, 0, 0.02)'
                }}
              />
            </Paper>
          </Grow>
        </Box>
      </Fade>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity} 
          sx={{ 
            width: '100%',
            borderRadius: 2,
            backdropFilter: 'blur(10px)'
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Orders;
