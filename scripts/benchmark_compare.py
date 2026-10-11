"""Start only the prospectively frozen and evaluator-validated one-task block."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from keisho.benchmark.comparison import execute, dry_run
from keisho.core import ValidationError
import json


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--authorization', type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--approve-live', action='store_true')
    a = p.parse_args(argv)
    args = {'config_path': a.config, 'plan_path': a.plan, 'run_dir': a.run_dir, 'authorization_path': a.authorization}
    try:
        if a.dry_run:
            print(json.dumps(dry_run(**args), indent=2))
        else:
            print(execute(approve_live=a.approve_live, **args))
    except (ValidationError, OSError, ValueError) as exc:
        print('Benchmark start refused: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
