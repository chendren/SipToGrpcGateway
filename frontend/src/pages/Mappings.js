import React, { useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';

// Icons
import RefreshIcon from '@mui/icons-material/Refresh';
import EditIcon from '@mui/icons-material/Edit';

function Mappings() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mappings, setMappings] = useState(null);
  const [tabValue, setTabValue] = useState(0);

  // Load mappings
  const fetchMappings = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get('/mappings');
      setMappings(response.data);
    } catch (err) {
      setError('Failed to load mappings. Please ensure the backend is running.');
      console.error('Error fetching mappings:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchMappings();
  }, []);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Render SIP to gRPC mappings
  const renderSipToGrpcMappings = () => {
    if (!mappings?.sip_to_grpc) return null;
    
    const sipMappings = Object.entries(mappings.sip_to_grpc);
    
    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>SIP Method</TableCell>
              <TableCell>gRPC Endpoint</TableCell>
              <TableCell>gRPC Method</TableCell>
              <TableCell>Fields Mapped</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sipMappings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body1" sx={{ py: 3 }}>
                    No SIP to gRPC mappings configured.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              sipMappings.map(([method, mapping]) => (
                <TableRow key={method}>
                  <TableCell>{method}</TableCell>
                  <TableCell>{mapping.endpoint}</TableCell>
                  <TableCell>{mapping.method}</TableCell>
                  <TableCell>{mapping.fields ? Object.keys(mapping.fields).length : 0}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit">
                      <IconButton>
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Render gRPC to SIP mappings
  const renderGrpcToSipMappings = () => {
    if (!mappings?.grpc_to_sip) return null;
    
    const grpcMappings = Object.entries(mappings.grpc_to_sip);
    
    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>gRPC Method</TableCell>
              <TableCell>SIP Status</TableCell>
              <TableCell>Headers Mapped</TableCell>
              <TableCell>Has Body Mapping</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {grpcMappings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body1" sx={{ py: 3 }}>
                    No gRPC to SIP mappings configured.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              grpcMappings.map(([key, mapping]) => (
                <TableRow key={key}>
                  <TableCell>{key}</TableCell>
                  <TableCell>{mapping.status_code} {mapping.reason}</TableCell>
                  <TableCell>{mapping.headers ? Object.keys(mapping.headers).length : 0}</TableCell>
                  <TableCell>{mapping.body ? 'Yes' : 'No'}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit">
                      <IconButton>
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">Mappings</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchMappings} disabled={loading}>
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
        <Box>
          <Paper sx={{ mb: 3 }}>
            <Tabs value={tabValue} onChange={handleTabChange} variant="fullWidth">
              <Tab label="SIP to gRPC" />
              <Tab label="gRPC to SIP" />
            </Tabs>
          </Paper>

          {tabValue === 0 ? renderSipToGrpcMappings() : renderGrpcToSipMappings()}
        </Box>
      )}
    </Box>
  );
}

export default Mappings;