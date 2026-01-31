import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import webbrowser

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
PORT = 8000

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppresses per-request logs to keep console clean

async def run_http_server():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[HTTP] Serving frontend on http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, server.serve_forever)
