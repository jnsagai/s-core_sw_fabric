import json,sys,subprocess,shutil,tempfile,time
from pathlib import Path
root=Path('/tmp/score-someip84-factory-_etjbuqw')
sys.path.insert(0,str(root))
import overnight_hooks, isolate_docker
policy=json.loads((root/'overnight-policy.json').read_text())
nodes=policy['nodes']
impl_id=next(k for k,v in nodes.items() if v['ref']=='reproducer')
review_id=next(k for k,v in nodes.items() if v['ref']=='scope')
check_id=next(k for k,v in nodes.items() if v['ref']=='check_unit_matrix')
repair_id=next(k for k,v in nodes.items() if v['ref']=='repair_unit_matrix')
now=time.time();tested=[]

def hook(label,ctx,expected,policy_root=root):
 r=subprocess.run([sys.executable,str(root/'overnight_hooks.py'),str(policy_root)],input=json.dumps(ctx),text=True,capture_output=True,timeout=5)
 assert r.returncode==expected,(label,r.returncode,r.stdout,r.stderr)
 tested.append(label)

source='/workspace/score/socom/impl/service_identifier.cpp'
ctx={'event':'pre_tool_use','node_id':impl_id,'tool_name':'write_file','tool_input':{'file_path':source,'content':'draft'}}
hook('implementation-source-allowed',ctx,0)
ctx['node_id']=review_id;hook('review-source-denied',ctx,2)
ctx['tool_input']['file_path']=nodes[review_id]['write_paths'][0];hook('review-report-allowed',ctx,0)
ctx['tool_input']['file_path']='/workspace/.llm_tmp/overnight/validation/measurement.json';hook('measurement-overwrite-denied',ctx,2)
ctx['tool_input']['file_path']='../../outside';hook('path-escape-denied',ctx,2)
for tool in ['shell','spawn_agent','apply_patch','web_fetch','update_plan']:
 ctx['tool_name']=tool;hook(tool+'-denied',ctx,2)
ctx['tool_name']='read_file';ctx['tool_input']={'file_path':source};hook('workspace-read-allowed',ctx,0)
ctx['node_id']='unknown';hook('unknown-node-denied',ctx,2)
ctx['node_id']=impl_id
node=nodes[impl_id];deadline=policy['deadline_epoch'];before={'event':'stage_start','node_id':impl_id}
assert overnight_hooks.admissible(policy,before,deadline-node['timeout_seconds']-61)
assert not overnight_hooks.admissible(policy,before,deadline-node['timeout_seconds']-59)
assert not overnight_hooks.admissible(policy,ctx,deadline)
tested.extend(['deadline-with-reserved-grace-allowed','insufficient-time-denied','at-deadline-tool-denied'])
expired=root/'expired-hook-check';expired.mkdir();old=dict(policy,deadline_epoch=now-1)
(expired/'overnight-policy.json').write_text(json.dumps(old));hook('expired-deadline-process-denied',ctx,2,expired)
(root/'latest-measurement.json').write_text(json.dumps({'check_ref':'check_unit_matrix','status':'unavailable'}))
hook('infrastructure-failure-not-reworked',{'event':'stage_start','node_id':repair_id},2)
(root/'latest-measurement.json').unlink()
fixture=root/'verification-fixture';shutil.copytree(root/'target',fixture,symlinks=True)
repo=Path('/home/jefferson/s-core_sw_fabric')
for p in json.loads((repo/'docs/handoff/someip-84/candidate-files.json').read_text()):
 shutil.copyfile(repo/'.tools/someip-84/work'/p,fixture/p)
feedback=root/'verification-feedback';feedback.mkdir()
measurement_root=root/'measurement-component-fixture';measurement_root.mkdir()
shutil.copytree(root/'target',measurement_root/'target',symlinks=True)
shutil.copyfile(root/'measurement-inputs.json',measurement_root/'measurement-inputs.json')
fixture_run='01M3WF6CGPT9DQBVV4Q6DN63XH'
(measurement_root/'native-run-id').write_text(fixture_run+'\n')

def transport(*args):
 if args[0]=='ps':
  assert 'label=petri.run='+fixture_run in args
  return 'component-verification-container'
 if args[0]=='inspect':return json.dumps([{'Image':policy['image_id'],'NetworkSettings':{'Networks':{}},'Config':{'Labels':{'petri.run':fixture_run}}}])
 if args[0]=='exec':return ''
 if args[0]=='cp':
  if args[1].startswith('component-verification-container:'):
   shutil.copytree(fixture,Path(args[2]),symlinks=True,dirs_exist_ok=True)
  else:shutil.copytree(Path(args[1].removesuffix('/.')),feedback,dirs_exist_ok=True)
  return ''
 raise AssertionError(args)

isolate_docker.docker=transport
overnight_hooks.measure(measurement_root,policy,nodes[check_id],initiator='component verification: stub Docker transport, real GCC/GTest, known external candidate')
measurement=json.loads((measurement_root/'latest-measurement.json').read_text())
assert measurement['status']=='completed',measurement
assert measurement['baseline_with_agent_tests']['failures']==7
assert measurement['candidate']['tests']==13 and measurement['candidate']['failures']==0
assert (feedback/'check-result').read_text()=='0\n'
tested.append('real-GCC-baseline-fails-7-candidate-passes-13-with-stub-Docker')
(measurement_root/'latest-measurement.json').unlink()
record={'origin':'component_verification_not_Fabro_execution','checks':tested,'passed':len(tested),'transport':'Docker stub; live hook admission unverified','actual_measurement':{'baseline':measurement['baseline_with_agent_tests'],'candidate':measurement['candidate']},'engineering_acceptance':'pending'}
(root/'component-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
