import hashlib,json,sys
from datetime import datetime
from pathlib import Path
from native_probe import ROOT,PRIVATE,api
from score_sw_fabric.optimization.common import record
from score_sw_fabric.optimization.runtime_boundary import runtime_config
from score_sw_fabric.optimization.token_governor import govern
def prepare(label,prompt,tasks=None,mcp=True):
 target=ROOT/(label+"-target"); target.mkdir(exist_ok=True)
 private=PRIVATE/label; private.mkdir(mode=0o700,exist_ok=True)
 context=record("optimized_context_bundle",manifest_digest=hashlib.sha256(prompt.encode()).hexdigest(),l0={"task":label,"constraints":["qualification only; human remains pending"]},l1={"prompt":prompt},skills=[])
 admission=record("agent_admission",decision="admissible",call_authorized=False,remaining={"input_tokens":20000,"output_tokens":2000,"calls":1},profile={"id":"scoped-owner-flash-qualification","max_output_tokens":2000},provider_configured=True,offering={"id":"deepseek-v4-flash"})
 governor=govern("S0",admission,len(prompt.encode()),[],manifest_digest=context["manifest_digest"])
 role=record("qualification_role",role="draft",output_limit=2000,task=label,provider="deepseek",model="deepseek-flash")
 skills=record("qualification_skills",skills=[],origin="development-fixture")
 artifacts={"context":context,"governor":governor,"role":role,"skills":skills}
 files={}; bindings={}
 for name,value in artifacts.items():
  path=private/(name+".json");path.write_text(json.dumps(value));path.chmod(0o600)
  files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest(); bindings[name]=value["digest"]
 runbinding=private/"run.json"; runbinding.write_text(json.dumps({"run_id":"awaiting-native-create","stopped":False}));runbinding.chmod(0o600)
 instruction={"kind":"qualification_instruction","scope":"qualification_only","owner_instructions":["go","deepseek flash only"],"workspace":str(ROOT),"run_binding":str(runbinding),"stage":"draft","task":label,"bindings":bindings,"files":files,"provider":"deepseek","models":["deepseek-flash","deepseek-v4-flash"],"limits":{"requests":10,"request_bytes":24000,"output_tokens":2000,"cost_microusd":100000},"price_bounds":{"input_microusd_per_token":0.3,"output_microusd_per_token":1.2},"tasks":tasks or [{"marker":"qualification:"+label,"prompt":prompt,"max_requests":1}]}
 path=private/"instruction.json"; path.write_text(json.dumps(instruction));path.chmod(0o600);pin=hashlib.sha256(path.read_bytes()).hexdigest()
 graph='digraph Qualification { graph [backend="api", default_max_retries=0]; start [shape=Mdiamond]; draft [prompt='+json.dumps(prompt)+', provider="deepseek", model="deepseek-flash", max_tokens=2000, reasoning_effort="low"]; exit [shape=Msquare]; start -> draft -> exit; }'
 config='_version = 1\n[workflow]\ngraph = "workflow.fabro"\n'+runtime_config(Path(sys.executable),ROOT,private/"service.json",private/"governor.json","draft",instruction=path,instruction_sha256=pin)
 config=config.replace(json.dumps([str(Path(sys.executable)), "-m", "score_sw_fabric.optimization.cli", "guard"])[1:-1],json.dumps([str(Path(sys.executable)),str(ROOT/"capture_hook.py")])[1:-1])
 if not mcp:
  start=config.index('[run.agent.mcps.score_bounded]');end=config.index('[[run.hooks]]',start);config=config[:start]+config[end:]
 workflow={"entrypoint":"workflow.fabro","files":{"workflow.fabro":graph,"workflow.toml":config},"workflow_dependencies":{}}
 (ROOT/(label+"-workflow.json")).write_text(json.dumps(workflow))
 version=api("POST","/workflow-versions",workflow)
 run=api("POST","/runs",{"workflow_version_id":version["workflow_version_id"],"target":{"kind":"folder","path":str(target)},"environment_id":"local","title":"011 "+label+" qualification","args":{"provider":"deepseek","model":"deepseek-flash","auto_approve":False}})
 runbinding.write_text(json.dumps({"run_id":run["id"],"workflow_version_id":version["workflow_version_id"],"stopped":False,"native_context":{"run_id":"petri","source_commit":"1b4fb15281ebb724426f9e480dce48d0100ff79b","server_root":str(PRIVATE),"cwd":str(PRIVATE/"storage/scratch"/(datetime.now().strftime("%Y%m%d")+"-"+run["id"])/"petri/scopes/invocation-0-scope-0/work")}}))
 (ROOT/(label+"-created.json")).write_text(json.dumps(run))
 return run["id"],path,pin
if __name__=="__main__":
 label="capture-cwd";prompt="qualification:capture-cwd Return only a JSON object with human_review set to pending. Use no tools."
 id,path,pin=prepare(label,prompt)
 api("POST","/runs/"+id+"/start",{})
 print({"run_id":id,"instruction_pin":pin})
