#!/usr/bin/env python3
"""
Enhanced server for the SIP to gRPC Gateway UI.
Includes audio streaming and protocol tracing functionality.
"""

import http.server
import json
import os
import socketserver
import io
import sys
import time
import base64
import uuid
import datetime
import struct
import threading
import logging

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logging with both console and file output
logger = logging.getLogger('sip-grpc-gateway')
# Remove any existing handlers to avoid duplicates
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
logger.setLevel(logging.DEBUG)

# Custom formatter for protocol messages
class ProtocolFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, 'protocol_message') and record.protocol_message:
            # Add special formatting for protocol messages
            protocol = getattr(record, 'protocol', 'UNKNOWN')
            direction = getattr(record, 'direction', 'UNKNOWN')
            
            # Format the timestamp
            timestamp = self.formatTime(record, self.datefmt)
            
            # Create a formatted header with direction indicators
            if direction == 'client_to_sip':
                header = f"\n{'=' * 80}\n⬇️  CLIENT TO SIP - {protocol} - {timestamp}\n{'-' * 80}"
            elif direction == 'sip_to_grpc':
                header = f"\n{'=' * 80}\n➡️  SIP TO GRPC - {protocol} - {timestamp}\n{'-' * 80}"
            elif direction == 'grpc_to_sip':
                header = f"\n{'=' * 80}\n⬅️  GRPC TO SIP - {protocol} - {timestamp}\n{'-' * 80}"
            elif direction == 'sip_to_client':
                header = f"\n{'=' * 80}\n⬆️  SIP TO CLIENT - {protocol} - {timestamp}\n{'-' * 80}"
            else:
                header = f"\n{'=' * 80}\n🔄 {direction.upper()} - {protocol} - {timestamp}\n{'-' * 80}"
            
            # Format the message and add footer
            formatted_msg = f"{header}\n{record.getMessage()}\n{'-' * 80}"
            return formatted_msg
        else:
            # Use standard formatting for regular log messages
            return super().format(record)

# Console handler with custom protocol message formatting
console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
console_handler.setLevel(logging.INFO)
console_format = ProtocolFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# File handler with DEBUG level
file_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'trace_server.log'))
file_handler.setLevel(logging.DEBUG)
file_format = ProtocolFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Add both handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Helper function for logging protocol messages with pretty formatting
def log_protocol_message(direction, protocol, message, level=logging.INFO):
    """Log a protocol message with special formatting"""
    if isinstance(message, (dict, list)):
        # Pretty print JSON
        formatted_message = json.dumps(message, indent=2)
    else:
        # Use the message as is
        formatted_message = str(message)
    
    # Force the log level to INFO to ensure protocol messages are displayed
    level = logging.INFO
    
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname='',
        lineno=0,
        msg=formatted_message,
        args=(),
        exc_info=None
    )
    # Add custom attributes
    record.protocol_message = True
    record.protocol = protocol
    record.direction = direction
    
    # Ensure all handlers process this message regardless of their level
    for handler in logger.handlers:
        if handler.level > level:
            old_level = handler.level
            handler.setLevel(level)
            logger.handle(record)
            handler.setLevel(old_level)
            return
    
    # If we didn't return above, just handle normally
    logger.handle(record)

logger.info("Starting SIP to gRPC Gateway with tracing capability")

# PCAP file constants
PCAP_MAGIC = 0xa1b2c3d4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
PCAP_THISZONE = 0
PCAP_SIGFIGS = 0
PCAP_SNAPLEN = 65535
PCAP_NETWORK = 1  # Ethernet

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

