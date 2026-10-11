"""Freeze prospective repair settings/cost assumptions offline, without credentials."""
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.agents.base import Message, ModelRequest
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_PRICES, validate_catalog
from keisho.benchmark.comparison import response_settings
from keisho.core import digest, require
from keisho.pilot.agent import request_upper_bound
from keisho.pilot.tokenizer import NativeTokenizer


def main():
    config = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
    old = json.loads((ROOT / 'configs/swebench-comparison-v1.json').read_text())
    for key in set(old) - {'version'}: require(config[key] == old[key], 'frozen experiment changed: ' + key)
    require(config['live_execution_authorized'] is False, 'repair is offline-only')
    preselection = ROOT / 'runs/swebench-integration/preselection'
    task = json.loads((preselection / 'task.json').read_text())
    require(task['instance_id'] == config['selected_instance'], 'task changed')
    catalog = json.loads((preselection / 'provider-catalog.json').read_text())
    validate_catalog(catalog)  # Saved public catalog only, not a remote request.
    system, policy, output_format = response_settings(config)
    tokenizer = NativeTokenizer()
    model = OpenRouterChatModel(config['predecessor_model'], tokenizer=tokenizer, agent_response_format=output_format)
    request = ModelRequest((Message('system', system), Message('user', task['problem_statement']), Message('user', '')),
                           config['branch_seed'], config['predecessor_budgets']['output_tokens'], 0)
    upper = request_upper_bound(model, request)
    require(upper <= config['predecessor_budgets']['request_input_tokens'], 'request exceeds input cap')
    parts = {}
    for role, count in [('predecessor', 1), ('successor', 5)]:
        b = config[role + '_budgets']; output = min(b['total_tokens'], b['model_calls'] * b['output_tokens'])
        rates = MODEL_PRICES[config[role + '_model']]
        parts[role] = Decimal('1.05') * ((b['total_tokens'] - output) * rates[0] + output * rates[2]) / 1000000 * count
    rates = MODEL_PRICES[config['generation_model']]
    parts['note_generation'] = Decimal('1.05') * config['generation_calls'] * (32000 * rates[0] + config['generation_output_tokens'] * rates[2]) / 1000000
    envelope = sum(parts.values())
    reserve = Decimal('1.05') * (32000 * Decimal('2') + 2048 * Decimal('8')) / 1000000
    require(envelope + reserve <= Decimal(config['cap_usd']), 'proposed block cannot fit')
    support = {}
    for alias in ('openai/gpt-4.1-mini', 'openai/gpt-4.1'):
        e = next(e for e in catalog['endpoints'][alias]['data']['endpoints'] if e['tag'] == 'openai')
        require('structured_outputs' in e['supported_parameters'], 'frozen endpoint lacks schema support')
        support[alias] = {'endpoint': e['name'], 'supported_parameters': e['supported_parameters']}
    report = {'offline_only': True, 'provider_requests': 0, 'credential_validation_requests': 0,
              'new_spending_authorized': False, 'config_sha256': digest(config), 'task_sha256': digest(task),
              'catalog_sha256': digest(catalog), 'response_policy': policy,
              'response_format_sha256': digest(output_format), 'agent_prompt_sha256': digest(system),
              'schema_native_tokens': model.request_extra_tokens(), 'first_request_upper_bound': upper,
              'cap_usd_proposed': config['cap_usd'], 'maximum_noncached_costs_usd': {k: str(v) for k,v in parts.items()},
              'total_envelope_usd': str(envelope), 'largest_request_reservation_usd': str(reserve),
              'assumptions': 'Frozen catalog rates; no cache discounts; possible 5% BYOK fee; schema tokens counted inside unchanged token budgets; two note calls; no retries; unknown usage stops calls. No live endpoint verification.',
              'endpoint_schema_support_in_saved_catalog': support}
    output = ROOT / 'runs/swebench-integration/response-policy-repair/prospective-plan-check.json'
    with output.open('x') as f: json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
