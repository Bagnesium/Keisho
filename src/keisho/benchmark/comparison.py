"""One guarded task/checkpoint and five independent, equally budgeted branches."""
from decimal import Decimal
from dataclasses import dataclass
from functools import partial
import hashlib
import json
from pathlib import Path
import random
import re

from keisho.agents.base import Message, ModelRequest
from keisho.agents.providers.openai_chat import http_transport
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, BASE_URL, validate_catalog
from keisho.core import canonical_json, digest, require
from keisho.handoff.compact import compile_handoff
from keisho.handoff.session import load_session
from keisho.local_env import load_project_env
from keisho.logging.raw import RawRun, EventKind
from keisho.metrics.definitions import CallPurpose
from keisho.pilot.agent import Budgets, Recorder, run_agent, logged_generate, request_upper_bound
from keisho.pilot.response_policy import (STRICT, AUXILIARY, agent_response_format,
    ANNOTATION_GUIDANCE, ANNOTATION_GUIDANCE_VERSION)
from keisho.pilot.spending import SpendLedger, BudgetedModel
from keisho.pilot.tokenizer import NativeTokenizer
from .environment import RepositorySession, docker
from .evaluator import evaluate, write_prediction, report_status
from .protocol import ValidationCheckpoint, deterministic_fields, generation_messages, render_structured, PROMPTS

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / 'configs/swebench-comparison-v1.json'
PRIVATE = ROOT / '.cache/swebench-evaluator'
PRESELECT = ROOT / 'runs/swebench-integration/preselection'
RUNROOT = ROOT / 'runs/swebench-integration/comparison'
# Immutable anchors from the completed repair and blocked preflight, not hashes
# regenerated from candidate launch inputs.
SPEC_SHA = 'f6c5898f2400e7f6d24f70643da2333ea86fd3ba1b5fd30f4ec64ea0c2b3895e'
PLAN_SHA = 'acdb2ec7a25568290b2d0f4ace90b5c43190088825f9ea543402a71d18480ba2'
SELECTION_PLAN_SHA = '20d7a61cc04fba73afc055febbdafeec2d3706090b4e8644b0fd90628830d1c0'
AUTH_SHA = '92736e956e4a097172a4addd7f99fb54e862ad0544325efd9298c184bd0d6276'
PROVIDER_SHA = 'b78d68a9775e40d96bec5098e7a52c6080fa06968474e364fda228a90b5ea506'
IMAGE_METADATA_SHA = '7b84f30a9701357e7317a796a52bff4a84ee769cd3eeb6ddaa5a992a53e5e5ed'
NEXT_SPEC_SHA = 'f4c7733335e0991aebdc59ac393b8a347207b452accc1119831273f77691d425'
NEXT_PLAN_SHA = '6bd86821a4d40df417c49a03f5564546e212d7f401bd74d8d0ee9ea5105902ba'
WIRE_SPEC_SHA = '471feb73c690c9d202ef7a42dc25bd0d00175dd752256973adf3e3afdc043a5a'
WIRE_PLAN_SHA = '48ffc5d96806d5e4d3bbfb75ff41ec01ea3ab9b1fd3ec3f847b4101e9a873d42'
READINESS_SPEC_SHA = 'e6a5ad8c56043924890b393363cee457ae88b6e7dbf14d6a1fa97f2ac4a14b2f'
READINESS_PLAN_SHA = '60cb7044d642bb37234a5b01d8e096a74474de023bd450d585553ea46c49e2ff'
V15_SPEC_SHA = 'cb389a1a7a7fed8bc45bf82e931976ab852cb4df607c4184f768de1bd1079d0a'
V15_PLAN_SHA = 'ba04d2a92d8970242cbe4bf0c761af8d7d9c5fa2160c833ddaad3ba0a4117b24'
V16_SPEC_SHA = '64fa6d56bb0af4317be2696d8a6fc183a720ac73a960f73e113eda95430adf23'
V16_PLAN_SHA = '47b209c9fe95f7a14031303d081828876c6fd8cd8166ceb23b1202eb46993b40'

SYSTEM = '''You are a coding agent in an isolated repository at /testbed. Solve the original issue.
Use only the issue and available repository/evidence. Test important changes with public tests.
Respond as one JSON object with exactly action and claims. One action per response.
Tools: {"tool":"list_files"}; {"tool":"read_file","path":"relative/path"};
{"tool":"write_file","path":"relative/path","content":"complete contents"};
{"tool":"shell","command":"repository command"}; {"tool":"finish","answer":"result"}.
Shell commands run in the installed testbed environment without network or host access.
File tools reject repository escapes. Commands have a 120-second deadline. Do not leave background processes.
Tool results must fit 49152 bytes; use targeted shell reads for large files rather than reading entire files.
Claims is an array (at most eight) with statement, status (OBSERVED/VERIFIED/INFERRED/UNCERTAIN/FALSIFIED),
evidence_ids (only result event IDs available in this conversation), and basis (tool/predecessor/independent).
Historical evidence IDs in handoffs are provenance, not available tool-result IDs for new claims.
Claiming done does not establish official resolution. Missing evidence remains unknown.
'''

