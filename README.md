# Chat and File Transfer System

## Overview

This project aims to implement a multi-client chat server and client tool that supports global, private and group messaging aswell as file transfer.
Supporting both TCP and UDP for file transfer to demonstrate reliability and speed tradeoffs between the 2 transport protocols.

## Features
- Multi-client chat
- Private messaging
- Group chat
- File listing
- File transfer over:
    - TCP (reliable)
    - UDP (connectionless and fast)
- Non-blocking server using select
- Graceful client and server disconnection

## Architecture
The

## Commands
/help                       Displays all valid commands
/msg <user> <message>       Sends a private message
/join <group>               Joins a group
/leave <group>              Leaves a group
/group <group> <message>    Sends group message
/files                      Lists shared files
/get <filename>             Downloads file (uses current protocol)
/protocol <tcp|udp>         Select file transfer protocol
/quit                       Disconnect from server

## TCP vs UDP File Transfer

### TCP
- Reliable

### UDP
- Not

## Error Handling and Robustness

## How to Run
Please run the server before attempting to connect with it from clients.
In order to run the server please navigate to the folder this README is in and run the following command:
```
python server.py <port> # port must be > 1023
```
To run the client program please run the following command:
```
python client.py <username> <ip> <port> # ip should be 127.0.0.1
```

## Testing
