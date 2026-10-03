from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import json
ROOT=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  body=self.rfile.read(int(self.headers.get("Content-Length","0")))
  (ROOT/"native-request-capture.json").write_bytes(body)
  print(json.dumps({"bytes":len(body),"model":json.loads(body).get("model")}),flush=True)
  self.send_response(403); self.send_header("Content-Type","application/json"); self.end_headers()
  self.wfile.write(b'{"error":{"message":"CAPTURE_ONLY","type":"qualification_stop"}}')
HTTPServer(("127.0.0.1",18791),Handler).serve_forever()
