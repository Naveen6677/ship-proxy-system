# proxy/protocol.py
# Simple framing protocol for ship <-> offshore
import struct
import socket

TYPE_REQUEST = 0
TYPE_RESPONSE = 1
TYPE_TUNNEL_INIT = 2
TYPE_TUNNEL_DATA = 3
TYPE_TUNNEL_CLOSE = 4

HEADER_LEN = 5

def send_msg(sock: socket.socket, msg_type: int, payload: bytes):
    length = len(payload)
    header = struct.pack(">I", length) + struct.pack("B", msg_type)
    sock.sendall(header + payload)

def recv_all(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed while reading")
        data.extend(chunk)
    return bytes(data)

def recv_msg(sock: socket.socket):
    header = recv_all(sock, HEADER_LEN)
    length = struct.unpack(">I", header[:4])[0]
    msg_type = header[4]
    payload = recv_all(sock, length) if length > 0 else b""
    return msg_type, payload
