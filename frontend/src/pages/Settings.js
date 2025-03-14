import React, { useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';
import {
  Box,
  Typography,
  Paper,
  TextField,
  FormControlLabel,
  Switch,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';

function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [config, setConfig] = useState(null);

  // Load config
  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get('/config');
      setConfig(response.data);
    } catch (err) {
      setError('Failed to load configuration. Please ensure the backend is running.');
      console.error('Error fetching config:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchConfig();
  }, []);

  // Handle input change
  const handleInputChange = (section, field, value) => {
    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [field]: value
      }
    });
  };

  // Save config
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    try {
      await apiClient.put('/config', config);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError('Failed to save configuration. Please try again.');
      console.error('Error saving config:', err);
    } finally {
      setSaving(false);
    }
  };

  // SIP Server settings
  const renderSipSettings = () => {
    if (!config?.sip) return null;
    
    return (
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>SIP Server Settings</Typography>
        <Divider sx={{ mb: 3 }} />
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              label="Host"
              value={config.sip.host}
              onChange={(e) => handleInputChange('sip', 'host', e.target.value)}
              fullWidth
              helperText="IP address or hostname for the SIP server to bind to"
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              label="Port"
              type="number"
              value={config.sip.port}
              onChange={(e) => handleInputChange('sip', 'port', parseInt(e.target.value))}
              fullWidth
              helperText="Port for the SIP server to listen on"
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.sip.enable_udp}
                  onChange={(e) => handleInputChange('sip', 'enable_udp', e.target.checked)}
                />
              }
              label="Enable UDP"
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.sip.enable_tcp}
                  onChange={(e) => handleInputChange('sip', 'enable_tcp', e.target.checked)}
                />
              }
              label="Enable TCP"
            />
          </Grid>
        </Grid>
      </Paper>
    );
  };

  // API Server settings
  const renderApiSettings = () => {
    if (!config?.api) return null;
    
    return (
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>API Server Settings</Typography>
        <Divider sx={{ mb: 3 }} />
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              label="Host"
              value={config.api.host}
              onChange={(e) => handleInputChange('api', 'host', e.target.value)}
              fullWidth
              helperText="IP address or hostname for the API server to bind to"
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              label="Port"
              type="number"
              value={config.api.port}
              onChange={(e) => handleInputChange('api', 'port', parseInt(e.target.value))}
              fullWidth
              helperText="Port for the API server to listen on"
            />
          </Grid>
        </Grid>
      </Paper>
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">Settings</Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      ) : (
        <Box>
          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              Settings saved successfully!
            </Alert>
          )}
          
          {renderSipSettings()}
          {renderApiSettings()}
          
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </Button>
          </Box>
        </Box>
      )}
    </Box>
  );
}

export default Settings;