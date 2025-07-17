import React, { useState } from 'react';
import {
  Container,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Box,
  Snackbar,
  Alert,
  AppBar,
  Toolbar,
  Link,
  Paper
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import axios from 'axios';

const Products = () => {
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    customerName: '',
    contactNumber: '',
    address: '',
    productName: '',
    price: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmitOrder = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL || 'http://192.168.100.61:5000/api'}/manual-orders`, formData);
      setSnackbar({
        open: true,
        message: 'Order placed successfully!',
        severity: 'success'
      });
      setFormData({
        customerName: '',
        contactNumber: '',
        address: '',
        productName: '',
        price: ''
      });
    } catch (error) {
      console.error('Error submitting order:', error);
      setSnackbar({
        open: true,
        message: 'Failed to place order',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Package Store
          </Typography>
          <Link
            component={RouterLink}
            to="/admin"
            color="inherit"
            sx={{
              textDecoration: 'none',
              '&:hover': {
                textDecoration: 'underline'
              }
            }}
          >
            Admin Dashboard
          </Link>
        </Toolbar>
      </AppBar>

      <Container maxWidth="sm" sx={{ py: 6 }}>
        <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mb: 4 }}>
            Place Your Order
          </Typography>
          
          <form onSubmit={handleSubmitOrder}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <TextField
                required
                fullWidth
                label="Full Name"
                name="customerName"
                value={formData.customerName}
                onChange={handleInputChange}
                variant="outlined"
                sx={{ mb: 2 }}
              />
              
              <TextField
                required
                fullWidth
                label="Phone Number"
                name="contactNumber"
                type="tel"
                value={formData.contactNumber}
                onChange={handleInputChange}
                placeholder="+63 912 345 6789"
                variant="outlined"
                sx={{ mb: 2 }}
              />
              
              <TextField
                required
                fullWidth
                label="Address"
                name="address"
                multiline
                rows={4}
                value={formData.address}
                onChange={handleInputChange}
                variant="outlined"
                sx={{ mb: 2 }}
              />
              
              <TextField
                required
                fullWidth
                label="Product Name"
                name="productName"
                value={formData.productName}
                onChange={handleInputChange}
                variant="outlined"
                sx={{ mb: 2 }}
              />
              
              <TextField
                required
                fullWidth
                label="Price"
                name="price"
                type="number"
                inputProps={{ min: 0, step: 0.01 }}
                value={formData.price}
                onChange={handleInputChange}
                variant="outlined"
                sx={{ mb: 3 }}
              />
              
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  py: 1.5,
                  fontSize: '1.1rem',
                  backgroundColor: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.dark'
                  }
                }}
              >
                {loading ? 'Placing Order...' : 'Place Order'}
              </Button>
            </Box>
          </form>
        </Paper>

        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
        >
          <Alert
            onClose={handleCloseSnackbar}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Container>
    </Box>
  );
};

export default Products; 