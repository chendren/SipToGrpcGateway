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
            # Check if this is a request for the root path
            if self.path == '/':
                self.path = '/trace_dashboard.html'
                # Fall back to index.html if trace_dashboard.html doesn't exist
                if not os.path.exists(os.path.join(os.getcwd(), 'trace_dashboard.html')):
                    self.path = '/index.html'
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
