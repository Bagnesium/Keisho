"""Pin and verify the one official published task image before model admission."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.benchmark.comparison import PRIVATE, load_frozen_plan, validate_setup
from keisho.benchmark.environment import RepositorySession, docker
from keisho.core import require, digest
from swebench.task.repo import load_task_repo

IMAGE = 'swebench/sweb.eval.x86_64.pydata_1776_xarray-6721@sha256:58c7f4ada7f3cbcfcde50e0b55157701100cf694faa87978c672e368c0531898'


def main():
    config, task, plan = load_frozen_plan()
    validate_setup(config)
    require(task['instance_id'] == 'pydata__xarray-6721', 'preselected task changed')
    inspection = json.loads(docker('image', 'inspect', IMAGE).stdout)[0]
    require(inspection['Architecture'] == 'amd64' and inspection['Os'] == 'linux', 'unexpected official image platform')
    image = inspection['Id']
    session = RepositorySession(image)
    try:
        inventory = session.initialize_base(task['base_commit'])
        result = session.execute({'tool': 'shell', 'command': "python -c 'import sys,xarray,numpy,pandas; print(sys.version); print(xarray.__version__,numpy.__version__,pandas.__version__)'"})
        require(result['exit_code'] == 0 and not result['changed_paths'], 'prepared task imports or base files changed')
        versions = result['output']
    finally:
        session.close()
    recipe = PRIVATE / 'sources' / ('swe-bench-tasks-' + config['task_repo_commit'])
    row = load_task_repo(recipe, [task['instance_id']])[0]
    require(not row.get('test_assets'), 'this local-row path does not handle binary evaluator assets')
    row['image'] = IMAGE
    evaluator_dataset = PRIVATE / 'selected-task-evaluator.jsonl'
    with evaluator_dataset.open('x') as stream:
        stream.write(json.dumps(row) + '\n')
    meta = {'instance_id': task['instance_id'], 'image_ref': IMAGE, 'image_id': image,
            'platform': 'linux/amd64', 'host_execution': 'ARM Docker Desktop emulation',
            'environment_verified': True, 'base_commit': task['base_commit'],
            'base_inventory_sha256': digest(inventory), 'environment_versions': versions,
            'source': 'official SWE-bench registry; source build failed on incomplete libgdal download',
            'evaluator_dataset_sha256': hashlib.sha256(evaluator_dataset.read_bytes()).hexdigest(),
            'dataset_revision': config['dataset_revision'], 'task_repo_commit': config['task_repo_commit']}
    with (PRIVATE / 'prepared-task-image.json').open('x') as stream:
        stream.write(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
