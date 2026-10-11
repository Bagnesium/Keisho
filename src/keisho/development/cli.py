import argparse
import json
from pathlib import Path
import tempfile

from keisho.core import canonical_json
from .suite import IDS,check_workspace,load_public,validate_suite,verify_development_sandbox,write_workspace
from .comparison import DEFAULT,execute,plan,prepare


def main(argv):
    parser=argparse.ArgumentParser(prog='keisho '+argv[0])
    if argv[0]=='dev-plan':
        parser.add_argument('--config',type=Path,default=DEFAULT);parser.add_argument('--out',type=Path)
    elif argv[0]=='dev-prepare':
        parser.add_argument('case',choices=IDS);parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
        parser.add_argument('--seed',type=int,default=17);parser.add_argument('--checkpoint-mode',choices=('prospective','user','retrospective-development'),default='prospective')
    elif argv[0]=='dev-continue':
        parser.add_argument('prepared',type=Path);parser.add_argument('--approve-live',action='store_true');parser.add_argument('--dollar-cap')
    elif argv[0]=='dev-suite':parser.add_argument('--out',type=Path)
    else:
        parser.add_argument('case',choices=IDS);parser.add_argument('--workspace',type=Path)
        parser.add_argument('--public',action='store_true')
    args=parser.parse_args(argv[1:])
    try:
        if argv[0]=='dev-plan':
            report=plan(args.config)
            if args.out:
                with args.out.open('x') as stream:stream.write(canonical_json(report)+'\n')
            print(json.dumps(report,indent=2));return 0
        if argv[0]=='dev-prepare':
            prepared=prepare(args.case,args.bundle,args.out,args.seed,args.checkpoint_mode)
            print(json.dumps({'prepared':str(args.out),'checkpoint_qualified':prepared['checkpoint_qualified'],'branch_order':prepared['branch_order'],'api_calls':0},indent=2));return 0
        if argv[0]=='dev-continue':
            if not args.approve_live or args.dollar_cap is None:
                raise ValueError('New paid continuation requires fresh explicit --approve-live and --dollar-cap; completed calibration approval cannot be reused')
            path=execute(args.prepared,args.dollar_cap,approve_live=True)
            status=json.loads((path/'result.json').read_text())['status']
            print(f'Continuation {status}; recorded {path}');return 0 if status=='complete' else 1
        if argv[0]=='dev-suite':
            report=validate_suite()
            if args.out:
                with args.out.open('x') as stream:stream.write(canonical_json(report)+'\n')
            print(json.dumps({'six_initial_states_failed':all(not row['outcomes']['initial']['passed'] for row in report['records']),
                'six_references_passed':all(row['outcomes']['reference']['passed'] for row in report['records']),
                'six_incomplete_fixes_rejected':all(not row['outcomes']['incomplete']['passed'] for row in report['records']),
                'api_calls':0,'report':str(args.out) if args.out else None},indent=2))
            return 0
        with tempfile.TemporaryDirectory(prefix='keisho-dev-check-') as temporary:
            root=Path(temporary).resolve();sandbox=verify_development_sandbox(root)
            workspace=args.workspace.resolve() if args.workspace else root/'task'
            if not args.workspace:task,_=load_public(args.case);write_workspace(workspace,task.files)
            result=check_workspace(args.case,workspace,sandbox,public_only=args.public)
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 0 if all(row['passed'] for row in result['results']) else 1
    except (ValueError,OSError,RuntimeError) as exc:print('Keisho development stopped: '+str(exc));return 2
