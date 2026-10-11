"""One setup-only API-driven check using the existing agent and Docker tools.

Uses the existing agent scaffold, model routing and versioned local wire admission.
The comparison is intentionally not launched here: it requires a demonstrated
repair as well as a passing functional check under the user's authorization.
"""
import argparse
from decimal import Decimal
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from keisho.agents.providers.openai_chat import http_transport
from keisho.agents.providers.openrouter_chat import BASE_URL, OpenRouterChatModel
from keisho.benchmark.comparison import (response_settings, check_public_catalog, read_input,
        execution_result, SPEC_SHA, NEXT_SPEC_SHA, WIRE_SPEC_SHA, PROVIDER_SHA, IMAGE_METADATA_SHA, action_wire_options)
from keisho.benchmark.environment import RepositorySession, docker
from keisho.benchmark.protocol import completed_validation_command
from keisho.core import canonical_json, digest, require
from keisho.local_env import load_project_env
from keisho.logging.raw import RawRun, EventKind
from keisho.pilot.agent import Budgets, Recorder, run_agent
from keisho.pilot.spending import BudgetedModel, SpendLedger
from keisho.pilot.tokenizer import NativeTokenizer
from keisho.benchmark.response_measurements import capture_response, measure_run

SCOPE = ROOT / 'runs/swebench-integration/interface-diagnosis-v1'
CONFIG = ROOT / 'configs/swebench-functional-check-v1.json'
CONFIRMATION12_SHA = '1cb6cab0b171ca0adbb9d6ba4f2e75738e640f88d70690dbff40d6c682a1e76c'
CONFIRMATION12_V12_SHA = 'a2e7207a8226c173ec76eb43256f8011e80e6e3b26a8fadab1e032cfb5e327b4'
CONFIRMATION12_V13_SHA = 'a833849a3b6706b17c96ed60e2e3252b89fa57e03418c8720cce8b067e781f61'
CHECKER = '''import importlib,json
from pathlib import Path
cases = json.loads(Path('tests.json').read_text())
failures = []
for case in cases:
    actual = getattr(importlib.import_module(case['module']), case['function'])(*case['args'])
    ok = actual == case['expected']
    print(case['id'], 'PASS' if ok else 'FAIL', repr(actual))
    if not ok: failures.append(case['id'])
if failures: raise SystemExit(1)
print('PUBLIC_ACCEPTANCE passed', len(cases), 'cases')
'''
OBJECTIVE = '''Reservation replacement leaves phantom inventory holds. Fix this repository while preserving its API and documented input contracts.
Inspect relevant source contents, make the necessary source change, and run the public acceptance test: python check_public.py.
Only api.py, ledger.py, and normalize.py may change; CONTRACT.md, tests.json, and check_public.py are immutable acceptance inputs.
This is a disposable setup-only software fixture. No hidden tests or benchmark solution information is available.
'''

def fixture_files():
    initial = ROOT / 'tasks/task_001/initial'
    files = {name: (initial / name).read_text() for name in ('api.py', 'ledger.py', 'normalize.py', 'CONTRACT.md')}
    cases = read_input(ROOT / 'tasks/task_001/public.json')['cases']
    files['tests.json'] = canonical_json([{k: v for k, v in c.items() if k != 'initial_failure'} for c in cases]) + '\n'
    files['check_public.py'] = CHECKER
    return files

class AcceptanceBoundary:
    """Observe completion of the model's public test; never choose its actions."""
    def __init__(self):
        self.inspected = False
        self.edited = False
        self.test_event = None
    def __call__(self, action, result):
        if action.get('tool') == 'read_file' and action.get('path') in ('api.py', 'ledger.py', 'normalize.py') and result.get('content'):
            self.inspected = True
        if action.get('tool') == 'shell':
            import re
            command = action.get('command', '')
            if re.search(r'\b(cat|sed|grep|head)\b', command) and any(p in command for p in ('api.py', 'ledger.py', 'normalize.py')) and result.get('output'):
                self.inspected = True
        self.edited |= bool(set(result.get('changed_paths', [])) & {'api.py', 'ledger.py', 'normalize.py'})
        if self.edited and action.get('tool') == 'shell' and 'check_public.py' in action.get('command', '') and completed_validation_command(action['command']):
            self.test_event = result
            return True  # First post-edit acceptance attempt, pass or fail; no retry trajectory.
        return False

