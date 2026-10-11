"""Prospectively freeze one task, public input boundary, sources and cost plan.

Run with the dedicated SWE-bench venv. Answer-key fields never leave .cache.
"""
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    from keisho.agents.providers.openrouter_chat import validate_catalog, MODEL_PRICES
    from keisho.core import digest
    from keisho.local_env import load_project_env
    from swebench.task.repo import load_task_repo
    import pyarrow.parquet as pq
    c = json.loads((ROOT / 'configs/swebench-comparison-v1.json').read_text())
    private = ROOT / '.cache/swebench-evaluator'
    sources = private / 'sources'
    out = ROOT / 'runs/swebench-integration/preselection'
    out.mkdir(parents=True, exist_ok=False)
    rows = pq.read_table(private / 'verified.parquet').to_pylist()
    public = {r['instance_id']: {k: r[k] for k in
              ('instance_id', 'repo', 'base_commit', 'problem_statement', 'version', 'difficulty', 'created_at')}
              for r in rows}
    excluded = {i: 'setup-only smoke instance' if i == c['smoke_instance'] else 'outside published difficulty tiers'
                for i, r in public.items() if i == c['smoke_instance'] or r['difficulty'] not in c['selection']['difficulty']}
    order = sorted(set(public) - set(excluded))
    random.Random(c['selection']['seed']).shuffle(order)
    task = public[order[0]]
    (out / 'task.json').write_text(json.dumps(task, indent=2) + '\n')
    (out / 'selection.json').write_text(json.dumps({'rule': c['selection'], 'exclusions': excluded,
         'candidate_order': order, 'selected': [order[0]], 'model_outcomes_seen': False}, indent=2) + '\n')
    # Verify task-repo answer keys privately, without emitting answer content.
    wanted = [c['smoke_instance'], task['instance_id']]
    recipes = sources / ('swe-bench-tasks-' + c['task_repo_commit'])
    loaded = {r['instance_id']: r for r in load_task_repo(recipes, wanted)}
    checks = {}
    for row in rows:
        if row['instance_id'] not in wanted:
            continue
        check = {}
        for field in ('repo', 'base_commit', 'problem_statement', 'patch', 'test_patch', 'FAIL_TO_PASS', 'PASS_TO_PASS'):
            a, b = row[field], loaded[row['instance_id']][field]
            if field in ('FAIL_TO_PASS', 'PASS_TO_PASS'):
                a = json.loads(a) if isinstance(a, str) else a
                b = json.loads(b) if isinstance(b, str) else b
            check[field] = a == b
        checks[row['instance_id']] = check
    (out / 'dataset-recipe-crosscheck.json').write_text(json.dumps(checks, indent=2) + '\n')
    if not all(all(v.values()) for v in checks.values()):
        raise RuntimeError('pinned recipe and dataset differ; evaluator gate remains closed')
    catalog = {'models': json.loads((sources / 'provider-models.json').read_text())['data'],
               'endpoints': {k: json.loads((sources / f).read_text()) for k, f in
                [('openai/gpt-4.1-mini', 'provider-mini-endpoint.json'), ('openai/gpt-4.1', 'provider-successor-endpoint.json')]}}
    validate_catalog(catalog)
    cost = Decimal(0)
    parts = {}
    for role, count in [('predecessor', 1), ('successor', 5)]:
        budget = c[role + '_budgets']
        outputs = min(budget['total_tokens'], budget['model_calls'] * budget['output_tokens'])
        rates = MODEL_PRICES[c[role + '_model']]
        amount = Decimal('1.05') * ((budget['total_tokens'] - outputs) * rates[0] + outputs * rates[2]) / 1000000 * count
        parts[role] = str(amount)
        cost += amount
    rates = MODEL_PRICES[c['generation_model']]
    generation = Decimal('1.05') * c['generation_calls'] * (32000 * rates[0] + c['generation_output_tokens'] * rates[2]) / 1000000
    cost += generation
    parts['note_generation'] = str(generation)
    # Admission also requires one full per-request reservation in available funds.
    reserve = Decimal('1.05') * (32000 * Decimal('2') + 2048 * Decimal('8')) / 1000000
    plan = {'label': c['label'], 'config_sha256': digest(c), 'task_sha256': digest(task),
            'maximum_noncached_costs_usd': parts, 'total_envelope_usd': str(cost),
            'largest_request_reservation_usd': str(reserve), 'cap_usd': c['cap_usd'],
            'plausibly_fits': cost + reserve <= Decimal(c['cap_usd']),
            'assumptions': 'No cache discount; configured model rates; possible 5% BYOK fee; 2 note calls; no retries; unknown usage stops all calls.',
            'credential_presence': load_project_env(ROOT)['present'], 'catalog_sha256': digest(catalog),
            'branch_order': random.Random(c['branch_seed']).sample(c['conditions'], len(c['conditions'])),
            'checkpoint_uses_hidden_grades': False, 'agent_calls_so_far': 0}
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    (out / 'provider-catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    # Preserve unmodified, licensed author artifacts. Only pure signals.py is imported.
    author = sources / ('agent-handoff-debt-' + c['author_code_commit'])
    vendor = ROOT / 'src/keisho/benchmark/vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / '__init__.py').write_text('"""MIT-licensed author source; see LICENSE and provenance.json."""\n')
    paths = {'signals.py': 'src/handoff_debt/tracing/checkpoints/signals.py',
             'summary_summarizer.py.txt': 'src/handoff_debt/handoff/summary_summarizer.py',
             'structured_summarizer.py.txt': 'src/handoff_debt/handoff/structured_summarizer.py',
             'prompt_parts.py.txt': 'src/handoff_debt/handoff/prompt_parts.py', 'LICENSE': 'LICENSE'}
    hashes = {}
    for dest, source in paths.items():
        shutil.copyfile(author / source, vendor / dest)
        hashes[dest] = hashlib.sha256((vendor / dest).read_bytes()).hexdigest()
    (vendor / 'provenance.json').write_text(json.dumps({'repository': 'https://github.com/anjilab/agent-handoff-debt',
        'commit': c['author_code_commit'], 'files': paths, 'sha256': hashes,
        'adaptation': 'Keisho event mapping and tool protocol; no OpenHands runtime replacement. Generation uses first-pass author prompts without repair or automatic retry, 1600 output tokens, 2048 total rendered handoff tokens. Hidden continuation classification stays UNKNOWN.'}, indent=2) + '\n')
    # Extract prompt literals from the verified source AST, without importing its runtime.
    context = {'evidence_packet': '{evidence_packet}', 'source_change_rule': '', 'retry_rule': '',
       'STRUCTURED_FIELDS': ['problem_understanding', 'work_completed', 'evidence_observed',
       'observed_failures_or_error_evidence', 'remaining_uncertainty', 'rollback_notes', 'recommended_next_action'], 'json': json}
    prompts = {}
    for key in ('summary', 'structured'):
        tree = ast.parse((vendor / (key + '_summarizer.py.txt')).read_text())
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'completion_text')
        prompts[key] = eval(compile(ast.Expression(call.args[1]), '<pinned-author-prompts>', 'eval'), {'__builtins__': {}}, context)
    tree = ast.parse((vendor / 'prompt_parts.py.txt').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_takeover_context_prompt')
    prompts['takeover'] = eval(compile(ast.Expression(fn.body[0].value), '<pinned-author-prompts>', 'eval'), {'__builtins__': {}}, {})
    prompts['structured_fields'] = context['STRUCTURED_FIELDS']
    (vendor / 'prompts.json').write_text(json.dumps(prompts, indent=2) + '\n')
    print(json.dumps({'task': task['instance_id'], 'plan': plan, 'dataset_recipe_matches': True}, indent=2))


if __name__ == '__main__':
    main()
