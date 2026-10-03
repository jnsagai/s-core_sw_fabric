from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import json
ROOT=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 count=0
 def log_message(self,*args): pass
 def do_POST(self):
  body=self.rfile.read(int(self.headers.get("Content-Length","0")))
  index=Handler.count; Handler.count+=1
  (ROOT/f"fixture-provider-qualified-request-{index}.json").write_bytes(body)
  delta={"role":"assistant"}
  finish="tool_calls"
  if index==0: delta["tool_calls"]=[{"index":0,"id":"fixture-call-0","type":"function","function":{"name":"mcp__score_bounded__evidence_summary","arguments":json.dumps({"path":"qualification.sarif"})}}]
  elif index==1: delta["tool_calls"]=[{"index":0,"id":"fixture-call-1","type":"function","function":{"name":"read_file","arguments":json.dumps({"file_path":str(ROOT/"qualification.sarif")})}}]
  else: delta["content"]='{"human_review":"pending","origin":"fixture-provider"}';finish="stop"
  chunks=[{"id":"fixture-completion","object":"chat.completion.chunk","model":"deepseek-v4-flash","choices":[{"index":0,"delta":delta,"finish_reason":None}]},{"id":"fixture-completion","object":"chat.completion.chunk","model":"deepseek-v4-flash","choices":[{"index":0,"delta":{},"finish_reason":finish}],"usage":{"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}}]
  response=b"".join(b"data: "+json.dumps(x).encode()+b"\n\n" for x in chunks)+b"data: [DONE]\n\n"
  self.send_response(200);self.send_header("Content-Type","text/event-stream");self.send_header("Content-Length",str(len(response)));self.end_headers();self.wfile.write(response)
  print(json.dumps({"fixture_turn":index,"request_bytes":len(body)}),flush=True)
HTTPServer(("127.0.0.1",18791),Handler).serve_forever()
