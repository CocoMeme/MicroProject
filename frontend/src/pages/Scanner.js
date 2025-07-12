import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Alert,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';

const RASPI_SERVER = 'http://192.168.100.63:5001'; // Your Raspberry Pi address

export default function Scanner() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastScan, setLastScan] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState({ online: false, camera_running: false });

  useEffect(() => {
    checkStatus();

    // Poll status every 5 seconds
    const statusInterval = setInterval(checkStatus, 5000);

    let qrInterval;
    if (isStreaming) {
      qrInterval = setInterval(getLastQR, 1000);
    }

    return () => {
      clearInterval(statusInterval);
      if (qrInterval) clearInterval(qrInterval);
      if (isStreaming) stopCamera();
    };
  }, [isStreaming]);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/status`);
      const data = await response.json();
      
      // Update streaming state based on camera status
      setIsStreaming(data.camera_running);
      
      setStatus({
        online: true,
        camera_running: data.camera_running,
        has_camera: data.has_camera,
        initialization_error: data.initialization_error
      });

      // Clear any previous errors if the status check is successful
      setError(null);
    } catch (err) {
      console.error('Failed to check camera status:', err);
      setError('Failed to connect to Raspberry Pi server');
      setStatus({ online: false, camera_running: false });
    }
  };

  const getLastQR = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/last-qr`);
      const data = await response.json();
      if (data.last_qr_data && (!lastScan || data.last_qr_data !== lastScan.data)) {
        setLastScan({
          data: data.last_qr_data,
          timestamp: new Date().toLocaleString(),
          type: 'QR Code'
        });
      }
    } catch (err) {
      console.error('Failed to get last QR code:', err);
    }
  };

  const startCamera = async () => {
    try {
      // First check if camera is already running
      const statusResponse = await fetch(`${RASPI_SERVER}/camera/status`);
      const statusData = await statusResponse.json();

      if (statusData.camera_running) {
        // Camera is already running, just update our state
        setIsStreaming(true);
        setError(null);
        return;
      }

      // If camera is not running, try to start it
      const response = await fetch(`${RASPI_SERVER}/camera/start`, {
        method: 'POST',
      });
      const data = await response.json();

      if (response.ok) {
        setIsStreaming(true);
        setError(null);
      } else {
        throw new Error(data.error || 'Failed to start camera');
      }
    } catch (err) {
      console.error('Failed to start camera:', err);
      setError(err.message || 'Failed to start camera');
      setIsStreaming(false);
    }
  };

  const stopCamera = async () => {
    try {
      const response = await fetch(`${RASPI_SERVER}/camera/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (response.ok) {
        setIsStreaming(false);
        setError(null);
      } else {
        throw new Error(data.error || 'Failed to stop camera');
      }
    } catch (err) {
      console.error('Failed to stop camera:', err);
      setError(err.message || 'Failed to stop camera');
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        QR Code Scanner
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Camera Feed</Typography>
              <Button
                variant="contained"
                color={isStreaming ? 'error' : 'primary'}
                startIcon={isStreaming ? <StopIcon /> : <PlayArrowIcon />}
                onClick={isStreaming ? stopCamera : startCamera}
                disabled={!status.online || status.initialization_error}
              >
                {isStreaming ? 'Stop Camera' : 'Start Camera'}
              </Button>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {!status.online && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Raspberry Pi server is offline
              </Alert>
            )}

            {status.initialization_error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Camera initialization error: {status.initialization_error}
              </Alert>
            )}

            <Box
              sx={{
                width: '100%',
                height: 480,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                bgcolor: 'black',
                position: 'relative',
              }}
            >
              {isStreaming ? (
                <img
                  src={`${RASPI_SERVER}/video_feed`}
                  alt="Camera Feed"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                  }}
                />
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    color: 'grey.500',
                  }}
                >
                  <QrCodeScannerIcon sx={{ fontSize: 60, mb: 2 }} />
                  <Typography>Camera is stopped</Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Last Scan
            </Typography>
            {lastScan ? (
              <Box>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  Data: {lastScan.data}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Type: {lastScan.type}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Time: {lastScan.timestamp}
                </Typography>
              </Box>
            ) : (
              <Typography color="text.secondary">No QR codes scanned yet</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