SYSTEM_V2 = SYSTEM + '''Response contract benchmark-agent/2.0: claims are auxiliary annotations, not action authorization.
Use the declared enums; [] is appropriate when no supported annotations are available.
Malformed annotations are archived with diagnostics and excluded from validated state.
Schema conformity does not establish truth. A VERIFIED label alone verifies nothing.
Action structure, tool arguments, workspace boundaries and execution restrictions remain mandatory.
'''
SYSTEM_V3 = SYSTEM_V2 + '''Agent interface benchmark-agent/3.0 uses locally validated JSON-object actions.
list_files accepts optional prefix (literal repository-relative prefix), cursor (returned next_cursor), and limit (1..100).
Listings are bounded by 100 entries and 8192 path bytes. truncated/has_more and next_cursor explicitly describe omitted entries.
Request another page or a narrower prefix to discover further paths. Exact unchanged pages may reference an earlier listing_id instead of repeating filenames; the original tool result stays in this conversation.
Cursors become stale after repository changes; restart the listing when told so. Listing names do not establish file contents or task completion.
'''
SYSTEM_V4 = SYSTEM_V3 + ANNOTATION_GUIDANCE


def observable_audit_enabled(config):
    return config.get('agent_prompt_version') in ('benchmark-agent/3.0', 'benchmark-agent/4.0')


def response_settings(config):
    policy = config.get('response_policy', STRICT)
    require(policy in (STRICT, AUXILIARY), 'unsupported benchmark response policy')
    if policy == STRICT:
        return SYSTEM, policy, None
    if config.get('agent_prompt_version') == 'benchmark-agent/4.0':
        require(config.get('annotation_guidance_version') == ANNOTATION_GUIDANCE_VERSION
            and config.get('annotation_guidance_sha256') == digest(ANNOTATION_GUIDANCE)
            and config.get('agent_prompt_sha256') == digest(SYSTEM_V4), 'version-4 annotation guidance pin changed')
        require(config.get('action_wire_version') == 'flat-or-args/1.0'
            and config.get('action_contract_version') == '4.0'
            and config.get('internal_action_contract_version') == '3.0'
            and config.get('internal_action_contract_sha256') == digest(agent_response_format('3.0')['json_schema']['schema'])
            and config.get('action_contract_sha256') == digest(agent_response_format('4.0')['json_schema']['schema'])
            and config.get('agent_output_format') == 'json_object/3.0'
            and config.get('agent_output_format_sha256') == digest({'type':'json_object'})
            and config.get('listing_policy') == 'bounded-listing/1.0'
            and config.get('execution_contract_version') in ('agent-runtime/3.2', 'agent-runtime/3.3')
            and config.get('patch_export_policy') == 'source-and-artifacts/2.0', 'version-4 shared interface changed')
        if config.get('tool_output_policy'):
            require(config['tool_output_policy'] == 'bounded-output/1.0', 'version-4 tool output policy changed')
        return SYSTEM_V4, policy, None
    if config.get('agent_prompt_version')=='benchmark-agent/3.0':
        wire = config.get('action_wire_version')
        if wire is not None:
            require(wire == 'flat-or-args/1.0' and config.get('action_contract_version') == '4.0'
                and config.get('internal_action_contract_version') == '3.0'
                and config.get('internal_action_contract_sha256') == digest(agent_response_format('3.0')['json_schema']['schema'])
                and config.get('execution_contract_version') == 'agent-runtime/3.1', 'version-1.3 wire contract must be selected together')
        else:
            require(config.get('action_contract_version') == '3.0', 'version-3 action contract changed')
        require(config.get('agent_output_format')=='json_object/3.0'
            and config.get('listing_policy')=='bounded-listing/1.0','version-3 contract must be selected together')
        require(config.get('agent_prompt_sha256')==digest(SYSTEM_V3) and
            config.get('agent_output_format_sha256')==digest({'type':'json_object'}) and
            config.get('action_contract_sha256')==digest(agent_response_format(config['action_contract_version'])['json_schema']['schema']), 'version-3 interface pin changed')
        return SYSTEM_V3,policy,None
    require(config.get('agent_prompt_version') == 'benchmark-agent/2.0' and
            config.get('agent_output_format') == 'json_schema/2.0', 'amended response contract must be versioned together')
    output_format = agent_response_format()
    require(config.get('agent_prompt_sha256') == digest(SYSTEM_V2) and
            config.get('agent_output_format_sha256') == digest(output_format), 'amended prompt/schema pin changed')
    return SYSTEM_V2, policy, output_format


def action_wire_options(config):
    """One explicit selection shared by predecessor and every successor."""
    return {'action_wire_version': config['action_wire_version']} if config.get('action_wire_version') else {}


def read_input(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'unsafe or missing input file')
    def unique(pairs):
        row = {}
        for k, v in pairs:
            require(k not in row, 'duplicate configuration key')
            row[k] = v
        return row
    return json.loads(path.read_text(), object_pairs_hook=unique)


