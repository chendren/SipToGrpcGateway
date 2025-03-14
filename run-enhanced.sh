#!/bin/bash
# Run the enhanced SIP to gRPC Gateway with voice and trace capabilities

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if there's a running server
pkill -f "python3.*simple_server.py" 2>/dev/null

# Create logs directory if it doesn't exist and ensure it's writable
mkdir -p "$SCRIPT_DIR/logs"
chmod 755 "$SCRIPT_DIR/logs"

# Determine an available port
PORT=8080
while nc -z localhost $PORT 2>/dev/null; do
    PORT=$((PORT+1))
    if [ $PORT -gt 8100 ]; then
        echo "Could not find an available port in the range 8080-8100"
        exit 1
    fi
done

# Print banner
echo "============================================="
echo "  SIP to gRPC Gateway - Enhanced Edition"
echo "============================================="
echo "  Features:"
echo "  - Voice communication (Press to Speak)"
echo "  - Protocol tracing (SIP ↔ gRPC)"
echo "  - PCAP file generation"
echo "============================================="
echo ""

# Make sure the trace server is executable
chmod +x "$SCRIPT_DIR/trace_server.py"

# Run the server with our dedicated trace implementation
echo "Starting enhanced server on port $PORT..."
cd "$SCRIPT_DIR"
python3 -u trace_server.py $PORT direct_ui &
SERVER_PID=$!

# Wait for the server to start
sleep 1

# Open the browser
if command -v open >/dev/null 2>&1; then
    open "http://localhost:$PORT"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:$PORT"
elif command -v start >/dev/null 2>&1; then
    start "http://localhost:$PORT"
else
    echo "Please open a browser and navigate to http://localhost:$PORT"
fi

echo "Server running at http://localhost:$PORT"
echo "Press Ctrl+C to stop the server"

# Handle shutdown gracefully
trap "kill $SERVER_PID 2>/dev/null; echo 'Server stopped'; exit" SIGINT SIGTERM

# Wait for the server
wait $SERVER_PID