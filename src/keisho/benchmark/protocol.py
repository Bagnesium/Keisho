"""Author signal reuse plus an explicit completed-result interpretation."""
import json
from pathlib import Path
import re
import shlex

from keisho.core import require
from .vendor.signals import is_source_file, validation_command

BUILD = re.compile(r'\b(?:build|lint|compileall|check|verify|validate)\b', re.I)
PROMPTS = Path(__file__).parent / 'vendor/prompts.json'


def is_repo_bin_test(tok):
    """Check if token refers to a repository-local bin/test runner (e.g. SymPy).

    Accepts:
      - 'bin/test'
      - './bin/test'
      - '/testbed/bin/test' (standard SWE-bench repo worktree root)

    Rejects:
      - 'test' (shell builtin or generic command)
      - '/usr/bin/test', '/bin/test' (POSIX system test utilities)
    """
    try:
        p = Path(tok)
    except Exception:
        return False
    if not p.is_absolute() and p.parts == ('bin', 'test'):
        return True
    if p.as_posix() in ('/testbed/bin/test', './bin/test', 'bin/test'):
        return True
    return False


def completed_validation_command(command):
    """Author signals, narrowed to executed command heads (not echo/read output).

    Shell compounds are eligible if a recognized validation command is a head;
    overall process exit/output is retained without claiming individual test passes.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|()')
        lexer.whitespace_split = True
        parts, current = [], []
        for token in lexer:
            if token and all(c in ';&|()' for c in token):
                if current:
                    parts.append(current)
                    current = []
            else:
                current.append(token)
        if current:
            parts.append(current)
    except ValueError:
        return False
    for tokens in parts:
        while tokens and re.fullmatch(r'[A-Za-z_]\w*=.*', tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            continue
        head = Path(tokens[0]).name
        rest = ' '.join(tokens[1:])
        if head in ('pytest', 'tox', 'nox', 'ruff', 'mypy', 'pylint', 'flake8'):
            return True
        if is_repo_bin_test(tokens[0]):
            return True
        if head in ('python', 'python3') and (
            (len(tokens) > 1 and is_repo_bin_test(tokens[1])) or
            (rest.startswith('-m ') and rest.split()[1] in ('pytest', 'unittest', 'compileall', 'build')) or
            (tokens[1:2] and re.search(r'(repro|reproduce|check|verify|validate|test).*\.py$', tokens[1])) or
            (tokens[1:3] in (['setup.py', 'build'], ['setup.py', 'check']))
        ):
            return True
        if head in ('make', 'npm', 'pnpm', 'yarn', 'cargo', 'go', 'gradle', 'mvn') and any(t in ('test', 'build', 'lint', 'check') for t in tokens[1:]):
            return True
    return False


class ValidationCheckpoint:
    def __init__(self):
        self.source_edit_seen = False
        self.first_edit = None
        self.completed = 0
        self.checkpoint = None

    def __call__(self, action, result):
        self.completed += 1
        preceding_source_edit = self.source_edit_seen
        # Only completed-boundary byte/mode changes are observable. If the first
        # edit and validation share one shell action, their order is unknown;
        # that action records the edit but a subsequent validation must qualify.
        paths = result.get('changed_paths', [])
        if any(is_source_file(p) for p in paths):
            self.source_edit_seen = True
            self.first_edit = self.first_edit or self.completed
        command = action.get('command', '')
        recognized = completed_validation_command(command)
        # Checkpoint is an empirical boundary marking when predecessor work ends
        # and successor takeover begins. A completed validation command execution
        # (with integer exit code, e.g. 0, 1, or other) qualifies as completed validation;
        # exit code is recorded in the checkpoint record without requiring tests to pass.
        if preceding_source_edit and action.get('tool') == 'shell' and recognized and type(result.get('exit_code')) is int:
            self.checkpoint = {'rule': 'after_first_validation_result', 'completed_action': self.completed,
                               'first_source_edit_action': self.first_edit, 'command': command,
                               'exit_code': result['exit_code'], 'uses_hidden_grades': False}
            return True
        return False


def deterministic_fields(events, changed_paths, adapter_version='structured-adapter/1.0'):
    require(adapter_version in ('structured-adapter/1.0', 'structured-adapter/1.1'), 'unsupported notes adapter')
    latest_edit = -1
    latest = None
    observed_artifacts = set()
    for n, event in enumerate(events):
        if event.kind.value != 'tool_result':
            continue
        r = json.loads(event.payload_json)
        observed_artifacts.update(p for p in r.get('changed_paths', []) if not is_source_file(p))
        if any(is_source_file(p) for p in r.get('changed_paths', [])):
            latest_edit = n
        a = r.get('action', {})
        command = a.get('command', '')
        if a.get('tool') == 'shell' and completed_validation_command(command):
            latest = (n, command, r.get('exit_code'), r.get('output', ''))
    fields = {'repository_change_state': 'changes present' if changed_paths else 'no changes observed',
            'changed_source_files': [p for p in changed_paths if is_source_file(p)],
            'non_source_artifacts_observed': [p for p in changed_paths if not is_source_file(p)],
            'validation_outcome_after_latest_source_change':
                ('exit code ' + str(latest[2])) if latest and latest[0] > latest_edit else 'UNKNOWN',
            'latest_predecessor_validation_command': latest[1] if latest else 'UNKNOWN',
            'latest_validation_evidence': ((('Earlier output omitted; last 2000 characters:\n' if len(latest[3]) > 2000 else '') + latest[3][-2000:]) if latest else 'UNKNOWN'),
            'continuation_state_label': 'UNKNOWN; official classification withheld from handoff'}
    if adapter_version == 'structured-adapter/1.1':
        fields['non_source_artifacts_observed'] = sorted(observed_artifacts | set(fields['non_source_artifacts_observed']))
        source = fields['changed_source_files']
        after_edit = latest and latest[0] > latest_edit and latest_edit >= 0
        fields['repository_change_state'] = 'source changes present' if source else 'no source changes observed'
        fields['continuation_state_label'] = ('source-change-needs-verification' if source else 'no-source-change-work-observed')
        if source and after_edit:
            fields['continuation_state_label'] = ('source-change-validated-by-predecessor' if latest[2] == 0 else
                                                  'source-change-with-failing-validation' if type(latest[2]) is int else 'source-change-needs-verification')
        if not after_edit:
            fields['validation_outcome_after_latest_source_change'] = 'UNKNOWN'
            fields['latest_predecessor_validation_command'] = 'NONE OBSERVED'
            fields['latest_validation_evidence'] = 'NONE OBSERVED'
    return fields


def generation_messages(kind, evidence, adapter_version='structured-adapter/1.0', deterministic=None):
    require(adapter_version in ('structured-adapter/1.0', 'structured-adapter/1.1'), 'unsupported notes adapter')
    data = json.loads(PROMPTS.read_text())
    require(kind in ('summary', 'structured'), 'unsupported note generation')
    messages = [{**m, 'content': m['content'].replace('{evidence_packet}', evidence)} for m in data[kind]]
    messages[1]['content'] += '\nRendered handoff must fit 2048 native tokens including all fields. Preserve useful evidence and uncertainty within that budget.'
    if adapter_version == 'structured-adapter/1.1' and kind == 'structured' and (deterministic or {}).get('changed_source_files'):
        # Restore the author's conditional first-pass rule omitted by the original
        # AST prompt extraction. No author retries or semantic rewriting are added.
        messages[1]['content'] += ('\nThe repository state facts list changed source files. work_completed must acknowledge predecessor source changes; '
                                 'do not say no fix or no code changes were implemented. Do not say the implementation remains; '
                                 'recommend verification of the current changes before any further edits.')
    return messages


def render_structured(fields, deterministic):
    data = json.loads(PROMPTS.read_text())
    require(set(fields) == set(data['structured_fields']) and all(isinstance(v, str) and v.strip() for v in fields.values()), 'invalid structured notes schema')
    return 'Historical structured notes; verify against the repository.\n' + json.dumps(
        {'deterministic_continuation_state': deterministic, 'predecessor_notes': fields}, ensure_ascii=False, indent=2)
