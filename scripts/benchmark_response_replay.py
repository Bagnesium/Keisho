"""Offline saved-text replay in an owned setup-only Docker fixture, never live."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.agents.scripted import ScriptedModel
from keisho.benchmark.comparison import response_settings
from keisho.benchmark.environment import RepositorySession, docker
from keisho.core import require
from keisho.handoff.session import load_session
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets, Recorder, run_agent, parse_output


def main():
    fixture = ROOT / 'tests/data/swebench-first-response'
    manifest = json.loads((fixture / 'provenance.json').read_text())
    for name, row in manifest['files'].items():
        require(hashlib.sha256((fixture / name).read_bytes()).hexdigest() == row['sha256'], 'fixture provenance mismatch')
    text = (fixture / 'response-text.json').read_text()
    try:
        parse_output(text, set())
    except ValueError as exc:
        legacy_failure = {'type': type(exc).__name__, 'reason': str(exc), 'tool_actions': 0}
    else:
        raise ValueError('legacy failure no longer reproduced')
    config = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
    system, policy, _ = response_settings(config)
    # Existing local setup image only. No pull/build and no original Xarray workspace.
    image_name = 'swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest'
    image = json.loads(docker('image', 'inspect', image_name).stdout)[0]['Id']
    output = ROOT / 'runs/swebench-integration/response-policy-repair'
    raw = RawRun(output, 'docker-replay')  # Exclusive offline artifact, not the live guard.
    raw.write_artifact('provenance.json', manifest)
    session = RepositorySession(image, audit=raw)
    try:
        session.base_inventory = session.inventory()
        action = json.loads(text)['action']
        require(action['tool'] == 'write_file', 'fixture permits only the saved write')
        require(action['path'] not in session.base_inventory, 'fixture target already exists')
        execution = run_agent(ScriptedModel((text,)), session, Recorder(raw), 'OFFLINE SOFTWARE FIXTURE ONLY',
                              system, '', 1, Budgets(1, 1, 2048, 20000, 32000, 128000),
                              role='predecessor', response_policy=policy)
        require(execution.tool_calls == 1 and execution.reason == 'budget_exhausted', 'saved write replay failed')
        inventory = session.inventory()
        require(inventory[action['path']]['sha256'] == hashlib.sha256(action['content'].encode()).hexdigest(), 'written content changed')
        raw.freeze()
        state, _, _ = load_session(raw.path, 'OFFLINE SOFTWARE FIXTURE ONLY')
        require(not any(i['category'] == 'hypothesis' for i in state['items']), 'invalid annotations entered state')
        result = {'offline_software_fixture_only': True, 'provider_requests': 0, 'credential_validation_requests': 0,
                  'scripted_responses': 1, 'saved_write_actions': 1, 'script_content_executed': False,
                  'image_id': image, 'setup_image': image_name, 'original_task_workspace_used': False,
                  'legacy_policy': legacy_failure, 'amended_policy': policy,
                  'annotation_coverage': state['extraction']['annotation_coverage'],
                  'official_task_grade': None, 'cost_usd': '0'}
        raw.write_artifact('replay-result.json', result)
        print(json.dumps(result, indent=2))
    finally:
        session.close()


if __name__ == '__main__':
    main()
