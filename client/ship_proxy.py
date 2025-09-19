import http.server
import socketserver
import socket
import ssl
import urllib.parse
import requests
import argparse


class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward_request(self):
        """Forward client request to the target server."""
        url = self.path
        parsed = urllib.parse.urlparse(url)

        # Handle relative URLs (from browser/curl)
        if not parsed.scheme:
            url = f"http://{self.headers['Host']}{url}"

        method = self.command
        headers = dict(self.headers)

        # Remove hop-by-hop headers that cause issues
        for h in ["Proxy-Connection", "Connection", "Keep-Alive", "Upgrade"]:
            headers.pop(h, None)

        data = None
        if "Content-Length" in headers:
            length = int(headers["Content-Length"])
            data = self.rfile.read(length)

        try:
            resp = requests.request(method, url, headers=headers, data=data, stream=True, timeout=10)

            # Log request details
            print(f"[Proxy] {method} {url} -> {resp.status_code}")

            # Send response back to client
            self.send_response(resp.status_code)
            for key, value in resp.headers.items():
                if key.lower() not in ["transfer-encoding", "content-encoding", "content-length", "connection"]:
                    self.send_header(key, value)
            if resp.content:
                self.send_header("Content-Length", str(len(resp.content)))
            self.end_headers()

            if resp.content:
                self.wfile.write(resp.content)

        except Exception as e:
            print(f"[Error] Failed to forward {method} {url}: {e}")
            self.send_error(502, f"Bad Gateway: {e}")

    def do_GET(self): self._forward_request()
    def do_POST(self): self._forward_request()
    def do_PUT(self): self._forward_request()
    def do_DELETE(self): self._forward_request()

    def do_CONNECT(self):
        """Handle HTTPS CONNECT tunneling."""
        host, port = self.path.split(":")
        port = int(port)

        try:
            with socket.create_connection((host, port)) as upstream:
                self.send_response(200, "Connection Established")
                self.end_headers()

                # Tunnel data between client and server
                self._tunnel(self.connection, upstream)

        except Exception as e:
            print(f"[Error] CONNECT tunnel to {host}:{port} failed: {e}")
            self.send_error(502, f"Tunnel Failed: {e}")

    def _tunnel(self, client_sock, upstream_sock):
        """Bidirectional tunneling between client and upstream."""
        import select
        sockets = [client_sock, upstream_sock]
        while True:
            rlist, _, _ = select.select(sockets, [], [])
            if client_sock in rlist:
                data = client_sock.recv(4096)
                if not data: break
                upstream_sock.sendall(data)
            if upstream_sock in rlist:
                data = upstream_sock.recv(4096)
                if not data: break
                client_sock.sendall(data)



def run_server(host, port):
    with socketserver.ThreadingTCPServer((host, port), ProxyHTTPRequestHandler) as httpd:
        print(f"[Ship Proxy] Listening on {host}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Ship Proxy] Shutting down.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ship Proxy Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind")
    args = parser.parse_args()

    run_server(args.host, args.port)


