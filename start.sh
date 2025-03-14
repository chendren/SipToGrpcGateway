#!/bin/bash
# Start script for the SIP to gRPC Gateway

# Change to the script's directory
cd "$(dirname "$0")"

# Make temp directory for logs
mkdir -p logs

# Start the mock API server
echo "Starting mock API server..."
python3 mock_api.py > logs/api.log 2>&1 &
API_PID=$!

# Wait for the API server to start
sleep 2

# Check if the API server is running
if ! ps -p $API_PID > /dev/null; then
  echo "Failed to start mock API server. Check logs/api.log for details."
  exit 1
fi

echo "Mock API server running at http://localhost:8080"

# Build and serve the frontend
echo "Setting up the frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies (this may take a few minutes)..."
  npm install > ../logs/npm_install.log 2>&1
  if [ $? -ne 0 ]; then
    echo "Failed to install frontend dependencies. Check logs/npm_install.log for details."
    kill $API_PID
    exit 1
  fi
fi

echo "Starting frontend development server..."
npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for the frontend to start
sleep 5

# Check if the frontend server is running
if ! ps -p $FRONTEND_PID > /dev/null; then
  echo "Failed to start frontend server. Check logs/frontend.log for details."
  kill $API_PID
  exit 1
fi

echo "Frontend running at http://localhost:3000"
echo "You can now access the application at http://localhost:3000"
echo "Press Ctrl+C to stop all servers"

# Function to clean up on exit
cleanup() {
  echo "Shutting down servers..."
  kill $API_PID
  kill $FRONTEND_PID
  exit
}

# Register the cleanup function for signals
trap cleanup SIGINT SIGTERM

# Keep the script running
wait $FRONTEND_PID