def initialize_public_fixture(session, raw, files):
    # Replace /testbed only in this uniquely owned, disposable container. No
    # host workspace, previous trajectory or benchmark data is copied in.
    setup = "import json,sys,shutil; from pathlib import Path; root=Path('/testbed'); shutil.rmtree(root); root.mkdir(); files=json.load(sys.stdin); [(root/name).write_text(text) for name,text in files.items()]"
    docker('exec', '-i', session.name, 'python3', '-c', setup, input=canonical_json(files).encode())
    init = session.command('git init -q\ngit config user.name "setup fixture"\ngit config user.email "setup@example.invalid"\ngit add -A\ngit commit -qm "public fixture base"\ngit rev-parse HEAD')
    require(init.returncode == 0, 'fixture Git initialization failed')
    base = init.stdout.decode().strip().splitlines()[-1]
    session.base_inventory = session.inventory()
    raw.write_artifact('base.json', {'base_commit': base, 'inventory': session.base_inventory})
    initial = session.command('python check_public.py')
    raw.write_artifact('initial-public-test.json', {'exit_code': initial.returncode, 'output': (initial.stdout + initial.stderr).decode()})
    require(initial.returncode == 1, 'fixture must initially fail its public test')
    return base

def assess_public_fixture(session, raw, base, execution, boundary):
    after = session.inventory()
    immutable = ('CONTRACT.md', 'tests.json', 'check_public.py')
    preserved = all(after.get(p) == session.base_inventory[p] for p in immutable)
    changed = set(after) ^ set(session.base_inventory)
    changed |= {p for p in set(after) & set(session.base_inventory) if after[p] != session.base_inventory[p]}
    allowed_changes = changed <= {'api.py', 'ledger.py', 'normalize.py'}
    check = session.command('python check_public.py') if preserved else None
    public_pass = check is not None and check.returncode == 0
    raw.write_artifact('final-public-test.json', {'exit_code': check.returncode if check else None,
        'output': (check.stdout + check.stderr).decode() if check else 'withheld: immutable fixture inputs changed'})
    raw.write_artifact('cumulative-patch.json', {'base_commit': base, 'patch': session.patch(base), 'setup_only': True})
    raw.write_artifact('calls.json', execution.calls)
    success = execution.reason == 'checkpoint' and boundary.inspected and boundary.edited and boundary.test_event['exit_code'] == 0 and public_pass and preserved and allowed_changes
    result = dict(status='passed' if success else 'failed', execution=execution_result(execution),
            inspected_contents=boundary.inspected, edited_source=boundary.edited,
            model_executed_public_test=boundary.test_event is not None,
            model_public_test_exit=boundary.test_event['exit_code'] if boundary.test_event else None,
            immutable_inputs_preserved=preserved, allowed_source_changes_only=allowed_changes,
            independent_public_test_passed=public_pass)
    return result


class PublicAcceptanceBoundary12(AcceptanceBoundary):
    """Versioned measurement: actual inspection and direct post-edit acceptance."""
    def __call__(self, action, result):
        import shlex
        from keisho.benchmark.inspection import information_action
        source = ('api.py', 'ledger.py', 'normalize.py')
        if action.get('tool') == 'read_file' and action.get('path') in source and result.get('content'):
            self.inspected = True
        if action.get('tool') == 'shell':
            qualifies, _ = information_action(action, dict.fromkeys(source))
            if qualifies is True and result.get('exit_code') == 0 and result.get('output'):
                self.inspected = True
        preceding_edit = self.edited
        self.edited |= bool(set(result.get('changed_paths', [])) & set(source))
        try: tokens = shlex.split(action.get('command', ''))
        except ValueError: tokens = []
        public_command = tokens in ([p, 'check_public.py'] for p in ('python', 'python3')) or tokens in (
            [p, '-B', 'check_public.py'] for p in ('python', 'python3'))
        if preceding_edit and action.get('tool') == 'shell' and public_command and type(result.get('exit_code')) is int:
            self.test_event = result
            return True
        return False