def load_frozen_plan(config_path=None, plan_path=None):
    require((config_path is None) == (plan_path is None), 'config and plan must be supplied together')
    config = read_input(config_path or CONFIG)
    task = read_input(PRESELECT / 'task.json')
    plan = read_input(plan_path or PRESELECT / 'plan.json')
    if config_path is not None:
        supported = {SPEC_SHA: PLAN_SHA, NEXT_SPEC_SHA: NEXT_PLAN_SHA, WIRE_SPEC_SHA: WIRE_PLAN_SHA,
                     READINESS_SPEC_SHA: READINESS_PLAN_SHA, V15_SPEC_SHA: V15_PLAN_SHA,
                     V16_SPEC_SHA: V16_PLAN_SHA}
        require(digest(config) in supported, 'configuration differs from frozen supported specification')
        expected_plan = supported[digest(config)]
        require(digest(plan) == expected_plan, 'plan differs from matched frozen plan')
        require(digest(config) == plan['config_sha256'] and digest(task) == plan['task_sha256'], 'prospective plan changed')
        selection = read_input(PRESELECT / 'plan.json')
        require(digest(selection) == SELECTION_PLAN_SHA, 'frozen selection/order changed')
        require(selection['task_sha256'] == digest(task) and task['instance_id'] == config['selected_instance'], 'selected task changed')
        require(selection['branch_order'] == random.Random(config['branch_seed']).sample(config['conditions'], len(config['conditions'])), 'branch order changed')
        plan = {**plan, 'branch_order': selection['branch_order'], 'cap_usd': config['cap_usd'],
                'plausibly_fits': Decimal(plan['total_envelope_usd']) + Decimal(plan['largest_request_reservation_usd']) <= Decimal(config['cap_usd'])}
    require(digest(config) == plan['config_sha256'] and digest(task) == plan['task_sha256'], 'prospective plan changed')
    require(plan['plausibly_fits'] and config['selection']['count'] == 1, 'one comparison must fit cap')
    require(config['automatic_retries'] == 0, 'no automatic paid retries')
    if digest(config) in (READINESS_SPEC_SHA, V15_SPEC_SHA, V16_SPEC_SHA):
        from .experiment_freeze import validate_freeze
        validate_freeze(config, ROOT)
    return config, task, plan


@dataclass(frozen=True)
class LaunchBinding:
    config_path: Path
    plan_path: Path
    authorization_path: Path
    run_dir: Path
    authorization_guard: Path
    config: dict
    task: dict
    plan: dict
    authorization: dict

    def record(self):
        return {'binding_version': 'swebench-launch/1.0', 'config_path': str(self.config_path),
                'config_sha256': digest(self.config), 'plan_path': str(self.plan_path), 'plan_sha256': digest(read_input(self.plan_path)),
                'authorization_path': str(self.authorization_path), 'authorization_sha256': digest(self.authorization),
                'run_dir': str(self.run_dir), 'execution_guard': str(self.run_dir),
                'authorization_guard': str(self.authorization_guard), 'authorization_cap_usd': self.authorization['cap_usd'],
                'preselection': str(PRESELECT), 'private_evaluator': str(PRIVATE),
                'task_sha256': digest(self.task), 'branch_order': self.plan['branch_order'],
                'exploratory_after_protocol_repair': True}


def safe_destination(path):
    path = Path(path).absolute()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', path.name), 'unsafe run identifier')
    require(path.parent.is_dir() and not any(p.is_symlink() for p in (path, *path.parents)), 'unsafe output destination')
    require(path == path.resolve() and not path.exists(), 'occupied or unsafe output destination')
    # Refuse additions anywhere inside historical artifacts or private inputs.
    protected = [PRIVATE, ROOT / 'configs', ROOT / 'src', ROOT / 'scripts', ROOT / 'tests', ROOT / 'results']
    protected += [p for p in RUNROOT.parent.iterdir() if p.is_dir()]
    require(not any(path.is_relative_to(p.resolve()) for p in protected), 'historical or private output destination')
    require(path.parent != ROOT and path.parent != Path.home(), 'unsafe live output parent')
    return path


