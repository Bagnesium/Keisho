"""Regenerate the v2.2 freeze files offline. Never touches v2.1 or historical records."""
import copy, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

m = copy.deepcopy(load('analysis/swebench-experiment-v2.1-manifest.json'))
for f in ('src/keisho/benchmark/notes_reader.py', 'src/keisho/benchmark/vendor/provenance.json'):
    m['files'][f] = sha(f)
for f in list(m['files']):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        m['files'][f] = sha(f)  # tracked files re-hashed (unchanged ones keep their v2.1 value)
m['files'] = dict(sorted(m['files'].items()))
m['freeze_status'] = 'FROZEN 2026-10-23 (Bagi approved v2.2 freeze); live execution NOT authorized'
m['binding_module_note'] = ('Binding modules (comparison.py, benchmark_compare.py, notes_reader.py, experiment_freeze.py) are pinned in '
    'analysis/swebench-v2.2-final-source-freeze.json, whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = ['swebench-handoff/2.2: schema-specific guarded reader structured-notes-reader/1.0 for STRUCTURED_NOTES_2K note generation (src/keisho/benchmark/notes_reader.py); framing log and failure artifact; zero retries',
    'binding-module pin via final source freeze bound by authorization']
dump('analysis/swebench-experiment-v2.2-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.1.json')
cfg.update({'version': 'swebench-handoff/2.2', 'supersedes_configuration': 'configs/swebench-comparison-v2.1.json',
            'experiment_manifest': 'analysis/swebench-experiment-v2.2-manifest.json', 'experiment_manifest_sha256': digest(m),
            'notes_reader_version': 'structured-notes-reader/1.0', 'live_execution_authorized': False})
dump('configs/swebench-comparison-v2.2.json', cfg)

plan = load('analysis/swebench-comparison-v2.1-plan.json')
plan.update({'version': 'swebench-plan/2.2', 'config_sha256': digest(cfg), 'experiment_manifest_sha256': digest(m),
             'freeze_status': 'FROZEN; no spending authorized', 'new_spending_authorized': False,
             'intervention': 'Specification v2.2 adds a schema-specific guarded reader for the STRUCTURED_NOTES_2K generator output and pins binding modules; all prompts, models, task, budgets, reasoning effort none and cost envelope unchanged from v2.1.'})
dump('analysis/swebench-comparison-v2.2-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V22_SPEC_SHA = '[^']*'", f"V22_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V22_PLAN_SHA = '[^']*'", f"V22_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {'version': 'swebench-final-source-freeze/1.0', 'freeze_status': 'FROZEN',
          'config_sha256': digest(cfg), 'plan_sha256': digest(plan),
          'files': {f: sha(f) for f in ('scripts/benchmark_compare.py', 'src/keisho/benchmark/comparison.py',
                    'src/keisho/benchmark/experiment_freeze.py', 'src/keisho/benchmark/notes_reader.py')}}
dump('analysis/swebench-v2.2-final-source-freeze.json', freeze)

auth = {'version': 'swebench-authorization/2.0', 'authorization_id': 'PENDING-V22-NEW-USER-AUTHORIZATION',
        'config_sha256': digest(cfg), 'plan_sha256': digest(plan), 'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00', 'attempts': 1, 'provider_inference_authorized': False,
        'note': 'TEMPLATE ONLY; no inference authorized. Create a fresh explicit authorization record after approval; never reuse a guard.'}
dump('analysis/swebench-comparison-v2.2-authorization-template.json', auth)
print(json.dumps({'manifest': digest(m), 'config': digest(cfg), 'plan': digest(plan), 'final_source_freeze': digest(freeze),
                  'authorization_template': digest(auth), 'comparison.py_sha256': freeze['files']['src/keisho/benchmark/comparison.py']}, indent=1))
