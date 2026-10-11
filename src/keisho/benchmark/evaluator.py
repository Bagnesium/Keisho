"""Command bridge to an unchanged, dedicated official evaluator installation."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time
import uuid

from keisho.core import require


def unique_run_id(instance, condition, patch, namespace=None):
    fingerprint = hashlib.sha256(patch.encode()).hexdigest()[:12]
    require(namespace is None or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', namespace), 'unsafe evaluation namespace')
    prefix = (namespace + '-') if namespace else ''
    return 'keisho-' + prefix + condition.lower().replace('_', '-') + '-' + fingerprint + '-' + uuid.uuid4().hex[:12]


def write_prediction(path, task, model, patch):
    require(isinstance(patch, str), 'patch must be text')
    row = {'instance_id': task['instance_id'], 'model_name_or_path': model, 'model_patch': patch}
    with Path(path).open('x') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def report_status(report, instance):
    if instance in report.get('resolved_ids', []):
        return 'resolved'
    if instance in report.get('unresolved_ids', []):
        return 'unresolved'
    return 'error'


def evaluate(private, config, task, condition, prediction=None, *, gold=False, no_patch=False, run_namespace=None):
    private = Path(private).resolve()
    patch = Path(prediction).read_text() if prediction else ('gold' if gold else 'unpatched')
    run_id = unique_run_id(task['instance_id'], condition, patch, run_namespace)
    out = private / 'invocations' / run_id
    out.mkdir(parents=True, exist_ok=False)
    # A pinned official task-repo row is a documented local dataset input. Its
    # unchanged eval script/keys and digest-pinned image avoid rebuilding the
    # same image on every grade. The source/HF equality check is an admission gate.
    dataset = private / 'selected-task-evaluator.jsonl'
    require(dataset.is_file(), 'pinned evaluator task row not prepared')
    command = [str(private / 'venv/bin/swebench'), 'eval', str(dataset), '-i', task['instance_id'],
               '--run-id', run_id, '-j', '1']
    command += ['--gold'] if gold else ['-p', str(Path(prediction).resolve())]
    require(not no_patch, 'unpatched validation uses the official skip_patch API via benchmark_unpatched.py')
    metadata = {'command': command, 'run_id': run_id, 'condition': condition,
                'instance_id': task['instance_id'], 'setup_only': gold or no_patch, 'started_at': time.time()}
    (out / 'command.json').write_text(json.dumps(metadata, indent=2) + '\n')
    # Credentials never enter evaluator subprocess environment or containers.
    env = {k: v for k, v in os.environ.items() if k!='PYTHONPATH' and not k.startswith('KEISHO_TEST_')
           and not any(s in k.upper() for s in ('TOKEN', 'API_KEY', 'SECRET', 'PASSWORD'))}
    with (out / 'output.txt').open('wb') as stream:
        code = subprocess.run(command, cwd=private, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    report_path = private / 'logs/evaluation' / run_id / 'results.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    metadata.update(exit_code=code, ended_at=time.time(), report_path=str(report_path),
                    status=report_status(report, task['instance_id']) if code == 0 else 'error')
    (out / 'result.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata
