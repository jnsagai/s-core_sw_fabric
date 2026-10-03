import sys,json,shutil,contextlib,io
from pathlib import Path
root=Path('/tmp/score-someip84-factory-_etjbuqw');sys.path.insert(0,str(root))
import isolate_docker
policy=json.loads((root/'overnight-policy.json').read_text())
fixture=root/'container-scope-component-fixture';target=fixture/'target'
(target/'.llm_tmp/context').mkdir(parents=True)
(target/'score/socom/impl').mkdir(parents=True)
shutil.copyfile(root/'target/.llm_tmp/context/issue-snapshot.json',target/'.llm_tmp/context/issue-snapshot.json')
shutil.copyfile(root/'target/score/socom/impl/service_identifier.cpp',target/'score/socom/impl/service_identifier.cpp')
own='01M3WF6CGPT9DQBVV4Q6DN63XH';other='01M3W4HERGBZ5SVR52BZ2NHQ9K'
(fixture/'native-run-id').write_text(own+'\n');tested=[]
for mode,expected in [('own',0),('foreign',2),('two-owned',2)]:
 actions=[];networks={'bridge':{}}
 def docker(*args):
  actions.append(args)
  if args[0]=='ps':
   assert 'label=petri.run='+own in args
   return 'OWN\nSECOND' if mode=='two-owned' else ('FOREIGN' if mode=='foreign' else 'OWN')
  if args[0]=='inspect':
   label=other if mode=='foreign' else own
   return json.dumps([{'Image':policy['image_id'],'Config':{'Labels':{'petri.run':label,'petri.workspace':label+'/primary'}},'Mounts':[{'Type':'volume','Destination':'/workspace'}],'NetworkSettings':{'Networks':networks}}])
  if args[0]=='network':
   assert args[-1]=='OWN';networks.clear();return ''
  if args[0]=='cp':assert args[-1]=='OWN:/workspace/';return ''
  if args[0]=='exec':assert args[1]=='OWN';return ''
  raise AssertionError(args)
 isolate_docker.docker=docker
 sys.argv=['isolate_docker.py',policy['image_id'],str(target),str(fixture/'native-run-id')]
 with contextlib.redirect_stdout(io.StringIO()):code=isolate_docker.main()
 assert code==expected,(mode,code)
 if mode!='own':assert not any(x[0] in {'cp','network','exec'} for x in actions)
 tested.append(mode)
record={'origin':'component_verification_with_stub_Docker','passed':len(tested),'checks':tested,'foreign_container_mutations':0,'live_concurrency':'not_verified','engineering_acceptance':'pending'}
(root/'container-scope-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
