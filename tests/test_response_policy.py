"""Saved-response replay and prospective contracts: no provider/network calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from keisho.agents.base import Message, ModelRequest
from keisho.agents.scripted import ScriptedModel
from keisho.agents.providers.openai_chat import ProviderFailure
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel
from keisho.benchmark.comparison import response_settings, execute, ROOT, RUNROOT
from keisho.benchmark.environment import RepositorySession
from keisho.benchmark.protocol import deterministic_fields, generation_messages
from keisho.core import ValidationError, canonical_json
from keisho.handoff.session import load_session
from keisho.logging.raw import RawRun, EventKind
from keisho.pilot.agent import Budgets, Recorder, parse_output, run_agent, request_upper_bound
from keisho.pilot.response_policy import AUXILIARY, agent_response_format
from keisho.pilot.spending import SpendLedger, BudgetedModel

FIXTURE = Path(__file__).parent / 'data/swebench-first-response'
SAVED = json.loads((FIXTURE / 'predecessor_call_001-response.json').read_text())
TEXT = SAVED['text']
VALID = {'statement': 'a model interpretation', 'status': 'VERIFIED', 'evidence_ids': [], 'basis': 'independent'}


class DisposableRepository:
    """Actual RepositorySession file tools, generated subprocesses in an owned temp.

    Substitute only Docker namespace transport; never execute model script content
    or arbitrary shell, access the task repository, or contact any provider.
    """
    def __init__(self, root):
        self.root = root.resolve()
        self.session = RepositorySession.__new__(RepositorySession)
        self.session.listing_policy = 'legacy'  # Match constructor for frozen v1.1 replay.
        self.session.name, self.session.actions, self.session.audit = 'offline-fixture', 0, None
        self.session.output_bytes, self.session.base_inventory = 49152, {}
        self.session.inventory = self.inventory

    def inventory(self):
        return {str(p.relative_to(self.root)): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def transport(self, *args, **kwargs):
        if args[0] == 'top':
            return subprocess.CompletedProcess(args, 0, b'PID ARGS\n1 /bin/sleep infinity\n', b'')
        if args[:3] == ('exec', 'offline-fixture', 'python3'):
            code = args[-1].replace('/testbed', str(self.root))
            r = subprocess.run(['python3', '-c', code], capture_output=True, env={'PATH': '/usr/bin:/bin:/usr/local/bin'})
        elif args[:3] == ('exec', 'offline-fixture', 'cat'):
            r = subprocess.run(['cat', str(self.root / args[-1].removeprefix('/testbed/'))], capture_output=True)
        else:
            raise AssertionError('unapproved fixture transport')
        if kwargs.get('check', True) and r.returncode:
            raise AssertionError(r.stderr.decode())
        return r


class ResponsePolicyTests(unittest.TestCase):
    def replay(self, root, text=TEXT, role='predecessor', condition='fixture'):
        workspace = root / 'workspace'; workspace.mkdir()
        fixture = DisposableRepository(workspace)
        raw = RawRun(root, condition)
        model = ScriptedModel((text,))
        config = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
        system, policy, _ = response_settings(config)
        with patch('keisho.benchmark.environment.docker', fixture.transport):
            result = run_agent(model, fixture.session, Recorder(raw), 'offline fixture issue', system,
                               '' if role == 'predecessor' else 'historical fixture', 1,
                               Budgets(1, 1, 2048, 20000, 32000, 128000), role=role, response_policy=policy)
        raw.freeze()
        return result, raw, workspace

    def test_exact_fixture_provenance_and_original_failure(self):
        manifest = json.loads((FIXTURE / 'provenance.json').read_text())
        for name, row in manifest['files'].items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), row['sha256'])
            if 'source' in row:
                self.assertEqual((ROOT / row['source']).read_bytes(), (FIXTURE / name).read_bytes())
        self.assertEqual((FIXTURE / 'raw-provider-response.json').read_bytes(), SAVED['raw_response_json'].encode())
        self.assertEqual((FIXTURE / 'response-text.json').read_bytes(), TEXT.encode())
        native = json.loads(SAVED['raw_response_json'])
        self.assertEqual(native['choices'][0]['message']['content'], TEXT)
        with self.assertRaisesRegex(ValidationError, 'invalid claim basis'):
            parse_output(TEXT, set())  # Legacy contract remains strict.
        body = json.loads(SAVED['request_body_json'])
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertIn('basis (tool/predecessor/independent)', body['messages'][0]['content'])
        model = OpenRouterChatModel('openai/gpt-4.1-mini-2025-04-14')
        request = ModelRequest(tuple(Message(m['role'], m['content']) for m in body['messages']),
                               body['seed'], body['max_tokens'], body['temperature'])
        self.assertEqual(model.body(request), body)  # No generate/key/transport call.

    def test_saved_reply_under_amended_policy_actual_write_only(self):
        with tempfile.TemporaryDirectory() as t:
            result, raw, workspace = self.replay(Path(t))
            self.assertEqual((result.model_calls, result.tool_calls), (1, 1))
            self.assertEqual((workspace / 'test_chunk_access.py').read_text(), json.loads(TEXT)['action']['content'])
            self.assertEqual(len((workspace / 'test_chunk_access.py').read_bytes()), 1133)
            report = json.loads((raw.path / 'predecessor_call_001-annotations.json').read_text())
            self.assertEqual(report['coverage'], {'supplied': 4, 'validated': 0, 'rejected': 4})
            self.assertEqual(report['raw_claims'], json.loads(TEXT)['claims'])
            self.assertEqual([d['raw_claim']['basis'] for d in report['diagnostics']],
                             ['issue report', 'user environment details', 'issue traceback', 'issue report'])
            self.assertEqual(json.loads((raw.path / 'predecessor_call_001-response.json').read_text())['text'], TEXT)
            state, archive, _ = load_session(raw.path, 'offline fixture issue')
            self.assertFalse(any(i['category'] == 'hypothesis' for i in state['items']))
            self.assertEqual(state['extraction']['annotation_coverage']['rejected'], 4)
            self.assertIn('hypothesis', state['unknown'])
            self.assertTrue(any('excluded from state' in w for w in state['warnings']))
            self.assertTrue(any(json.loads(e['payload_json']).get('text') == TEXT for e in archive['events']))

    def test_identical_policy_predecessor_and_all_conditions(self):
        config = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
        for condition in ['predecessor', *config['conditions']]:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as t:
                result, raw, _ = self.replay(Path(t), role='predecessor' if condition == 'predecessor' else 'successor', condition=condition)
                self.assertEqual(result.tool_calls, 1)
                annotation = next(e for e in raw.load_frozen().events if 'annotations_001' in e.id)
                self.assertEqual(json.loads(annotation.payload_json)['coverage']['rejected'], 4)
            with self.subTest(invalid_condition=condition), tempfile.TemporaryDirectory() as t:
                text = json.dumps({'action': {'tool': 'read_file', 'path': '../outside'}, 'claims': [VALID]})
                result, _, _ = self.replay(Path(t), text, role='predecessor' if condition == 'predecessor' else 'successor', condition=condition)
                self.assertEqual((result.reason, result.tool_calls), ('invalid_run', 0))

    def test_valid_claim_never_authorizes_invalid_action(self):
        actions = [{'tool': 'unsupported'}, {'tool': []}, {'tool': 'write_file', 'path': '../escape', 'content': 'x'},
                   {'tool': 'read_file', 'path': '/etc/passwd'}, {'tool': 'write_file', 'path': '.git/config', 'content': 'x'},
                   {'tool': 'write_file', 'path': 'file', 'content': 1}, {'tool': 'write_file', 'path': 'file', 'content': 'x' * 49153},
                   {'tool': 'shell', 'command': ' '}, {'tool': 'shell', 'command': 'true', 'extra': True},
                   {'tool': 'shell', 'command': '\0'}, {'tool': 'finish', 'answer': 'done', 'extra': True},
                   {'tool': 'write_file', 'path': 'file', 'content': '\ud800'}]
        for action in actions:
            with self.subTest(action=action['tool']), tempfile.TemporaryDirectory() as t:
                result, raw, workspace = self.replay(Path(t), json.dumps({'action': action, 'claims': [VALID]}))
                self.assertEqual(result.tool_calls, 0)
                self.assertIn(result.reason, ('invalid_run', 'model_failure'))
                self.assertEqual(list(workspace.iterdir()), [])

    def test_ambiguous_or_invalid_top_level_fails_closed(self):
        for text in ('{"action":{"tool":"list_files"},"action":{"tool":"shell","command":"true"},"claims":[]}',
                     '{"action":{"tool":"list_files","tool":"shell"},"claims":[]}',
                     '{"action":{"tool":"list_files"},"claims":{},"extra":1}',
                     '{"action":{"tool":"list_files"},"claims":[NaN]}',
                     json.dumps({'action': {'tool': 'list_files'}, 'claims': [VALID] * 9})):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as t:
                result, _, workspace = self.replay(Path(t), text)
                self.assertEqual((result.reason, result.tool_calls), ('model_failure', 0))
                self.assertEqual(list(workspace.iterdir()), [])

    def test_unknown_or_unsupported_refs_excluded_not_rewritten(self):
        bad = [{**VALID, 'evidence_ids': ['future_result', 'gold_patch']}, {**VALID, 'evidence_ids': [1]},
               {**VALID, 'basis': 'issue report'}, {**VALID, 'status': []}, None]
        data = parse_output(json.dumps({'action': {'tool': 'list_files'}, 'claims': bad + [VALID]}), set(), AUXILIARY)
        self.assertEqual(data['claims'], [VALID])
        self.assertEqual(data['annotation_report']['raw_claims'], bad + [VALID])
        self.assertEqual(data['annotation_report']['coverage']['rejected'], 5)
        self.assertEqual(data['annotation_report']['diagnostics'][0]['errors'][0]['unavailable'], ['future_result', 'gold_patch'])
        for d in data['annotation_report']['diagnostics']:
            self.assertEqual(d['annotation_information'], 'unknown')
        valid = {**VALID, 'evidence_ids': ['available_result']}
        self.assertEqual(parse_output(json.dumps({'action': {}, 'claims': [valid]}), {'available_result'}, AUXILIARY)['claims'], [valid])

    def test_schema_valid_verified_label_is_only_hypothesis(self):
        text = json.dumps({'action': {'tool': 'list_files'}, 'claims': [VALID]})
        with tempfile.TemporaryDirectory() as t:
            _, raw, _ = self.replay(Path(t), text)
            state, _, _ = load_session(raw.path, 'fixture')
            item = next(i for i in state['items'] if i['text'] == VALID['statement'])
            self.assertEqual(item['status'], 'HYPOTHESIZED')
            self.assertEqual(item['scope']['files'], {})
            self.assertIn('scope not established', item['scope']['environment'])

    def test_symlink_escape_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); inside = root / 'inside'; inside.mkdir(); outside = root / 'outside'; outside.mkdir()
            (inside / 'link').symlink_to(outside, target_is_directory=True)
            fixture = DisposableRepository(inside)
            with patch('keisho.benchmark.environment.docker', fixture.transport):
                from keisho.pilot.tools import InvalidAction
                with self.assertRaisesRegex(InvalidAction, 'path escapes repository'):
                    fixture.session.execute({'tool': 'write_file', 'path': 'link/file', 'content': 'never write'})
            self.assertEqual(list(outside.iterdir()), [])

    def test_git_metadata_symlink_and_refusal_import(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); workspace = root / 'workspace'; workspace.mkdir()
            (workspace / '.git').mkdir(); (workspace / '.git/config').write_text('preserve')
            (workspace / 'alias').symlink_to(workspace / '.git', target_is_directory=True)
            fixture = DisposableRepository(workspace)
            raw = RawRun(root, 'refused')
            text = json.dumps({'action': {'tool': 'write_file', 'path': 'alias/config', 'content': 'denied'}, 'claims': []})
            with patch('keisho.benchmark.environment.docker', fixture.transport):
                result = run_agent(ScriptedModel((text,)), fixture.session, Recorder(raw), 'fixture', 'fixed', '', 1,
                                   Budgets(1, 1, 2048, 20000, 32000, 128000), response_policy=AUXILIARY)
            self.assertEqual(result.reason, 'invalid_run')
            self.assertEqual((workspace / '.git/config').read_text(), 'preserve')
            raw.freeze()
            state, _, _ = load_session(raw.path, 'fixture')
            self.assertFalse(state['checkpoint']['completed_boundary'])
            self.assertFalse(any(i['category'] in ('progress', 'change') for i in state['items']))

    def test_schema_routing_and_reservation_include_schema_tokens(self):
        request = ModelRequest((Message('user', 'fixture'),), 1, 2048, 0)
        for model_id in ('openai/gpt-4.1-mini-2025-04-14', 'openai/gpt-4.1-2025-04-14'):
            model = OpenRouterChatModel(model_id, tokenizer=SimpleNamespace(count=ScriptedModel().count_tokens), agent_response_format=agent_response_format())
            body = model.body(request)
            self.assertEqual(body['response_format'], agent_response_format())
            self.assertTrue(body['provider']['require_parameters'])
            self.assertFalse(body['provider']['allow_fallbacks'])
            self.assertEqual(body['provider']['only'], ['openai'])
            self.assertEqual(body['plugins'], [])
            ledger = SpendLedger('10', provider='openrouter', authorized_ceiling_usd='10', authorization_scope='swebench-one-comparison')
            wrapped = BudgetedModel(model, ledger, 'fixture', model_id)
            self.assertEqual(request_upper_bound(model, request), request_upper_bound(wrapped, request))
            self.assertGreater(model.request_extra_tokens(), 0)
            # Local gated generate exits before credentials or transport; never a key-validation request.
            with self.assertRaisesRegex(ProviderFailure, 'paid execution is gated'):
                model.generate(request)

    def test_original_guard_blocks_even_credential_validation(self):
        self.assertTrue(RUNROOT.is_dir())
        with patch('keisho.benchmark.comparison.load_project_env', side_effect=AssertionError('no credential inspection')):
            with self.assertRaisesRegex(ValidationError, 'completed comparison guard exists'):
                execute(approve_live=True)

    def test_prospective_config_keeps_frozen_experiment(self):
        old = json.loads((ROOT / 'configs/swebench-comparison-v1.json').read_text())
        new = json.loads((ROOT / 'configs/swebench-comparison-v1.1.json').read_text())
        for key in set(old) - {'version'}: self.assertEqual(new[key], old[key], key)
        self.assertFalse(new['live_execution_authorized'])
        self.assertEqual(response_settings(old)[1:], ('strict/1.0', None))
        self.assertEqual(response_settings(new)[1], AUXILIARY)
        with self.assertRaisesRegex(ValidationError, 'prompt/schema pin changed'):
            response_settings({**new, 'agent_prompt_sha256': '0' * 64})

    def test_baseline_observable_label_and_conditional_rule(self):
        from types import SimpleNamespace
        def event(action, paths, code=None):
            return SimpleNamespace(kind=EventKind.TOOL_RESULT, payload_json=canonical_json({'action': action, 'changed_paths': paths, 'exit_code': code, 'output': 'recorded result'}))
        edit = event({'tool': 'write_file'}, ['pkg/api.py'])
        validation = event({'tool': 'shell', 'command': 'pytest'}, [], 0)
        legacy = deterministic_fields([edit, validation], ['pkg/api.py'])
        self.assertIn('official classification withheld', legacy['continuation_state_label'])
        for code, label in ((0, 'source-change-validated-by-predecessor'), (1, 'source-change-with-failing-validation')):
            fields = deterministic_fields([edit, event({'tool': 'shell', 'command': 'pytest'}, [], code)], ['pkg/api.py'], 'structured-adapter/1.1')
            self.assertEqual(fields['continuation_state_label'], label)
        fields = deterministic_fields([validation, edit], ['pkg/api.py'], 'structured-adapter/1.1')
        self.assertEqual(fields['latest_predecessor_validation_command'], 'NONE OBSERVED')
        self.assertEqual(fields['continuation_state_label'], 'source-change-needs-verification')
        messages = generation_messages('structured', 'fixture evidence', 'structured-adapter/1.1', fields)
        self.assertIn('recommend verification of the current changes before any further edits', messages[1]['content'])


if __name__ == '__main__':
    unittest.main()
