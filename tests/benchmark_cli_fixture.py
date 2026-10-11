"""Test-only dependency injection around the actual public CLI; no network."""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

from keisho.agents.scripted import ScriptedModel
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel, MODEL_ALIASES, MODEL_PRICES
from keisho.benchmark import comparison as c
from keisho.benchmark.environment import RepositorySession
from keisho.benchmark.evaluator import unique_run_id


class Counter:
    count = ScriptedModel().count_tokens


class OfflineProvider(OpenRouterChatModel):
    def __init__(self, identity, **kwargs):
        kwargs.update(api_key='offline-fixture-key', transport=self.transport)
        super().__init__(identity, **kwargs)
        self.number = 0

    def transport(self, body, key):
        self.number += 1
        if self._mode == 'summary':
            text = 'Predecessor changed pkg/api.py and completed fixture compilation. Verify the current repository before continuing.'
        elif self._mode == 'state':
            text = json.dumps({k: 'Fixture evidence only; verify current changes.' for k in json.loads(c.PROMPTS.read_text())['structured_fields']})
        else:
            assert body['response_format']['type'] == 'json_schema'
            assert body['response_format']['json_schema']['name'] == 'keisho_agent_response_v2'
            if 'mini' in self.model_id():
                action = ({'tool': 'write_file', 'path': 'pkg/api.py', 'content': 'fixture = 1\n'} if self.number == 1
                          else {'tool': 'shell', 'command': 'python -m compileall pkg'})
            else:
                action = {'tool': 'finish', 'answer': 'OFFLINE FIXTURE ONLY'}
            text = json.dumps({'action': action, 'claims': []})
        inputs = sum(self.count_tokens(m['content']).count for m in body['messages'])
        outputs = self.count_tokens(text).count
        rates = MODEL_PRICES[self.model_id()]
        cost = str((inputs * rates[0] + outputs * rates[2]) / Decimal(1000000))
        return {'model': MODEL_ALIASES[self.model_id()], 'provider': 'OpenAI',
                'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': inputs, 'completion_tokens': outputs, 'prompt_tokens_details': {'cached_tokens': 0},
                          'cost': cost, 'is_byok': False, 'cost_details': {'upstream_inference_cost': cost}}}, 'offline-request'


class Session:
    saved = {}
    validate_action = RepositorySession.validate_action
    def __init__(self, image, *, audit=None, timeout=120, output_bytes=49152):
        self.files = dict(self.saved.get(image, {}))
        self.output_bytes, self.timeout = output_bytes, timeout
        self.audit = audit
    def inventory(self):
        return {p: {'sha256': hashlib.sha256(v.encode()).hexdigest(), 'mode': 420} for p,v in self.files.items()}
    def initialize_base(self, base):
        assert base == 'cc183652bf6e1273e985e1c4b3cba79c896c1193'
        self.base_inventory = self.inventory(); return self.base_inventory
    def execute(self, action):
        self.validate_action(action)
        changed = []
        if action['tool'] == 'write_file':
            self.files[action['path']] = action['content']; changed = [action['path']]
        return {'benchmark_observable': True, 'action': action, 'changed_paths': changed,
                'exit_code': 0, 'output': 'offline fixture compilation completed',
                'source_hashes_after': {p:v['sha256'] for p,v in self.inventory().items()}}
    def patch(self, base):
        return 'diff --git a/pkg/api.py b/pkg/api.py\n+fixture = 1\n'
    def freeze(self):
        image = 'sha256:' + 'b' * 64; self.saved[image] = dict(self.files)
        return image, self.inventory()
    def close(self): pass


def main():
    mode, temporary, *args = sys.argv[1:]
    temporary = Path(temporary)
    real_resolve = c.resolve_binding
    image = json.loads((c.PRIVATE / 'prepared-task-image.json').read_text())
    provider = json.loads((c.ROOT / 'configs/calibration-task001-openrouter-v1.2.0.yaml').read_text())
    def preflight(binding, **kwargs):
        return {'setup': {'status': 'resolved', 'software_fixture_only': True}, 'provider': provider,
                'ca': None, 'native': Counter(), 'image_metadata': image, 'credential_presence': {'OPENROUTER_API_KEY': True}}
    def resolve(*args, **kwargs):
        # Bind owned guard storage before admission, not only at claim time.
        # A completed real authorization must neither admit nor block this
        # offline fixture. All input/scientific checks still use real_resolve.
        return replace(real_resolve(*args, **kwargs), authorization_guard=temporary / 'test-authorization-claim')
    def evaluator(private, config, task, condition, prediction, **kwargs):
        assert Path(prediction).parent.name == kwargs['run_namespace']
        return {'status': 'unresolved', 'run_id': unique_run_id(task['instance_id'], condition, Path(prediction).read_text(), kwargs['run_namespace']),
                'software_fixture_only': True}
    def docker(*args):
        from types import SimpleNamespace
        assert args[:2] == ('image', 'inspect')
        return SimpleNamespace(stdout=json.dumps([{'Id': image['image_id']}]).encode())
    def no_public(*args):
        if mode == 'dry': raise AssertionError('dry-run must not request public metadata')
        return {'software_fixture_only': True}
    def no_client(*args, **kwargs):
        raise AssertionError('dry-run must not instantiate a provider client')
    sys.argv = [str(c.ROOT / 'scripts/benchmark_compare.py'), *args]
    with patch.object(c, 'runtime_preflight', preflight), patch.object(c, 'check_public_catalog', no_public), \
         patch.object(c, 'resolve_binding', resolve), patch.object(c, 'OpenRouterChatModel', no_client if mode == 'dry' else OfflineProvider), \
         patch.object(c, 'NativeTokenizer', Counter), patch.object(c, 'RepositorySession', Session), \
         patch.object(c, 'docker', docker), patch.object(c, 'evaluate', evaluator):
        runpy.run_path(str(c.ROOT / 'scripts/benchmark_compare.py'), run_name='__main__')


if __name__ == '__main__': main()
