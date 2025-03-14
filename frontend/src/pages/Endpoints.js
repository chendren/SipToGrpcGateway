import React, { useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';
import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  FormControlLabel,
  Switch,
  Stack
} from '@mui/material';

// Icons
import RefreshIcon from '@mui/icons-material/Refresh';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

function Endpoints() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [endpoints, setEndpoints] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState('add');
  const [currentEndpoint, setCurrentEndpoint] = useState({
    name: '',
    host: '',
    port: '',
    service: '',
    use_tls: false
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [endpointToDelete, setEndpointToDelete] = useState('');

  // Load endpoints
  const fetchEndpoints = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get('/endpoints');
      setEndpoints(response.data);
    } catch (err) {
      setError('Failed to load endpoints. Please ensure the backend is running.');
      console.error('Error fetching endpoints:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchEndpoints();
  }, []);

  // Open add endpoint dialog
  const handleAddEndpoint = () => {
    setCurrentEndpoint({
      name: '',
      host: '',
      port: '',
      service: '',
      use_tls: false
    });
    setDialogMode('add');
    setOpenDialog(true);
  };

  // Open edit endpoint dialog
  const handleEditEndpoint = (endpoint) => {
    setCurrentEndpoint({ ...endpoint });
    setDialogMode('edit');
    setOpenDialog(true);
  };

  // Open delete endpoint dialog
  const handleDeletePrompt = (name) => {
    setEndpointToDelete(name);
    setDeleteDialogOpen(true);
  };

  // Close dialog
  const handleDialogClose = () => {
    setOpenDialog(false);
  };

  // Handle input change
  const handleInputChange = (e) => {
    const { name, value, checked, type } = e.target;
    setCurrentEndpoint({
      ...currentEndpoint,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  // Save endpoint
  const handleSaveEndpoint = async () => {
    try {
      if (dialogMode === 'add') {
        await apiClient.post('/endpoints', currentEndpoint);
      } else {
        // In a real implementation, you'd have an update endpoint API
        // For now, we'll just delete and re-add
        await apiClient.delete(`/endpoints/${currentEndpoint.name}`);
        await apiClient.post('/endpoints', currentEndpoint);
      }
      
      setOpenDialog(false);
      fetchEndpoints();
    } catch (err) {
      console.error('Error saving endpoint:', err);
      setError('Failed to save endpoint. Please try again.');
    }
  };

  // Delete endpoint
  const handleDeleteEndpoint = async () => {
    try {
      await apiClient.delete(`/endpoints/${endpointToDelete}`);
      setDeleteDialogOpen(false);
      fetchEndpoints();
    } catch (err) {
      console.error('Error deleting endpoint:', err);
      setError('Failed to delete endpoint. Please try again.');
    }
  };

  // Validate form
  const isFormValid = () => {
    return (
      currentEndpoint.name.trim() !== '' &&
      currentEndpoint.host.trim() !== '' &&
      currentEndpoint.port.toString().trim() !== '' &&
      currentEndpoint.service.trim() !== ''
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">Endpoints</Typography>
        <Box>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchEndpoints} disabled={loading} sx={{ mr: 1 }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddEndpoint}
          >
            Add Endpoint
          </Button>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      ) : (
        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Host</TableCell>
                  <TableCell>Port</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>TLS</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {endpoints.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body1" sx={{ py: 3 }}>
                        No endpoints configured. Click "Add Endpoint" to create one.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  endpoints.map((endpoint) => (
                    <TableRow key={endpoint.name}>
                      <TableCell>{endpoint.name}</TableCell>
                      <TableCell>{endpoint.host}</TableCell>
                      <TableCell>{endpoint.port}</TableCell>
                      <TableCell>{endpoint.service}</TableCell>
                      <TableCell>{endpoint.use_tls ? 'Yes' : 'No'}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Edit">
                          <IconButton onClick={() => handleEditEndpoint(endpoint)}>
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton onClick={() => handleDeletePrompt(endpoint.name)} color="error">
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Add/Edit Endpoint Dialog */}
      <Dialog open={openDialog} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {dialogMode === 'add' ? 'Add New Endpoint' : 'Edit Endpoint'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              name="name"
              value={currentEndpoint.name}
              onChange={handleInputChange}
              fullWidth
              disabled={dialogMode === 'edit'}
              helperText="A unique identifier for this endpoint"
            />
            <TextField
              label="Host"
              name="host"
              value={currentEndpoint.host}
              onChange={handleInputChange}
              fullWidth
              helperText="Hostname or IP address of the gRPC server"
            />
            <TextField
              label="Port"
              name="port"
              type="number"
              value={currentEndpoint.port}
              onChange={handleInputChange}
              fullWidth
              helperText="Port number of the gRPC server"
            />
            <TextField
              label="Service"
              name="service"
              value={currentEndpoint.service}
              onChange={handleInputChange}
              fullWidth
              helperText="Name of the gRPC service to use"
            />
            <FormControlLabel
              control={
                <Switch
                  name="use_tls"
                  checked={currentEndpoint.use_tls}
                  onChange={handleInputChange}
                />
              }
              label="Use TLS"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Cancel</Button>
          <Button
            onClick={handleSaveEndpoint}
            variant="contained"
            disabled={!isFormValid()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Endpoint</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the endpoint "{endpointToDelete}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteEndpoint} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Endpoints;