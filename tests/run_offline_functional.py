"""Durable real-Docker synthetic CLI check. Not a production launch option."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_functional_public import prepare, launch

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',default='complete',choices=['complete','invalid_json','invalid_action','provider_failure','infrastructure','task_failure','budget'])
    parser.add_argument('--config-name',default='functional-confirmation12-v1.json')
    args=parser.parse_args()
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    prepare(root,args.mode,args.config_name)
    result,run=launch(root)
    print(result.stdout+result.stderr,end='')
    print(json.dumps({'synthetic_engineering_check':True,'actual_provider_requests':0,
                      'public_command_record':str(root/'cli-command.json'),'artifacts':str(run)}))
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
