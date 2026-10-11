"""Archived and adversarial annotation replay; no inference or benchmark runs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from keisho.core import canonical_json, digest
from keisho.handoff.compact import compile_handoff
from keisho.handoff.session import load_session
from keisho.handoff.workspace import compare_scope_hashes
from keisho.logging.raw import EventKind, RawRun
from keisho.pilot.action_wire import canonicalize_action
from keisho.pilot.agent import Recorder, parse_output
from keisho.pilot.response_policy import (
    ANNOTATION_GUIDANCE, ANNOTATION_GUIDANCE_VERSION, AUXILIARY, BASES,
    STATUSES, agent_response_format, parse_auxiliary,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = json.loads((Path(__file__).parent / 'data/annotation-v1.3-live-packet.json').read_text())
CLAIM = {'statement': 'The cache may explain this issue', 'status': 'INFERRED',
         'evidence_ids': [], 'basis': 'independent'}


def envelope(claims):
    return canonical_json({'action': {'tool': 'list_files'}, 'claims': claims})


class AnnotationReadinessTests(unittest.TestCase):
    def saved_state(self, root):
        path = root / 'saved-trace.json'
        path.write_text(canonical_json(PACKET['trajectory']))
        return load_session(path, 'Archived functional issue')

    def trace_state(self, root, results=(), claims=()):
        raw = RawRun(root, 'adversarial'); recorder = Recorder(raw)
        recorder.emit('task', EventKind.USER_MESSAGE, 'user', {'content': 'Offline issue'})
        recorder.emit('policy', EventKind.ANNOTATION, 'response-validator',
                      {'type': 'response_policy', 'version': AUXILIARY})
        for n, payload in enumerate(results, 1):
            call = f'tool_{n}'; result = f'result_{n}'
            recorder.emit(call, EventKind.TOOL_CALL, 'predecessor', {'action': payload['action']})
            recorder.emit(result, EventKind.TOOL_RESULT, 'predecessor', payload, (call,))
        recorder.emit('response', EventKind.MODEL_RESPONSE, 'predecessor', {'text': envelope(list(claims))})
        raw.freeze()
        return load_session(raw.path, 'Offline issue')

    @staticmethod
    def tool_result(passed, file_hash='a' * 64):
        return {'action': {'tool': 'run_tests', 'test_ids': ['targeted']},
                'results': [{'id': 'targeted', 'passed': passed}],
                'source_hashes_before': {'module.py': file_hash},
                'source_hashes_after': {'module.py': file_hash}}

    def test_archived_fixture_text_evidence_and_provenance(self):
        events = {e['id']: e for e in PACKET['trajectory']['events']}
        for row in PACKET['rows']:
            self.assertEqual(hashlib.sha256(row['response_text'].encode()).hexdigest(), row['response_text_sha256'])
            payload = json.loads(events[f"predecessor_response_{row['call']:03d}"]['payload_json'])
            self.assertEqual(payload['text'], row['response_text'])
            result = json.loads(events[f"predecessor_result_{row['call']:03d}"]['payload_json'])
            self.assertEqual(result, row['tool_observable'])
            self.assertEqual(row['known_evidence_ids'], [f'predecessor_result_{n:03d}' for n in range(1, row['call'])])
            for provenance in row['provenance'].values():
                original = ROOT / provenance['source']
                if original.exists():  # Standalone fixture remains usable without ignored historical runs.
                    self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), provenance['sha256'])
        with tempfile.TemporaryDirectory() as t:
            _, _, trajectory = self.saved_state(Path(t))
            self.assertEqual(trajectory.sha256, PACKET['trajectory']['sha256'])

    def test_retrospective_old_and_proposed_contract_have_identical_counts(self):
        old, proposed = [], []
        for row in PACKET['rows']:
            known = set(row['known_evidence_ids'])
            report = parse_auxiliary(row['response_text'], known)['annotation_report']
            self.assertEqual(report, row['saved_annotation_report'])
            old.append(report['coverage'])
            # Prospective change is prompt guidance; parser and contract are unchanged.
            proposed.append(parse_output(row['response_text'], known, AUXILIARY,
                                         'flat-or-args/1.0')['annotation_report']['coverage'])
        self.assertEqual(old, proposed)
        self.assertEqual(sum(c['supplied'] for c in old), 8)
        self.assertEqual(sum(c['validated'] for c in old), 1)
        self.assertEqual(sum(c['rejected'] for c in old), 7)
        self.assertEqual(sum(c['rejected'] == 0 for c in old), 1)

    def test_guidance_is_prospective_without_schema_or_enum_widening(self):
        self.assertEqual(ANNOTATION_GUIDANCE_VERSION, 'annotation-guidance/1.0')
        self.assertEqual(BASES, ('tool', 'predecessor', 'independent'))
        frozen = json.loads((ROOT / 'configs/swebench-comparison-v1.3.json').read_text())
        self.assertEqual(digest(agent_response_format('4.0')['json_schema']['schema']), frozen['action_contract_sha256'])
        for rule in ('provenance class', 'not semantic truth', 'BEFORE the action', 'hypothesis',
                     'cite future results', 'claims:[]', 'code changes', 'independent verification'):
            self.assertIn(rule.lower(), ANNOTATION_GUIDANCE.lower())
        for line in ANNOTATION_GUIDANCE.splitlines():
            if line.startswith('{'):
                example = json.loads(line)
                self.assertEqual(parse_auxiliary(envelope([example]), {'result_read', 'result_test'})['claims'], [example])

    def test_all_existing_basis_and_status_values_remain_structurally_valid(self):
        for basis in BASES:
            for status in STATUSES:
                with self.subTest(basis=basis, status=status):
                    claim = {**CLAIM, 'basis': basis, 'status': status}
                    parsed = parse_auxiliary(envelope([claim]), set())
                    self.assertEqual(parsed['claims'], [claim])
                    self.assertFalse(parsed['annotation_report']['semantic_truth_verified'])

    def test_unknown_basis_values_and_types_are_never_mapped(self):
        bases = [json.loads(r['response_text'])['claims'][0]['basis'] for r in PACKET['rows'][1:]]
        for basis in [*bases, 'tool_result', 'observation', 'verified', '', None, 1, []]:
            with self.subTest(basis=basis):
                claim = {**CLAIM, 'basis': basis}
                report = parse_auxiliary(envelope([claim]), set())['annotation_report']
                self.assertEqual(report['coverage'], {'supplied': 1, 'validated': 0, 'rejected': 1})
                self.assertEqual(report['raw_claims'], [claim])
                self.assertEqual(report['diagnostics'][0]['raw_claim'], claim)
                self.assertEqual(report['diagnostics'][0]['annotation_information'], 'unknown')

    def test_unavailable_historical_future_or_non_result_references_reject(self):
        for refs in (['future_result'], ['predecessor_result_001'], ['user_issue'], ['gold_patch'], [7], 'result_1'):
            with self.subTest(refs=refs):
                claim = {**CLAIM, 'evidence_ids': refs, 'basis': 'predecessor'}
                report = parse_auxiliary(envelope([claim]), {'result_1'})['annotation_report']
                self.assertEqual(report['validated_claims'], [])
                self.assertTrue(any(e['field'] == 'evidence_ids' for e in report['diagnostics'][0]['errors']))
        valid = {**CLAIM, 'evidence_ids': ['result_1'], 'basis': 'tool'}
        self.assertEqual(parse_auxiliary(envelope([valid]), {'result_1'})['claims'], [valid])

    def test_missing_or_malformed_provenance_is_preserved_and_excluded(self):
        invalid = []
        for field in ('basis', 'evidence_ids', 'status', 'statement'):
            claim = dict(CLAIM); del claim[field]; invalid.append(claim)
        invalid += [{**CLAIM, 'source': 'invented'}, {**CLAIM, 'status': 'FACT'},
                    {**CLAIM, 'evidence_ids': [None]}, None]
        report = parse_auxiliary(envelope(invalid), set())['annotation_report']
        self.assertEqual(report['coverage']['rejected'], len(invalid))
        self.assertEqual(report['raw_claims'], invalid)
        self.assertEqual(report['validated_claims'], [])
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            parse_auxiliary('{"action":{},"claims":[{"statement":"x","status":"OBSERVED","evidence_ids":[],"basis":"tool","basis":"independent"}]}', set())

    def test_hypotheses_without_evidence_are_not_promoted(self):
        claims = [{**CLAIM, 'status': status} for status in ('INFERRED', 'UNCERTAIN', 'VERIFIED', 'OBSERVED')]
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), claims=claims)
        self.assertEqual(len(state['items']), 4)
        self.assertTrue(all(i['status'] == 'HYPOTHESIZED' for i in state['items']))
        self.assertTrue(all(i['scope']['files'] == {} for i in state['items']))
        self.assertEqual([i['declared_status'] for i in state['items']], [c['status'] for c in claims])

    def test_contradictory_model_claims_remain_unverified_interpretations(self):
        claims = [{**CLAIM, 'statement': statement, 'status': 'VERIFIED'}
                  for statement in ('The test passes', 'The test fails')]
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), claims=claims)
        self.assertEqual({i['text'] for i in state['items']}, {'The test passes', 'The test fails'})
        self.assertTrue(all(i['status'] == 'HYPOTHESIZED' for i in state['items']))
        self.assertTrue(all('conflicts_with' not in i for i in state['items']))

    def test_tool_failure_cannot_be_overridden_by_model_verified_label(self):
        claims = [{**CLAIM, 'statement': 'The targeted test passed', 'status': 'VERIFIED',
                   'evidence_ids': ['result_1'], 'basis': 'tool'}]
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), results=[self.tool_result(False)], claims=claims)
        model_item = next(i for i in state['items'] if i['text'] == 'The targeted test passed')
        self.assertEqual(model_item['status'], 'HYPOTHESIZED')
        observation = next(i for i in state['items'] if i.get('claim_key') == 'test:targeted')
        self.assertEqual(observation['status'], 'SUPPORTED_WITHIN_SCOPE')
        self.assertFalse(observation['claim_value'])
        self.assertTrue(any(i['status'] == 'REJECTED_SUPPORTED' for i in state['items']))

    def test_model_falsification_without_evidence_is_not_semantic_refutation(self):
        claim = {**CLAIM, 'status': 'FALSIFIED'}
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), claims=[claim])
        self.assertEqual(state['items'][0]['status'], 'REJECTED_UNSUPPORTED')
        self.assertEqual(state['items'][0]['evidence_ids'], [])

    def test_identical_scope_conflicting_test_results_remain_visible(self):
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), results=[self.tool_result(True), self.tool_result(False)])
        observations = [i for i in state['items'] if i.get('claim_key') == 'test:targeted']
        self.assertEqual([i['status'] for i in observations], ['SUPPORTED_WITHIN_SCOPE'] * 2)
        self.assertEqual(observations[0]['conflicts_with'], [observations[1]['id']])
        self.assertEqual(observations[1]['conflicts_with'], [observations[0]['id']])
        text, _ = compile_handoff(state, {'files': [], 'exclusions': []}, 8192)
        self.assertIn('CONFLICT', text)
        self.assertIn('passed', text); self.assertIn('failed', text)

    def test_changed_scope_supersedes_evidence_and_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.trace_state(Path(t), results=[self.tool_result(True), self.tool_result(False, 'b' * 64)])
        observations = [i for i in state['items'] if i.get('claim_key') == 'test:targeted']
        self.assertEqual(observations[0]['status'], 'SUPERSEDED')
        self.assertEqual(observations[0]['superseded_by'], observations[1]['id'])
        changed = compare_scope_hashes(observations[0], {'module.py': {'sha256': 'b' * 64}})
        self.assertTrue(changed['requires_revalidation'])
        self.assertEqual(changed['changed_paths'], ['module.py'])
        unchanged = compare_scope_hashes(observations[1], {'module.py': {'sha256': 'b' * 64}})
        self.assertFalse(unchanged['requires_revalidation'])
        unknown = compare_scope_hashes({'scope': {'files': {'module.py': None}}}, {})
        self.assertTrue(unknown['requires_revalidation'])
        self.assertEqual(unknown['unknown_paths'], ['module.py'])

    def test_rejected_claims_do_not_remove_real_archived_tool_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            state, archive, _ = self.saved_state(Path(t))
        self.assertEqual(state['extraction']['annotation_coverage'],
                         {'supplied': 8, 'validated': 1, 'rejected': 7, 'unparsed_responses': 0})
        self.assertEqual(state['checkpoint']['completed_tool_results'], 8)
        counts = Counter((i['category'], i['status']) for i in state['items'])
        self.assertEqual(counts[('observation', 'OBSERVED')], 6)
        self.assertEqual(counts[('change', 'OBSERVED')], 2)
        self.assertEqual(counts[('progress', 'OBSERVED')], 2)
        self.assertEqual(counts[('hypothesis', 'HYPOTHESIZED')], 1)
        text = '\n'.join(i['text'] for i in state['items'])
        for name in ('api.py', 'ledger.py', 'normalize.py', 'check_public.py', 'tests.json'):
            self.assertIn('Inspected ' + name, text)
        self.assertIn('PUBLIC_ACCEPTANCE passed 4 cases', text)
        rejected_statements = [json.loads(r['response_text'])['claims'][0]['statement'] for r in PACKET['rows'][1:]]
        self.assertFalse(any(i['text'] in rejected_statements for i in state['items']))
        for row in PACKET['rows']:
            self.assertTrue(any(json.loads(e['payload_json']).get('text') == row['response_text'] for e in archive['events']))

    def test_temporally_premature_archived_claims_are_not_observations(self):
        first, last = PACKET['rows'][0], PACKET['rows'][-1]
        first_claim = json.loads(first['response_text'])['claims'][0]
        self.assertEqual(first['known_evidence_ids'], [])
        self.assertEqual(first_claim['status'], 'OBSERVED')
        self.assertEqual(json.loads(last['response_text'])['claims'][0]['evidence_ids'], ['predecessor_result_007'])
        self.assertEqual(last['tool_observable']['action']['tool'], 'shell')
        self.assertNotIn('predecessor_result_008', last['known_evidence_ids'])
        with tempfile.TemporaryDirectory() as t:
            state, _, _ = self.saved_state(Path(t))
        first_item = next(i for i in state['items'] if i['text'] == first_claim['statement'])
        self.assertEqual(first_item['status'], 'HYPOTHESIZED')
        observed_tests = next(i for i in state['items'] if 'PUBLIC_ACCEPTANCE passed 4 cases' in i['text'])
        self.assertEqual(observed_tests['source_ids'], ['predecessor_result_008'])

    def test_wire_canonicalization_does_not_rewrite_annotations_or_raw_response(self):
        row = PACKET['rows'][0]; original = row['response_text']
        parsed = parse_output(original, set(), AUXILIARY, 'flat-or-args/1.0')
        original_action = json.loads(original)['action']
        canonical = canonicalize_action(parsed['action'], lambda action: None)
        self.assertEqual(canonical['canonical_action'], {'tool': 'list_files', 'limit': 100})
        self.assertTrue(canonical['canonicalization_occurred'])
        self.assertEqual(parsed['action'], original_action)
        self.assertEqual(parsed['annotation_report'], row['saved_annotation_report'])
        self.assertEqual(row['response_text'], original)


if __name__ == '__main__':
    unittest.main()