def resolve_binding(config_path, plan_path, run_dir, authorization_path, *, allow_pending=False):
    require(all(v is not None for v in (config_path, plan_path, run_dir, authorization_path)),
            'explicit config, plan, run-dir and authorization are all required; no fallback')
    config, task, plan = load_frozen_plan(config_path, plan_path)
    response_settings(config)
    authorization = read_input(authorization_path)
    require(authorization['cap_usd'] == config['cap_usd'] == '10.00', 'authorization cap changed')
    if digest(config) in (NEXT_SPEC_SHA, WIRE_SPEC_SHA, READINESS_SPEC_SHA, V15_SPEC_SHA, V16_SPEC_SHA):
        expected_plan = {NEXT_SPEC_SHA:NEXT_PLAN_SHA, WIRE_SPEC_SHA:WIRE_PLAN_SHA,
                         READINESS_SPEC_SHA:READINESS_PLAN_SHA, V15_SPEC_SHA: V15_PLAN_SHA,
                         V16_SPEC_SHA: V16_PLAN_SHA}[digest(config)]
        require(authorization.get('version')=='swebench-authorization/2.0' and
            authorization.get('config_sha256')==digest(config) and authorization.get('plan_sha256')==expected_plan and
            authorization.get('attempts')==1 and isinstance(authorization.get('authorization_id'),str) and authorization['authorization_id'].strip(),
            'new scope must explicitly bind the frozen configuration and plan')
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',authorization['authorization_id']) is not None,'unsafe authorization scope identifier')
        require(authorization.get('provider_inference_authorized') is True or
            (allow_pending and authorization.get('provider_inference_authorized') is False), 'new paid scope is not authorized')
        guard = RUNROOT.parent / ('authorized-' + digest({'authorization_id':authorization['authorization_id']})[:24])
        return LaunchBinding(Path(config_path).resolve(),Path(plan_path).resolve(),Path(authorization_path).resolve(),
            safe_destination(run_dir),guard,config,task,plan,authorization)
    require(digest(authorization) == AUTH_SHA, 'authorization differs from recorded exploratory scope')
    # The preflight ledger is historical. Its zero usage is reconciled, not reset.
    historical = read_input(ROOT / 'runs/swebench-integration/exploratory-v1.1-preflight/spending.json')
    require(not historical['attempts'] and Decimal(historical['noncached_accounted_usd']) == 0 and
            Decimal(historical['unreconciled_reservations_usd']) == 0, 'preflight has spending or unknown usage; cannot start a fresh ledger')
    guard = RUNROOT.parent / ('authorized-' + AUTH_SHA[:24])
    return LaunchBinding(Path(config_path).resolve(), Path(plan_path).resolve(), Path(authorization_path).resolve(),
                         safe_destination(run_dir), guard, config, task, plan, authorization)


def claim_launch(binding):
    # RawRun mkdir is exclusive and atomic. The authorization-wide claim is
    # independent of output name and remains after errors, including before API use.
    safe_destination(binding.run_dir)
    claim = RawRun(binding.authorization_guard.parent, binding.authorization_guard.name)
    claim.write_artifact('claim.json', binding.record())
    claim.freeze()
    return RawRun(binding.run_dir.parent, binding.run_dir.name)