# Trace management
class TracingManager:
    def __init__(self):
        self.traces = {}
        self.active_trace_id = None
        self.lock = threading.Lock()
        
    def start_trace(self):
        """Start a new trace session and return its ID"""
        with self.lock:
            # Make sure logs directory exists
            os.makedirs(LOGS_DIR, exist_ok=True)
            
            trace_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pcap_path = os.path.join(LOGS_DIR, f"sip_grpc_trace_{timestamp}_{trace_id[:8]}.pcap")
            
            try:
                # Create PCAP file with header
                with open(pcap_path, 'wb') as f:
                    # Write global header
                    f.write(struct.pack(
                        '=IHHiIII',
                        PCAP_MAGIC,
                        PCAP_VERSION_MAJOR,
                        PCAP_VERSION_MINOR,
                        PCAP_THISZONE,
                        PCAP_SIGFIGS,
                        PCAP_SNAPLEN,
                        PCAP_NETWORK
                    ))
                
                self.traces[trace_id] = {
                    'id': trace_id,
                    'file_path': pcap_path,
                    'start_time': time.time(),
                    'active': True,
                    'packets': []
                }
                
                self.active_trace_id = trace_id
                
                # Log colorful trace start message
                start_message = f"""
🔍 Protocol Trace Started
   Trace ID:     {trace_id}
   PCAP File:    {pcap_path}
   Time:         {timestamp}
   
   All SIP and gRPC messages will be captured to this trace file.
   The file can be opened with Wireshark for detailed analysis.
"""
                logger.info(start_message)
                
                return trace_id
            except Exception as e:
                logger.error(f"Failed to create trace file {pcap_path}: {e}")
                raise
    
    def stop_trace(self, trace_id=None):
        """Stop an active trace"""
        with self.lock:
            if trace_id is None:
                trace_id = self.active_trace_id
                
            if trace_id in self.traces:
                self.traces[trace_id]['active'] = False
                if self.active_trace_id == trace_id:
                    self.active_trace_id = None
                
                duration = time.time() - self.traces[trace_id]['start_time']
                packet_count = len(self.traces[trace_id]['packets'])
                file_path = self.traces[trace_id]['file_path']
                
                # Calculate protocol counts
                sip_to_grpc_count = sum(1 for p in self.traces[trace_id]['packets'] if p['direction'] == 'sip_to_grpc')
                grpc_to_sip_count = sum(1 for p in self.traces[trace_id]['packets'] if p['direction'] == 'grpc_to_sip')
                client_packets = sum(1 for p in self.traces[trace_id]['packets'] if p['direction'] in ['client_to_sip', 'sip_to_client'])
                
                # Log colorful trace stop message
                stop_message = f"""
⏹️ Protocol Trace Stopped
   Trace ID:     {trace_id}
   PCAP File:    {file_path}
   Duration:     {duration:.2f} seconds
   Total Packets: {packet_count}
   
   Protocol Breakdown:
   • SIP ➡️ gRPC:   {sip_to_grpc_count} packets
   • gRPC ➡️ SIP:   {grpc_to_sip_count} packets
   • Client ↔ SIP:  {client_packets} packets
   
   The PCAP file can be downloaded from the web interface
   or opened directly with Wireshark at: {file_path}
"""
                logger.info(stop_message)
                
                return {
                    'id': trace_id,
                    'file_path': file_path,
                    'duration': duration,
                    'packet_count': packet_count,
                    'sip_to_grpc_count': sip_to_grpc_count,
                    'grpc_to_sip_count': grpc_to_sip_count,
                    'client_packets': client_packets
                }
            return None
    
    def add_packet(self, direction, protocol, data, src_addr="127.0.0.1", dst_addr="127.0.0.1", src_port=5060, dst_port=50051, trace_id=None):
        """Add a packet to the trace"""
        with self.lock:
            try:
                if trace_id is None:
                    trace_id = self.active_trace_id
                    if trace_id is None:
                        # No active trace
                        logger.debug("No active trace found for packet addition")
                        return None
                    
                if trace_id in self.traces and self.traces[trace_id]['active']:
                    trace = self.traces[trace_id]
                    
                    # Create mock packet
                    now = time.time()
                    seconds = int(now)
                    microseconds = int((now - seconds) * 1000000)
                    
                    # Validate ports
                    try:
                        src_port = int(src_port)
                        dst_port = int(dst_port)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid port values: src={src_port}, dst={dst_port}. Using defaults.")
                        src_port = 5060
                        dst_port = 50051
                    
                    # Create mock ethernet, IP and UDP/TCP headers for visualization purposes
                    packet_data = self._create_mock_packet(direction, protocol, data, src_addr, dst_addr, src_port, dst_port)
                    
                    # Packet header for PCAP
                    packet_header = struct.pack('=IIII', seconds, microseconds, len(packet_data), len(packet_data))
                    
                    # Append to PCAP file
                    try:
                        # Ensure file exists before writing
                        if not os.path.exists(trace['file_path']):
                            logger.warning(f"Trace file {trace['file_path']} not found, creating new header")
                            with open(trace['file_path'], 'wb') as f:
                                # Write global header
                                f.write(struct.pack(
                                    '=IHHiIII',
                                    PCAP_MAGIC,
                                    PCAP_VERSION_MAJOR,
                                    PCAP_VERSION_MINOR,
                                    PCAP_THISZONE,
                                    PCAP_SIGFIGS,
                                    PCAP_SNAPLEN,
                                    PCAP_NETWORK
                                ))
                        
                        # Now append packet data
                        with open(trace['file_path'], 'ab') as f:
                            f.write(packet_header)
                            f.write(packet_data)
                            
                        logger.debug(f"Added packet to trace {trace_id}: {direction} {protocol} {len(packet_data)} bytes")
                    except Exception as e:
                        logger.error(f"Failed to write packet to trace file: {e}")
                        # Continue with in-memory recording even if file write fails
                    
                    # Get data size safely
                    if isinstance(data, (bytes, str)):
                        data_size = len(data)
                    elif isinstance(data, (dict, list)):
                        data_size = len(json.dumps(data))
                    else:
                        data_size = len(str(data))
                    
                    # Add to our in-memory list
                    packet_info = {
                        'timestamp': now,
                        'direction': direction,
                        'protocol': protocol,
                        'src_addr': src_addr,
                        'dst_addr': dst_addr,
                        'src_port': src_port,
                        'dst_port': dst_port,
                        'size': data_size
                    }
                    trace['packets'].append(packet_info)
                    
                    return packet_info
                else:
                    logger.debug(f"Trace {trace_id} not found or not active")
                    return None
            except Exception as e:
                logger.error(f"Error adding packet to trace: {e}")
                return None
    
    def get_trace_info(self, trace_id=None):
        """Get information about a trace"""
        with self.lock:
            if trace_id is None:
                trace_id = self.active_trace_id
                if trace_id is None:
                    # No active trace
                    return None
                    
            if trace_id in self.traces:
                trace = self.traces[trace_id]
                return {
                    'id': trace_id,
                    'file_path': trace['file_path'],
                    'start_time': trace['start_time'],
                    'active': trace['active'],
                    'packet_count': len(trace['packets']),
                    'duration': time.time() - trace['start_time']
                }
            return None
    
    def list_traces(self):
        """List all traces"""
        with self.lock:
            result = []
            for trace_id, trace in self.traces.items():
                result.append({
                    'id': trace_id,
                    'file_path': trace['file_path'],
                    'start_time': trace['start_time'],
                    'active': trace['active'],
                    'packet_count': len(trace['packets']),
                    'duration': time.time() - trace['start_time']
                })
            return result
            
    def _create_mock_packet(self, direction, protocol, data, src_addr, dst_addr, src_port, dst_port):
        """Create a mock packet with Ethernet, IP, and UDP/TCP headers for visualization"""
        try:
            # Mock MAC addresses
            if direction == "sip_to_grpc":
                src_mac = b"\x00\x11\x22\x33\x44\x55"  # SIP server MAC
                dst_mac = b"\x66\x77\x88\x99\xaa\xbb"  # gRPC server MAC
            else:
                src_mac = b"\x66\x77\x88\x99\xaa\xbb"  # gRPC server MAC
                dst_mac = b"\x00\x11\x22\x33\x44\x55"  # SIP server MAC
            
            # Ethernet header (14 bytes)
            eth_header = src_mac + dst_mac + b"\x08\x00"  # 0x0800 = IPv4
            
            # IP header (simplified, 20 bytes)
            ip_header = bytearray(20)
            ip_header[0] = 0x45  # Version=4, Header length=5 (20 bytes)
            
            # Convert data to bytes first to get accurate length
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            elif isinstance(data, dict) or isinstance(data, list):
                data_bytes = json.dumps(data).encode('utf-8')
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                data_bytes = str(data).encode('utf-8')
            
            # Convert packet length to bytes
            packet_length = 20 + (8 if protocol == "UDP" else 20) + len(data_bytes)
            ip_header[2:4] = struct.pack("!H", packet_length)  # Total length
            
            ip_header[8] = 64  # TTL
            ip_header[9] = 17 if protocol == "UDP" else 6  # Protocol (UDP=17, TCP=6)
            
            # Validate IP addresses and handle errors
            try:
                # Handle special cases for 'localhost'
                if src_addr == 'localhost':
                    src_ip_parts = [127, 0, 0, 1]
                else:
                    src_ip_parts = [int(p) for p in src_addr.split('.')]
                    
                if dst_addr == 'localhost':
                    dst_ip_parts = [127, 0, 0, 1]
                else:
                    dst_ip_parts = [int(p) for p in dst_addr.split('.')]
                
                # Ensure we have 4 parts for IPv4
                if len(src_ip_parts) != 4 or len(dst_ip_parts) != 4:
                    raise ValueError("Invalid IP address format")
                
                # Ensure each part is in valid range
                for part in src_ip_parts + dst_ip_parts:
                    if part < 0 or part > 255:
                        raise ValueError("IP address part out of range")
                
                ip_header[12:16] = bytes(src_ip_parts)
                ip_header[16:20] = bytes(dst_ip_parts)
            except Exception as e:
                logger.debug(f"IP address conversion issue, using localhost: {e}")
                # Use fallback IP addresses
                ip_header[12:16] = bytes([127, 0, 0, 1])  # localhost
                ip_header[16:20] = bytes([127, 0, 0, 1])  # localhost
            
            # UDP/TCP header (8 bytes for UDP, 20 for TCP)
            if protocol == "UDP":
                # Ensure port values are valid
                src_port = max(1, min(src_port, 65535))
                dst_port = max(1, min(dst_port, 65535))
                
                udp_header = struct.pack("!HHHH", 
                    src_port,                # Source port
                    dst_port,                # Destination port
                    8 + len(data_bytes),     # Length
                    0                        # Checksum (0 for simplicity)
                )
                transport_header = udp_header
            else:  # TCP
                # Ensure port values are valid
                src_port = max(1, min(src_port, 65535))
                dst_port = max(1, min(dst_port, 65535))
                
                tcp_header = bytearray(20)
                struct.pack_into("!HH", tcp_header, 0, src_port, dst_port)  # Source & dest ports
                tcp_header[12] = 5 << 4  # Data offset (5 * 4 = 20 bytes)
                tcp_header[13] = 0x18    # ACK and PSH flags set
                transport_header = bytes(tcp_header)
            
            # Combine all parts
            return eth_header + bytes(ip_header) + transport_header + data_bytes
            
        except Exception as e:
            logger.error(f"Error creating mock packet: {e}")
            # Return a minimal valid packet in case of error
            minimal_eth_header = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00"
            minimal_ip_header = bytearray(20)
            minimal_ip_header[0] = 0x45  # Version=4, Header length=5
            minimal_ip_header[8] = 64    # TTL
            minimal_ip_header[9] = 17    # Protocol (UDP)
            minimal_ip_header[12:16] = bytes([127, 0, 0, 1])  # localhost
            minimal_ip_header[16:20] = bytes([127, 0, 0, 1])  # localhost
            minimal_udp_header = struct.pack("!HHHH", 5060, 50051, 8, 0)
            minimal_data = b"ERROR: Failed to create proper packet"
            return minimal_eth_header + bytes(minimal_ip_header) + minimal_udp_header + minimal_data

