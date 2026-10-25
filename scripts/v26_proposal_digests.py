"""Generate prospective v2.6 PROPOSAL freeze files offline (read only).

v2.6 = v2.5 + startup-dispatch repair:
(1) Define V20_HANDOFF_VERSIONS as single source of truth for v2.0-v2.6 handoffs;
(2) Expose select_model_class and build_model for production construction parity
    across predecessor, note generators, and all 5 successor conditions;
(3) Update runtime_preflight, check_public_catalog, make_handoffs, and execute
    to uniformly recognize v2.6;
(4) Test harness enforces strict fail-closed network guards.
Budgets, prices, models, prompt, task and envelope are unchanged from v2.5.
Never touches v2.1/v2.2/v2.3/v2.4/v2.5 or historical records.
"""
import copy, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

m = copy.deepcopy(load('analysis/swebench-experiment-v2.5-manifest.json'))
for f in list(m['files']):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        m['files'][f] = sha(f)
if 'src/keisho/benchmark/comparison.py' in m['files']:
    del m['files']['src/keisho/benchmark/comparison.py']
m['files'] = dict(sorted(m['files'].items()))
m['freeze_status'] = 'PROSPECTIVE PROPOSAL (not approved or launchable; live execution not authorized)'
m['binding_module_note'] = ('Binding modules are pinned in analysis/swebench-v2.6-final-source-freeze.json, '
                            'whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = [
    'model-dispatch: define V20_HANDOFF_VERSIONS as single source of truth for v2.0-v2.6, unifying selection for V20OpenRouterChatModel and provider-catalog-v2.0.json across comparison.py',
    'model-factory: expose select_model_class(config) and build_model(...) to eliminate dispatch divergence between production execute() and offline test harnesses',
    'catalog-preflight: check_public_catalog uses V20_HANDOFF_VERSIONS to evaluate v20 pricing/endpoints for v2.5 and v2.6',
    'fail-closed-offline: test harness enforces strict fail-closed transport preventing external endpoint reach'
]
dump('analysis/swebench-experiment-v2.6-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.5.json')
cfg.update({
    'version': 'swebench-handoff/2.6',
    'supersedes_configuration': 'configs/swebench-comparison-v2.5.json',
    'experiment_manifest': 'analysis/swebench-experiment-v2.6-manifest.json',
    'experiment_manifest_sha256': digest(m),
    'live_execution_authorized': False
})
dump('configs/swebench-comparison-v2.6.json', cfg)

plan = load('analysis/swebench-comparison-v2.5-plan.json')
plan.update({
    'version': 'swebench-plan/2.6',
    'config_sha256': digest(cfg),
    'experiment_manifest_sha256': digest(m),
    'freeze_status': 'PROSPECTIVE PROPOSAL; no spending authorized',
    'new_spending_authorized': False,
    'intervention': plan['intervention'] + ' Specification v2.6 unifies OpenRouter model dispatch under V20_HANDOFF_VERSIONS, exposes select_model_class and build_model for production construction parity across predecessor, note generators and successors, and enforces fail-closed offline test transport.'
})
dump('analysis/swebench-comparison-v2.6-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V26_SPEC_SHA = '[^']*'", f"V26_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V26_PLAN_SHA = '[^']*'", f"V26_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {
    'version': 'swebench-final-source-freeze/1.0',
    'freeze_status': 'PROSPECTIVE PROPOSAL',
    'revision': 1,
    'config_sha256': digest(cfg),
    'plan_sha256': digest(plan),
    'files': {
        f: sha(f) for f in (
            'scripts/benchmark_compare.py',
            'src/keisho/benchmark/comparison.py',
            'src/keisho/benchmark/experiment_freeze.py',
            'src/keisho/benchmark/notes_reader.py',
            'src/keisho/benchmark/response_measurements.py'
        )
    }
}
dump('analysis/swebench-v2.6-final-source-freeze.json', freeze)

auth = {
    'version': 'swebench-authorization/2.0',
    'authorization_id': 'PROSPECTIVE-V26-TEMPLATE-NOT-APPROVED',
    'config_sha256': digest(cfg),
    'plan_sha256': digest(plan),
    'final_source_freeze_sha256': digest(freeze),
    'cap_usd': '10.00',
    'attempts': 1,
    'provider_inference_authorized': False,
    'note': 'PROPOSAL TEMPLATE ONLY; no inference authorized. Bagi has not approved this proposal.'
}
dump('analysis/swebench-comparison-v2.6-authorization-template.json', auth)

# Pass 2: ensure any manifest updates are settled
if 'src/keisho/benchmark/comparison.py' in m['files']:
    del m['files']['src/keisho/benchmark/comparison.py']
m['files'] = dict(sorted(m['files'].items()))
dump('analysis/swebench-experiment-v2.6-manifest.json', m)

cfg['experiment_manifest_sha256'] = digest(m)
dump('configs/swebench-comparison-v2.6.json', cfg)

plan['config_sha256'] = digest(cfg)
plan['experiment_manifest_sha256'] = digest(m)
dump('analysis/swebench-comparison-v2.6-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V26_SPEC_SHA = '[^']*'", f"V26_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V26_PLAN_SHA = '[^']*'", f"V26_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {
    'version': 'swebench-final-source-freeze/1.0',
    'freeze_status': 'PROSPECTIVE PROPOSAL',
    'revision': 1,
    'config_sha256': digest(cfg),
    'plan_sha256': digest(plan),
    'files': {
        f: sha(f) for f in (
            'scripts/benchmark_compare.py',
            'src/keisho/benchmark/comparison.py',
            'src/keisho/benchmark/experiment_freeze.py',
            'src/keisho/benchmark/notes_reader.py',
            'src/keisho/benchmark/response_measurements.py'
        )
    }
}
dump('analysis/swebench-v2.6-final-source-freeze.json', freeze)

auth = {
    'version': 'swebench-authorization/2.0',
    'authorization_id': 'PROSPECTIVE-V26-TEMPLATE-NOT-APPROVED',
    'config_sha256': digest(cfg),
    'plan_sha256': digest(plan),
    'final_source_freeze_sha256': digest(freeze),
    'cap_usd': '10.00',
    'attempts': 1,
    'provider_inference_authorized': False,
    'note': 'PROPOSAL TEMPLATE ONLY; no inference authorized. Bagi has not approved this proposal.'
}
dump('analysis/swebench-comparison-v2.6-authorization-template.json', auth)

print(json.dumps({
    'manifest': digest(m),
    'config': digest(cfg),
    'plan': digest(plan),
    'final_source_freeze': digest(freeze),
    'authorization_template': digest(auth),
    'comparison.py_sha256': freeze['files']['src/keisho/benchmark/comparison.py'],
    'envelope': plan['maximum_noncached_costs_usd'],
    'total_envelope_usd': plan['total_envelope_usd'],
    'reservation': plan['largest_request_reservation_usd']
}, indent=2))
