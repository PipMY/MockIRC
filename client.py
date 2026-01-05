import socket
import sys
import threading
import os

udp_sock = None

def receive_loop(sock):
    global udp_sock

    while True:
        data = sock.recv(1024)
        if not data:
            print("\n[server] Disconnected")
            break

        if data.startswith(b"FILE "):
            buffer = data
            while b"\n" not in buffer:
                buffer += sock.recv(1024)

            header, remainder = buffer.split(b"\n", 1)
            _, filename, size = header.decode().split(" ", 2)
            size = int(size)

            os.makedirs(username, exist_ok=True)
            path = os.path.join(username, filename)

            received = len(remainder)
            with open(path, "wb") as f:
                f.write(remainder)
                while received < size:
                    chunk = sock.recv(min(4096, size - received))
                    f.write(chunk)
                    received += len(chunk)

            print(f"\nDownloaded {filename} ({size} bytes)\n> ", end="")
            continue

        if data.startswith(b"FILE_UDP "):
            _, filename, size = data.decode().split()
            size = int(size)

            os.makedirs(username, exist_ok=True)
            path = os.path.join(username, filename)

            received = 0
            with open(path, "wb") as f:
                while received < size:
                    chunk, _ = udp_sock.recvfrom(4096)
                    f.write(chunk)
                    received += len(chunk)

            udp_sock.close()
            udp_sock = None
            print(f"\nDownloaded {filename} ({size} bytes via UDP)\n> ", end="")
            continue

        print("\n" + data.decode() + "\n> ", end="")

# ---------- ARGUMENTS ----------
if len(sys.argv) != 4:
    print("Usage: python3 client.py <username> <ip> <port>")
    sys.exit(1)

username = sys.argv[1]
host = sys.argv[2]
port = int(sys.argv[3])

download_protocol = "tcp"

# ---------- CONNECT ----------
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    s.sendall(username.encode())

    threading.Thread(target=receive_loop, args=(s,), daemon=True).start()

    while True:
        msg = input("> ").strip()
        parts = msg.split()

        if parts[:2] == ["/protocol", "tcp"] or parts[:2] == ["/protocol", "udp"]:
            download_protocol = parts[1]
            print(f"Protocol set to {download_protocol}")
            continue

        if parts[:1] == ["/get"] and len(parts) == 2:
            if download_protocol == "udp":
                udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_sock.bind(("", 0))
                msg = f"/get {parts[1]} udp {udp_sock.getsockname()[1]}"
            else:
                msg = f"/get {parts[1]} tcp"

        if msg == "/q":
            s.sendall(b"/quit")
            break

        s.sendall(msg.encode())

