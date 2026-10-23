"""Regenerate the v2.3 PROPOSAL freeze files offline. Never touches v2.1/v2.2 or historical records.

All prices below are the frozen catalog rates recorded in the v2.2 run's public-catalog-preflight.json
(gpt-6-sol / OpenAI: prompt 2.0, input_cache_write 2.5, completion 10.0 USD per million tokens;
gpt-6-luna / OpenAI: prompt 0.1, input_cache_write 0.125, completion 0.5). The v2.3 envelope charges every
input token at the cache-WRITE rate (the v2.2 call was billed 1315 of 1322 prompt tokens as cache writes).
"""
import copy, hashlib, json, re, sys
from decimal import Decimal as D
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.core import digest

def load(p): return json.loads((ROOT / p).read_text())
def dump(p, d): (ROOT / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

NO_HANDOFF = ('No handoff context is provided for this run. The repository is available at /testbed; '
              'begin work on the issue above using the tools.')
SOL = (D('2.5'), D('10'))    # worst-case input (cache write) and output, USD per 1M tokens
LUNA = (D('0.125'), D('0.5'))
FEE = D('1.05')              # possible 5% BYOK fee, as in earlier plans
MAX_ATTEMPTS = 3
SUCCESSOR_TOTAL = 234000     # lowered from 248,400 so that the cache-write-priced envelope fits the USD 10.00 cap
FIRST_REQUEST_BOUND = 2380 + 64  # v2.2 first-request bound plus a conservative allowance for the non-empty user turn

m = copy.deepcopy(load('analysis/swebench-experiment-v2.2-manifest.json'))
for f in list(m['files']):
    if (ROOT / f).is_file() and not f.startswith(('.cache/', 'runs/')):
        m['files'][f] = sha(f)
m['files'] = dict(sorted(m['files'].items()))
m['freeze_status'] = 'PROPOSAL (not frozen; live execution NOT authorized)'
m['binding_module_note'] = ('Binding modules are pinned in analysis/swebench-v2.3-final-source-freeze.json, '
                            'whose digest the authorization record must bind (checked in resolve_binding).')
m['prospective_changes'] = [
    'swebench-handoff/2.3: non-empty constant user turn replaces the empty trailing user message whenever there is no handoff (predecessor and REPOSITORY_ONLY)',
    'premature-finish-guard/1.0: a predecessor finish with zero completed tool calls is an invalid attempt; no handoff is built from it',
    'pre-registered predecessor attempt rule: at most %d attempts; only a first-call premature finish admits a new attempt; zero automatic retries otherwise' % MAX_ATTEMPTS,
    'cost envelope recomputed at cache-write input rates; successor total tokens lowered to %d' % SUCCESSOR_TOTAL]
dump('analysis/swebench-experiment-v2.3-manifest.json', m)

cfg = load('configs/swebench-comparison-v2.2.json')
cfg['successor_budgets'] = dict(cfg['successor_budgets'], total_tokens=SUCCESSOR_TOTAL)
cfg.update({'version': 'swebench-handoff/2.3', 'supersedes_configuration': 'configs/swebench-comparison-v2.2.json',
            'experiment_manifest': 'analysis/swebench-experiment-v2.3-manifest.json', 'experiment_manifest_sha256': digest(m),
            'empty_handoff_user_text': NO_HANDOFF,
            'early_finish_guard': 'premature-finish-guard/1.0',
            'predecessor_attempts': {'max_attempts': MAX_ATTEMPTS, 'seed_policy': 'same branch_seed every attempt (provider determinism is not guaranteed)',
                                     'new_attempt_only_if': 'previous attempt finished on its first model call with zero completed tool calls',
                                     'valid_attempt': 'an attempt that completes at least one tool call; only the first valid attempt can reach the checkpoint',
                                     'disclosure': 'every attempt is kept and reported; invalid attempts are never used for handoffs'},
            'live_execution_authorized': False})
dump('configs/swebench-comparison-v2.3.json', cfg)

def run_cost(budget, rates):
    out = budget['model_calls'] * budget['output_tokens']
    return FEE * ((budget['total_tokens'] - out) * rates[0] + out * rates[1]) / 1000000
pred = run_cost(cfg['predecessor_budgets'], SOL)
succ = run_cost(cfg['successor_budgets'], SOL) * len(cfg['conditions'])
gen = FEE * cfg['generation_calls'] * (64000 * LUNA[0] + cfg['generation_output_tokens'] * LUNA[1]) / 1000000
invalid = FEE * (FIRST_REQUEST_BOUND * SOL[0] + cfg['predecessor_budgets']['output_tokens'] * SOL[1]) / 1000000 * (MAX_ATTEMPTS - 1)
reserve = FEE * (cfg['predecessor_budgets']['request_input_tokens'] * SOL[0] + cfg['predecessor_budgets']['output_tokens'] * SOL[1]) / 1000000
total = pred + succ + gen + invalid
q = lambda x: str(x.quantize(D('0.00000001')))
assert total + reserve <= D(cfg['cap_usd']), (total, reserve)

plan = load('analysis/swebench-comparison-v2.2-plan.json')
plan.update({'version': 'swebench-plan/2.3', 'config_sha256': digest(cfg), 'experiment_manifest_sha256': digest(m),
             'freeze_status': 'PROPOSAL; no spending authorized', 'new_spending_authorized': False,
             'first_request_upper_bound': FIRST_REQUEST_BOUND,
             'maximum_noncached_costs_usd': {'predecessor': q(pred), 'successor': q(succ), 'note_generation': q(gen),
                                             'invalid_predecessor_attempts': q(invalid)},
             'total_envelope_usd': q(total), 'largest_request_reservation_usd': q(reserve),
             'assumptions': ('Frozen catalog rates with every input token charged at the cache-write rate (sol 2.5, luna 0.125 USD/M), '
                             'no cache-read discount, possible 5%% BYOK fee. Predecessor total tokens 276,000; successor total tokens %d; '
                             'request input tokens 64,000; note generation input allowance 64,000; up to %d extra first-call-only predecessor attempts '
                             'bounded by a %d-token first request. Task sympy__sympy-20590; gpt-6-sol predecessor and successors; gpt-6-luna note generation; '
                             'reasoning effort none. No paid inference authorized.') % (SUCCESSOR_TOTAL, MAX_ATTEMPTS - 1, FIRST_REQUEST_BOUND),
             'intervention': ('Specification v2.3 replaces the empty trailing user message with a constant non-empty turn, adds a premature-finish '
                              'guard for the predecessor, a pre-registered bound of %d predecessor attempts, and a cache-write-priced envelope.') % MAX_ATTEMPTS})
dump('analysis/swebench-comparison-v2.3-plan.json', plan)

src = (ROOT / 'src/keisho/benchmark/comparison.py').read_text()
src = re.sub(r"V23_SPEC_SHA = '[^']*'", f"V23_SPEC_SHA = '{digest(cfg)}'", src)
src = re.sub(r"V23_PLAN_SHA = '[^']*'", f"V23_PLAN_SHA = '{digest(plan)}'", src)
(ROOT / 'src/keisho/benchmark/comparison.py').write_text(src)

freeze = {'version': 'swebench-final-source-freeze/1.0', 'freeze_status': 'PROPOSAL', 'revision': 1,
          'config_sha256': digest(cfg), 'plan_sha256': digest(plan),
          'files': {f: sha(f) for f in ('scripts/benchmark_compare.py', 'src/keisho/benchmark/comparison.py',
                    'src/keisho/benchmark/experiment_freeze.py', 'src/keisho/benchmark/notes_reader.py')}}
dump('analysis/swebench-v2.3-final-source-freeze.json', freeze)

auth = {'version': 'swebench-authorization/2.0', 'authorization_id': 'PENDING-V23-NEW-USER-AUTHORIZATION',
        'config_sha256': digest(cfg), 'plan_sha256': digest(plan), 'final_source_freeze_sha256': digest(freeze),
        'cap_usd': '10.00', 'attempts': 1, 'provider_inference_authorized': False,
        'note': 'TEMPLATE ONLY; no inference authorized. "attempts" counts launches; predecessor attempts are governed by the config rule.'}
dump('analysis/swebench-comparison-v2.3-authorization-template.json', auth)
print(json.dumps({'manifest': digest(m), 'config': digest(cfg), 'plan': digest(plan), 'final_source_freeze': digest(freeze),
                  'authorization_template': digest(auth), 'comparison.py_sha256': freeze['files']['src/keisho/benchmark/comparison.py'],
                  'envelope': plan['maximum_noncached_costs_usd'], 'total_envelope_usd': plan['total_envelope_usd'],
                  'reservation': plan['largest_request_reservation_usd']}, indent=1))
