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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress
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

  // WebSocket and printing states
  const [wsConnected, setWsConnected] = useState(false);
  const [connectingWs, setConnectingWs] = useState(false);
  const [printingOrders, setPrintingOrders] = useState(new Set());
  const [printDialog, setPrintDialog] = useState({
    open: false,
    orderId: null,
    status: '',
    progress: 0
  });

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
    if (data.order_number) {
      let progress = 0;
      switch (data.status) {
        case 'processing': progress = 25; break;
        case 'creating': progress = 50; break;
        case 'printing': progress = 75; break;
        default: progress = 0;
      }
      
      setPrintDialog(prev => ({
        ...prev,
        status: data.message,
        progress: progress
      }));
    }
  };

  const handlePrintSuccess = (data) => {
    setPrintingOrders(prev => {
      const newSet = new Set(prev);
      newSet.delete(data.order_number);
      return newSet;
    });
    
    setPrintDialog(prev => ({
      ...prev,
      status: 'Print completed successfully!',
      progress: 100
    }));

    setTimeout(() => {
      setPrintDialog({ open: false, orderId: null, status: '', progress: 0 });
    }, 2000);

    setSnackbar({
      open: true,
      message: `QR code printed successfully for order ${data.order_number}`,
      severity: 'success'
    });
  };

  const handlePrintError = (data) => {
    setPrintingOrders(prev => {
      const newSet = new Set(prev);
      newSet.delete(data.order_number);
      return newSet;
    });
    
    setPrintDialog({ open: false, orderId: null, status: '', progress: 0 });
    
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

    // Show progress dialog for WebSocket printing
    if (wsConnected) {
      setPrintDialog({
        open: true,
        orderId: orderId,
        status: 'Initializing print request...',
        progress: 0
      });
    }

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
      }
    } catch (error) {
      console.error('Error printing QR code:', error);
      
      // Remove from printing set on error
      setPrintingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });

      // Close progress dialog on error
      setPrintDialog({ open: false, orderId: null, status: '', progress: 0 });
      
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
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Orders
        </Typography>
        
        {/* Connection Status */}
        <Stack direction="row" spacing={1} alignItems="center">
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
      
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 440 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Order Number</TableCell>
                <TableCell>Customer Name</TableCell>
                <TableCell>Email</TableCell>
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
                    <TableCell>{order.email}</TableCell>
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
                  <TableCell colSpan={8} align="center">
                    No orders found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 100]}
          component="div"
          count={orders.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

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

      {/* Print Progress Dialog */}
      <Dialog 
        open={printDialog.open} 
        onClose={() => {}} 
        disableEscapeKeyDown 
        maxWidth="sm" 
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PrintIcon />
            Printing QR Code
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Order ID: {printDialog.orderId}
            </Typography>
            <Typography variant="body1" gutterBottom>
              {printDialog.status}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={printDialog.progress} 
              sx={{ mt: 2 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {printDialog.progress}% complete
            </Typography>
          </Box>
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Using WebSocket connection for optimal performance on slow networks.
              This dialog will close automatically when printing is complete.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Typography variant="caption" color="text.secondary">
            Please wait while printing...
          </Typography>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Orders; 