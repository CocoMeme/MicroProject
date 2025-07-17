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
  Grid
} from '@mui/material';
import { 
  QrCode2 as QrCodeIcon, 
  Print as PrintIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon 
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
    // Just log the status without showing modal
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

    // Reload the page after successful printing
    setTimeout(() => {
      window.location.reload();
    }, 1000); // Wait 1 second to show the success message
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
      const response = await axios.get('http://192.168.100.61:5000/api/orders');
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
    // Prevent multiple simultaneous prints for the same order
    if (printingOrders.has(orderId)) {
      setSnackbar({
        open: true,
        message: 'Print already in progress for this order',
        severity: 'warning'
      });
      return;
    }

    // Find the order data
    const order = orders.find(o => o.id === orderId);
    if (!order) {
      setSnackbar({
        open: true,
        message: 'Order not found',
        severity: 'error'
      });
      return;
    }

    // Add to printing set
    setPrintingOrders(prev => new Set([...prev, orderId]));

    try {
      if (wsConnected) {
        // Use WebSocket for better performance on slow connections
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
        // Fallback to HTTP
        console.log('Using HTTP fallback for printing');
        
        const response = await axios.post('http://192.168.100.61:5000/api/print-qr', {
          orderId: orderId.toString()
        }, {
          timeout: 15000 // Increased timeout for Raspberry Pi browser
        });
        
        // Remove from printing set on HTTP success
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

        // Reload the page after successful HTTP printing
        setTimeout(() => {
          window.location.reload();
        }, 1000); // Wait 1 second to show the success message
      }
    } catch (error) {
      console.error('Error printing QR code:', error);
      
      // Remove from printing set on error
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
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 2,
        flexDirection: { xs: 'column', sm: 'row' },
        gap: { xs: 2, sm: 0 }
      }}>
        <Typography variant="h4" sx={{ fontSize: { xs: '1.5rem', md: '2rem' } }}>
          Orders
        </Typography>
        
        {/* Connection Status */}
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          {connectingWs && (
            <Chip 
              icon={<CircularProgress size={16} />}
              label="Connecting..." 
              size="small" 
              color="info"
            />
          )}
          <Chip
            icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
            label={wsConnected ? 'WebSocket Ready' : 'HTTP Fallback'}
            color={wsConnected ? 'success' : 'warning'}
            size="small"
          />
          <Chip
            icon={<PrintIcon />}
            label={`${printingOrders.size} printing`}
            color={printingOrders.size > 0 ? 'primary' : 'default'}
            size="small"
          />
        </Stack>
      </Box>
      
      {/* Mobile Card View */}
      {isMobile ? (
        <Box>
          <Grid container spacing={2}>
            {orders
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((order) => (
                <Grid item xs={12} key={order.id}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                          {order.order_number}
                        </Typography>
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={printingOrders.has(order.id) ? <CircularProgress size={16} /> : <QrCodeIcon />}
                          onClick={() => handlePrintQRCode(order.id)}
                          disabled={printingOrders.has(order.id)}
                          color={printingOrders.has(order.id) ? "secondary" : "primary"}
                        >
                          {printingOrders.has(order.id) ? 'Printing...' : 'Print QR'}
                        </Button>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        <strong>Customer:</strong> {order.customer_name}
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        <strong>Contact:</strong> {order.contact_number || 'N/A'}
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        <strong>Product:</strong> {order.product_name}
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        <strong>Amount:</strong> ₱{parseFloat(order.amount || 0).toFixed(2)}
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary">
                        <strong>Date:</strong> {new Date(order.date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
          </Grid>
          
          {orders.length === 0 && (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No orders found
              </Typography>
            </Paper>
          )}
        </Box>
      ) : (
        /* Desktop Table View */
        <Paper sx={{ width: '100%', overflow: 'hidden' }}>
          <TableContainer sx={{ maxHeight: 440 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Order Number</TableCell>
                  <TableCell>Customer Name</TableCell>
                  <TableCell>Contact</TableCell>
                  <TableCell>Product</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((order) => (
                    <TableRow hover key={order.id}>
                      <TableCell>{order.order_number}</TableCell>
                      <TableCell>{order.customer_name}</TableCell>
                      <TableCell>{order.contact_number || 'N/A'}</TableCell>
                      <TableCell>{order.product_name}</TableCell>
                      <TableCell>₱{parseFloat(order.amount || 0).toFixed(2)}</TableCell>
                      <TableCell>
                        {new Date(order.date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={printingOrders.has(order.id) ? <CircularProgress size={16} /> : <QrCodeIcon />}
                            onClick={() => handlePrintQRCode(order.id)}
                            disabled={printingOrders.has(order.id)}
                            color={printingOrders.has(order.id) ? "secondary" : "primary"}
                          >
                            {printingOrders.has(order.id) ? 'Printing...' : 'Print QR'}
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                {orders.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      No orders found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
      
      {/* Pagination */}
      <TablePagination
        rowsPerPageOptions={[10, 25, 100]}
        component="div"
        count={orders.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        sx={{ 
          mt: 2,
          '& .MuiTablePagination-toolbar': {
            flexDirection: { xs: 'column', sm: 'row' },
            alignItems: { xs: 'stretch', sm: 'center' },
            gap: { xs: 1, sm: 0 }
          },
          '& .MuiTablePagination-spacer': {
            display: { xs: 'none', sm: 'block' }
          }
        }}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Orders; 