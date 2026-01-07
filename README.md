# MockIRC - Chat and File Transfer System

---

## 1. Overview

This program implements a multi-client instant messenger using Python and raw sockets.

- **TCP** is used for all chat messaging and reliable file transfers.
- **UDP** is available as an alternative for faster (but connectionless) file downloads.

The server uses non-blocking I/O with `select()` to handle multiple concurrent clients efficiently. Clients can send broadcast messages, private messages, join/leave groups, and download files from a shared directory.

---

## 2. How to Run

> **All code runs on Windows as required.**

### Start Server

```
python server.py [port]
```

**Example:**
```
python server.py 5020
```

The server will listen on `127.0.0.1` at the specified port. The `SharedFiles/` directory must exist in the same folder as `server.py`.

### Start Client

```
python client.py [username] [hostname] [port]
```

**Example:**
```
python client.py John 127.0.0.1 5020
```

### Notes

- Port must be > 1023 (unprivileged port).
- The shared files directory can be overridden using the `SERVER_SHARED_FILES` environment variable if needed.
- Downloaded files are saved to a folder named after the client's username (auto-created).

---

## 3. Implemented Functionality

### 3.1 Connection Functions

| Feature | Implementation | How to Test |
|---------|----------------|-------------|
| Server accepts connections | Server uses `select()` for non-blocking multiplexing | Start server, connect a client |
| Multiple clients supported | All connected sockets tracked in a list, handled via `select()` | Open 3+ terminals and connect different usernames |
| Join message broadcast | `[server] [username] joined` sent to all clients | Connect a new client, observe message on other clients |
| Leave/disconnect broadcast | `[server] [username] left` or `disconnected` sent to all | Type `/quit` or close terminal unexpectedly |
| Graceful disconnect handling | Server removes socket from tracking, cleans up group memberships | Close a client terminal abruptly — server continues running |
| Duplicate username rejected | Server checks if username already exists | Try connecting two clients with the same username |

### 3.2 Messaging Functions

#### Broadcast (Public Messages)

Simply type a message and press **Enter**. The message is automatically broadcast to all other connected clients.

```
> Hello everyone!
```

All other clients see:
```
John> Hello everyone!
```

#### Unicast (Private Messages)

```
/msg <username> <message>
```

**Example:**
```
/msg Alice Hey, how are you?
```

Only Alice receives:
```
[private] John> Hey, how are you?
```

#### Groups (Multicast)

| Command | Description |
|---------|-------------|
| `/join <groupname>` | Join a group (creates it if it doesn't exist) |
| `/leave <groupname>` | Leave a group |
| `/group <groupname> <message>` | Send a message to all group members |

**Example:**
```
/join developers
/group developers Anyone working on the bug fix?
/leave developers
```

Group members see:
```
[server] [John] joined [developers]
[developers] John> Anyone working on the bug fix?
[server] [John] left [developers]
```

#### Mode Switching

The messaging mode is determined by the command used:
- No prefix → Broadcast
- `/msg` → Unicast
- `/group` → Multicast

### 3.3 File Downloading

#### List Shared Files

```
/files
```

Displays all files available in the server's `SharedFiles/` directory.

#### Select Protocol

```
/protocol tcp
/protocol udp
```

Switches the download protocol for subsequent `/get` commands. Default is TCP.

#### Download a File

```
/get <filename>
```

**Example:**
```
/protocol tcp
/get test.txt
```

Output:
```
Downloaded test.txt (1234 bytes)
```

- Files are saved to a folder named after your username (e.g., `John/test.txt`).
- File size in bytes is sent by the server and displayed to the client.

#### TCP vs UDP

| Protocol | Characteristics |
|----------|-----------------|
| **TCP** | Reliable, ordered delivery. File integrity guaranteed. |
| **UDP** | Connectionless, faster for local networks. No retransmission — assumes reliable local network. |

---

## 4. Folder Structure

```
server.py           # Server application
client.py           # Client application
SharedFiles/        # Directory containing files available for download
    test.txt
    dog
README.md           # This file
John/               # Auto-created when John downloads files
```

---

## 5. Commands Reference

| Command | Description |
|---------|-------------|
| `/help` | Display all valid commands |
| `/msg <user> <message>` | Send a private message to a user |
| `/join <group>` | Join a group (creates if doesn't exist) |
| `/leave <group>` | Leave a group |
| `/group <group> <message>` | Send a message to a group |
| `/files` | List all shared files available for download |
| `/get <filename>` | Download a file using the current protocol |
| `/protocol <tcp\|udp>` | Switch file transfer protocol |
| `/quit` or `/q` | Disconnect from the server |

---

## 6. Error Handling

- **Invalid commands** → Returns `[server] <command> is not a valid command`
- **Unknown username in /msg** → Returns `[server] User [X] not found`
- **File not found in /get** → Returns `[server] File not found`
- **Not a group member** → Returns `[server] Not a member of [group]`
- **Username already taken** → Returns `[server] Username already taken` and closes connection
- **Transfer already in progress** → Returns `[server] File transfer already in progress`
- **Unexpected client disconnect** → Server cleans up gracefully and notifies other clients

---

## 7. Known Limitations

- Messages are limited to 1024 bytes per receive call.
- UDP file transfers assume local network reliability (no retransmission or ordering).
- Only one file transfer can be active per client at a time.
- The server binds to `127.0.0.1` only (localhost connections).

---

## 8. Testing Instructions

Follow these steps to test all functionality:

### Setup
1. Start the server: `python server.py 5020`
2. Open 3 terminals and connect 3 clients:
   - `python client.py Alice 127.0.0.1 5020`
   - `python client.py Bob 127.0.0.1 5020`
   - `python client.py Charlie 127.0.0.1 5020`

### Test Broadcast
3. From Alice, type `Hello everyone!` — verify Bob and Charlie receive it.

### Test Unicast
4. From Alice, type `/msg Bob Hey Bob!` — verify only Bob receives the private message.

### Test Groups
5. From Alice: `/join team`
6. From Bob: `/join team`
7. From Alice: `/group team Team message here` — verify Bob receives it, Charlie does not.
8. From Bob: `/leave team` — verify Alice sees the leave notification.

### Test File Transfer (TCP)
9. From Alice: `/files` — verify file list is displayed.
10. From Alice: `/get test.txt` — verify file downloads to `Alice/test.txt`.

### Test File Transfer (UDP)
11. From Bob: `/protocol udp`
12. From Bob: `/get test.txt` — verify file downloads via UDP.

### Test Disconnect Handling
13. Close Charlie's terminal abruptly (Ctrl+C or close window).
14. Verify Alice and Bob receive `[server] [Charlie] disconnected`.
15. Verify server continues running without errors.

### Test Error Cases
16. From Alice: `/msg Nobody Hello` — verify "User not found" error.
17. From Alice: `/get nonexistent.txt` — verify "File not found" error.
18. From Alice: `/invalidcmd` — verify invalid command error with help suggestion.

---
