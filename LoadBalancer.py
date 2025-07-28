import http.server
import socketserver
import threading
import requests

# List of backend servers
BACKENDS = [
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003"
]

current = 0  # Index of the next server to forward to
lock = threading.Lock()  # Thread-safe counter

class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global current
        with lock:
            backend = BACKENDS[current]
            current = (current + 1) % len(BACKENDS)

        try:
            # Forward the request to the chosen backend
            response = requests.get(backend + self.path)
            self.send_response(response.status_code)
            for header, value in response.headers.items():
                if header.lower() != 'content-encoding':
                    self.send_header(header, value)
            self.end_headers()
            self.wfile.write(response.content)
        except requests.exceptions.RequestException as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Bad Gateway: {e}".encode())

if __name__ == "__main__":
    PORT = 8080
    with socketserver.ThreadingTCPServer(("", PORT), LoadBalancerHandler) as httpd:
        print(f"Load balancer running on port {PORT}...")
        httpd.serve_forever()
