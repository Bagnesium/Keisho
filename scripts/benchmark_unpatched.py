"""Setup-only official API validation with skip_patch=True, unchanged grading."""
import argparse
import json
from pathlib import Path

from swebench.harness.run_evaluation import run_instances, write_run_metadata
from swebench.harness.reporting import make_run_report
from swebench.task.repo import load_task_repo


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task-repo', required=True)
    p.add_argument('--instance', required=True)
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    require_instance = 'sympy__sympy-20590'
    if a.instance != require_instance:
        raise ValueError('only designated setup instance allowed')
    rows = load_task_repo(a.task_repo, [a.instance])
    predictions = {a.instance: {'instance_id': a.instance, 'model_name_or_path': 'setup-unpatched', 'model_patch': ''}}
    write_run_metadata(a.run_id, 'princeton-nlp/SWE-bench_Verified', 'test', a.task_repo)
    run_instances(predictions, rows, max_workers=1, run_id=a.run_id, timeout=1800,
                  rewrite_reports=False, skip_patch=True, task_repo=a.task_repo)
    import docker
    client = docker.from_env()
    try:
        print(make_run_report(predictions, rows, a.run_id, client))
    finally:
        client.close()
    # The official aggregate reporter deliberately counts empty predictions as
    # empty rather than completed. The unchanged per-instance grader is the
    # relevant outcome for skip_patch setup validation.
    instance_report = Path('logs/evaluation') / a.run_id / 'setup-unpatched' / a.instance / 'report.json'
    official = json.loads(instance_report.read_text())
    print(json.dumps({'official_per_instance_report': str(instance_report),
                      'resolved': official[a.instance]['resolved'], 'setup_only': True,
                      'aggregate_note': 'empty patch counted separately by official reporter'}))


if __name__ == '__main__':
    main()