def execute_confirmation12(config_path, authorization_path, run_dir, *, approve_live=False, dry_run=False):
    """Explicit prospective binding; old eight-call entry point stays unchanged."""
    config = read_input(config_path)
    config_sha = digest(config)
    require(config_sha in (CONFIRMATION12_SHA, CONFIRMATION12_V12_SHA, CONFIRMATION12_V13_SHA), 'prepared 12-call configuration changed')
    version13 = config_sha == CONFIRMATION12_V13_SHA
    version12 = config_sha in (CONFIRMATION12_V12_SHA, CONFIRMATION12_V13_SHA)
    require(config['live_execution_authorized'] is False, 'prospective configuration must remain disabled')
    run_dir = Path(run_dir).absolute()
    require(run_dir == ROOT / config['run_dir'] and not any(p.is_symlink() for p in (run_dir, *run_dir.parents)), 'unsafe or unbound output directory')
    require(not run_dir.exists(), 'confirmation attempt already claimed; no retry')
    frozen = read_input(ROOT / 'configs' / (config['source_comparison_config'] if version12 else 'swebench-comparison-v1.1.json'))
    require(digest(frozen) == (WIRE_SPEC_SHA if version13 else NEXT_SPEC_SHA if version12 else SPEC_SHA) == config['source_comparison_sha256'], 'frozen benchmark specification changed')
    system, policy, _ = response_settings(frozen)
    require(digest(system) == config['system_sha256'] and policy == config['response_policy'], 'prompt/policy pin changed')
    if version12:
        require(all(config[name] == frozen[name] for name in ('agent_prompt_version', 'agent_prompt_sha256',
            'agent_output_format', 'agent_output_format_sha256', 'action_contract_version', 'action_contract_sha256',
            'listing_policy', 'execution_contract_version')), 'version-1.2 execution contract changed')
    if version13:
        require(all(config[name] == frozen[name] for name in ('action_wire_version',
            'internal_action_contract_version', 'internal_action_contract_sha256')), 'version-1.3 action wire contract changed')
    require(config['output_mode'] == 'json_object' and config['model_id'] == frozen['predecessor_model'], 'selected model/mode changed')
    require(digest(fixture_files()) == config['fixture_sha256'] and digest(OBJECTIVE) == config['objective_sha256'], 'fixture/objective changed')
    provider = read_input(ROOT / 'configs' / config['provider_config'])
    require(digest(provider) == PROVIDER_SHA == config['provider_config_sha256'], 'provider pin changed')
    require(provider['models']['predecessor']['model_id'] == config['model_id'], 'model mapping changed')
    budgets = Budgets(**config['budgets'])
    require(budgets.model_calls == budgets.tool_calls == 12, '12-call limit changed')
    maximum = Decimal('1.05') * 12 * (32000 * Decimal('.4') + 2048 * Decimal('1.6')) / 1000000
    require(maximum == Decimal(config['maximum_reservations_usd']), 'reservation assumptions changed')
    auth = read_input(authorization_path) if authorization_path else None
    if auth is not None:
        require(auth.get('version') == config['version'] and auth.get('config_sha256') == digest(config)
            and auth.get('run_dir') == config['run_dir'] and auth.get('attempts') == 1
            and (auth.get('user_authorized') is True or
                (version13 and dry_run and auth.get('user_authorized') is False))
            and auth.get('swebench_authorized') is False,
            'authorization does not bind this one functional attempt')
        if version13:
            require(auth.get('provider_inference_authorized') is True or
                (dry_run and auth.get('provider_inference_authorized') is False), 'new provider inference authorization required')
        cap = Decimal(auth['cap_usd'])
        require(cap.is_finite() and maximum <= cap <= Decimal('2'), 'new diagnostic cap insufficient or outside registered ceiling')
    else:
        cap = None
    if dry_run:
        contract = {name: config[name] for name in ('source_comparison_sha256', 'system_sha256',
            'agent_prompt_version', 'agent_output_format', 'action_contract_version', 'action_contract_sha256',
            'listing_policy', 'execution_contract_version')} if version12 else {}
        if version13:
            contract.update({name: config[name] for name in ('action_wire_version',
                'internal_action_contract_version', 'internal_action_contract_sha256')})
        print(canonical_json({'configuration': str(Path(config_path).resolve()), 'config_sha256': digest(config),
            'run_dir': str(run_dir), 'authorization': str(authorization_path) if authorization_path else None,
            'live_admission': auth is not None and auth.get('user_authorized') is True and approve_live
                and (not version13 or auth.get('provider_inference_authorized') is True), 'cap_usd': str(cap) if cap else None,
            'maximum_reservations_usd': str(maximum), 'model': config['model_id'], 'output_mode': config['output_mode'],
            'budgets': config['budgets'], 'live_guard_created': False, 'provider_requests': 0,
            'remaining_check': 'live also verifies credential presence, public catalog and prepared image', **contract}))
        return 0
    require(approve_live is True and auth is not None, 'new spending authorization and explicit approval required; old scopes closed')
    require(auth.get('user_authorized') is True, 'new user spending authorization required')
    ca = (ROOT / 'configs' / provider['tls']['ca_file']).resolve()
    require(hashlib.sha256(ca.read_bytes()).hexdigest() == provider['tls']['ca_sha256'], 'verified CA changed')
    require(load_project_env(ROOT)['present']['OPENROUTER_API_KEY'], 'configured credential missing')
    image = read_input(ROOT / '.cache/swebench-evaluator/prepared-task-image.json')
    require(digest(image) == IMAGE_METADATA_SHA, 'prepared image identity changed')
    require(json.loads(docker('image', 'inspect', image['image_id']).stdout)[0]['Id'] == image['image_id'], 'prepared image unavailable')
    catalog = check_public_catalog(ca)
    raw = RawRun(run_dir.parent, run_dir.name)  # Atomic, one attempt; no reset or relocation.
    rec = Recorder(raw)
    count = 0
    def emit(row):
        nonlocal count
        count += 1
        rec.emit(f'spend-{count}', EventKind.ANNOTATION, 'spending-control', row)
    # Reuse the registered diagnostic ledger; the new authorization's cap is the
    # actual run cap. Nothing from the completed diagnostic ledger is reused.
    ledger = SpendLedger(str(cap), emit, provider='openrouter', authorized_ceiling_usd='2', authorization_scope='agent-decision-diagnostic')
    for name, value in (('authorization.json', auth), ('config.json', config), ('public-catalog.json', catalog)):
        raw.write_artifact(name, value)
    result = {'status': 'interrupted', 'setup_only': True, 'comparison_started': False, 'automatic_retries': False}
    session = None
    try:
        options = {'listing_policy': config['listing_policy']} if version12 else {}
        session = RepositorySession(image['image_id'], audit=raw, timeout=config['tool_timeout_seconds'],
            output_bytes=config['tool_output_bytes'], **options)
        base = initialize_public_fixture(session, raw, fixture_files())
        def transport(body, key):
            number = len(ledger.records)
            raw.write_artifact(f'wire-request-{number:03d}.json', body)
            return http_transport(body, key, base_url=BASE_URL, provider='OpenRouter', ca_file=ca,
                response_observer=lambda payload, status, redacted: capture_response(raw, number, payload, status, redacted))
        model = OpenRouterChatModel(config['model_id'], authorized=True, tokenizer=NativeTokenizer(),
            response_model_ids=provider['models']['predecessor']['accepted_response_model_ids'], transport=transport)
        boundary = PublicAcceptanceBoundary12()
        execution = run_agent(BudgetedModel(model, ledger, 'functional_confirmation12', config['model_id']), session, rec,
            OBJECTIVE, system, '', config['seed'], budgets, role='predecessor', checkpoint_predicate=boundary,
            time_limit_seconds=config['time_limit_seconds'], response_policy=policy, **action_wire_options(config))
        result.update(assess_public_fixture(session, raw, base, execution, boundary))
        result.update(model_executed_post_edit_public_test=boundary.test_event is not None,
            post_edit_acceptance_marker=bool(boundary.test_event and 'PUBLIC_ACCEPTANCE passed 4 cases' in boundary.test_event.get('output', '')))
        if result['status'] == 'passed' and not result['post_edit_acceptance_marker']:
            result['status'] = 'failed'
    except Exception as exc:
        result.update(status='error', exception=type(exc).__name__, reason=str(exc), automatic_retry=False)
    finally:
        if session is not None:
            try: session.close()
            except Exception as exc: result.update(status='error', cleanup_exception=type(exc).__name__, cleanup_reason=str(exc))
        ledger.stop(ledger.reason or 'one 12-call functional confirmation ended; no retries or SWE-bench authorized')
        validator = RepositorySession.__new__(RepositorySession)
        validator.output_bytes = config['tool_output_bytes']
        if version12:
            validator.listing_policy = config['listing_policy']
        measurement_options = {'action_contract_version': config['action_contract_version']} if version12 else {}
        measurement_options.update(action_wire_options(config))
        raw.write_artifact('response-measurements.json', measure_run(raw, validator.validate_action, **measurement_options))
        raw.write_artifact('spending.json', ledger.report())
        raw.write_artifact('result.json', result)
        raw.freeze()
    print(canonical_json(result))
    print('Artifacts:', raw.path)
    return 0 if result['status'] == 'passed' else 1


