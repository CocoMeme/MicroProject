import React, { useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  IconButton,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

// Sample data - replace with API call in production
const sampleParcels = [
  { id: 'PKG001', trackingNumber: 'TRK123456', weight: 2.5, size: 'Medium', status: 'Pending', destination: 'Zone A', created: '2024-01-15' },
  { id: 'PKG002', trackingNumber: 'TRK789012', weight: 1.2, size: 'Small', status: 'Processing', destination: 'Zone B', created: '2024-01-15' },
  { id: 'PKG003', trackingNumber: 'TRK345678', weight: 4.7, size: 'Large', status: 'Delivered', destination: 'Zone C', created: '2024-01-14' },
  // Add more sample data as needed
];

export default function Parcels() {
  const [parcels, setParcels] = useState(sampleParcels);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState({
    trackingNumber: '',
    weight: '',
    size: 'Medium',
    destination: 'Zone A',
  });

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleOpenDialog = (parcel = null) => {
    if (parcel) {
      setSelectedParcel(parcel);
      setFormData({
        trackingNumber: parcel.trackingNumber,
        weight: parcel.weight,
        size: parcel.size,
        destination: parcel.destination,
      });
    } else {
      setSelectedParcel(null);
      setFormData({
        trackingNumber: '',
        weight: '',
        size: 'Medium',
        destination: 'Zone A',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedParcel(null);
  };

  const handleSubmit = () => {
    if (selectedParcel) {
      // Update existing parcel
      setParcels(parcels.map(p => 
        p.id === selectedParcel.id 
          ? { ...p, ...formData }
          : p
      ));
    } else {
      // Add new parcel
      const newParcel = {
        id: `PKG${Math.floor(Math.random() * 1000)}`,
        ...formData,
        status: 'Pending',
        created: new Date().toISOString().split('T')[0],
      };
      setParcels([newParcel, ...parcels]);
    }
    handleCloseDialog();
  };

  const handleDelete = (id) => {
    setParcels(parcels.filter(p => p.id !== id));
  };

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'info';
      case 'delivered':
        return 'success';
      default:
        return 'default';
    }
  };

  const filteredParcels = parcels.filter(parcel =>
    Object.values(parcel).some(value =>
      value.toString().toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  return (
    <Box className="fade-in">
      <Typography variant="h4" sx={{ mb: 4, fontWeight: 600 }}>
        Parcels
      </Typography>
      <Box sx={{ p: 3 }}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5" component="h1">
            Parcel Management
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add New Parcel
          </Button>
        </Box>

        <Paper sx={{ mb: 2 }}>
          <Box sx={{ p: 2 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search parcels..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Tracking Number</TableCell>
                  <TableCell>Weight (kg)</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Destination</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredParcels
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((parcel) => (
                    <TableRow key={parcel.id}>
                      <TableCell>{parcel.id}</TableCell>
                      <TableCell>{parcel.trackingNumber}</TableCell>
                      <TableCell>{parcel.weight}</TableCell>
                      <TableCell>{parcel.size}</TableCell>
                      <TableCell>
                        <Chip
                          label={parcel.status}
                          color={getStatusColor(parcel.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{parcel.destination}</TableCell>
                      <TableCell>{parcel.created}</TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(parcel)}
                          color="primary"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(parcel.id)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={filteredParcels.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </Paper>

        <Dialog open={openDialog} onClose={handleCloseDialog}>
          <DialogTitle>
            {selectedParcel ? 'Edit Parcel' : 'Add New Parcel'}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                fullWidth
                label="Tracking Number"
                value={formData.trackingNumber}
                onChange={(e) => setFormData({ ...formData, trackingNumber: e.target.value })}
              />
              <TextField
                fullWidth
                label="Weight (kg)"
                type="number"
                value={formData.weight}
                onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
              />
              <FormControl fullWidth>
                <InputLabel>Size</InputLabel>
                <Select
                  value={formData.size}
                  label="Size"
                  onChange={(e) => setFormData({ ...formData, size: e.target.value })}
                >
                  <MenuItem value="Small">Small</MenuItem>
                  <MenuItem value="Medium">Medium</MenuItem>
                  <MenuItem value="Large">Large</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Destination</InputLabel>
                <Select
                  value={formData.destination}
                  label="Destination"
                  onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                >
                  <MenuItem value="Zone A">Zone A</MenuItem>
                  <MenuItem value="Zone B">Zone B</MenuItem>
                  <MenuItem value="Zone C">Zone C</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancel</Button>
            <Button onClick={handleSubmit} variant="contained">
              {selectedParcel ? 'Update' : 'Add'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Box>
  );
} 