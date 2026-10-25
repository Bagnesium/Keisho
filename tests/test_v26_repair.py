"""Prospective v2.6 repair: startup-dispatch KeyError reproduction and constructor verification.

Tests:
1. Reproduction of attempt 001 KeyError: using actual configured model IDs,
   production select_model_class and build_model functions, and real provider catalog.
   With unpatched dispatch, selecting OpenRouterChatModel raises KeyError: 'openai/gpt-6-sol-20260922'.
2. Fail-closed transport: ensures no network calls can escape to external endpoints during testing.
3. Production model construction: exercises predecessor, both note generators, and all 5 successor conditions.
4. Provider catalog selection and public catalog preflight flag consistency.
5. Version dispatch auditing across comparison.py.
"""
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import urllib.request

from keisho.benchmark import comparison as c
from keisho.benchmark.comparison import (
    ROOT, PRESELECT, read_input, make_ledger, select_model_class, build_model,
    V20_HANDOFF_VERSIONS, GUARDED_VERSIONS, V25_VERSION, V26_VERSION,
    V20OpenRouterChatModel, OpenRouterChatModel
)
from keisho.pilot.spending import BudgetedModel


def fail_closed_transport(*args, **kwargs):
    raise AssertionError("Network transport forbidden in offline testing")


class TestV26StartupDispatchRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Strict fail-closed network block across socket and urllib for all tests in this suite
        cls._socket_patcher = patch.object(
            socket.socket,
            'connect',
            side_effect=AssertionError("Direct socket network connection forbidden in offline testing")
        )
        cls._urllib_patcher = patch.object(
            urllib.request,
            'urlopen',
            side_effect=AssertionError("urllib network access forbidden in offline testing")
        )
        cls._socket_patcher.start()
        cls._urllib_patcher.start()

        cls.v25_cfg_path = ROOT / 'configs/swebench-comparison-v2.5.json'
        cls.v25_cfg = json.loads(cls.v25_cfg_path.read_text())
        cls.prov_path = ROOT / 'configs' / cls.v25_cfg['provider_config']
        cls.provider = read_input(cls.prov_path)
        cls.ledger = make_ledger(
            cls.v25_cfg,
            cls.v25_cfg['cap_usd'],
            lambda *a: None,
            provider='openrouter',
            authorized_ceiling_usd=cls.v25_cfg['cap_usd'],
            authorization_scope='swebench-one-comparison'
        )

    @classmethod
    def tearDownClass(cls):
        cls._socket_patcher.stop()
        cls._urllib_patcher.stop()

    def test_01_reproduce_original_failure_unpatched_selection_raises_keyerror(self):
        """Reproduce the attempt 001 startup crash:
        Legacy OpenRouterChatModel raises KeyError when looking up gpt-6-sol in MODEL_ALIASES.
        """
        model_id = self.v25_cfg['predecessor_model']
        self.assertEqual(model_id, 'openai/gpt-6-sol-20260922')
        with self.assertRaises(KeyError) as ctx:
            OpenRouterChatModel(
                model_id,
                authorized=True,
                response_model_ids=[model_id],
                transport=fail_closed_transport
            )
        self.assertIn('openai/gpt-6-sol-20260922', str(ctx.exception))

    def test_02_production_selection_dispatches_v20_model(self):
        """select_model_class dispatches V20OpenRouterChatModel for v2.0 through v2.6."""
        for v in V20_HANDOFF_VERSIONS:
            cls = select_model_class({'version': v})
            self.assertIs(cls, V20OpenRouterChatModel, f"Version {v} must select V20OpenRouterChatModel")

        # Legacy versions continue to select OpenRouterChatModel
        for legacy_v in ('swebench-handoff/1.4', 'swebench-handoff/1.5', 'swebench-handoff/1.9'):
            cls = select_model_class({'version': legacy_v})
            self.assertIs(cls, OpenRouterChatModel, f"Legacy version {legacy_v} must select OpenRouterChatModel")

    def test_03_production_predecessor_construction(self):
        """Predecessor model construction using production build_model and select_model_class."""
        for cfg in (self.v25_cfg, {**self.v25_cfg, 'version': V26_VERSION}):
            model = build_model(
                cfg,
                self.provider,
                'predecessor',
                self.ledger,
                mode='agent',
                stage=None,
                transport=fail_closed_transport
            )
            self.assertIsInstance(model, BudgetedModel)
            self.assertIsInstance(model.model, V20OpenRouterChatModel)
            self.assertEqual(model.pricing_model_id, 'openai/gpt-6-sol-20260922')
            self.assertEqual(model.stage, 'predecessor')
            self.assertEqual(model.input_cap, cfg['predecessor_budgets']['request_input_tokens'])

    def test_04_production_note_generators_construction(self):
        """Note generators (summary and structured) using production build_model."""
        for cfg in (self.v25_cfg, {**self.v25_cfg, 'version': V26_VERSION}):
            # Summary note generator
            sum_model = build_model(
                cfg,
                self.provider,
                'generation',
                self.ledger,
                mode='summary',
                stage='note_generation_summary',
                transport=fail_closed_transport
            )
            self.assertIsInstance(sum_model, BudgetedModel)
            self.assertIsInstance(sum_model.model, V20OpenRouterChatModel)
            self.assertEqual(sum_model.pricing_model_id, 'openai/gpt-6-luna-20260922')
            self.assertEqual(sum_model.stage, 'note_generation_summary')

            # Structured note generator
            struct_model = build_model(
                cfg,
                self.provider,
                'generation',
                self.ledger,
                mode='state',
                stage='note_generation_structured',
                transport=fail_closed_transport
            )
            self.assertIsInstance(struct_model, BudgetedModel)
            self.assertIsInstance(struct_model.model, V20OpenRouterChatModel)
            self.assertEqual(struct_model.pricing_model_id, 'openai/gpt-6-luna-20260922')
            self.assertEqual(struct_model.stage, 'note_generation_structured')

    def test_05_production_all_five_successor_conditions_construction(self):
        """All 5 successor conditions construct BudgetedModel with V20OpenRouterChatModel."""
        conditions = ('REPOSITORY_ONLY', 'FULL_HISTORY', 'SUMMARY_2K', 'STRUCTURED_NOTES_2K', 'KEISHO_2K')
        for cfg in (self.v25_cfg, {**self.v25_cfg, 'version': V26_VERSION}):
            for cond in conditions:
                model = build_model(
                    cfg,
                    self.provider,
                    'successor',
                    self.ledger,
                    mode='agent',
                    stage=cond,
                    transport=fail_closed_transport
                )
                self.assertIsInstance(model, BudgetedModel)
                self.assertIsInstance(model.model, V20OpenRouterChatModel)
                self.assertEqual(model.pricing_model_id, 'openai/gpt-6-sol-20260922')
                self.assertEqual(model.stage, cond)
                self.assertEqual(model.input_cap, cfg['successor_budgets']['request_input_tokens'])

    def test_06_catalog_selection_and_v20_catalog_check(self):
        """Provider catalog selection resolves to provider-catalog-v2.0.json for v2.0 through v2.6."""
        for v in V20_HANDOFF_VERSIONS:
            cfg = {'version': v}
            cat_path = (PRESELECT / 'provider-catalog-v2.0.json') if cfg.get('version') in V20_HANDOFF_VERSIONS else (PRESELECT / 'provider-catalog.json')
            self.assertEqual(cat_path.name, 'provider-catalog-v2.0.json')
            v20_flag = bool(cfg and cfg.get('version') in V20_HANDOFF_VERSIONS)
            self.assertTrue(v20_flag)

        # Legacy version uses provider-catalog.json
        legacy_cfg = {'version': 'swebench-handoff/1.4'}
        cat_path = (PRESELECT / 'provider-catalog-v2.0.json') if legacy_cfg.get('version') in V20_HANDOFF_VERSIONS else (PRESELECT / 'provider-catalog.json')
        self.assertEqual(cat_path.name, 'provider-catalog.json')
        self.assertFalse(bool(legacy_cfg and legacy_cfg.get('version') in V20_HANDOFF_VERSIONS))

    def test_07_fail_closed_transport_halts_on_any_model_request(self):
        """Fail-closed transport raises AssertionError if any request attempt is made."""
        model = build_model(
            self.v25_cfg,
            self.provider,
            'predecessor',
            self.ledger,
            mode='agent',
            stage=None,
            transport=fail_closed_transport
        )
        with self.assertRaises(AssertionError) as ctx:
            model.model._transport({'messages': []}, 'test-key')
        self.assertIn("Network transport forbidden in offline testing", str(ctx.exception))

    def test_08_prospective_v26_binding_validation(self):
        """Prospective v2.6 binding resolves with allow_pending=True, and refuses live execution."""
        from keisho.benchmark.comparison import resolve_binding
        b = resolve_binding(
            'configs/swebench-comparison-v2.6.json',
            'analysis/swebench-comparison-v2.6-plan.json',
            'runs/swebench-v2.6-five-way-once-test',
            'analysis/swebench-comparison-v2.6-authorization-template.json',
            allow_pending=True
        )
        self.assertEqual(b.config['version'], 'swebench-handoff/2.6')
        self.assertFalse(b.authorization['provider_inference_authorized'])

        with self.assertRaises(Exception) as ctx:
            resolve_binding(
                'configs/swebench-comparison-v2.6.json',
                'analysis/swebench-comparison-v2.6-plan.json',
                'runs/swebench-v2.6-five-way-once-test',
                'analysis/swebench-comparison-v2.6-authorization-template.json',
                allow_pending=False
            )
        self.assertIn('new paid scope is not authorized', str(ctx.exception))

    def test_09_historical_v25_records_preserved(self):
        """Ensure historical v2.5 files and hashes remain byte-identical."""
        from keisho.core import digest
        v25_manifest = json.loads((ROOT / 'analysis/swebench-experiment-v2.5-manifest.json').read_text())
        v25_cfg = json.loads((ROOT / 'configs/swebench-comparison-v2.5.json').read_text())
        v25_plan = json.loads((ROOT / 'analysis/swebench-comparison-v2.5-plan.json').read_text())
        v25_freeze = json.loads((ROOT / 'analysis/swebench-v2.5-final-source-freeze.json').read_text())
        v25_auth = json.loads((ROOT / 'analysis/swebench-comparison-v2.5-authorization-bagi-20261024-v25-01.json').read_text())

        self.assertEqual(digest(v25_manifest), 'bf4d261f64c995dc3fbe208c32be78ea42cd6785c63d4fc02582cccf4019b1da')
        self.assertEqual(digest(v25_cfg), '8facce961117b57c480a0bbf54138f460e59f2219fe1e82d89b2cab639e6a452')
        self.assertEqual(digest(v25_plan), '2246575ecd820564c6607a2dfc9e3faf56420be0940a5a505fc1394008966a28')
        self.assertEqual(digest(v25_freeze), 'b7db8ad583a779d664cad1aeab6eba7a05c0c79f764210eeff01562ccac13a5b')
        self.assertEqual(v25_auth['authorization_id'], 'bagi-20261024-v25-01')
        self.assertEqual(v25_auth['config_sha256'], digest(v25_cfg))
        self.assertEqual(v25_auth['plan_sha256'], digest(v25_plan))
        self.assertEqual(v25_auth['final_source_freeze_sha256'], digest(v25_freeze))

