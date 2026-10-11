"""Public five-branch command with test-only transport and real Docker tools."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--official-checkpoint-grade',action='store_true')
    args=parser.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    settings={'kind':'benchmark','fixture_root':str(root),'public_entry':str(ROOT/'scripts/benchmark_compare.py'),
              'official_evaluator':args.official_checkpoint_grade}
    (root/'settings.json').write_text(json.dumps(settings))
    (root/'runs').mkdir()
    env={**os.environ,'PYTHONPATH':str(ROOT/'tests/offline_launch')+os.pathsep+str(ROOT/'src'),
         'KEISHO_TEST_LAUNCH_SETTINGS':str(root/'settings.json'),
         'OPENROUTER_API_KEY':'OFFLINE_HOST_CANARY','OPENAI_API_KEY':'OFFLINE_HOST_CANARY_OPENAI'}
    command=[str(ROOT/'.cache/swebench-evaluator/venv/bin/python'),str(ROOT/'scripts/benchmark_compare.py'),
        '--config',str(ROOT/'configs/swebench-comparison-v1.2.json'),'--plan',str(ROOT/'analysis/swebench-comparison-v1.2-plan.json'),
        '--authorization',str(ROOT/'analysis/swebench-comparison-v1.2-authorization-template.json'),
        '--run-dir',str(root/'runs/five-way-synthetic'),'--approve-live']
    with (root/'cli-output.txt').open('wb') as output:
        result=subprocess.run(command,cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT)
    (root/'cli-command.json').write_text(json.dumps({'command':command,'exit_code':result.returncode,
        'synthetic_engineering_check':True,'actual_provider_requests':0},indent=2)+'\n')
    print((root/'cli-output.txt').read_text())
    path=root/'runs/five-way-synthetic/result.json'
    if path.exists():print(json.dumps(json.loads(path.read_text()),indent=2))
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