def validate_setup(config):
    # The documented gold run was evaluator-only, prior to any agent generation.
    invocation = ROOT / 'runs/swebench-integration/commands/smoke-gold-01/result.json'
    require(invocation.is_file(), 'official gold validation not completed')
    meta = json.loads(invocation.read_text())
    report = PRIVATE / 'logs/evaluation/keisho-setup-gold-20261007-01/results.json'
    require(meta['exit_code'] == 0 and report.is_file(), 'official gold validation failed or report missing')
    result = json.loads(report.read_text())
    require(report_status(result, config['smoke_instance']) == 'resolved', 'official reference patch did not resolve smoke')
    checks = json.loads((PRESELECT / 'dataset-recipe-crosscheck.json').read_text())
    require(len(checks) == 2 and all(all(row.values()) for row in checks.values()), 'dataset/recipe crosscheck incomplete')
    return {'run_id': 'keisho-setup-gold-20261007-01', 'status': 'resolved', 'setup_only': True,
            'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}


def make_handoffs(task, predecessor, inventory, base_inventory, note_models, config, plan, *, run_dir=None):
    trajectory = predecessor.load_frozen()
    state, archive, _ = load_session(predecessor.path, task['problem_statement'],
         acceptance=('Resolve the original issue; verify with repository tests. Official grade is unknown.',))
    if observable_audit_enabled(config):
        from keisho.handoff.workspace import compare_scope_hashes
        for item in state['items']:item['revalidation']=compare_scope_hashes(item,inventory)
    predecessor.write_artifact('handoff-imported-state.json', state)
    changed = sorted(p for p in inventory.keys() | base_inventory.keys() if inventory.get(p) != base_inventory.get(p))
    workspace = {'files': [{'path': p, **v} for p, v in inventory.items()], 'exclusions': [],
                 'original_issue_supplied_separately': True,
                 'git': {'status': [{'status': 'changed', 'path': p} for p in changed]},
                 'benchmark_environment': 'Independent container restored from the same frozen environment image. Git contains only the official shallow base plus current edits. No audit/evaluator mounts or evidence lookup.'}
    native = NativeTokenizer()
    keisho, compilation = compile_handoff(state, workspace, 2048, native)
    adapter_version = config.get('notes_adapter_version', 'structured-adapter/1.0')
    deterministic = deterministic_fields(trajectory.events, changed, adapter_version)
    # Identical evidence packet for both generators: complete observable record,
    # deterministic metadata and checkpoint cumulative patch. No grade is included.
    evidence = canonical_json({'original_issue': task['problem_statement'], 'observable_events': trajectory.events,
                              'checkpoint_changed_file_inventory': {p: inventory.get(p) for p in changed}, 'deterministic_fields': deterministic,
                              'cumulative_patch': json.loads((predecessor.path / 'checkpoint-patch.json').read_text())['patch']})
    note_run = RawRun(run_dir or RUNROOT, 'note-generation')
    recorder = Recorder(note_run)
    texts = {'REPOSITORY_ONLY': '', 'FULL_HISTORY': canonical_json(archive['events']), 'KEISHO_2K': keisho}
    for n, kind in enumerate(('summary', 'structured'), 1):
        messages = tuple(Message(m['role'], m['content']) for m in generation_messages(kind, evidence, adapter_version, deterministic))
        request = ModelRequest(messages, config['branch_seed'], config['generation_output_tokens'], 0.0)
        model = note_models(kind,audit=note_run) if observable_audit_enabled(config) else note_models(kind)
        require(request_upper_bound(model, request) <= 32000, 'note evidence exceeds frozen input budget; no truncation')
        response, call = logged_generate(model, request, recorder, kind, CallPurpose.SUMMARY, n)
        note_run.write_artifact(kind + '-call.json', call)
        require(response is not None and response.finish_reason == 'stop', 'note generation failed; no retry')
        if kind == 'summary':
            require(response.text.strip(), 'empty ordinary summary')
            texts['SUMMARY_2K'] = response.text.strip()
        else:
            texts['STRUCTURED_NOTES_2K'] = render_structured(json.loads(response.text), deterministic)
    note_run.freeze()
    for condition, text in texts.items():
        if condition.endswith('_2K'):
            require(native.count(text).count <= 2048, condition + ' handoff overflow; no truncation')
        whole = ModelRequest((Message('system', response_settings(config)[0] + json.loads(PROMPTS.read_text())['takeover']),
                              Message('user', task['problem_statement']), Message('user', text)),
                             config['branch_seed'], 2048, 0.0)
        upper = request_upper_bound(note_models('summary'), whole)
        schema = response_settings(config)[2]
        if schema is not None:
            upper += native.count(canonical_json(schema)).count
        require(upper <= config['successor_budgets']['request_input_tokens'], condition + ' exceeds whole request budget; FULL_HISTORY stays full')
    predecessor.write_artifact('handoffs.json', {'texts': texts, 'keisho_compilation': compilation,
                                               'tokens': {c: native.count(t).count for c,t in texts.items()},
                                               'source_trajectory_sha256': trajectory.sha256,
                                               'source_inventory_sha256': digest(inventory), 'official_classification': 'withheld'})
    return texts


def execution_result(execution):
    return {'reason': execution.reason, 'model_calls': execution.model_calls, 'tool_calls': execution.tool_calls,
            'input_tokens': sum(c.usage.input_tokens for c in execution.calls) if all(c.usage.input_tokens is not None for c in execution.calls) else None,
            'output_tokens': sum(c.usage.output_tokens for c in execution.calls) if all(c.usage.output_tokens is not None for c in execution.calls) else None,
            'elapsed_seconds': execution.elapsed_seconds}


def runtime_preflight(binding, *, dry=False):
    config, task, plan = binding.config, binding.task, binding.plan
    setup = validate_setup(config)  # Before creating a paid-run guard or any model.
    catalog = read_input(PRESELECT / 'provider-catalog.json')
    validate_catalog(catalog)
    if response_settings(config)[2] is not None:
        for alias in ('openai/gpt-4.1-mini', 'openai/gpt-4.1'):
            endpoint = next(e for e in catalog['endpoints'][alias]['data']['endpoints'] if e['tag'] == 'openai')
            require('structured_outputs' in endpoint['supported_parameters'], 'frozen endpoint lacks schema support')
    require(digest(catalog) == plan['catalog_sha256'], 'pricing/catalog pin changed')
    credentials = load_project_env(ROOT, environ=dict(__import__('os').environ) if dry else None)['present']
    require(credentials['OPENROUTER_API_KEY'], 'configured provider credential missing')
    provider = read_input(ROOT / 'configs' / config['provider_config'])
    require(digest(provider) == PROVIDER_SHA, 'frozen provider mapping/routing changed')
    ca = (ROOT / 'configs' / provider['tls']['ca_file']).resolve()
    require(ca.is_file() and hashlib.sha256(ca.read_bytes()).hexdigest() == provider['tls']['ca_sha256'], 'pinned verified CA missing/changed')
    native = NativeTokenizer()
    import importlib.metadata
    import swebench
    require(importlib.metadata.version('swebench') == config['harness_version'], 'installed harness version changed')
    source = PRIVATE / 'sources' / ('SWE-bench-' + config['harness_commit']) / 'swebench'
    installed = Path(swebench.__file__).parent
    for module in ('harness/run_evaluation.py', 'harness/grading.py', 'harness/reporting.py', 'harness/utils.py'):
        require(hashlib.sha256((source / module).read_bytes()).digest() == hashlib.sha256((installed / module).read_bytes()).digest(), 'installed official evaluator modified')
    image_metadata = read_input(PRIVATE / 'prepared-task-image.json')
    require(digest(image_metadata) == IMAGE_METADATA_SHA and image_metadata['instance_id'] == task['instance_id'] and
            image_metadata['base_commit'] == task['base_commit'] and image_metadata['environment_verified'], 'prepared task environment changed')
    require(hashlib.sha256((PRIVATE / 'selected-task-evaluator.jsonl').read_bytes()).hexdigest() == image_metadata['evaluator_dataset_sha256'], 'private evaluator row changed')
    require(json.loads(docker('image', 'inspect', image_metadata['image_id']).stdout)[0]['Id'] == image_metadata['image_id'], 'prepared image unavailable')
    require(not (PRIVATE / 'predictions' / binding.run_dir.name).exists(), 'occupied private prediction namespace')
    # Reuse the existing gate and its full reservation, without making a request.
    probe = SpendLedger(config['cap_usd'], provider='openrouter', authorized_ceiling_usd=binding.authorization['cap_usd'], authorization_scope='swebench-one-comparison')
    require(Decimal(plan['total_envelope_usd']) + Decimal(plan['largest_request_reservation_usd']) <= probe.cap, 'envelope plus reservation headroom exceeds cap')
    return {'setup': setup, 'provider': provider, 'ca': ca, 'native': native,
            'image_metadata': image_metadata, 'credential_presence': credentials}


def check_public_catalog(ca):
    """Unauthenticated public metadata only; no model/credential validation call."""
    from urllib.request import Request
    from keisho.agents.providers.openai_chat import verified_opener
    def get(path):
        with verified_opener(ca).open(Request(BASE_URL + path, headers={'Accept': 'application/json'}), timeout=60) as r:
            return json.loads(r.read())
    models = get('/models')['data']
    aliases = ('openai/gpt-4.1-mini', 'openai/gpt-4.1')
    catalog = {'models': [m for m in models if m['id'] in aliases],
               'endpoints': {m: get('/models/' + m + '/endpoints') for m in aliases}}
    validate_catalog(catalog)
    for alias in aliases:
        e = next(e for e in catalog['endpoints'][alias]['data']['endpoints'] if e['tag'] == 'openai')
        require('structured_outputs' in e['supported_parameters'], 'current endpoint lacks schema support')
    return catalog


def dry_run(*, config_path, plan_path, run_dir, authorization_path):
    binding = resolve_binding(config_path, plan_path, run_dir, authorization_path,allow_pending=True)
    ctx = runtime_preflight(binding, dry=True)
    permitted=binding.authorization.get('provider_inference_authorized',True)
    return {**binding.record(), 'dry_run': True, 'live_start_admitted': permitted and not binding.authorization_guard.exists(),
            'admission_reason': 'new provider-spending authorization pending; no live start admitted' if not permitted else
                'authorization already claimed' if binding.authorization_guard.exists() else 'binding and local preflight pass; live start also checks current public catalog',
            'response_policy': binding.config['response_policy'], 'agent_prompt_version': binding.config['agent_prompt_version'],
            'agent_output_format': binding.config['agent_output_format'], 'agent_prompt_sha256': binding.config['agent_prompt_sha256'],
            'agent_output_format_sha256': binding.config['agent_output_format_sha256'], 'notes_adapter_version': binding.config['notes_adapter_version'],
            'selected_task': binding.task['instance_id'], 'base_commit': binding.task['base_commit'],
            'action_wire_version': binding.config.get('action_wire_version'),
            'internal_action_contract_version': binding.config.get('internal_action_contract_version', binding.config.get('action_contract_version')),
            'annotation_guidance_version': binding.config.get('annotation_guidance_version'),
            'patch_export_policy': binding.config.get('patch_export_policy'),
            'tool_output_policy': binding.config.get('tool_output_policy'),
            'experiment_manifest_sha256': binding.config.get('experiment_manifest_sha256'),
            'models': ctx['provider']['models'], 'conditions': binding.config['conditions'],
            'cost_envelope_usd': binding.plan['total_envelope_usd'], 'reservation_headroom_usd': binding.plan['largest_request_reservation_usd'],
            'pricing_assumptions': binding.plan['assumptions'], 'credential_presence': ctx['credential_presence'],
            'evaluator_setup': ctx['setup'], 'environment': ctx['image_metadata'], 'provider_requests': 0, 'guard_created': False}


def execute(*, approve_live=False, config_path=None, plan_path=None, run_dir=None, authorization_path=None):
    require(approve_live is True, 'explicit new live authorization required')
    if all(v is None for v in (config_path, plan_path, run_dir, authorization_path)):
        require(not RUNROOT.exists(), 'completed comparison guard exists; no restart or credential validation')
    binding = resolve_binding(config_path, plan_path, run_dir, authorization_path)
    require(not binding.authorization_guard.exists(), 'authorization already claimed; no restart elsewhere')
    config, task, plan = binding.config, binding.task, binding.plan
    system, response_policy, output_format = response_settings(config)
    wire_options = action_wire_options(config)
    ctx = runtime_preflight(binding)
    public_catalog = check_public_catalog(ctx['ca'])
    index = claim_launch(binding)  # Atomic authorization claim before any model.
    provider, ca, native = ctx['provider'], ctx['ca'], ctx['native']
    prediction_dir = PRIVATE / 'predictions' / binding.run_dir.name
    recorder = Recorder(index)
    emitted = 0
    def emit(row):
        nonlocal emitted
        emitted += 1
        recorder.emit('spend-' + str(emitted), EventKind.ANNOTATION, 'spending-control', row)
    ledger = SpendLedger(config['cap_usd'], emit, provider='openrouter', authorized_ceiling_usd=binding.authorization['cap_usd'], authorization_scope='swebench-one-comparison')
    index.write_artifact('authorization.json', {'reference_record': binding.authorization, 'approve_live': True,
                          'cap_usd': config['cap_usd'], 'reference': str(binding.authorization_path),
                          'reference_sha256': digest(binding.authorization), 'continued_scope': digest(config)==SPEC_SHA, 'prior_scope_accounted_usd': '0', 'cap_is_not_additional': digest(config)==SPEC_SHA})
    index.write_artifact('binding.json', binding.record())
    index.write_artifact('plan.json', {'source_config': config, 'plan': plan, 'setup': ctx['setup']})
    if config.get('experiment_manifest'):
        index.write_artifact('experiment-manifest.json', read_input(ROOT / config['experiment_manifest']))
    index.write_artifact('execution-config.json', {'source_config_sha256': digest(config), 'config': {**config, 'live_execution_authorized': True},
                          'execution_metadata': binding.record()})
    index.write_artifact('public-catalog-preflight.json', public_catalog)
    def model(role, mode='agent', stage=None, audit=None):
        identity = config[role + '_model']
        allowed = provider['models']['successor' if (role == 'successor' or config[role + '_model'] == config['successor_model']) else 'predecessor']['accepted_response_model_ids']
        transport=partial(http_transport, base_url=BASE_URL, provider='OpenRouter', ca_file=ca)
        if audit is not None:
            from .response_measurements import capture_response
            number=0
            def transport(body,key):
                nonlocal number
                number+=1
                prefix=(stage+'-') if mode!='agent' else ''
                audit.write_artifact(f'{prefix}wire-request-{number:03d}.json',body)
                if mode=='agent':
                    observer=lambda payload,status,redacted:capture_response(audit,number,payload,status,redacted)
                else:
                    import base64
                    observer=lambda payload,status,redacted:audit.write_artifact(f'{prefix}wire-response-{number:03d}.json',
                        {'body_base64':base64.b64encode(payload).decode(),'http_status':status,'credential_redaction_applied':redacted,'headers_recorded':False})
                return http_transport(body,key,base_url=BASE_URL,provider='OpenRouter',ca_file=ca,response_observer=observer)
        adapter = OpenRouterChatModel(identity, authorized=True, tokenizer=native, mode=mode, response_model_ids=allowed,
                 agent_response_format=output_format if mode == 'agent' else None,
                 transport=transport)
        return BudgetedModel(adapter, ledger, stage or role, identity)
    def session_for(image,raw):
        if config.get('tool_output_policy') == 'bounded-output/1.0':
            from .bounded_output import BoundedRepositorySession
            return BoundedRepositorySession(image, audit=raw, timeout=config['tool_timeout_seconds'], output_bytes=config['tool_output_bytes'],
                                            listing_policy=config.get('listing_policy', 'legacy'),
                                            patch_export_policy=config.get('patch_export_policy', 'legacy'))
        options={'listing_policy':config['listing_policy']} if config.get('listing_policy') else {}
        if config.get('patch_export_policy'):
            options['patch_export_policy'] = config['patch_export_policy']
        return RepositorySession(image,audit=raw,timeout=config['tool_timeout_seconds'],output_bytes=config['tool_output_bytes'],**options)
    def measure(raw,session,role):
        if observable_audit_enabled(config):
            from .response_measurements import measure_run
            raw.write_artifact('response-measurements.json',measure_run(raw,session.validate_action,role=role,
                action_contract_version=config['action_contract_version'], **wire_options))
    results = {c: {'status': 'unstarted', 'official_status': None} for c in config['conditions']}
    overall = 'interrupted'
    predecessor_info = None
    checkpoint_grade = None
    try:
        prediction_dir.mkdir(parents=True, exist_ok=False)
        image_metadata = ctx['image_metadata']
        require(image_metadata['instance_id'] == task['instance_id'] and image_metadata['environment_verified'], 'task environment not validated')
        dataset = PRIVATE / 'selected-task-evaluator.jsonl'
        require(hashlib.sha256(dataset.read_bytes()).hexdigest() == image_metadata['evaluator_dataset_sha256'], 'private evaluator row changed')
        image = image_metadata['image_id']
        require(json.loads(docker('image', 'inspect', image).stdout)[0]['Id'] == image, 'prepared image unavailable')
        index.write_artifact('task-image.json', image_metadata)
        predecessor = RawRun(binding.run_dir, 'predecessor')
        session = session_for(image,predecessor)
        try:
            base_inventory = session.initialize_base(task['base_commit'])
            checkpoint = ValidationCheckpoint()
            execution = run_agent(model('predecessor',audit=predecessor if observable_audit_enabled(config) else None), session, Recorder(predecessor), task['problem_statement'], system, '',
                                  config['branch_seed'], Budgets(**config['predecessor_budgets']), role='predecessor',
                                  checkpoint_predicate=checkpoint, time_limit_seconds=config['time_limit_seconds'], response_policy=response_policy, **wire_options)
            predecessor_info = execution_result(execution)
            predecessor.write_artifact('execution.json', predecessor_info)
            predecessor.write_artifact('calls.json', execution.calls)
            measure(predecessor,session,'predecessor')
            if execution.reason != 'checkpoint':
                predecessor.write_artifact('terminal-patch.json', {'patch': session.patch(task['base_commit']),
                        'from_base_commit': task['base_commit'], 'checkpoint_eligible': False})
                predecessor.write_artifact('checkpoint.json', {'eligible': False, 'reason': execution.reason, 'resampling': False})
                predecessor.freeze()
                overall = 'checkpoint_not_reached'
                return index.path
            patch = session.patch(task['base_commit'])
            predecessor.write_artifact('checkpoint-patch.json', {'patch': patch, 'from_base_commit': task['base_commit']})
            frozen_image, inventory = session.freeze()
            predecessor.write_artifact('checkpoint.json', {'eligible': True, **checkpoint.checkpoint,
                        'image_id': frozen_image, 'inventory': inventory, 'inventory_sha256': digest(inventory)})
            predecessor.freeze()
        finally:
            session.close()
        texts = make_handoffs(task, predecessor, inventory, base_inventory,
                             lambda kind,audit=None: model('generation', mode='summary' if kind == 'summary' else 'state', stage='note_generation_' + kind,audit=audit), config, plan, run_dir=binding.run_dir)
        checkpoint_prediction = prediction_dir / 'checkpoint-prediction.jsonl'
        write_prediction(checkpoint_prediction, task, 'checkpoint-only', patch)
        checkpoint_grade = evaluate(PRIVATE, config, task, 'checkpoint', checkpoint_prediction, run_namespace=binding.run_dir.name)
        # This grade is supervisor-only and cannot affect notes/stopping/task selection.
        index.write_artifact('checkpoint-grade-private.json', checkpoint_grade)
        successor_system = system + json.loads(PROMPTS.read_text())['takeover']
        for condition in plan['branch_order']:
            if ledger.stopped:
                overall = 'spending_stopped'
                break
            results[condition] = {'status': 'interrupted', 'official_status': None}
            branch = RawRun(binding.run_dir, condition)
            branch.write_artifact('input.json', {'task': task, 'handoff': texts[condition], 'system': successor_system,
                    'image_id': frozen_image, 'budgets': config['successor_budgets'], 'seed': config['branch_seed']})
            session = session_for(frozen_image,branch)
            try:
                session.base_inventory = base_inventory
                require(session.inventory() == inventory, 'branch restoration mismatch')
                execution = run_agent(model('successor', stage=condition,audit=branch if observable_audit_enabled(config) else None), session, Recorder(branch), task['problem_statement'], successor_system,
                                      texts[condition], config['branch_seed'], Budgets(**config['successor_budgets']),
                                      time_limit_seconds=config['time_limit_seconds'], response_policy=response_policy, **wire_options)
                branch.write_artifact('calls.json', execution.calls)
                branch.write_artifact('execution.json', execution)
                measure(branch,session,'successor')
                prediction = prediction_dir / (condition + '-prediction.jsonl')
                final_patch = session.patch(task['base_commit'])
                write_prediction(prediction, task, config['successor_model'], final_patch)
                branch.write_artifact('prediction.json', {'model_patch': final_patch, 'from_base_commit': task['base_commit'], 'instance_id': task['instance_id']})
                branch.freeze()
                status = ('interrupted' if execution.reason in ('model_failure', 'invalid_run', 'infrastructure_failure') else
                          'budget_stopped' if execution.reason in ('budget_exhausted', 'time_budget_exhausted') else 'completed')
                result = {'status': status, **execution_result(execution)}
                result['official_evaluation'] = evaluate(PRIVATE, config, task, condition, prediction, run_namespace=binding.run_dir.name)
                result['official_status'] = result['official_evaluation']['status']
                branch.write_artifact('result.json', result)
                results[condition] = result
            finally:
                session.close()
        else:
            overall = 'complete'
    except Exception as exc:
        index.write_artifact('failure.json', {'exception': type(exc).__name__, 'reason': str(exc), 'retry': False})
        overall = 'stopped_on_error'
    finally:
        if not ledger.stopped:
            ledger.stop('bounded one-task comparison ended; no further requests authorized by this block')
        index.write_artifact('spending.json', ledger.report())
        index.write_artifact('result.json', {'label': config['label'], 'status': overall, 'predecessor': predecessor_info,
               'checkpoint_classification': checkpoint_grade, 'conditions': results,
               'note_generation_cost_usd': str(sum(Decimal(r.get('noncached_accounted_usd', '0')) for r in ledger.records if r['stage'].startswith('note_generation'))),
               'model_assisted_semantic_review': None, 'human_review': False})
        index.freeze()
    return index.path
