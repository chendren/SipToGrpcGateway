#!/bin/bash
# Simple script to run a standalone web page that communicates directly with the API server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we should use the existing server script
if [ "$1" = "--use-existing" ]; then
  echo "Using existing simple_server.py"
else
  # Create a simple API server that serves the config and status
  cat > "$SCRIPT_DIR/simple_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Ultra-simple API server for the SIP to gRPC Gateway UI.
This provides just enough API endpoints to show the dashboard.
"""

import http.server
import json
import os
import socketserver
import io
import time
import base64

# Load the config file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

# Mock status
STATUS = {
    "running": True,
    "sip_server": {
        "host": CONFIG.get("sip", {}).get("host", "0.0.0.0"),
        "port": CONFIG.get("sip", {}).get("port", 5060),
        "udp_enabled": CONFIG.get("sip", {}).get("enable_udp", True),
        "tcp_enabled": CONFIG.get("sip", {}).get("enable_tcp", True)
    },
    "grpc_client": {
        "connected": True
    }
}

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    """Simple handler for API requests"""
    
    def send_cors_headers(self):
        """Send CORS headers to support cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/status':
            # Return status
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(STATUS).encode())
        
        elif self.path == '/config':
            # Return config
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(CONFIG).encode())
            
        elif self.path == '/favicon.ico':
            # Return empty response for favicon
            self.send_response(204)
            self.end_headers()
            
        else:
            # Serve static files from the directory
            return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/stream-audio':
            # Handle audio streaming from client
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                try:
                    # Parse the audio data (base64 encoded in JSON)
                    data = json.loads(body.decode('utf-8'))
                    audio_data = data.get('audio')
                    
                    # In a real implementation, this would forward the audio to SIP/gRPC
                    # For this mock, we'll just echo it back (loopback)
                    
                    # Send response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    
                    # Return the same audio data as loopback
                    response = {
                        'status': 'success',
                        'audio': audio_data  # Echo back the same audio data
                    }
                    self.wfile.write(json.dumps(response).encode())
                    
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No audio data provided'}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Endpoint not found'}).encode())

def run_server(port=8080, directory=None):
    """Run the server"""
    if directory:
        os.chdir(directory)
    
    handler = SimpleHandler
    server = socketserver.TCPServer(('', port), handler)
    print(f"Server running at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    directory = sys.argv[2] if len(sys.argv) > 2 else None
    run_server(port, directory)
EOF
fi

# Make the server script executable
chmod +x "$SCRIPT_DIR/simple_server.py"

# Create the direct UI directory
mkdir -p "$SCRIPT_DIR/direct_ui"

# Create the HTML file
cat > "$SCRIPT_DIR/direct_ui/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SIP to gRPC Gateway</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
      color: #333;
    }
    header {
      background-color: #2196f3;
      color: white;
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem;
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .card {
      background-color: white;
      border-radius: 4px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 1rem;
    }
    .card h2 {
      margin-top: 0;
      font-size: 1.2rem;
    }
    .panel {
      background-color: white;
      border-radius: 4px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 1rem;
      margin-bottom: 1rem;
    }
    .chip {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 16px;
      font-size: 0.8rem;
      margin-right: 0.5rem;
    }
    .success {
      background-color: #e8f5e9;
      color: #2e7d32;
      border: 1px solid #2e7d32;
    }
    .error {
      background-color: #ffebee;
      color: #c62828;
      border: 1px solid #c62828;
    }
    button {
      background-color: #2196f3;
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      cursor: pointer;
    }
    button:hover {
      background-color: #1976d2;
    }
    button:disabled {
      background-color: #b0b0b0;
      cursor: not-allowed;
    }
    button.recording {
      background-color: #f44336;
    }
    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 200px;
    }
    .loader {
      border: 4px solid #f3f3f3;
      border-top: 4px solid #2196f3;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .error-message {
      background-color: #ffebee;
      color: #c62828;
      padding: 1rem;
      border-radius: 4px;
      margin-bottom: 1rem;
    }
    .grid-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }
    .stats {
      text-align: center;
    }
    .stats h3 {
      margin-bottom: 0.5rem;
      color: #666;
    }
    .stats .number {
      font-size: 2rem;
      font-weight: bold;
      color: #2196f3;
    }
    .stats .details {
      color: #666;
      font-size: 0.9rem;
    }
    .audio-controls {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
    }
    .audio-status {
      margin-top: 0.5rem;
      font-size: 0.9rem;
      color: #666;
    }
    .visualizer {
      width: 100%;
      height: 60px;
      margin-top: 0.5rem;
      background-color: #f5f5f5;
      border-radius: 4px;
      overflow: hidden;
    }
    .visualizer-canvas {
      width: 100%;
      height: 100%;
    }
  </style>
