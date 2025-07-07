import React from 'react';
import {
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import { format } from 'date-fns';

const getZoneColor = (zone) => {
  switch (zone) {
    case 'Zone A':
      return '#1976d2';
    case 'Zone B':
      return '#2e7d32';
    case 'Zone C':
      return '#ed6c02';
    default:
      return '#9c27b0';
  }
};

const getSizeColor = (size) => {
  switch (size.toLowerCase()) {
    case 'small':
      return 'success';
    case 'medium':
      return 'primary';
    case 'large':
      return 'warning';
    default:
      return 'default';
  }
};

function RecentParcels({ parcels }) {
  if (!parcels || parcels.length === 0) return null;

  return (
    <>
      <Typography component="h2" variant="h6" color="primary" gutterBottom>
        Recent Parcels
      </Typography>
      
      <TableContainer>
        <Table sx={{ minWidth: 650 }} aria-label="recent parcels table">
          <TableHead>
            <TableRow>
              <TableCell>Parcel ID</TableCell>
              <TableCell align="right">Weight (kg)</TableCell>
              <TableCell align="center">Size</TableCell>
              <TableCell align="center">Destination</TableCell>
              <TableCell align="right">Timestamp</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {parcels.map((parcel) => (
              <TableRow
                key={parcel.id}
                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
              >
                <TableCell component="th" scope="row">
                  {parcel.id}
                </TableCell>
                <TableCell align="right">{parcel.weight}</TableCell>
                <TableCell align="center">
                  <Chip
                    label={parcel.size}
                    color={getSizeColor(parcel.size)}
                    size="small"
                  />
                </TableCell>
                <TableCell align="center">
                  <Chip
                    label={parcel.destination}
                    sx={{
                      bgcolor: getZoneColor(parcel.destination),
                      color: 'white',
                    }}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  {format(new Date(parcel.timestamp), 'MMM d, yyyy HH:mm:ss')}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}

export default RecentParcels; 