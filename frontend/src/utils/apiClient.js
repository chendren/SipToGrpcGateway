import axios from 'axios';

// Create API client
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8080',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Response interceptor
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Log the error for debugging
    console.error('API Error:', error.message);
    
    if (error.response) {
      // Server responded with a status code outside of 2xx range
      console.error('Error response:', error.response.data);
    } else if (error.request) {
      // Request was made but no response was received
      console.error('No response received from server');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;