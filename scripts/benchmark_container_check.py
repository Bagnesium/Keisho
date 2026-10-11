"""API-free container restoration and tool checks on the setup-only image."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.benchmark.environment import RepositorySession, docker
from keisho.benchmark.protocol import ValidationCheckpoint
from keisho.core import require
from keisho.pilot.tools import InvalidAction


def main():
    image_name = 'swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest'
    image = json.loads(docker('image', 'inspect', image_name).stdout)[0]['Id']
    session = RepositorySession(image)
    try:
        base = 'cffd4e0f86fefd4802349a9f9b19ed70934ea354'
        baseline = session.initialize_base(base)
        session.execute({'tool': 'write_file', 'path': 'keisho_fixture.py', 'content': 'predecessor = 1\n'})
        validation = session.execute({'tool': 'shell', 'command': 'python -m compileall -q keisho_fixture.py'})
        gate = ValidationCheckpoint()
        gate({'tool': 'write_file'}, {'changed_paths': ['keisho_fixture.py']})
        require(gate(validation['action'], validation), 'completed validation checkpoint missed')
        checkpoint_image, checkpoint = session.freeze()
    finally:
        session.close()
    a, b = RepositorySession(checkpoint_image), RepositorySession(checkpoint_image)
    try:
        a.base_inventory = b.base_inventory = baseline
        require(a.inventory() == b.inventory() == checkpoint, 'checkpoint restoration differs')
        a.execute({'tool': 'write_file', 'path': 'keisho_fixture.py', 'content': 'predecessor = 1\nsuccessor = 2\n'})
        require(b.inventory() == checkpoint and a.inventory() != checkpoint, 'branch write contaminated sibling')
        patch = a.patch(base)
        require('+predecessor = 1' in patch and '+successor = 2' in patch, 'cumulative patch lost predecessor edit')
        try:
            b.execute({'tool': 'read_file', 'path': '../../.env'})
        except InvalidAction:
            pass
        else:
            raise ValueError('path escape allowed')
        r = b.execute({'tool': 'shell', 'command': "python -c 'import os; assert not any(k.endswith(\"API_KEY\") for k in os.environ); assert not os.path.exists(\"/var/run/docker.sock\"); assert not os.path.exists(\"/Users/bagnesium\")'"})
        require(r['exit_code'] == 0, 'host/credential boundary check failed')
        print(json.dumps({'software_fixture_only': True, 'smoke_image': image_name, 'image_id': image,
                  'checkpoint_image_id': checkpoint_image, 'restoration_equal': True, 'branches_independent': True,
                  'cumulative_patch': True, 'host_mounts_or_keys': False, 'official_task_success_claim': False}, indent=2))
    finally:
        a.close()
        b.close()


if __name__ == '__main__':
    main()
