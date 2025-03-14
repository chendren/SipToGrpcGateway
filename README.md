<<<<<<< HEAD
# SIP to gRPC Gateway

This project demonstrates a gateway application that converts between SIP (Session Initiation Protocol) and gRPC (Google Remote Procedure Call) protocols. It includes a visual web interface that shows the protocol conversion in action.

## Features

- **Voice Communication**: Press-to-speak functionality with microphone input
- **Protocol Conversion**: Converts between SIP and gRPC protocols in real-time
- **Protocol Tracing**: Visualizes the flow of data through the gateway
- **PCAP Generation**: Creates Wireshark-compatible packet captures for analysis

## Components

- **SIP Server**: Handles SIP protocol (UDP/5060)
- **gRPC Client**: Connects to gRPC services (TCP/50051)
- **Web Interface**: Interactive UI for demonstrating the protocol conversion

## Visual Protocol Flow

The interface includes a visual representation of the protocol flow:

1. Audio is captured from the browser microphone
2. Converted to SIP protocol format
3. Sent to the gRPC service
4. Response received from gRPC
5. Converted back to SIP
6. Audio is played back in the browser

This demonstrates the full round-trip of voice data through the protocol conversion gateway.

## Running the Application

```bash
./run-enhanced.sh
```

Then open your browser to the displayed URL (typically http://localhost:8080).

## Capturing Protocol Traces

1. Click "Start Trace" to begin capturing protocol data
2. Record audio using "Press to Speak"
3. Click "Stop Trace" when finished
4. Download the PCAP file for analysis in Wireshark

## Implementation Details

The gateway handles protocol conversion between:
- SIP (UDP/5060) - A standard protocol for VoIP communications
- gRPC (TCP/50051) - A high-performance RPC framework

Audio is transcoded and converted between the protocols in real-time.
## Instructions for browsers


If you encounter microphone access issues, please make sure your browser:

1. Has permission to access your microphone
2. Is running from a secure context (HTTPS or localhost)
3. Has JavaScript enabled
4. Is up to date (Chrome, Firefox, or Safari recommended)

For best results, use Chrome or Firefox.

=======
# SipToGrpcGateway
>>>>>>> 16b899dd22d22daab33e43fd69739a735bdfd9c8
