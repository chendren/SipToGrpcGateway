#!/usr/bin/env python3
"""
Simple mock API server for the SIP to gRPC Gateway.
This provides a simplified API interface for the frontend without all the complexity of the real backend.
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.parse

# Get the config path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')

# Load the config
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

class MockAPIHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for the mock API server"""
    
    def send_json_response(self, data, status=200):
        """Helper to send JSON responses"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def read_json_body(self):
        """Read and parse JSON from request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return None
        return {}
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        path = urllib.parse.urlparse(self.path).path
        
        # API endpoints
        if path == '/status':
            self.send_json_response(STATUS)
        
        elif path == '/config':
            self.send_json_response(CONFIG)
        
        elif path == '/endpoints':
            endpoints = CONFIG.get('grpc', {}).get('endpoints', [])
            self.send_json_response(endpoints)
        
        elif path == '/mappings':
            mappings = CONFIG.get('mapping', {})
            self.send_json_response(mappings)
        
        # Handle favicon.ico requests
        elif path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        
        # Serve static files
        else:
            if path == '/':
                self.path = '/index.html'
            try:
                return super().do_GET()
            except:
                self.send_error(404, 'File not found')
    
    def do_POST(self):
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/endpoints':
            # Add a new endpoint
            data = self.read_json_body()
            if data is None:
                self.send_error(400, 'Invalid JSON')
                return
            
            # Add to config
            endpoints = CONFIG.setdefault('grpc', {}).setdefault('endpoints', [])
            endpoints.append(data)
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': 'Endpoint added successfully',
                'endpoint': data
            })
        
        else:
            self.send_error(404, 'Not found')
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/config':
            # Update entire config
            data = self.read_json_body()
            if data is None:
                self.send_error(400, 'Invalid JSON')
                return
            
            # Update config
            global CONFIG
            CONFIG = data
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': 'Configuration updated successfully'
            })
        
        elif path.startswith('/mappings/sip_to_grpc/'):
            # Update SIP to gRPC mapping
            method = path.split('/')[-1]
            data = self.read_json_body()
            if data is None:
                self.send_error(400, 'Invalid JSON')
                return
            
            # Update mapping
            CONFIG.setdefault('mapping', {}).setdefault('sip_to_grpc', {})[method] = data
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': f'SIP to gRPC mapping for "{method}" updated successfully',
                'mapping': data
            })
        
        elif path.startswith('/mappings/grpc_to_sip/'):
            # Update gRPC to SIP mapping
            key = path.split('/')[-1]
            data = self.read_json_body()
            if data is None:
                self.send_error(400, 'Invalid JSON')
                return
            
            # Update mapping
            CONFIG.setdefault('mapping', {}).setdefault('grpc_to_sip', {})[key] = data
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': f'gRPC to SIP mapping for "{key}" updated successfully',
                'mapping': data
            })
        
        else:
            self.send_error(404, 'Not found')
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path.startswith('/endpoints/'):
            # Delete endpoint
            name = path.split('/')[-1]
            
            # Find and remove endpoint
            endpoints = CONFIG.get('grpc', {}).get('endpoints', [])
            original_count = len(endpoints)
            CONFIG['grpc']['endpoints'] = [e for e in endpoints if e['name'] != name]
            
            if len(CONFIG['grpc']['endpoints']) == original_count:
                self.send_error(404, 'Endpoint not found')
                return
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': f'Endpoint "{name}" deleted successfully'
            })
        
        elif path.startswith('/mappings/sip_to_grpc/'):
            # Delete SIP to gRPC mapping
            method = path.split('/')[-1]
            
            # Check if mapping exists
            mappings = CONFIG.get('mapping', {}).get('sip_to_grpc', {})
            if method not in mappings:
                self.send_error(404, 'Mapping not found')
                return
            
            # Delete mapping
            del mappings[method]
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': f'SIP to gRPC mapping for "{method}" deleted successfully'
            })
        
        elif path.startswith('/mappings/grpc_to_sip/'):
            # Delete gRPC to SIP mapping
            key = path.split('/')[-1]
            
            # Check if mapping exists
            mappings = CONFIG.get('mapping', {}).get('grpc_to_sip', {})
            if key not in mappings:
                self.send_error(404, 'Mapping not found')
                return
            
            # Delete mapping
            del mappings[key]
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(CONFIG, f, indent=2)
            
            self.send_json_response({
                'status': f'gRPC to SIP mapping for "{key}" deleted successfully'
            })
        
        else:
            self.send_error(404, 'Not found')


def run_server(port=8080, directory=None):
    """Run the HTTP server"""
    if directory:
        os.chdir(directory)
    
    handler = MockAPIHandler
    handler.protocol_version = "HTTP/1.1"
    
    server = socketserver.ThreadingTCPServer(('', port), handler)
    server.allow_reuse_address = True
    
    print(f"Mock API server running on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run the mock API server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on (default: 8080)')
    parser.add_argument('--directory', type=str, help='Directory to serve static files from')
    
    args = parser.parse_args()
    run_server(args.port, args.directory)