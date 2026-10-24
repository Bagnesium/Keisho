"""Generate prospective v2.5 PROPOSAL freeze files offline (read only).

v2.5 = v2.4 + two fixes:
(1) response_measurements.py: assess_text uses extract_action_json so runtime-accepted
    framing is measured consistently without parser divergence;
(2) response_measurements.py: measure_run handles absent actions explicitly, ensuring
    an unparseable or absent action cannot crash with AttributeError, does not invent
    a successful action, and evaluates tool_execution_successful=False.
Checkpoint rule strictly follows registered specification; bin/test recognition proposed.
Budgets, prices, models, prompt, task and envelope are unchanged from v2.4.
Never touches v2.1/v2.2/v2.3/v2.4 or historical records.
"""
import copy, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

m = copy.deepcopy(load('analysis/swebench-experiment-v2.4-manifest.json'))
for f in list(m['files']):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        m['files'][f] = sha(f)
m['files'] = dict(sorted(m['files'].items()))
m['freeze_status'] = 'PROSPECTIVE PROPOSAL (not approved or launchable; live execution not authorized)'
m['binding_module_note'] = ('Binding modules are pinned in analysis/swebench-v2.5-final-source-freeze.json, '
                            'whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = [
    'response-measurements: assess_text uses extract_action_json to align audit measurement with runtime reader framing rules without parser divergence',
    'response-measurements: measure_run guards action against absent/non-dict shapes, preventing AttributeError and explicitly evaluating tool_execution_successful=False without inventing actions',
    'checkpoint-rule: confirms that checkpoint on validation result with exit 1 strictly follows registered rule; proposes bin/test recognition in completed_validation_command'
]
dump('analysis/swebench-experiment-v2.5-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.4.json')
cfg.update({'version': 'swebench-handoff/2.5', 'supersedes_configuration': 'configs/swebench-comparison-v2.4.json',
            'experiment_manifest': 'analysis/swebench-experiment-v2.5-manifest.json', 'experiment_manifest_sha256': digest(m),
            'live_execution_authorized': False})
dump('configs/swebench-comparison-v2.5.json', cfg)

plan = load('analysis/swebench-comparison-v2.4-plan.json')
plan.update({'version': 'swebench-plan/2.5', 'config_sha256': digest(cfg), 'experiment_manifest_sha256': digest(m),
             'freeze_status': 'PROSPECTIVE PROPOSAL; no spending authorized', 'new_spending_authorized': False,
             'intervention': plan['intervention'] + ' Specification v2.5 aligns response audit measurement with the runtime framing reader and handles absent actions safely.'})
