"""
Server

A simple IRC-like chat server that supports:
- Public messaging to all connected clients
- Private messaging between users
- Group/channel creation and messaging
- File sharing via TCP or UDP protocols

Usage: python server.py <port>
"""

import socket
import select
import sys
import os
import threading

# Directory containing files available for download by clients
shared_dir = os.environ.get("SERVER_SHARED_FILES", "SharedFiles")

if not os.path.isdir(shared_dir):
    print(f"Shared files directory '{shared_dir}' does not exist")
    sys.exit(1)

# Parse command line arguments and initialize the TCP server socket
port = int(sys.argv[1])
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", port))
server_socket.listen()

print(f"Server listening on port {port}")

# Track all active sockets for select() multiplexing
sockets = [server_socket]

# Map of socket objects to their associated usernames
clients = {}

# Map of group names to sets of member sockets
groups = {}

# Track sockets with active file transfers to prevent concurrent downloads
active_transfers = set()


def safe_send(sock, msg):
    """
    Safely send an encoded message to a socket.
    Silently handles any transmission errors.
    """
    try:
        sock.sendall(msg.encode())
    except:
        pass


def cast(target_sockets, sender, msg):
    """
    Broadcast a message to multiple sockets.
    Logs the message to the server console and sends to all targets except the sender.
    """
    print(msg)
    for s in target_sockets:
        if s != sender:
            safe_send(s, msg)


def send_file_tcp(sock, path, filename):
    """
    Send a file to a client over TCP.
    Sends a header with filename and size, followed by the file contents in chunks.
    Removes the socket from active_transfers when complete.
    """
    try:
        size = os.path.getsize(path)
        sock.sendall(f"FILE {filename} {size}\n".encode())
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                sock.sendall(chunk)
    finally:
        active_transfers.discard(sock)


