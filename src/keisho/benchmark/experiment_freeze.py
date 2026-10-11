"""Verify prospectively pinned local experiment components before admission."""
import hashlib
import json
from pathlib import Path, PurePosixPath

from keisho.core import digest, require


def validate_freeze(config, root):
    root = Path(root).resolve()
    manifest_path = config.get('experiment_manifest')
    require(isinstance(manifest_path, str) and PurePosixPath(manifest_path).as_posix() == manifest_path
            and not PurePosixPath(manifest_path).is_absolute()
            and all(part not in ('.', '..') for part in manifest_path.split('/')), 'unsafe experiment manifest path')
    path = root / manifest_path
    require(path.is_file() and not any(parent.is_symlink() for parent in (path, *path.parents)), 'unsafe or missing experiment manifest')
    manifest = json.loads(path.read_text())
    require(digest(manifest) == config.get('experiment_manifest_sha256'), 'experiment manifest pin changed')
    require(manifest.get('version') == 'swebench-experiment-freeze/1.4', 'unsupported experiment freeze')
    require(isinstance(manifest.get('files'), dict) and manifest['files'], 'empty experiment freeze')
    for relative, expected in manifest['files'].items():
        pure = PurePosixPath(relative)
        require(not pure.is_absolute() and pure.as_posix() == relative and '\\' not in relative
                and all(part not in ('.', '..') for part in relative.split('/')), 'unsafe frozen component path')
        component = root / relative
        require(component.is_file() and not any(parent.is_symlink() for parent in (component, *component.parents)),
                'unsafe or missing frozen component: ' + relative)
        require(hashlib.sha256(component.read_bytes()).hexdigest() == expected, 'frozen experiment component changed: ' + relative)
    return manifest
