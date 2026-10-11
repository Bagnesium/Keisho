import argparse
import json
from pathlib import Path

from .bundle import inspect,pack,resume


def main(argv):
    parser=argparse.ArgumentParser(prog="keisho "+argv[0])
    if argv[0]=="pack":
        parser.add_argument("--repo",type=Path,required=True);parser.add_argument("--session",type=Path,required=True)
        parser.add_argument("--task",required=True);parser.add_argument("--out",type=Path,required=True)
        parser.add_argument("--token-budget",type=int,default=2048);parser.add_argument("--accept",action="append",default=[])
        parser.add_argument("--constraint",action="append",default=[])
    else:
        parser.add_argument("bundle",type=Path)
        if argv[0]=="resume":
            parser.add_argument("--manual",action="store_true",required=True);parser.add_argument("--workspace",type=Path,required=True)
        else:
            parser.add_argument("--item");parser.add_argument("--compare-workspace",type=Path);parser.add_argument("--json",action="store_true")
    args=parser.parse_args(argv[1:])
    try:
        if argv[0]=="pack":
            path,manifest=pack(args.repo,args.session,args.task,args.out,args.token_budget,args.accept,args.constraint)
            selection=manifest["token_counts"]["compact"]
            print(f"Packed {path}: {selection['tokens']}/{selection['budget']} ({selection['method']}, exact={selection['exact']}); {len(selection['omissions'])} whole items omitted. No API calls.")
            data=inspect(path)
            for warning in data["state"]["warnings"]:print("Warning: "+warning)
            print(f"Workspace exclusions: {len(data['workspace']['exclusions'])}; inspect before continuing.")
        elif argv[0]=="resume":
            directory,prompt=resume(args.bundle,args.workspace)
            print(f"Open {directory} in a NEW coding-agent session. Supply {prompt}. No API calls or repository commands executed.")
        else:
            data=inspect(args.bundle,args.item,args.compare_workspace)
            if args.json:print(json.dumps(data,indent=2,ensure_ascii=False))
            elif args.item:print(json.dumps({key:data[key] for key in ("item","supporting_sources")},indent=2,ensure_ascii=False))
            else:
                print(data["handoff"])
                print("Omitted state items: "+json.dumps(data["state"]["selection"]["omissions"],ensure_ascii=False))
                print("Workspace exclusions: "+json.dumps(data["workspace"]["exclusions"],ensure_ascii=False))
                if args.compare_workspace:print(json.dumps({key:data[key] for key in ("scope_comparison","workspace_changes")},indent=2,ensure_ascii=False))
        return 0
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(f"Keisho handoff stopped: {exc}");return 2