def send_file_udp(client_ip, client_port, path):
    """
    Send a file to a client over UDP.
    Creates a temporary UDP socket and sends file contents in datagrams.
    Note: UDP does not guarantee delivery or ordering.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                udp.sendto(chunk, (client_ip, client_port))
    finally:
        udp.close()

# Main server loop - uses select() for non-blocking I/O multiplexing
while True:
    readable, _, _ = select.select(sockets, [], [])

    for sock in readable:
        # Handle new incoming connections
        if sock is server_socket:
            conn, _ = server_socket.accept()
            sockets.append(conn)
            continue

        # Receive data from existing client connections
        try:
            data = sock.recv(1024)
        except:
            data = b""

        # Handle client disconnection (empty data)
        if not data:
            if sock in clients:
                username = clients[sock]
                cast(clients, sock, f"[server] [{username}] disconnected")
                del clients[sock]

                # Remove disconnected user from all groups
                for g in list(groups):
                    groups[g].discard(sock)
                    if not groups[g]:
                        del groups[g]

            sockets.remove(sock)
            sock.close()
            continue

        msg = data.decode().strip()

        # First message from a new connection is treated as the username registration
        if sock not in clients:
            if msg in clients.values():
                safe_send(sock, "[server] Username already taken")
                sock.close()
                sockets.remove(sock)
                continue
            clients[sock] = msg
            cast(clients, sock, f"[server] [{msg}] joined")
            continue

        username = clients[sock]
        parts = msg.split()

        # Process client commands (all start with /)
        if parts[0] == "/quit":
            # Disconnect the user and clean up their session
            cast(clients, sock, f"[server] [{username}] left")
            del clients[sock]

            for g in list(groups):
                groups[g].discard(sock)
                if not groups[g]:
                    del groups[g]

            sockets.remove(sock)
            sock.close()

        elif parts[0] == "/msg":
            # Send a private message to a specific user
            if len(parts) < 3:
                safe_send(sock, "[server] Usage: /msg <user> <message>")
                continue

            target = parts[1]
            message = " ".join(parts[2:])
            for s, name in clients.items():
                if name == target:
                    safe_send(s, f"[private] {username}> {message}")
                    break
            else:
                safe_send(sock, f"[server] User [{target}] not found")

        elif parts[0] == "/join":
            # Join a group (creates it if it doesn't exist)
            if len(parts) != 2:
                safe_send(sock, "[server] Usage: /join <group>")
                continue

            group = parts[1]
            if sock in groups.get(group, set()):
                safe_send(sock, f"[server] Already in [{group}]")
                continue

            groups.setdefault(group, set()).add(sock)
            cast(groups[group], None, f"[server] [{username}] joined [{group}]")

        elif parts[0] == "/leave":
            # Leave a group the user is a member of
            if len(parts) != 2:
                safe_send(sock, "[server] Usage: /leave <group>")
                continue

            group = parts[1]
            if group in groups and sock in groups[group]:
                groups[group].remove(sock)
                cast(groups[group], None, f"[server] [{username}] left [{group}]")
                if not groups[group]:
                    del groups[group]
            else:
                safe_send(sock, f"[server] Not a member of [{group}]")

        elif parts[0] == "/group":
            # Send a message to all members of a group
            if len(parts) < 3:
                safe_send(sock, "[server] Usage: /group <group> <message>")
                continue

            group = parts[1]
            message = " ".join(parts[2:])
            if group in groups and sock in groups[group]:
                cast(groups[group], sock, f"[{group}] {username}> {message}")
            else:
                safe_send(sock, f"[server] Not a member of [{group}]")

        elif parts[0] == "/files":
            # List all files available for download in the shared directory
            files = sorted(
                f for f in os.listdir(shared_dir)
                if os.path.isfile(os.path.join(shared_dir, f))
            )
            if files:
                safe_send(sock, "Shared files:\n" + "\n".join(files))
            else:
                safe_send(sock, "[server] No shared files available")

        elif parts[0] == "/get":
            # Download a file using TCP or UDP protocol
            if sock in active_transfers:
                safe_send(sock, "[server] File transfer already in progress")
                continue

            if len(parts) not in (3, 4):
                safe_send(sock, "[server] Usage: /get <filename> <tcp|udp> [udp_port]")
                continue

            filename = parts[1]
            protocol = parts[2]
            path = os.path.join(shared_dir, filename)

            if not os.path.isfile(path):
                safe_send(sock, "[server] File not found")
                continue

            active_transfers.add(sock)

            if protocol == "tcp":
                # TCP transfer: spawn a thread to send file over the existing connection
                threading.Thread(
                    target=send_file_tcp,
                    args=(sock, path, filename),
                    daemon=True
                ).start()

            elif protocol == "udp":
                # UDP transfer: send file to client's specified UDP port
                client_port = int(parts[3])
                client_ip = sock.getpeername()[0]
                size = os.path.getsize(path)
                safe_send(sock, f"FILE_UDP {filename} {size}")
                threading.Thread(
                    target=send_file_udp,
                    args=(client_ip, client_port, path),
                    daemon=True
                ).start()
                active_transfers.discard(sock)

            else:
                active_transfers.discard(sock)
                safe_send(sock, "[server] Protocol must be tcp or udp")

        elif parts[0] == "/help":
            # Display available commands and their usage
            safe_send(sock, f"[server] here is a list of valid commands:\n/msg <username> <message> - Privately messages the user\n/quit - Exits the chat\n/join <groupname> - Joins a group if it exists if not creates it\n/leave <groupname> - Leaves a group if you're in it\n/group <groupname> <message> - Sends a message to everyone in the specified group if you're a member of it\n/files - Lists all the files in the shared space availible for download\n/get <filename> - Downloads the specified file to a personal folder (by default using TCP)\n/protocol <tcp|udp> - Changes the download protocol to either TCP or UDP")

        elif parts[0].startswith("/"):
            # Unknown command - notify user
            safe_send(sock, f"[server] {parts[0]} is not a valid command\nplease use /help for a list of valid commands")

        else:
            # Regular message - broadcast to all connected clients
            cast(clients, sock, f"{username}> {msg}")

