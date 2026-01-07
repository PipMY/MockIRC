"""
Client

A simple IRC-like chat client that connects to a server.
Supports public/private messaging, group chats, and file downloads via TCP or UDP.

Usage: python client.py <username> <server_ip> <port>
"""

import socket
import sys
import threading
import os

# Global UDP socket used for receiving files via UDP protocol
udp_sock = None


def receive_loop(sock):
    """
    Background thread that continuously receives and processes messages from the server.
    Handles regular chat messages and file transfer protocols (TCP and UDP).
    """
    global udp_sock

    while True:
        data = sock.recv(1024)
        if not data:
            print("\n[server] Disconnected")
            break

        # Handle incoming TCP file transfer
        if data.startswith(b"FILE "):
            # Read the complete header (ends with newline)
            buffer = data
            while b"\n" not in buffer:
                buffer += sock.recv(1024)

            # Parse header to get filename and file size
            header, remainder = buffer.split(b"\n", 1)
            _, filename, size = header.decode().split(" ", 2)
            size = int(size)

            # Create user's download directory if it doesn't exist
            os.makedirs(username, exist_ok=True)
            path = os.path.join(username, filename)

            # Write file data, starting with any bytes received after the header
            received = len(remainder)
            with open(path, "wb") as f:
                f.write(remainder)
                while received < size:
                    chunk = sock.recv(min(4096, size - received))
                    f.write(chunk)
                    received += len(chunk)

            print(f"\nDownloaded {filename} ({size} bytes)\n> ", end="")
            continue

        # Handle incoming UDP file transfer notification
        if data.startswith(b"FILE_UDP "):
            # Parse the UDP file header
            _, filename, size = data.decode().split()
            size = int(size)

            # Create user's download directory if it doesn't exist
            os.makedirs(username, exist_ok=True)
            path = os.path.join(username, filename)

            # Receive file data over the pre-bound UDP socket
            received = 0
            with open(path, "wb") as f:
                while received < size:
                    chunk, _ = udp_sock.recvfrom(4096)
                    f.write(chunk)
                    received += len(chunk)

            # Clean up UDP socket after transfer completes
            udp_sock.close()
            udp_sock = None
            print(f"\nDownloaded {filename} ({size} bytes via UDP)\n> ", end="")
            continue

        # Display regular chat messages
        print("\n" + data.decode() + "\n> ", end="")


# Validate command line arguments
if len(sys.argv) != 4:
    print("Usage: python3 client.py <username> <ip> <port>")
    sys.exit(1)

username = sys.argv[1]
host = sys.argv[2]
port = int(sys.argv[3])

# Default file download protocol (can be changed with /protocol command)
download_protocol = "tcp"

# Establish connection to the server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    
    # Send username as the first message to register with the server
    s.sendall(username.encode())

    # Start background thread for receiving server messages
    threading.Thread(target=receive_loop, args=(s,), daemon=True).start()

    # Main input loop - process user commands and messages
    while True:
        msg = input("> ").strip()
        parts = msg.split()

        # Handle protocol switching (client-side only command)
        if parts[:2] == ["/protocol", "tcp"] or parts[:2] == ["/protocol", "udp"]:
            download_protocol = parts[1]
            print(f"Protocol set to {download_protocol}")
            continue

        # Transform /get command to include protocol information
        if parts[:1] == ["/get"] and len(parts) == 2:
            if download_protocol == "udp":
                # Create and bind a UDP socket to receive file data
                udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_sock.bind(("", 0))
                msg = f"/get {parts[1]} udp {udp_sock.getsockname()[1]}"
            else:
                msg = f"/get {parts[1]} tcp"

        # Handle shortcut quit command
        if msg == "/q":
            s.sendall(b"/quit")
            break

        # Send the message/command to the server
        s.sendall(msg.encode())

