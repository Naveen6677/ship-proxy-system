import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import socket
import threading
import http.client
from proxy import protocol
from urllib.parse import urlsplit

OFFSHORE_LISTEN_HOST = "0.0.0.0"
OFFSHORE_LISTEN_PORT = 9999
BUFFER = 8192

def handle_ship_connection(conn: socket.socket, addr):
    print("Ship connected from", addr)
    try:
        while True:
            msg_type, payload = protocol.recv_msg(conn)
            if msg_type == protocol.TYPE_REQUEST:
                # parse request
                try:
                    first_line = payload.split(b"\r\n", 1)[0].decode(errors="ignore")
                except Exception:
                    first_line = ""
                parts = first_line.split()
                if len(parts) < 3:
                    resp = b"HTTP/1.1 400 Bad Request\r\nContent-Length:0\r\n\r\n"
                    protocol.send_msg(conn, protocol.TYPE_RESPONSE, resp)
                    continue
                method, path, _ = parts
                headers_body = payload.split(b"\r\n\r\n", 1)
                headers = headers_body[0].decode(errors="ignore")
                body = headers_body[1] if len(headers_body) > 1 else b""
                host = None
                for line in headers.split("\r\n")[1:]:
                    if line.lower().startswith("host:"):
                        host = line.split(":",1)[1].strip()
                        break

                if path.startswith("http://") or path.startswith("https://"):
                    split = urlsplit(path)
                    hostname = split.hostname
                    port = split.port or (443 if split.scheme == "https" else 80)
                    url_path = split.path or "/"
                    if split.query:
                        url_path += "?" + split.query
                    is_https = split.scheme == "https"
                else:
                    if not host:
                        resp = b"HTTP/1.1 400 Bad Request\r\nContent-Length:0\r\n\r\n"
                        protocol.send_msg(conn, protocol.TYPE_RESPONSE, resp)
                        continue
                    if ":" in host:
                        hostname, port = host.split(":",1)
                        port = int(port)
                    else:
                        hostname = host
                        port = 80
                    url_path = path
                    is_https = False

                try:
                    if is_https:
                        c = http.client.HTTPSConnection(hostname, port, timeout=20)
                    else:
                        c = http.client.HTTPConnection(hostname, port, timeout=20)
                    header_lines = headers.split("\r\n")[1:]
                    headers_dict = {}
                    for h in header_lines:
                        if ":" in h:
                            k,v = h.split(":",1)
                            headers_dict[k.strip()] = v.strip()
                    c.request(method, url_path, body, headers_dict)
                    resp = c.getresponse()
                    resp_body = resp.read()
                    status_line = f"HTTP/1.1 {resp.status} {resp.reason}\r\n".encode()
                    resp_header_bytes = b""
                    for k, v in resp.getheaders():
                        resp_header_bytes += f"{k}: {v}\r\n".encode()
                    resp_bytes = status_line + resp_header_bytes + b"\r\n" + resp_body
                    protocol.send_msg(conn, protocol.TYPE_RESPONSE, resp_bytes)
                except Exception as e:
                    err_text = str(e).encode()
                    err = b"HTTP/1.1 502 Bad Gateway\r\n" + \
                          b"Content-Type: text/plain\r\n" + \
                          f"Content-Length: {len(err_text)}\r\n\r\n".encode() + err_text
                    protocol.send_msg(conn, protocol.TYPE_RESPONSE, err)

            elif msg_type == protocol.TYPE_TUNNEL_INIT:
                target = payload.decode()
                try:
                    host, port_s = target.split(":")
                    port = int(port_s)
                    remote = socket.create_connection((host, port), timeout=20)
                except Exception as e:
                    err_text = str(e).encode()
                    err = b"HTTP/1.1 502 Bad Gateway\r\n" + \
                          f"Content-Length: {len(err_text)}\r\n\r\n".encode() + err_text
                    protocol.send_msg(conn, protocol.TYPE_RESPONSE, err)
                    continue

                ok = b"HTTP/1.1 200 Connection established\r\n\r\n"
                protocol.send_msg(conn, protocol.TYPE_RESPONSE, ok)

                def read_from_remote():
                    try:
                        while True:
                            chunk = remote.recv(BUFFER)
                            if not chunk:
                                break
                            protocol.send_msg(conn, protocol.TYPE_TUNNEL_DATA, chunk)
                    except Exception:
                        pass
                    finally:
                        try:
                            protocol.send_msg(conn, protocol.TYPE_TUNNEL_CLOSE, b"")
                        except Exception:
                            pass
                        try:
                            remote.close()
                        except:
                            pass

                t = threading.Thread(target=read_from_remote, daemon=True)
                t.start()

                try:
                    while True:
                        mt, pl = protocol.recv_msg(conn)
                        if mt == protocol.TYPE_TUNNEL_DATA:
                            if pl:
                                remote.sendall(pl)
                        elif mt == protocol.TYPE_TUNNEL_CLOSE:
                            break
                        else:
                            # ignore
                            pass
                except Exception:
                    pass
                finally:
                    try:
                        remote.close()
                    except:
                        pass

            else:
                # ignore unknown type
                pass

    except ConnectionError:
        print("Ship disconnected")
    except Exception as e:
        print("Server error:", e)
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((OFFSHORE_LISTEN_HOST, OFFSHORE_LISTEN_PORT))
    s.listen(1)
    print("Offshore listening on", OFFSHORE_LISTEN_HOST, OFFSHORE_LISTEN_PORT)
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_ship_connection, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()

