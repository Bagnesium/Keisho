"""Generate prospective v2.7 PROPOSAL freeze files offline (read only).

v2.7:
(1) Task pydata__xarray-6721 on SWE-bench Verified (multi-file dataset bug in xarray/core/common.py);
(2) Predecessor model openai/gpt-6-sol; Successor model anthropic/claude-opus-5.5; Note generation openai/gpt-6-luna;
(3) Early stopping rule: halt after genuine task-bug reproduction (exit code != 0, test failure, not env/import error);
(4) Checkpoint verification guard: official grading in Docker must confirm checkpoint is unresolved before successor takeover;
(5) $20.00 spend cap with conservative cache-write reservations ($5.00/M for Opus, $2.50/M for Sol).
"""
import copy, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

m = copy.deepcopy(load('analysis/swebench-experiment-v2.6-manifest.json'))
files = dict(m['files'])

# Swap out sympy-specific files for xarray-6721 files
files.pop('.cache/swebench-evaluator/sympy__sympy-20590-prepared-task-image.json', None)
files.pop('.cache/swebench-evaluator/sympy__sympy-20590-selected-task-evaluator.jsonl', None)
files.pop('runs/swebench-integration/preselection/sympy__sympy-20590-plan.json', None)
files.pop('runs/swebench-integration/preselection/sympy__sympy-20590-task.json', None)
files.pop('configs/calibration-task001-openrouter-v2.0.yaml', None)

files['.cache/swebench-evaluator/prepared-task-image.json'] = sha('.cache/swebench-evaluator/prepared-task-image.json')
files['.cache/swebench-evaluator/selected-task-evaluator.jsonl'] = sha('.cache/swebench-evaluator/selected-task-evaluator.jsonl')
files['runs/swebench-integration/preselection/plan.json'] = sha('runs/swebench-integration/preselection/plan.json')
files['runs/swebench-integration/preselection/task.json'] = sha('runs/swebench-integration/preselection/task.json')
files['configs/calibration-task001-openrouter-v2.7.yaml'] = sha('configs/calibration-task001-openrouter-v2.7.yaml')

for f in list(files):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        files[f] = sha(f)

if 'src/keisho/benchmark/comparison.py' in files:
    del files['src/keisho/benchmark/comparison.py']

m['files'] = dict(sorted(files.items()))
m['freeze_status'] = 'PROSPECTIVE PROPOSAL (authorized for exactly one approved live attempt)'
m['binding_module_note'] = ('Binding modules are pinned in analysis/swebench-v2.7-final-source-freeze.json, '
                            'whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = [
    'task: switch to pydata__xarray-6721 on SWE-bench Verified (multi-file issue in xarray/core/common.py)',
    'models: gpt-6-sol predecessor, claude-opus-5.5 successor, gpt-6-luna note generation',
    'checkpoint: intercept first attempted source-code edit and pause before execution for successor takeover',
    'checkpoint-guard: official SWE-bench evaluation confirms checkpoint is unresolved before successor takeover',
    'budget: $20.00 authorized cap with conservative cache-write reservations'
]
dump('analysis/swebench-experiment-v2.7-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.6.json')
cfg.update({
    'version': 'swebench-handoff/2.7',
    'selected_instance': 'pydata__xarray-6721',
    'checkpoint': 'intercept first attempted source-code edit and pause before execution for successor takeover',
    'predecessor_model': 'openai/gpt-6-sol-20260922',
    'successor_model': 'anthropic/claude-opus-5.5-20260921',
    'generation_model': 'openai/gpt-6-luna-20260922',
    'provider_config': 'calibration-task001-openrouter-v2.7.yaml',
    'cap_usd': '20.00',
    'supersedes_configuration': 'configs/swebench-comparison-v2.6.json',
    'experiment_manifest': 'analysis/swebench-experiment-v2.7-manifest.json',
    'experiment_manifest_sha256': digest(m),
    'live_execution_authorized': False,
    'reservation_input_rates_per_million': {
        'openai/gpt-6-sol-20260922': '2.50',
        'openai/gpt-6-sol': '2.50',
        'openai/gpt-6-luna-20260922': '0.125',
        'openai/gpt-6-luna': '0.125',
        'anthropic/claude-opus-5.5-20260921': '5.00',
        'anthropic/claude-opus-5.5': '5.00'
    }
})
dump('configs/swebench-comparison-v2.7.json', cfg)

task = load('runs/swebench-integration/preselection/task.json')
plan = {
    'offline_only': True,
    'provider_requests': 0,
    'credential_validation_requests': 0,
    'new_spending_authorized': False,
    'config_sha256': digest(cfg),
    'task_sha256': digest(task),
    'catalog_sha256': 'c2401039b8759242b9d59dcd388eedc906ce1856d136197aa6bcc6f202fa574b',
    'response_policy': 'auxiliary-claims/2.0',
    'response_format_sha256': '376bde7986cc2f8fd182f04e745c607933760bea7c306ea6e8e992b7f70be25a',
    'agent_prompt_sha256': 'bcede4362a8ba0c4e8cfb2104f87ad418eaee92923f7d1f7fe522af01005c5fe',
    'schema_native_tokens': 0,
    'first_request_upper_bound': 2444,
    'cap_usd_proposed': '20.00',
    'maximum_noncached_costs_usd': {
        'predecessor': '1.49864400',
        'successor': '17.50000000',
        'note_generation': '0.01848000',
        'invalid_predecessor_attempts': '0.05583900'
    },
    'total_envelope_usd': '19.07296300',
    'largest_request_reservation_usd': '0.37900800',
    'assumptions': 'Frozen catalog rates with every input token charged at the cache-write rate (sol 2.5, luna 0.125, opus 5.0 USD/M), no cache-read discount, possible 5% BYOK fee. Predecessor total tokens 276,000; successor total tokens 234000; request input tokens 64,000; note generation input allowance 64,000; up to 2 extra first-call-only predecessor attempts bounded by a 2444-token first request. Task pydata__xarray-6721; gpt-6-sol predecessor; claude-opus-5.5 successors; gpt-6-luna note generation. No paid inference authorized.',
    'checkpoint_uses_hidden_grades': False,
    'agent_calls_so_far': 0
}
dump('analysis/swebench-comparison-v2.7-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V27_SPEC_SHA = '[^']*'", f"V27_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V27_PLAN_SHA = '[^']*'", f"V27_PLAN_SHA = '{digest(plan)}'", src)
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
            'src/keisho/benchmark/protocol.py',
            'src/keisho/benchmark/response_measurements.py'
        )
    }
}
dump('analysis/swebench-v2.7-final-source-freeze.json', freeze)

auth = {
    'version': 'swebench-authorization/2.0',
    'authorization_id': 'PROSPECTIVE-V27-TEMPLATE-NOT-APPROVED',
    'config_sha256': digest(cfg),
    'plan_sha256': digest(plan),
    'final_source_freeze_sha256': digest(freeze),
    'cap_usd': '20.00',
    'attempts': 1,
    'provider_inference_authorized': False,
    'note': 'PROPOSAL TEMPLATE ONLY; live execution requires fresh single-use authorization.'
}
dump('analysis/swebench-comparison-v2.7-authorization-template.json', auth)

print('V27_SPEC_SHA:', digest(cfg))
print('V27_PLAN_SHA:', digest(plan))
print('V27_FREEZE_SHA:', digest(freeze))
print('V27_MANIFEST_SHA:', digest(m))
