"""Read-only repository capture and safe fresh-directory restoration."""

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess

from keisho.core import digest, require
from keisho.environments.base import safe_relative_path
from keisho.local_env import redact_credentials

EXCLUDED_DIRS = {".git", ".ssh", ".aws", ".agents", ".codex", ".venv", "node_modules",
                 "__pycache__", ".cache", "runs", "results", "analysis", "evaluators", "evaluator", "private"}
EXCLUDED_NAMES = {"gold.json", "evaluator.json", "evaluator_data.json", "credentials", "credentials.json",
                  "id_rsa", "id_ed25519", "id_ecdsa", ".netrc", ".npmrc", ".pypirc"}
SECRET = re.compile(r"-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|\b(?:sk-or-v1-[A-Za-z0-9_-]{12,}|sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})\b")
ASSIGNMENT = re.compile(r'''(?im)((?:[A-Z_]*(?:API_KEY|SECRET|ACCESS_TOKEN|PASSWORD)|api_key|password)["']?\s*[:=]\s*["']?)([^\s"',;]{12,})''')


def placeholder(value):
    return value.lower().startswith(("fake", "dummy", "example", "synthetic", "unit-test", "canary", "[redacted", "${")) or bool(re.fullmatch(r"[A-Za-z_]\w*(?:\.\w+)+\([^)]*",value))


def excluded(path):
    parts = Path(path).parts
    name = parts[-1]
    if any(part in EXCLUDED_DIRS for part in parts): return "excluded infrastructure, personal or evaluator directory"
    if name in EXCLUDED_NAMES or name.startswith(".env") or name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "credential or evaluator filename"
    return None


def sensitive(data):
    text = data.decode("utf-8", errors="replace")
    if SECRET.search(text): return True
    for match in ASSIGNMENT.finditer(text):
        value = match[2]
        if not placeholder(value):
            return True
    return any(value and value.encode() in data for key, value in os.environ.items() if key.endswith("API_KEY"))


def scrub(text):
    text = redact_credentials(text)
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]", text, flags=re.S)
    text = SECRET.sub("[REDACTED_CREDENTIAL]", text)
    def replace(match):
        return match[0] if placeholder(match[2]) else match[1] + "[REDACTED_CREDENTIAL]"
    return ASSIGNMENT.sub(replace, text)


def git(repo, *args, check=True):
    env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"GIT_OPTIONAL_LOCKS":"0","GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":"/dev/null"}
    base=["git","-C",str(repo),"-c","core.fsmonitor=false","-c","core.hooksPath=/dev/null"]
    # Reading a worktree must not invoke repository-configured filter or monitor programs.
    drivers=subprocess.run(base+["config","--name-only","--get-regexp",r"^filter\..*\.(clean|smudge|process|required)$"],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=30)
    overrides=[]
    for key in drivers.stdout.decode('utf-8').splitlines():
        require(re.fullmatch(r'filter\.[A-Za-z0-9_.-]+\.(?:clean|smudge|process|required)',key) is not None,'unsupported Git filter name')
        overrides += ['-c',key+('=false' if key.endswith('.required') else '=')]
    result = subprocess.run(base+overrides+list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=env,timeout=30)
    if check: require(result.returncode == 0, "read-only Git metadata query failed")
    return result.stdout if result.returncode == 0 else None


