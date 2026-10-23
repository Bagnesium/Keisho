"""Regenerate the v2.4 FROZEN freeze files offline from the frozen v2.3 records (read only).

v2.4 = v2.3 + two fixes: (1) malformed/schema-invalid responses are invalid-action strikes
(invalid-action-strike/1.0) instead of ending the run; (2) the evaluator uses the task-specific
evaluator row and refuses on an instance-id mismatch. Budgets, prices and the envelope are unchanged.
Never touches v2.1/v2.2/v2.3 or historical records. Do NOT run scripts/v23_proposal_digests.py on this branch.
"""
import copy, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

m = copy.deepcopy(load('analysis/swebench-experiment-v2.3-manifest.json'))
for f in list(m['files']):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        m['files'][f] = sha(f)
m['files'] = dict(sorted(m['files'].items()))
m['freeze_status'] = 'FROZEN 2026-10-23 (Bagi approved v2.4 freeze); live execution requires a separate authorization record'
m['binding_module_note'] = ('Binding modules are pinned in analysis/swebench-v2.4-final-source-freeze.json, '
                            'whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = [
    'invalid-action-strike/1.0: an unparseable or schema-invalid action response is an invalid action under the existing 3-strikes rule; nothing executes; same rejection feedback; usage/identity/truncation failures stay terminal',
    'evaluator: task-specific evaluator row for the frozen task; refuses unless the row instance id equals the task']
dump('analysis/swebench-experiment-v2.4-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.3.json')
cfg.update({'version': 'swebench-handoff/2.4', 'supersedes_configuration': 'configs/swebench-comparison-v2.3.json',
            'experiment_manifest': 'analysis/swebench-experiment-v2.4-manifest.json', 'experiment_manifest_sha256': digest(m),
            'malformed_response_policy': 'invalid-action-strike/1.0',
            'evaluator_dataset_policy': 'task-specific row; refuse on instance-id mismatch',
            'live_execution_authorized': False})
dump('configs/swebench-comparison-v2.4.json', cfg)

plan = load('analysis/swebench-comparison-v2.3-plan.json')
plan.update({'version': 'swebench-plan/2.4', 'config_sha256': digest(cfg), 'experiment_manifest_sha256': digest(m),
             'freeze_status': 'FROZEN; no spending authorized', 'new_spending_authorized': False,
             'intervention': plan['intervention'] + ' Specification v2.4 counts malformed or schema-invalid action responses as invalid-action strikes and grades with the task-specific evaluator row.'})
dump('analysis/swebench-comparison-v2.4-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V24_SPEC_SHA = '[^']*'", f"V24_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V24_PLAN_SHA = '[^']*'", f"V24_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {'version': 'swebench-final-source-freeze/1.0', 'freeze_status': 'FROZEN', 'revision': 1,
          'config_sha256': digest(cfg), 'plan_sha256': digest(plan),
          'files': {f: sha(f) for f in ('scripts/benchmark_compare.py', 'src/keisho/benchmark/comparison.py',
                    'src/keisho/benchmark/experiment_freeze.py', 'src/keisho/benchmark/notes_reader.py')}}
dump('analysis/swebench-v2.4-final-source-freeze.json', freeze)

auth = {'version': 'swebench-authorization/2.0', 'authorization_id': 'PENDING-V24-NEW-USER-AUTHORIZATION',
        'config_sha256': digest(cfg), 'plan_sha256': digest(plan), 'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00', 'attempts': 1, 'provider_inference_authorized': False,
        'note': 'TEMPLATE ONLY; no inference authorized. "attempts" counts launches; predecessor attempts are governed by the config rule.'}
dump('analysis/swebench-comparison-v2.4-authorization-template.json', auth)
print(json.dumps({'manifest': digest(m), 'config': digest(cfg), 'plan': digest(plan), 'final_source_freeze': digest(freeze),
                  'authorization_template': digest(auth), 'comparison.py_sha256': freeze['files']['src/keisho/benchmark/comparison.py'],
                  'agent.py_sha256': m['files']['src/keisho/pilot/agent.py'], 'evaluator.py_sha256': m['files']['src/keisho/benchmark/evaluator.py'],
                  'envelope': plan['maximum_noncached_costs_usd'], 'total_envelope_usd': plan['total_envelope_usd'],
                  'reservation': plan['largest_request_reservation_usd']}, indent=1))
