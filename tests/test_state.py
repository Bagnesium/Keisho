from dataclasses import replace
import json
import unittest

from keisho.compiler.serializer import deserialize, serialize
from keisho.core import ValidationError, primitive
from keisho.state.extractor import extract_state
from keisho.state.provenance import EpistemicStatus as Status, SourceType, Verdict
from keisho.state.schema import Action, ActionOutcome, Change, Constraint, ConstraintKind, Importance, NextAction, Observation, OpenQuestion, PlanStep, Uncertainty, VerifiedFact
from keisho.state.validator import merge_states, validate_state
from tests.fixtures import fixture


class StateTests(unittest.TestCase):
    def setUp(self):
        self.trajectory, self.state = fixture()

    def test_round_trip_preserves_every_category_and_provenance(self):
        validate_state(self.state)
        self.assertEqual(deserialize(serialize(self.state)), self.state)
        self.assertEqual(extract_state(primitive(self.state), self.trajectory), self.state)
        self.assertEqual(json.loads(serialize(self.state))["current_plan"], [])

    def test_nonempty_categories_preserve_preferences_observations_and_plans(self):
        observed = replace(self.state.goal.provenance, source_ids=("tool_01",))
        uncertain = replace(observed, epistemic_status=Status.UNCERTAIN)
        inferred = replace(observed, epistemic_status=Status.INFERRED)
        state = replace(self.state,
            constraints=(Constraint(id="constraint", provenance=self.state.goal.provenance, statement="Prefer a small patch", kind=ConstraintKind.PREFERENCE, confidence=1.0),),
            observations=(Observation(id="observation", provenance=observed, statement="Regression command returned exit status 1", timestamp=self.state.created_at),),
            actions=(Action(id="action", provenance=observed, description="Run regression test", result="Exit status 1", outcome=ActionOutcome.FAILURE),),
            changes=(Change(id="change", provenance=observed, target="auth.py", change="Attempted database initialization change", reason="Test the current hypothesis"),),
            open_questions=(OpenQuestion(id="question", provenance=uncertain, question="Which metadata boundary is wrong?", importance=Importance.HIGH),),
            uncertainties=(Uncertainty(id="uncertainty", provenance=uncertain, statement="The root cause is unresolved", reason="No passing fix yet"),),
            current_plan=(PlanStep(id="plan", provenance=inferred, step="Inspect metadata handling"),),
            next_actions=(NextAction(id="next", provenance=inferred, action="Read auth.py", rationale="Inspect the failing path"),),
        )
        restored = deserialize(serialize(state))
        self.assertEqual(restored, state)
        self.assertEqual(restored.constraints[0].kind, ConstraintKind.PREFERENCE)
        self.assertEqual(restored.observations[0].provenance.epistemic_status, Status.OBSERVED)

    def test_incorrect_inference_stays_unverified(self):
        state = extract_state(primitive(self.state), self.trajectory)
        self.assertEqual(state.hypotheses[0].provenance.epistemic_status, Status.INFERRED)
        self.assertNotIn(state.hypotheses[0].statement, [fact.statement for fact in state.verified_facts])

    def test_no_inference_promotion_or_self_verification(self):
        hypothesis = self.state.hypotheses[0]
        fake_fact = VerifiedFact(id=hypothesis.id, statement=hypothesis.statement, provenance=replace(hypothesis.provenance, epistemic_status=Status.VERIFIED))
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, hypotheses=(), verified_facts=self.state.verified_facts + (fake_fact,)))
        bad_source = replace(self.state.sources[1], source_type=SourceType.MODEL_MESSAGE)
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, sources=(self.state.sources[0], bad_source) + self.state.sources[2:]))

    def test_dangling_wrong_claim_and_wrong_scope_evidence(self):
        for record in (replace(self.state.evidence[0], source_id="missing"), replace(self.state.evidence[0], claim_id="hypothesis_01"), replace(self.state.evidence[0], scope="different configuration")):
            with self.subTest(record=record), self.assertRaises(ValidationError):
                validate_state(replace(self.state, evidence=(record,) + self.state.evidence[1:]))

    def test_rejected_hypothesis_requires_refutation_scope_and_retry(self):
        rejection = self.state.rejected_hypotheses[0]
        for changed in (replace(rejection, retry_conditions=()), replace(rejection, provenance=replace(rejection.provenance, scope="")), replace(rejection, provenance=replace(rejection.provenance, epistemic_status=Status.VERIFIED))):
            with self.subTest(changed=changed), self.assertRaises(ValidationError):
                validate_state(replace(self.state, rejected_hypotheses=(changed,)))
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, evidence=(self.state.evidence[0], replace(self.state.evidence[1], verdict=Verdict.SUPPORTS), self.state.evidence[2])))

    def test_inconclusive_is_not_failure(self):
        attempt = replace(self.state.failed_attempts[0], outcome=ActionOutcome.INCONCLUSIVE)
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, failed_attempts=(attempt,)))
        valid = replace(self.state, failed_attempts=(attempt,), evidence=self.state.evidence[:2] + (replace(self.state.evidence[2], verdict=Verdict.INCONCLUSIVE),))
        validate_state(valid)
        self.assertEqual(deserialize(serialize(valid)).failed_attempts[0].outcome, ActionOutcome.INCONCLUSIVE)

    def test_merge_exact_duplicates_and_reject_conflicts(self):
        self.assertEqual(merge_states(self.state, self.state), self.state)
        changed = replace(self.state, hypotheses=(replace(self.state.hypotheses[0], confidence=0.1),))
        with self.assertRaises(ValidationError):
            merge_states(self.state, changed)
        with self.assertRaises(ValidationError):
            merge_states(self.state, replace(self.state, trajectory_sha256="b" * 64))

    def test_strict_input_types_versions_duplicate_keys(self):
        for mutate in (
            lambda data: data.update(memory="flattened"),
            lambda data: data.update(version="999"),
            lambda data: data["hypotheses"][0].update(confidence=True),
            lambda data: data["hypotheses"][0].update(confidence=float("nan")),
            lambda data: data["observations"].append({"statement": "missing metadata"}),
        ):
            data = primitive(self.state)
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValidationError):
                deserialize(json.dumps(data))
        with self.assertRaises(ValidationError):
            deserialize('{"version":"0.1.0","version":"999"}')

    def test_source_hash_kind_and_trajectory_binding(self):
        for state in (
            replace(self.state, trajectory_sha256="c" * 64),
            replace(self.state, sources=(replace(self.state.sources[0], sha256="d" * 64),) + self.state.sources[1:]),
            replace(self.state, sources=(replace(self.state.sources[0], source_type=SourceType.ANNOTATION),) + self.state.sources[1:]),
        ):
            with self.subTest(state=state), self.assertRaises(ValidationError):
                extract_state(primitive(state), self.trajectory)

    def test_conflicting_or_unlinked_evidence_cannot_look_verified(self):
        fact = self.state.verified_facts[0]
        refutation = replace(self.state.evidence[0], id="ev_conflict", verdict=Verdict.REFUTES)
        linked_fact = replace(fact, provenance=replace(fact.provenance, evidence_ids=fact.provenance.evidence_ids + (refutation.id,)))
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, evidence=self.state.evidence + (refutation,), verified_facts=(linked_fact,)))
        with self.assertRaises(ValidationError):
            validate_state(replace(self.state, evidence=self.state.evidence + (refutation,)))


if __name__ == "__main__":
    unittest.main()