</head>
<body>
  <header>
    <h1>SIP to gRPC Gateway</h1>
    <button onclick="fetchDashboardData()">Refresh</button>
  </header>

  <div class="container">
    <div id="error-container"></div>
    
    <div id="loading" class="loading">
      <div class="loader"></div>
    </div>
    
    <div id="dashboard-content" style="display: none;">
      <h2>Dashboard</h2>
      
      <div class="card-grid">
        <!-- Gateway Status Card -->
        <div class="card">
          <h2>Gateway Status</h2>
          <div id="gateway-status"></div>
          <div style="margin-top: 1rem;">
            <button disabled id="gateway-toggle-btn">Stop Gateway</button>
          </div>
        </div>
        
        <!-- SIP Server Card -->
        <div class="card">
          <h2>SIP Server</h2>
          <div id="sip-details"></div>
        </div>
        
        <!-- gRPC Client Card -->
        <div class="card">
          <h2>gRPC Client</h2>
          <div id="grpc-status"></div>
        </div>
        
        <!-- Audio Card -->
        <div class="card">
          <h2>Voice Communication</h2>
          <div id="audio-status" class="audio-status">Ready to speak</div>
          <div class="visualizer">
            <canvas id="audio-visualizer" class="visualizer-canvas"></canvas>
          </div>
          <div class="audio-controls">
            <button id="speak-btn">Press to Speak</button>
            <button id="stop-btn" disabled>Stop</button>
          </div>
        </div>
      </div>
      
      <div class="panel">
        <h2>Configuration Summary</h2>
        <hr>
        <div class="grid-row">
          <div class="stats">
            <h3>Endpoints</h3>
            <div id="endpoints-count" class="number">0</div>
            <div id="endpoints-list" class="details">None configured</div>
          </div>
          
          <div class="stats">
            <h3>SIP to gRPC Mappings</h3>
            <div id="sip-grpc-count" class="number">0</div>
          </div>
          
          <div class="stats">
            <h3>gRPC to SIP Mappings</h3>
            <div id="grpc-sip-count" class="number">0</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // API Base URL - adjust this to point to your backend
    const API_BASE_URL = window.location.origin;
    
    // Function to fetch dashboard data
    async function fetchDashboardData() {
      document.getElementById('loading').style.display = 'flex';
      document.getElementById('dashboard-content').style.display = 'none';
      document.getElementById('error-container').innerHTML = '';
      
      try {
        // Fetch status
        const statusResponse = await fetch(`${API_BASE_URL}/status`);
        if (!statusResponse.ok) {
          throw new Error(`API error: ${statusResponse.status}`);
        }
        const status = await statusResponse.json();
        
        // Fetch config
        const configResponse = await fetch(`${API_BASE_URL}/config`);
        if (!configResponse.ok) {
          throw new Error(`API error: ${configResponse.status}`);
        }
        const config = await configResponse.json();
        
        // Update the UI
        updateDashboard(status, config);
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
      } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error-container').innerHTML = `
          <div class="error-message">
            Failed to load gateway status. Please ensure the backend is running at ${API_BASE_URL}.<br>
            Error: ${error.message}
          </div>
        `;
      }
    }
    
    // Function to update the dashboard UI
    function updateDashboard(status, config) {
      // Gateway status
      const gatewayStatusEl = document.getElementById('gateway-status');
      if (status.running) {
        gatewayStatusEl.innerHTML = '<span class="chip success">✓ Running</span>';
        document.getElementById('gateway-toggle-btn').textContent = 'Stop Gateway';
      } else {
        gatewayStatusEl.innerHTML = '<span class="chip error">✗ Stopped</span>';
        document.getElementById('gateway-toggle-btn').textContent = 'Start Gateway';
      }
      
      // SIP Server details
      const sipDetailsEl = document.getElementById('sip-details');
      sipDetailsEl.innerHTML = `
        <div>Host: ${status.sip_server.host || 'N/A'}</div>
        <div>Port: ${status.sip_server.port || 'N/A'}</div>
        <div style="margin-top: 0.5rem;">
          ${status.sip_server.udp_enabled ? '<span class="chip success">UDP</span>' : '<span class="chip">UDP</span>'}
          ${status.sip_server.tcp_enabled ? '<span class="chip success">TCP</span>' : '<span class="chip">TCP</span>'}
        </div>
      `;
      
      // gRPC Client status
      const grpcStatusEl = document.getElementById('grpc-status');
      if (status.grpc_client.connected) {
        grpcStatusEl.innerHTML = '<span class="chip success">✓ Connected</span>';
      } else {
        grpcStatusEl.innerHTML = '<span class="chip error">✗ Disconnected</span>';
      }
      
      // Configuration summary
      const endpoints = config.grpc?.endpoints || [];
      document.getElementById('endpoints-count').textContent = endpoints.length;
      document.getElementById('endpoints-list').textContent = 
        endpoints.length > 0 ? endpoints.map(e => e.name).join(', ') : 'None configured';
      
      const sipMappings = Object.keys(config.mapping?.sip_to_grpc || {}).length;
      document.getElementById('sip-grpc-count').textContent = sipMappings;
      
      const grpcMappings = Object.keys(config.mapping?.grpc_to_sip || {}).length;
      document.getElementById('grpc-sip-count').textContent = grpcMappings;
    }
    
    // Audio functionality
    document.addEventListener('DOMContentLoaded', () => {
      fetchDashboardData();
      setupAudioFunctionality();
    });
    
    function setupAudioFunctionality() {
      const speakBtn = document.getElementById('speak-btn');
      const stopBtn = document.getElementById('stop-btn');
      const audioStatus = document.getElementById('audio-status');
      const visualizer = document.getElementById('audio-visualizer');
      const visualizerCtx = visualizer.getContext('2d');
      
      // Set canvas size
      visualizer.width = visualizer.offsetWidth;
      visualizer.height = visualizer.offsetHeight;
      
      // Audio contexts and streams
      let audioContext;
      let mediaStream;
      let mediaRecorder;
      let audioChunks = [];
      let loopbackAudio = [];
      let audioPlayer = new Audio();
      let analyser;
      let dataArray;
      let animationFrameId;
      
      // Draw the visualizer
      function drawVisualizer() {
        animationFrameId = requestAnimationFrame(drawVisualizer);
        
        if (analyser) {
          analyser.getByteTimeDomainData(dataArray);
          
          visualizerCtx.fillStyle = 'rgb(245, 245, 245)';
          visualizerCtx.fillRect(0, 0, visualizer.width, visualizer.height);
          
          visualizerCtx.lineWidth = 2;
          visualizerCtx.strokeStyle = 'rgb(33, 150, 243)';
          visualizerCtx.beginPath();
          
          const sliceWidth = visualizer.width / dataArray.length;
          let x = 0;
          
          for (let i = 0; i < dataArray.length; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * visualizer.height / 2;
            
            if (i === 0) {
              visualizerCtx.moveTo(x, y);
            } else {
              visualizerCtx.lineTo(x, y);
            }
            
            x += sliceWidth;
          }
          
          visualizerCtx.lineTo(visualizer.width, visualizer.height / 2);
          visualizerCtx.stroke();
        }
      }
      
      // Function to start audio recording
      async function startRecording() {
        try {
          // Request microphone access
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          
          // Set up audio context and analyzer
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          const source = audioContext.createMediaStreamSource(mediaStream);
          analyser = audioContext.createAnalyser();
          analyser.fftSize = 2048;
          source.connect(analyser);
          
          // Set up data array for visualization
          dataArray = new Uint8Array(analyser.frequencyBinCount);
          
          // Start visualization
          drawVisualizer();
          
          // Set up media recorder
          mediaRecorder = new MediaRecorder(mediaStream);
          audioChunks = [];
          loopbackAudio = [];
          
          // Handle data available event
          mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
              audioChunks.push(event.data);
              
              // Convert blob to base64
              const reader = new FileReader();
              reader.readAsDataURL(event.data);
              reader.onloadend = async () => {
                const base64data = reader.result.split(',')[1];
                
                // Send to server for loopback
                try {
                  const response = await fetch(`${API_BASE_URL}/stream-audio`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                      audio: base64data
                    })
                  });
                  
                  if (response.ok) {
                    const data = await response.json();
                    if (data.audio) {
                      // Store loopback audio
                      const binaryString = atob(data.audio);
                      const bytes = new Uint8Array(binaryString.length);
                      for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                      }
                      loopbackAudio.push(new Blob([bytes], { type: 'audio/webm' }));
                    }
                  }
                } catch (error) {
                  console.error('Error sending audio to server:', error);
                  audioStatus.textContent = 'Error: Failed to communicate with server';
                }
              };
            }
          };
          
          // Start recording
          mediaRecorder.start(500); // Capture in 500ms chunks for streaming
          audioStatus.textContent = 'Recording... Press Stop when finished';
          speakBtn.disabled = true;
          stopBtn.disabled = false;
          speakBtn.classList.add('recording');
        } catch (error) {
          console.error('Error starting recording:', error);
          audioStatus.textContent = 'Error: Microphone access denied or unavailable';
        }
      }
      
      // Function to stop recording
      function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
        }
        
        // Stop visualization
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
        
        // Stop microphone stream
        if (mediaStream) {
          mediaStream.getTracks().forEach(track => track.stop());
        }
        
        // Clean up audio context
        if (audioContext) {
          audioContext.close();
        }
        
        // Reset UI
        audioStatus.textContent = 'Processing audio...';
        speakBtn.disabled = false;
        stopBtn.disabled = true;
        speakBtn.classList.remove('recording');
        
        // Play back loopback audio after a small delay
        setTimeout(() => {
          if (loopbackAudio.length > 0) {
            const loopbackBlob = new Blob(loopbackAudio, { type: 'audio/webm' });
            const url = URL.createObjectURL(loopbackBlob);
            
            audioPlayer.src = url;
            audioPlayer.onloadedmetadata = () => {
              audioStatus.textContent = 'Playing loopback audio...';
              audioPlayer.play();
            };
            audioPlayer.onended = () => {
              audioStatus.textContent = 'Ready to speak';
              URL.revokeObjectURL(url);
            };
          } else {
            audioStatus.textContent = 'No audio received from server';
          }
        }, 500);
      }
      
      // Event listeners
      speakBtn.addEventListener('click', startRecording);
      stopBtn.addEventListener('click', stopRecording);
    }
  </script>
</body>
</html>
EOF

# Determine a port that doesn't conflict with an existing one
PORT=8080
while nc -z localhost $PORT 2>/dev/null; do
    PORT=$((PORT+1))
    if [ $PORT -gt 8100 ]; then
        echo "Could not find an available port in the range 8080-8100"
        exit 1
    fi
done

# Start the server
echo "Starting API server on port $PORT..."
python3 "$SCRIPT_DIR/simple_server.py" $PORT "$SCRIPT_DIR/direct_ui" &
SERVER_PID=$!

# Wait for the server to start
sleep 1

# Open the browser (if available)
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

# Handle shutdown
trap "kill $SERVER_PID; echo 'Server stopped'" SIGINT SIGTERM

# Wait for the server to finish
wait $SERVER_PID