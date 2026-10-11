"""Record one development/setup command without shell interpolation or retries."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--label', required=True)
    p.add_argument('--cwd', default='.')
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    root = Path(__file__).resolve().parents[1]
    out = root / 'runs/swebench-integration/commands' / a.label
    out.mkdir(parents=True, exist_ok=False)
    metadata = {'command': command, 'cwd': str(Path(a.cwd).resolve()),
                'started_at_unix': time.time(), 'automatic_retries': 0}
    (out / 'command.json').write_text(json.dumps(metadata, indent=2) + '\n')
    with (out / 'output.txt').open('wb') as log:
        child = subprocess.Popen(command, cwd=a.cwd, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = child.wait()
        except KeyboardInterrupt:
            child.terminate()
            code = child.wait()
        finally:
            metadata.update(exit_code=child.returncode, ended_at_unix=time.time())
            (out / 'result.json').write_text(json.dumps(metadata, indent=2) + '\n')
    sys.stdout.write((out / 'output.txt').read_text(errors='replace'))
    print('Recorded:', out, 'exit:', code)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
