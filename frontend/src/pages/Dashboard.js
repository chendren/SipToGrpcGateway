import React, { useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';

// Icons
import RefreshIcon from '@mui/icons-material/Refresh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);

  // Load status and config
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get status
      const statusResponse = await apiClient.get('/status');
      setStatus(statusResponse.data);
      
      // Get config
      const configResponse = await apiClient.get('/config');
      setConfig(configResponse.data);
    } catch (err) {
      setError('Failed to load gateway status. Please ensure the backend is running.');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchData();
  }, []);

  // Render status cards
  const renderStatusCards = () => {
    if (!status) return null;

    return (
      <Grid container spacing={3}>
        {/* Gateway Status */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" gutterBottom>
                Gateway Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
                {status.running ? (
                  <Chip 
                    icon={<CheckCircleIcon />} 
                    label="Running" 
                    color="success" 
                    variant="outlined"
                  />
                ) : (
                  <Chip 
                    icon={<ErrorIcon />} 
                    label="Stopped" 
                    color="error" 
                    variant="outlined"
                  />
                )}
              </Box>
            </CardContent>
            <CardActions>
              <Button 
                size="small" 
                startIcon={status.running ? <StopIcon /> : <PlayArrowIcon />}
                color={status.running ? "error" : "primary"}
                disabled // This would require an API to start/stop the service
              >
                {status.running ? "Stop Gateway" : "Start Gateway"}
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* SIP Server */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" gutterBottom>
                SIP Server
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Host: {status.sip_server.host || 'N/A'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Port: {status.sip_server.port || 'N/A'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  <Chip 
                    label="UDP" 
                    color={status.sip_server.udp_enabled ? "success" : "default"} 
                    size="small"
                    variant={status.sip_server.udp_enabled ? "filled" : "outlined"}
                  />
                  <Chip 
                    label="TCP" 
                    color={status.sip_server.tcp_enabled ? "success" : "default"} 
                    size="small"
                    variant={status.sip_server.tcp_enabled ? "filled" : "outlined"}
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* gRPC Client */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" gutterBottom>
                gRPC Client
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
                {status.grpc_client.connected ? (
                  <Chip 
                    icon={<CheckCircleIcon />} 
                    label="Connected" 
                    color="success" 
                    variant="outlined"
                  />
                ) : (
                  <Chip 
                    icon={<ErrorIcon />} 
                    label="Disconnected" 
                    color="error" 
                    variant="outlined"
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  // Render configuration summary
  const renderConfigSummary = () => {
    if (!config) return null;

    const endpoints = config.grpc?.endpoints || [];
    const sipMappings = Object.keys(config.mapping?.sip_to_grpc || {}).length;
    const grpcMappings = Object.keys(config.mapping?.grpc_to_sip || {}).length;

    return (
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Configuration Summary
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1">Endpoints</Typography>
            <Typography variant="h4" color="primary">
              {endpoints.length}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {endpoints.map(e => e.name).join(', ') || 'No endpoints configured'}
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1">SIP to gRPC Mappings</Typography>
            <Typography variant="h4" color="primary">
              {sipMappings}
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1">gRPC to SIP Mappings</Typography>
            <Typography variant="h4" color="primary">
              {grpcMappings}
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">Dashboard</Typography>
        <Tooltip title="Refresh Data">
          <IconButton onClick={fetchData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      ) : (
        <Stack spacing={3}>
          {renderStatusCards()}
          {renderConfigSummary()}
        </Stack>
      )}
    </Box>
  );
}

export default Dashboard;