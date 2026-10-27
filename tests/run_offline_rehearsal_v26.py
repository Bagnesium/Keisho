"""Public five-branch rehearsal command for v2.6 binding with test-only transport,
real Docker tools, and real official SWE-bench evaluator in Docker.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)

    settings = {
        'kind': 'benchmark_v26',
        'fixture_root': str(root),
        'public_entry': str(ROOT / 'scripts/benchmark_compare.py'),
        'rehearsal_binding': 'v2.6'
    }
    (root / 'settings.json').write_text(json.dumps(settings, indent=2))
    (root / 'runs').mkdir()

    cfg = json.loads((ROOT / 'configs/swebench-comparison-v2.6.json').read_text())
    plan = json.loads((ROOT / 'analysis/swebench-comparison-v2.6-plan.json').read_text())
    freeze = json.loads((ROOT / 'analysis/swebench-v2.6-final-source-freeze.json').read_text())

    # Create isolated rehearsal authorization template
    auth = {
        'version': 'swebench-authorization/2.0',
        'authorization_id': 'REHEARSAL-V26-OFFLINE-ONLY',
        'config_sha256': digest(cfg),
        'plan_sha256': digest(plan),
        'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00',
        'attempts': 1,
        'provider_inference_authorized': False,
        'note': 'REHEARSAL ONLY: strictly offline simulation with zero real inference authorized.'
    }
    auth_path = root / 'swebench-comparison-v2.6-rehearsal-authorization.json'
    auth_path.write_text(json.dumps(auth, indent=2) + '\n')

    env = {
        **os.environ,
        'PYTHONPATH': str(ROOT / 'tests/offline_launch') + os.pathsep + str(ROOT / 'src'),
        'KEISHO_TEST_LAUNCH_SETTINGS': str(root / 'settings.json'),
        'OPENROUTER_API_KEY': 'OFFLINE_REHEARSAL_CANARY',
        'OPENAI_API_KEY': 'OFFLINE_REHEARSAL_CANARY_OPENAI'
    }

    run_dir = root / 'runs' / root.name

    command = [
        str(ROOT / '.cache/swebench-evaluator/venv/bin/python'),
        str(ROOT / 'scripts/benchmark_compare.py'),
        '--config', str(ROOT / 'configs/swebench-comparison-v2.6.json'),
        '--plan', str(ROOT / 'analysis/swebench-comparison-v2.6-plan.json'),
        '--authorization', str(auth_path),
        '--run-dir', str(run_dir),
        '--approve-live'
    ]

    with (root / 'cli-output.txt').open('wb') as output:
        result = subprocess.run(command, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT)

    cli_command_record = {
        'command': command,
        'exit_code': result.returncode,
        'synthetic_engineering_check': True,
        'actual_provider_requests': 0
    }
    (root / 'cli-command.json').write_text(json.dumps(cli_command_record, indent=2) + '\n')
    print((root / 'cli-output.txt').read_text())

    res_path = run_dir / 'result.json'
    if res_path.exists():
        print(json.dumps(json.loads(res_path.read_text()), indent=2))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