def read_safe(root,relative):
    """Open each component relative to descriptors, refusing link substitution."""
    safe_relative_path(relative)
    descriptor=os.open(root,os.O_RDONLY|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_NOFOLLOW',0))
    try:
        parts=Path(relative).parts
        for part in parts[:-1]:
            child=os.open(part,os.O_RDONLY|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_NOFOLLOW',0),dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        file=os.open(parts[-1],os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0),dir_fd=descriptor)
        with os.fdopen(file,'rb') as stream:
            before=os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'unsupported file or link substitution')
            content=stream.read();after=os.fstat(stream.fileno())
        require((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'file changed during read')
        return content,after
    finally:os.close(descriptor)


def git_metadata(repo):
    if git(repo, "rev-parse", "--is-inside-work-tree", check=False) != b"true\n":
        return {"available": False, "warning": "No Git baseline; modifications, staging and deletions are unknown"}, None, {}
    top=git(repo,"rev-parse","--show-toplevel")
    if Path(os.fsdecode(top).strip()).resolve()!=repo.resolve():
        return {"available":False,"warning":"Supplied directory is inside an ancestor Git tree; unrelated repository metadata is not imported"},None,{}
    raw = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries, index = [], {}
    chunks = raw.split(b"\0"); i = 0
    while i < len(chunks) and chunks[i]:
        text = os.fsdecode(chunks[i]); status_code, path = text[:2], text[3:]; i += 1
        entry = {"status": status_code, "path": path}
        if "R" in status_code or "C" in status_code:
            entry["original_path"] = os.fsdecode(chunks[i]); i += 1
        entries.append(entry)
    for chunk in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not chunk: continue
        meta, path = chunk.split(b"\t", 1); mode, blob, stage = meta.decode().split()
        require(stage == "0", "unmerged Git index is unsupported; resolve or record it before packing")
        index[os.fsdecode(path)] = {"mode": mode, "blob": blob}
    names = set(os.fsdecode(p) for p in git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    head = git(repo, "rev-parse", "--verify", "HEAD", check=False)
    ignored = [os.fsdecode(p) for p in git(repo, "ls-files", "--others", "--ignored", "--exclude-standard", "-z").split(b"\0") if p]
    return {"available": True, "head": head.decode().strip() if head else None, "status": entries,
            "ignored_paths": ignored, "index_entries": index, "restoration": "working contents; index versions retained for inspection, Git history/index not recreated"}, names, index


def capture(repo,excluded_paths=()):
    repo = Path(repo).absolute()
    require(not repo.is_symlink() and repo.is_dir(), "repository must be a real directory")
    repo = repo.resolve()
    metadata, allowed, index = git_metadata(repo)
    files, directories, exclusions, data, signatures = [], [], [], {}, {}
    total = 0
    stack = [repo]
    while stack:
        directory = stack.pop()
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(repo).as_posix(); safe_relative_path(relative)
            if relative in excluded_paths:
                exclusions.append({'path':relative,'reason':'explicit session source retained in the audit only'});continue
            if index.get(relative,{}).get('mode')=='160000':
                exclusions.append({'path':relative,'reason':'submodule checkout state is unsupported; not traversed'});continue
            reason = excluded(relative)
            if reason:
                exclusions.append({"path": relative, "reason": reason}); continue
            info = path.lstat()
            require(not stat.S_ISLNK(info.st_mode), f"symlink transfer is unsupported: {relative}")
            require(not info.st_mode & 0o7000, f"privileged filesystem mode is unsupported: {relative}")
            if stat.S_ISDIR(info.st_mode):
                directories.append({"path": relative, "mode": stat.S_IMODE(info.st_mode)}); stack.append(path); continue
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, f"special or hard-linked file is unsupported: {relative}")
            if allowed is not None and relative not in allowed:
                exclusions.append({"path": relative, "reason": "Git-ignored untracked content; relevance not explicitly supplied"}); continue
            if info.st_size > 8 * 1024 * 1024:
                exclusions.append({"path": relative, "reason": "file exceeds 8 MiB capture limit"}); continue
            content,after=read_safe(repo,relative)
            require((info.st_dev,info.st_ino)==(after.st_dev,after.st_ino),'workspace replaced during capture')
            if sensitive(content):
                exclusions.append({"path": relative, "reason": "credential-like file content"}); continue
            total += len(content); require(total <= 128 * 1024 * 1024, "workspace exceeds 128 MiB capture limit")
            data[relative] = content
            signatures[relative] = (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            files.append({"path": relative, "mode": stat.S_IMODE(info.st_mode), "size": len(content),
                          "sha256": hashlib.sha256(content).hexdigest(), "binary": b"\0" in content})
    for relative, signature in signatures.items():
        info = (repo / relative).lstat()
        require(not stat.S_ISLNK(info.st_mode) and signature == (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns), "workspace changed during capture")
    require(git_metadata(repo)[0] == metadata, "Git state changed during capture")
    # Store index versions of changed tracked files separately, including a staged deletion's metadata.
    index_data = {}
    for entry in metadata.get("status", []):
        path = entry["path"]
        if path in index and not excluded(path) and (path in data or not (repo/path).exists()):
            content = git(repo, "cat-file", "blob", index[path]["blob"])
            if sensitive(content):
                exclusions.append({"path": path, "reason": "credential-like staged contents omitted"})
            else: index_data[path] = content
    manifest = {"version": "workspace/1.0", "files": sorted(files, key=lambda row: row["path"]),
                "directories": sorted(directories, key=lambda row: row["path"]), "git": metadata,
                "exclusions": exclusions, "capture_limits": {"file_bytes": 8*1024*1024, "total_bytes": 128*1024*1024},
                "limitations": ["No process, service, dependency installation, xattr, ACL or timestamp capture", "Secret detection is heuristic, not perfect"]}
    manifest["sha256"] = digest(manifest)
    return manifest, data, index_data


def compare_scope(item, workspace):
    changed, unknown = [], []
    for path, expected in item.get("scope", {}).get("files", {}).items():
        safe_relative_path(path)
        file = Path(workspace) / path
        if excluded(path): unknown.append(path); continue
        if expected is None: unknown.append(path); continue
        if file.is_symlink() or not file.resolve().is_relative_to(Path(workspace).resolve()) or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected: changed.append(path)
    return {"changed_paths": changed, "unknown_paths": unknown,
            "requires_revalidation": bool(changed or unknown), "dependency_graph_known": False}


def compare_scope_hashes(item, inventory):
    """Same scope policy for an already observed isolated-workspace inventory."""
    changed,unknown=[],[]
    for path,expected in item.get('scope',{}).get('files',{}).items():
        safe_relative_path(path)
        if excluded(path) or expected is None:unknown.append(path);continue
        current=inventory.get(path)
        if current is None or current.get('symlink') or current.get('sha256')!=expected:changed.append(path)
    return {'changed_paths':changed,'unknown_paths':unknown,'requires_revalidation':bool(changed or unknown),'dependency_graph_known':False}


def restore(manifest, source, destination):
    destination = Path(destination).absolute()
    require(not destination.exists() and not destination.is_symlink(), "workspace already exists; refusing overwrite")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = destination.parent.resolve() / destination.name
    destination.mkdir(exist_ok=False)
    # Completion marker is outside the allowed captured workspace and cannot mask a partial restore.
    for row in manifest["directories"]:
        safe_relative_path(row["path"]); (destination / row["path"]).mkdir(parents=True, exist_ok=True)
    for row in manifest["files"]:
        safe_relative_path(row["path"])
        content,_ = read_safe(source,row["path"])
        require(hashlib.sha256(content).hexdigest() == row["sha256"], "workspace content hash mismatch")
        file = destination / row["path"]; file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("xb") as stream: stream.write(content)
        file.chmod(row["mode"])
    for row in reversed(manifest["directories"]): (destination / row["path"]).chmod(row["mode"])
    for row in manifest["files"]:
        file = destination / row["path"]
        require(hashlib.sha256(file.read_bytes()).hexdigest() == row["sha256"] and stat.S_IMODE(file.stat().st_mode) == row["mode"], "restoration verification failed")
    return destination
