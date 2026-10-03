import sys,json,time
from pathlib import Path
from native_probe import api,ROOT,PRIVATE
from prepare_stage import prepare
from score_sw_fabric.storage import validate_run_root
rows=json.loads((ROOT/"live-inputs.json").read_text())
initial=json.loads((ROOT/"live-initial-run.json").read_text())
for number,row in enumerate(rows):
 validate_run_root(ROOT)
 ledger=PRIVATE/"live-meter/meter.json"
 if ledger.exists() and json.loads(ledger.read_bytes()).get("stopped"): raise RuntimeError("Persistent meter stop; no continuation")
 if number==0: id=initial["id"]
 else: id,_,_=prepare(row["label"],row["prompt"])
 api("POST","/runs/"+id+"/start",{})
 print(json.dumps({"started":row["label"],"run_id":id}),flush=True)
 deadline=time.monotonic()+240
 while time.monotonic()<deadline:
  value=api("GET","/runs/"+id)
  if value["lifecycle"]["status"]["kind"] in ("succeeded","failed","canceled"):break
  time.sleep(2)
 else:
  api("POST","/runs/"+id+"/cancel",{});raise RuntimeError("Native qualification timeout")
 for name,suffix in [("inspect",""),("events","/events?limit=1000"),("stages","/stages")]:
  v=api("GET","/runs/"+id+suffix);(ROOT/(row["label"]+"-"+name+".json")).write_text(json.dumps(v))
 meter=json.loads(ledger.read_bytes()) if ledger.exists() else {}
 print(json.dumps({"finished":row["label"],"native_state":value["lifecycle"]["status"],"meter_requests":meter.get("requests"),"meter_stopped":meter.get("stopped")}),flush=True)
 if meter.get("stopped"):raise RuntimeError("Persistent meter stop; no continuation")
 if meter.get("requests")!=number+1:raise RuntimeError("No measured provider request")
