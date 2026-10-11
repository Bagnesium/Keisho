"""Genuine bounded work on a capture-preview feature in a separate Keisho copy.

Records actual operations; it never fabricates or invokes a successor.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from keisho.core import canonical_json,utc_now
from keisho.handoff.workspace import capture,restore
from keisho.logging.raw import Event,EventKind,RawRun

base=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/"runs/local-dogfood-v2"
base.mkdir(exist_ok=False)
goal="Add a read-only capture-preview command to Keisho so a user can inspect allowed files and exclusions before writing a bundle. Preserve pack/inspect/resume behavior and all secret filters."
criteria=["./keisho preview --repo PATH --json reports the same allowed files and exclusion reasons as pack",
          "Preview creates no bundle or changes in the inspected repository and makes no API calls",
          "Sensitive contents remain excluded; test Unicode paths and Git-ignored inputs; document limitations"]
raw=RawRun(base/"session","actual-preview-investigation")
raw.append(Event("predecessor_task",EventKind.USER_MESSAGE,"user",utc_now(),canonical_json({"content":goal})))
raw.append(Event("criteria",EventKind.ANNOTATION,"developer",utc_now(),canonical_json({"type":"local_task_state","acceptance":criteria,
    "constraints":["Do not execute imported commands, initialize a provider, or modify the original repository", "Reuse capture policy; secret detection remains heuristic"],
    "next_actions":["Wire the working preview helper into the CLI, add focused no-write/secret-filter regression checks, and document preview usage"]})))
manifest,data,_=capture(ROOT)
(base/"capture-source-manifest.json").write_text(canonical_json(manifest)+"\n")
source=base/"source-workspace"
staging=base/"copy-source";staging.mkdir()
for path,content in data.items():
    file=staging/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(content)
restore(manifest,staging,source)
count=0
def hashes():
    return {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/"src/keisho/handoff/workspace.py",source/"src/keisho/pilot/cli.py",source/"src/keisho/handoff/preview.py") if p.exists()}
def operation(action,run):
    global count
    count+=1;call=f"predecessor_tool_{count:03d}";result=f"predecessor_result_{count:03d}";before=hashes()
    raw.append(Event(call,EventKind.TOOL_CALL,"developer",utc_now(),canonical_json({"action":action})))
    payload=run()
    raw.append(Event(result,EventKind.TOOL_RESULT,"developer",utc_now(),canonical_json({"action":action,**payload,"source_hashes_before":before,"source_hashes_after":hashes()}),(call,)))
for name in ("src/keisho/handoff/workspace.py","src/keisho/pilot/cli.py"):
    operation({"tool":"read_file","path":name},lambda name=name:{"path":name,"content":(source/name).read_text()})
prototype='''"""Read-only preview core. CLI wiring and regression coverage are unfinished."""
from keisho.handoff.workspace import capture

def preview(repo):
    manifest, _, _ = capture(repo)
    return {"allowed_files": [row["path"] for row in manifest["files"]],
            "exclusions": manifest["exclusions"], "limitations": manifest["limitations"],
            "api_calls": 0}
'''
path=source/"src/keisho/handoff/preview.py"
def write_prototype():
    path.write_text(prototype)
    return {"path":str(path.relative_to(source)),"content_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
operation({"tool":"write_file","path":str(path.relative_to(source)),"content":prototype},write_prototype)
def check_prototype():
    spec=importlib.util.spec_from_file_location("actual_preview_prototype",path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    result=module.preview(source)
    after={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    passed=before==after and 'src/keisho/handoff/preview.py' in result['allowed_files'] and result['api_calls']==0
    return {"results":[{"id":"preview_helper_no_source_changes","passed":passed}],"allowed_file_count":len(result['allowed_files']),"exclusion_count":len(result['exclusions']),"limitation":"Helper tested with identical host capture implementation; CLI wiring and platform cases remain unfinished"}
operation({"tool":"run_tests","test_ids":["preview_helper_no_source_changes"]},check_prototype)
def help_check():
    result=subprocess.run([str(source/"keisho"),"--help"],cwd=source,capture_output=True,text=True)
    return {"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr,"observation":"Preview command is not yet registered"}
operation({"tool":"run_command","command":"./keisho --help"},help_check)
raw.freeze()
for args in (["pack","--repo",str(source),"--session",str(raw.path/"trajectory.json"),"--task",goal,"--out",str(base/"bundle"),"--token-budget","2048"],
             ["inspect",str(base/"bundle")],
             ["resume",str(base/"bundle"),"--manual","--workspace",str(base/"resumed-workspace")],
             ["inspect",str(base/"bundle"),"--item","S3"]):
    result=subprocess.run([str(ROOT/"keisho"),*args],cwd=ROOT,capture_output=True,text=True)
    with (base/(args[0]+("-source" if "--item" in args else "")+"-output.txt")).open('x') as stream:stream.write(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError("dogfood CLI operation failed: "+result.stdout)
with (base/"dogfood-record.json").open('x') as stream:
    stream.write(canonical_json({"objective":goal,"acceptance":criteria,"actual_completed_tools":count,"origin":"genuine follow-on feature; bounded implementation in separate Keisho copy",
        "checkpoint":"user-triggered completed-tool boundary; unfinished CLI integration","fresh_successor_executed":False,"api_calls":0,
        "bundle":str(base/"bundle"),"workspace":str(base/"resumed-workspace"),"prompt":str(base/"resumed-workspace.keisho-resume/NEXT_SESSION_PROMPT.md")})+'\n')
print("Actual unfinished preview-feature handoff saved: "+str(base))