dump('analysis/swebench-comparison-v2.5-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
if 'V25_SPEC_SHA' not in src:
    anchor_src = f"""V24_VERSION = 'swebench-handoff/2.4'
V25_SPEC_SHA = '{digest(cfg)}'
V25_PLAN_SHA = '{digest(plan)}'
V25_FINAL_SOURCE_FREEZE = 'analysis/swebench-v2.5-final-source-freeze.json'
V25_VERSION = 'swebench-handoff/2.5'"""
    src = src.replace("V24_VERSION = 'swebench-handoff/2.4'", anchor_src)
    src = src.replace("GUARDED_VERSIONS = (V23_VERSION, V24_VERSION)", "GUARDED_VERSIONS = (V23_VERSION, V24_VERSION, V25_VERSION)")
    src = src.replace("V24_SPEC_SHA: V24_PLAN_SHA}", "V24_SPEC_SHA: V24_PLAN_SHA, V25_SPEC_SHA: V25_PLAN_SHA}")
    src = src.replace("V24_SPEC_SHA) else SELECTION_PLAN_SHA", "V24_SPEC_SHA, V25_SPEC_SHA) else SELECTION_PLAN_SHA")
    src = src.replace("V24_SPEC_SHA):", "V24_SPEC_SHA, V25_SPEC_SHA):")
    src = src.replace("V24_SPEC_SHA: V24_PLAN_SHA}[digest(config)]", "V24_SPEC_SHA: V24_PLAN_SHA, V25_SPEC_SHA: V25_PLAN_SHA}[digest(config)]")
    src = src.replace("if digest(config) == V24_SPEC_SHA:\n            validate_final_source_freeze(authorization, V24_FINAL_SOURCE_FREEZE)",
                      "if digest(config) == V24_SPEC_SHA:\n            validate_final_source_freeze(authorization, V24_FINAL_SOURCE_FREEZE)\n        if digest(config) == V25_SPEC_SHA:\n            validate_final_source_freeze(authorization, V25_FINAL_SOURCE_FREEZE)")
    src = src.replace("V24_VERSION):", "V24_VERSION, V25_VERSION):")
    src = src.replace("config.get('version') == V24_VERSION else {}", "config.get('version') in (V24_VERSION, V25_VERSION) else {}")
else:
    src = re.sub(r"V25_SPEC_SHA = '[^']*'", f"V25_SPEC_SHA = '{digest(cfg)}'", src)
    src = re.sub(r"V25_PLAN_SHA = '[^']*'", f"V25_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {'version': 'swebench-final-source-freeze/1.0', 'freeze_status': 'PROSPECTIVE PROPOSAL', 'revision': 1,
          'config_sha256': digest(cfg), 'plan_sha256': digest(plan),
          'files': {f: sha(f) for f in ('scripts/benchmark_compare.py', 'src/keisho/benchmark/comparison.py',
                    'src/keisho/benchmark/experiment_freeze.py', 'src/keisho/benchmark/notes_reader.py',
                    'src/keisho/benchmark/response_measurements.py')}}
dump('analysis/swebench-v2.5-final-source-freeze.json', freeze)

auth = {'version': 'swebench-authorization/2.0', 'authorization_id': 'PROSPECTIVE-V25-TEMPLATE-NOT-APPROVED',
        'config_sha256': digest(cfg), 'plan_sha256': digest(plan), 'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00', 'attempts': 1, 'provider_inference_authorized': False,
        'note': 'PROPOSAL TEMPLATE ONLY; no inference authorized. Bagi has not approved this proposal.'}
dump('analysis/swebench-comparison-v2.5-authorization-template.json', auth)

# Binding modules are pinned in final-source-freeze, not in manifest['files']
if 'src/keisho/benchmark/comparison.py' in m['files']:
    del m['files']['src/keisho/benchmark/comparison.py']
m['files'] = dict(sorted(m['files'].items()))
dump('analysis/swebench-experiment-v2.5-manifest.json', m)

cfg['experiment_manifest_sha256'] = digest(m)
dump('configs/swebench-comparison-v2.5.json', cfg)

plan['config_sha256'] = digest(cfg)
plan['experiment_manifest_sha256'] = digest(m)
dump('analysis/swebench-comparison-v2.5-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V25_SPEC_SHA = '[^']*'", f"V25_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V25_PLAN_SHA = '[^']*'", f"V25_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {'version': 'swebench-final-source-freeze/1.0', 'freeze_status': 'PROSPECTIVE PROPOSAL', 'revision': 1,
          'config_sha256': digest(cfg), 'plan_sha256': digest(plan),
          'files': {f: sha(f) for f in ('scripts/benchmark_compare.py', 'src/keisho/benchmark/comparison.py',
                    'src/keisho/benchmark/experiment_freeze.py', 'src/keisho/benchmark/notes_reader.py',
                    'src/keisho/benchmark/response_measurements.py')}}
dump('analysis/swebench-v2.5-final-source-freeze.json', freeze)

auth = {'version': 'swebench-authorization/2.0', 'authorization_id': 'PROSPECTIVE-V25-TEMPLATE-NOT-APPROVED',
        'config_sha256': digest(cfg), 'plan_sha256': digest(plan), 'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00', 'attempts': 1, 'provider_inference_authorized': False,
        'note': 'PROPOSAL TEMPLATE ONLY; no inference authorized. Bagi has not approved this proposal.'}
dump('analysis/swebench-comparison-v2.5-authorization-template.json', auth)

print(json.dumps({'manifest': digest(m), 'config': digest(cfg), 'plan': digest(plan), 'final_source_freeze': digest(freeze),
                  'authorization_template': digest(auth), 'comparison.py_sha256': freeze['files']['src/keisho/benchmark/comparison.py'],
                  'response_measurements.py_sha256': freeze['files']['src/keisho/benchmark/response_measurements.py'],
                  'envelope': plan['maximum_noncached_costs_usd'], 'total_envelope_usd': plan['total_envelope_usd'],
                  'reservation': plan['largest_request_reservation_usd']}, indent=1))
