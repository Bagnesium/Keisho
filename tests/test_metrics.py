from dataclasses import replace
import unittest

from keisho.agents.base import Message, ModelRequest, Usage
from keisho.agents.scripted import ScriptedModel
from keisho.core import ValidationError
from keisho.experiments.conditions import Condition, build_capsule
from keisho.experiments.manifest import RunOutcome, RunStatus
from keisho.logging.raw import EventKind, FrozenTrajectory
from keisho.metrics.calculations import calculate_metrics
from keisho.metrics.definitions import BehaviorMetric, CallPurpose, CallRecord, MetricAnnotation
from tests.fixtures import SCOPE, event, fixture


class MetricTests(unittest.TestCase):
    def setUp(self):
        predecessor, state = fixture()
        self.model = ScriptedModel(("final answer",))
        self.capsule = build_capsule(Condition.SUMMARY, predecessor, state, "normal summary", self.model, 10000)
        self.trajectory = FrozenTrajectory.create((
            event("request", EventKind.MODEL_REQUEST, "successor"),
            event("response", EventKind.MODEL_RESPONSE, "successor", parents=("request",)),
            event("inspect", EventKind.TOOL_CALL, "successor"),
            event("result", EventKind.TOOL_RESULT, "successor", parents=("inspect",)),
            event("attempt", EventKind.TOOL_CALL, "successor"),
            event("final", EventKind.FINAL_ANSWER, "successor"),
        ))
        self.calls = (CallRecord("call-1", CallPurpose.SUCCESSOR, self.model.model_id(), "request", "response", 0.5, Usage(10, 2, 2, "0.001", "fixture price")),)
        self.outcome = RunOutcome(RunStatus.TASK_FAILURE, False, "Hidden test failed", "fixture-grader/1")
        self.references = frozenset({"fact_01", "failure_01", "hypothesis_01"})

    def annotation(self, metric, target="inspect", positive=True, reference="fact_01"):
        return MetricAnnotation(metric, target, positive, (reference,), SCOPE, "Explicit reviewed rationale", "fixture annotator", "rubric/0.1.0")

    def report(self, annotations=(), calls=None, outcome=None):
        return calculate_metrics(self.trajectory, outcome or self.outcome, self.capsule, annotations, self.calls if calls is None else calls, 1.0, self.references)

    def test_raw_rates_denominators_steps_and_token_accounting(self):
        annotations = (
            self.annotation(BehaviorMetric.REDISCOVERY),
            self.annotation(BehaviorMetric.REDISCOVERY, "attempt", False),
            self.annotation(BehaviorMetric.REPEATED_FAILURE, "attempt", reference="failure_01"),
            self.annotation(BehaviorMetric.INHERITED_ERROR, "response", reference="hypothesis_01"),
            self.annotation(BehaviorMetric.CONTRADICTION, "final"),
        )
        report = self.report(annotations)
        self.assertFalse(report.task_success)
        self.assertEqual(report.post_handoff_steps, 3)
        self.assertEqual((report.rediscovery.numerator, report.rediscovery.denominator, report.rediscovery.value), (1, 2, 0.5))
        self.assertEqual(report.repeated_failure.value, 1.0)
        self.assertEqual(report.inherited_error.value, 1.0)
        self.assertEqual(report.contradiction.value, 1.0)
        self.assertEqual(report.handoff_tokens.count, 2)
        accounting = next(item for item in report.accounting if item.purpose == CallPurpose.SUCCESSOR)
        self.assertEqual((accounting.model_calls, accounting.input_tokens, accounting.output_tokens, accounting.cost_usd), (1, 10, 2, "0.001"))
        self.assertEqual(report.annotations, annotations)
        self.assertEqual(report.calls, self.calls)

    def test_no_opportunities_is_unknown_not_zero(self):
        report = self.report()
        self.assertIsNone(report.rediscovery.value)
        self.assertEqual(report.rediscovery.denominator, 0)
        for record in report.accounting:
            if record.purpose != CallPurpose.SUCCESSOR:
                self.assertFalse(record.coverage_complete)
                self.assertIsNone(record.cost_usd)

    def test_missing_usage_price_and_non_task_failure_remain_unknown(self):
        calls = (replace(self.calls[0], usage=Usage(None, 2)),)
        report = self.report(calls=calls, outcome=RunOutcome(RunStatus.INFRASTRUCTURE_FAILURE, None, "Grader crashed", "grader/1"))
        self.assertIsNone(report.task_success)
        accounting = next(item for item in report.accounting if item.purpose == CallPurpose.SUCCESSOR)
        self.assertIsNone(accounting.input_tokens)
        self.assertIsNone(accounting.cost_usd)

    def test_missing_call_duplicate_labels_and_unknown_references_rejected(self):
        annotation = self.annotation(BehaviorMetric.REDISCOVERY)
        for annotations in ((annotation, annotation), (replace(annotation, reference_ids=("unknown",)),), (replace(annotation, event_id="missing"),), (replace(annotation, reference_ids=()),), (replace(annotation, event_id="result"),)):
            with self.subTest(annotations=annotations), self.assertRaises(ValidationError):
                self.report(annotations)
        with self.assertRaises(ValidationError):
            self.report(calls=())

    def test_bad_usage_and_wrong_response_links_rejected(self):
        for usage in (Usage(-1, 2), Usage(10, 2, 11), Usage(10, 2, cost_usd="NaN", pricing_source="fixture"), Usage(10, 2, cost_usd="0.1")):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                usage.validate()
        with self.assertRaises(ValidationError):
            self.report(calls=(replace(self.calls[0], response_event_id="final"),))
        with self.assertRaises(ValidationError):
            self.report(calls=(replace(self.calls[0], response_event_id=None),))

    def test_scripted_counts_are_exact_only_for_synthetic_model(self):
        response = self.model.generate(ModelRequest((Message("user", "three word input"),), 42, 20, 0.0))
        self.assertEqual(response.resolved_model_id, "offline/scripted-whitespace-v1")
        self.assertEqual((response.usage.input_tokens, response.usage.output_tokens), (3, 2))
        self.assertEqual(self.model.count_tokens("").count, 0)
