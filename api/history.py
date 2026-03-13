from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

from core import database


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            limit = int(query.get("limit", [50])[0])
            offset = int(query.get("offset", [0])[0])
            limit = min(limit, 200)

            client = database.get_client()
            transactions = database.get_transactions(client, limit=limit, offset=offset)
            recent_runs = database.get_analysis_runs(client, limit=5)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "transactions": transactions,
                "recent_analysis_runs": recent_runs,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                },
            }, default=str).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