def execute(approve_live=False):
    require(approve_live is True, 'explicit functional-check approval required')
    require(not (SCOPE / 'functional').exists(), 'functional attempt already claimed; no retry')
    config = read_input(CONFIG)
    authorization = read_input(SCOPE / 'authorization.json')
    require(digest(config) == authorization['functional_config_sha256'], 'functional configuration changed')
    require(authorization['shared_cap_usd'] == '10.00' and authorization['functional_cap_usd'] == config['cap_usd'] == '0.50', 'shared/stage authorization changed')
    frozen = read_input(ROOT / 'configs/swebench-comparison-v1.1.json')
    require(digest(frozen) == SPEC_SHA and digest(frozen) == config['source_comparison_sha256'], 'historical scientific specification changed')
    system, policy, output_format = response_settings(frozen)
    require(digest(system) == config['system_sha256'] and digest(output_format) == config['response_format_sha256'], 'functional interface differs from benchmark')
    files = fixture_files()
    require(digest(files) == config['fixture_sha256'] and digest(OBJECTIVE) == config['objective_sha256'], 'public fixture/objective changed')
    budgets = Budgets(**config['budgets'])
    require(budgets.model_calls == 8 and budgets.tool_calls == 8, 'functional attempt bounds changed')
    worst = Decimal('1.05') * 8 * (32000 * Decimal('.4') + 2048 * Decimal('1.6')) / 1000000
    require(worst <= Decimal(config['cap_usd']), 'functional reservations exceed stage ceiling')
    provider = read_input(ROOT / 'configs/calibration-task001-openrouter-v1.2.0.yaml')
    require(digest(provider) == PROVIDER_SHA and provider['models']['predecessor']['model_id'] == config['model_id'], 'provider/model mapping changed')
    ca = (ROOT / 'configs' / provider['tls']['ca_file']).resolve()
    require(hashlib.sha256(ca.read_bytes()).hexdigest() == provider['tls']['ca_sha256'], 'verified CA changed')
    require(load_project_env(ROOT)['present']['OPENROUTER_API_KEY'], 'configured provider credential missing')
    image_metadata = read_input(ROOT / '.cache/swebench-evaluator/prepared-task-image.json')
    require(digest(image_metadata) == IMAGE_METADATA_SHA, 'prepared image metadata changed')
    image = image_metadata['image_id']
    require(json.loads(docker('image', 'inspect', image).stdout)[0]['Id'] == image, 'prepared image unavailable')
    catalog = check_public_catalog(ca)  # Public metadata, never credential validation or model inference.
    native = NativeTokenizer()
    raw = RawRun(SCOPE, 'functional')  # Exclusive guard before model construction/request; never reset.
    recorder = Recorder(raw)
    counter = 0
    def emit(row):
        nonlocal counter
        counter += 1
        recorder.emit(f'spend-{counter}', EventKind.ANNOTATION, 'spending-control', row)
    ledger = SpendLedger(config['cap_usd'], emit, provider='openrouter', authorized_ceiling_usd=authorization['shared_cap_usd'], authorization_scope='swebench-one-comparison')
    raw.write_artifact('authorization.json', authorization)
    raw.write_artifact('config.json', config)
    raw.write_artifact('public-catalog.json', catalog)
    raw.write_artifact('fixture.json', {'setup_only': True, 'original_files': files, 'objective': OBJECTIVE, 'image_id': image})
    result = {'status': 'interrupted', 'setup_only': True, 'interface_repair_demonstrated': False,
              'comparison_started': False, 'comparison_reason': 'a demonstrated repair is required; none established offline'}
    session = None
    try:
        session = RepositorySession(image, audit=raw)
        base = initialize_public_fixture(session, raw, files)
        def transport(body, key):
            raw.write_artifact(f'wire-request-{len(ledger.records):03d}.json', body)  # No headers/key.
            return http_transport(body, key, base_url=BASE_URL, provider='OpenRouter', ca_file=ca)
        model = OpenRouterChatModel(config['model_id'], authorized=True, tokenizer=native,
                    response_model_ids=provider['models']['predecessor']['accepted_response_model_ids'],
                    agent_response_format=output_format, transport=transport)
        boundary = AcceptanceBoundary()
        execution = run_agent(BudgetedModel(model, ledger, 'setup_functional', config['model_id']), session,
                recorder, OBJECTIVE, system, '', config['seed'], budgets, role='predecessor',
                checkpoint_predicate=boundary, time_limit_seconds=600, response_policy=policy)
        result.update(assess_public_fixture(session, raw, base, execution, boundary))
    except Exception as exc:
        result.update(status='error', exception=type(exc).__name__, reason=str(exc), automatic_retry=False)
    finally:
        if session is not None:
            try: session.close()
            except Exception as exc:
                result.update(status='error', cleanup_exception=type(exc).__name__, cleanup_reason=str(exc))
        ledger.stop('one setup-only attempt completed; no retries; comparison requires demonstrated repair')
        raw.write_artifact('spending.json', ledger.report())
        raw.write_artifact('result.json', result)
        raw.freeze()
    print(canonical_json(result))
    print('Artifacts:', raw.path)
    return 0 if result['status'] == 'passed' else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve-live', action='store_true')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.config is not None or args.authorization is not None or args.run_dir is not None or args.dry_run:
        require(args.config is not None and args.run_dir is not None, 'explicit config and run-dir required together')
        return execute_confirmation12(args.config, args.authorization, args.run_dir, approve_live=args.approve_live, dry_run=args.dry_run)
    return execute(args.approve_live)

if __name__ == '__main__': raise SystemExit(main())
