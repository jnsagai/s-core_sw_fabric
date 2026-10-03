from pathlib import Path
import json,sys,urllib.request,urllib.error,hashlib
from score_sw_fabric.storage import validate_run_root
from score_sw_fabric.optimization.common import record
from score_sw_fabric.optimization.runtime_boundary import runtime_config
ROOT=Path(__file__).parent
PRIVATE=Path("/home/jefferson/.local/state/s-core/fabro/score-011-qualification-9vmkm02n/qualification")
URL="http://127.0.0.1:18790"
def api(method,path,value=None):
 data=json.dumps(value).encode() if value is not None else None
 req=urllib.request.Request(URL+"/api/v1"+path,data,{"Authorization":"Bearer "+(PRIVATE/"dev-token").read_text(),"Content-Type":"application/json"},method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as reply: return json.loads(reply.read() or b"{}")
 except urllib.error.HTTPError as e: raise RuntimeError(str(e.code)+": "+e.read().decode()[:800]) from None
if __name__=="__main__":
 validate_run_root(ROOT)
 target=ROOT/"blocked-target"; target.mkdir(exist_ok=True)
 decision=record("token_governor_decision",decision="admissible",call_authorized=False)
 governor=PRIVATE/"blocked-governor.json"; governor.write_text(json.dumps(decision)); governor.chmod(0o600)
 graph='digraph Qualification { graph [backend="api", default_max_retries=0]; start [shape=Mdiamond]; draft [prompt="Qualification only. Return JSON with pending human review.", provider="deepseek", model="deepseek-flash", max_tokens=200, reasoning_effort="low"]; exit [shape=Msquare]; start -> draft -> exit; }'
 config='_version = 1\n[workflow]\ngraph = "workflow.fabro"\n'+runtime_config(Path(sys.executable),ROOT,PRIVATE/"service-state.json",governor,"draft")
 files={"workflow.fabro":graph,"workflow.toml":config}
 (ROOT/"blocked-workflow.json").write_text(json.dumps(files))
 version=api("POST","/workflow-versions",{"entrypoint":"workflow.fabro","files":files,"workflow_dependencies":{}})
 run=api("POST","/runs",{"workflow_version_id":version["workflow_version_id"],"target":{"kind":"folder","path":str(target)},"environment_id":"local","title":"011 guard qualification, zero provider calls","args":{"provider":"deepseek","model":"deepseek-flash","auto_approve":False}})
 (ROOT/"blocked-created.json").write_text(json.dumps(run))
 result=api("POST","/runs/"+run["id"]+"/start",{})
 (ROOT/"blocked-start.json").write_text(json.dumps(result))
 print({"run_id":run["id"],"start":result})
