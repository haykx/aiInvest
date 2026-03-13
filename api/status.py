from http.server import BaseHTTPRequestHandler
import json

from core import database
from core.portfolio_manager import get_portfolio_snapshot


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            client = database.get_client()
            snapshot = get_portfolio_snapshot(client)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(snapshot, default=str).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