# Create a global instance of the tracing manager
tracing_manager = TracingManager()

class EnhancedHandler(http.server.SimpleHTTPRequestHandler):
    """Enhanced handler for API requests with tracing support"""
    
    # Override the logging methods to use our logger instead of printing to console
    def log_message(self, format, *args):
        # Skip logging for common static file requests and favicon
        if (self.path.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.svg')) or 
            self.path == '/favicon.ico'):
            return
        
        # For API endpoints, do a debug level log
        if self.path.startswith('/status') or self.path.startswith('/config'):
            logger.debug(f"{self.address_string()} - {format % args}")
        else:
            # For all other endpoints, do info level
            logger.info(f"{self.address_string()} - {format % args}")
    
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
        path = self.path
        
        if path == '/status':
            # Return status
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(STATUS).encode())
        
        elif path == '/config':
            # Return config
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(CONFIG).encode())
        
        elif path.startswith('/trace/download/'):
            # Download a trace file
            trace_id = path.split('/trace/download/')[1]
            trace_info = tracing_manager.get_trace_info(trace_id)
            
            if trace_info and os.path.exists(trace_info['file_path']):
                file_path = trace_info['file_path']
                file_size = os.path.getsize(file_path)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.tcpdump.pcap')
                self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
                self.send_header('Content-Length', str(file_size))
                self.send_cors_headers()
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': f"Trace file not found"
                }).encode())
        
        elif path == '/trace/status':
            # Get current tracing status
            active_trace = None
            if tracing_manager.active_trace_id:
                active_trace = tracing_manager.get_trace_info()
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'tracing_active': tracing_manager.active_trace_id is not None,
                'active_trace': active_trace
            }).encode())
            
        elif path == '/favicon.ico':
            # Return empty response for favicon
            self.send_response(204)
            self.end_headers()
            
        else:
            # Check if this is a request for the root path
            if path == '/':
                self.path = '/trace_dashboard.html'
                # Fall back to index.html if trace_dashboard.html doesn't exist
                if not os.path.exists(os.path.join(os.getcwd(), 'trace_dashboard.html')):
                    self.path = '/index.html'
            # Serve static files from the directory
            try:
                return super().do_GET()
            except Exception as e:
                logger.error(f"Error serving file: {e}")
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': f"File not found: {self.path}"
                }).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        path = self.path
        
        if path == '/stream-audio':
            # Handle audio streaming from client
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                try:
                    # Parse the audio data (base64 encoded in JSON)
                    data = json.loads(body.decode('utf-8'))
                    audio_data = data.get('audio')
                    trace_id = data.get('trace_id')
                    
                    # Ensure audio_data is not None
                    if audio_data is None:
                        audio_data = ""
                    
                    # In a real implementation, this would forward the audio to SIP/gRPC
                    # For this mock, we'll simulate the SIP -> gRPC -> SIP flow with traces
                    
                    # Add verbose protocol logging message to show we're processing audio
                    logger.info(f"Processing audio stream: {len(audio_data) if audio_data else 0} bytes")

                    # Try to generate trace packets, but don't fail if it errors
                    try:
                        # If we have a trace ID, add packets to the trace
                        if trace_id or tracing_manager.active_trace_id:
                            # 1. Client -> SIP Server (client audio data)
                            client_ip = self.client_address[0]
                            sip_server_ip = CONFIG['sip']['host']
                            sip_port = CONFIG['sip']['port']
                        
                            # Create SIP INVITE message (simplified)
                            sip_invite = f"""INVITE sip:grpc@{sip_server_ip}:{sip_port} SIP/2.0
Via: SIP/2.0/UDP {client_ip}:12345
From: <sip:client@{client_ip}>;tag=123
To: <sip:grpc@{sip_server_ip}>
Call-ID: {uuid.uuid4()}@{client_ip}
CSeq: 1 INVITE
Content-Type: audio/webm
Content-Length: {len(audio_data) if audio_data else 0}

{audio_data[:30]}..."""
                            
                            # Log the SIP INVITE message with formatting
                            log_protocol_message(
                                direction="client_to_sip",
                                protocol="SIP INVITE",
                                message=sip_invite
                            )
                            
                            tracing_manager.add_packet(
                                direction="client_to_sip",
                                protocol="UDP",
                                data=sip_invite,
                                src_addr=client_ip,
                                dst_addr=sip_server_ip,
                                src_port=12345,  # Random client port
                                dst_port=sip_port,
                                trace_id=trace_id
                            )
                            
                            # 2. SIP Server -> gRPC Server (gRPC stream request)
                            grpc_endpoint = CONFIG['grpc']['endpoints'][0]
                            grpc_server_ip = grpc_endpoint['host']
                            grpc_port = grpc_endpoint['port']
                            
                            # Create gRPC request (simplified representation for PCAP)
                            grpc_request = {
                                "method": f"/{grpc_endpoint['service']}/StreamAudio",
                                "headers": {
                                    "content-type": "application/grpc"
                                },
                                "payload": {
                                    "audio_data": audio_data[:30] + "..." if audio_data else None,
                                    "encoding": "webm",
                                    "call_id": f"{uuid.uuid4()}"
                                }
                            }
                            
                            # Log the gRPC request with formatting
                            log_protocol_message(
                                direction="sip_to_grpc",
                                protocol="gRPC Request",
                                message=grpc_request
                            )
                            
                            tracing_manager.add_packet(
                                direction="sip_to_grpc",
                                protocol="TCP",
                                data=grpc_request,
                                src_addr=sip_server_ip,
                                dst_addr=grpc_server_ip,
                                src_port=sip_port,
                                dst_port=grpc_port,
                                trace_id=trace_id
                            )
                            
                            # 3. gRPC Server -> SIP Server (gRPC stream response - loopback)
                            grpc_response = {
                                "status": "OK",
                                "headers": {
                                    "content-type": "application/grpc"
                                },
                                "payload": {
                                    "audio_data": audio_data[:30] + "..." if audio_data else None,
                                    "encoding": "webm"
                                }
                            }
                            
                            # Log the gRPC response with formatting
                            log_protocol_message(
                                direction="grpc_to_sip",
                                protocol="gRPC Response",
                                message=grpc_response
                            )
                            
                            tracing_manager.add_packet(
                                direction="grpc_to_sip",
                                protocol="TCP",
                                data=grpc_response,
                                src_addr=grpc_server_ip,
                                dst_addr=sip_server_ip,
                                src_port=grpc_port,
                                dst_port=sip_port,
                                trace_id=trace_id
                            )
                            
                            # 4. SIP Server -> Client (SIP 200 OK with loopback audio)
                            sip_ok = f"""SIP/2.0 200 OK
Via: SIP/2.0/UDP {client_ip}:12345
From: <sip:client@{client_ip}>;tag=123
To: <sip:grpc@{sip_server_ip}>;tag=456
Call-ID: {uuid.uuid4()}@{client_ip}
CSeq: 1 INVITE
Content-Type: audio/webm
Content-Length: {len(audio_data) if audio_data else 0}

{audio_data[:30]}..."""
                            
                            # Log the SIP response with formatting
                            log_protocol_message(
                                direction="sip_to_client",
                                protocol="SIP 200 OK",
                                message=sip_ok
                            )
                            
                            tracing_manager.add_packet(
                                direction="sip_to_client",
                                protocol="UDP",
                                data=sip_ok,
                                src_addr=sip_server_ip,
                                dst_addr=client_ip,
                                src_port=sip_port,
                                dst_port=12345,  # Random client port
                                trace_id=trace_id
                            )
                    except Exception as e:
                        logger.error(f"Error adding trace packet: {e}")
                    
                    # Send response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    
                    # Return the same audio data as loopback plus trace info
                    try:
                        # Validate audio data is not too large (might cause JSON encoding issues)
                        # If it's very large, truncate it for the response but log it
                        if audio_data and len(audio_data) > 1024 * 1024: # 1MB
                            logger.warning(f"Audio data too large ({len(audio_data)} bytes), truncating for response")
                            audio_data_response = audio_data[:1024 * 1024] # 1MB limit
                        else:
                            audio_data_response = audio_data
                            
                        response = {
                            'status': 'success',
                            'audio': audio_data_response,  # Echo back the audio data
                            'trace_id': trace_id or tracing_manager.active_trace_id,
                            'trace_active': tracing_manager.active_trace_id is not None
                        }
                        self.wfile.write(json.dumps(response).encode())
                    except Exception as e:
                        logger.error(f"Error sending audio response: {e}")
                        error_response = {
                            'status': 'error',
                            'message': 'Error processing audio data',
                            'trace_id': trace_id or tracing_manager.active_trace_id,
                            'trace_active': tracing_manager.active_trace_id is not None
                        }
                        self.wfile.write(json.dumps(error_response).encode())
                    
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
                
        elif path == '/trace/start':
            # Start a new trace
            try:
                # Get the request body if present
                content_length = int(self.headers.get('Content-Length', 0))
                request_data = {}
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    try:
                        request_data = json.loads(body.decode('utf-8'))
                    except json.JSONDecodeError:
                        pass
                
                # Start the trace
                trace_id = tracing_manager.start_trace()
                logger.info(f"Started trace successfully with ID: {trace_id}")
                
                # Add an initial set of test messages to validate protocol logging
                try:
                    # Generate test messages for each protocol direction to ensure protocol logging works
                    client_ip = self.client_address[0]
                    sip_server_ip = CONFIG['sip']['host']
                    sip_port = CONFIG['sip']['port']
                    
                    # 1. Create an example SIP message for testing the logger
                    test_sip_message = f"""INVITE sip:test@{sip_server_ip}:{sip_port} SIP/2.0
Via: SIP/2.0/UDP {client_ip}:12345
From: <sip:test@{client_ip}>;tag=123
To: <sip:test@{sip_server_ip}>
Call-ID: test-call@{client_ip}
CSeq: 1 INVITE
Content-Type: text/plain
Content-Length: 4

Test"""
                    
                    # 2. Create an example gRPC message for testing
                    test_grpc_message = {
                        "method": "/example.Test/TestCall",
                        "headers": {
                            "content-type": "application/grpc"
                        },
                        "payload": {
                            "message": "Test gRPC message for protocol logging",
                            "timestamp": time.time()
                        }
                    }
                    
                    # 3. Create an example response
                    test_sip_response = f"""SIP/2.0 200 OK
Via: SIP/2.0/UDP {client_ip}:12345
From: <sip:test@{client_ip}>;tag=123
To: <sip:test@{sip_server_ip}>;tag=456
Call-ID: test-call@{client_ip}
CSeq: 1 INVITE
Content-Type: text/plain
Content-Length: 13

Test response"""
                    
                    # Log the test messages
                    log_protocol_message(
                        direction="client_to_sip",
                        protocol="SIP INVITE (Test)",
                        message=test_sip_message
                    )
                    
                    log_protocol_message(
                        direction="sip_to_grpc",
                        protocol="gRPC Request (Test)",
                        message=test_grpc_message
                    )
                    
                    log_protocol_message(
                        direction="grpc_to_sip",
                        protocol="gRPC Response (Test)",
                        message={"status": "OK", "message": "Test response message"}
                    )
                    
                    log_protocol_message(
                        direction="sip_to_client",
                        protocol="SIP 200 OK (Test)",
                        message=test_sip_response
                    )
                    
                except Exception as log_error:
                    logger.error(f"Error generating test protocol messages: {log_error}")
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'trace_id': trace_id,
                    'message': f"Trace started. Packets will be captured in PCAP format.",
                    'verbose_enabled': True
                }).encode())
            except Exception as e:
                logger.error(f"Error starting trace: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': f"Failed to start trace: {str(e)}"
                }).encode())
            
        elif path == '/trace/stop':
            # Stop the active trace
            content_length = int(self.headers.get('Content-Length', 0))
            trace_id = None
            if content_length > 0:
                body = self.rfile.read(content_length)
                try:
                    data = json.loads(body.decode('utf-8'))
                    trace_id = data.get('trace_id')
                except:
                    pass
                    
            trace_info = tracing_manager.stop_trace(trace_id)
            if trace_info:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'trace_info': trace_info,
                    'message': f"Trace stopped. {trace_info['packet_count']} packets captured."
                }).encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': "No active trace to stop"
                }).encode())
                
        elif path == '/trace/list':
            # List all traces
            traces = tracing_manager.list_traces()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'traces': traces,
                'active_trace_id': tracing_manager.active_trace_id
            }).encode())
            
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
    
    handler = EnhancedHandler
    server = socketserver.TCPServer(('', port), handler)
    
    # Print colorful server banner
    banner = f"""
{'=' * 80}
📡  SIP to gRPC Gateway with Protocol Tracing
{'=' * 80}
🔌 Server running at: http://localhost:{port}
🔍 Protocol tracing: Enabled (SIP ↔ gRPC)
📊 Dashboard UI:      http://localhost:{port}/trace_dashboard.html
📁 PCAP output:       {os.path.abspath(LOGS_DIR)}
{'=' * 80}
Press Ctrl+C to stop the server
    """
    print(banner)
    
    # Log server start
    logger.info(f"Server started on port {port}")
    logger.info(f"Serving files from {os.getcwd() if not directory else directory}")
    
    server.serve_forever()

if __name__ == "__main__":
    # Unbuffer stdout
    sys.stdout.reconfigure(line_buffering=True)
    
    # Parse command line arguments
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    directory = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Log startup
    logger.info(f"Starting server with explicit unbuffered stdout")
    
    # Run the server
    run_server(port, directory)