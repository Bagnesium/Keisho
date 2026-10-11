"""Shared deterministic inspection classification; no script dependencies."""
import shlex


def information_action(action, files):
    """Prospectively conservative assessment; never executes or repairs a proposal."""
    tool = action['tool']
    if tool == 'read_file':
        return (action['path'] in files, 'read of existing public fixture contents' if action['path'] in files else 'file not in initial fixture')
    if tool != 'shell': return False, 'listing, writing or finishing does not gather new contents'
    command = action['command']
    if any(c in command for c in ';|&><`$\n\r'):
        return None, 'compound/expanding shell proposal not assessed as read-only'
    try: tokens = shlex.split(command)
    except ValueError: return None, 'unparseable shell proposal'
    if not tokens or tokens[0] not in ('cat', 'head', 'tail', 'grep', 'rg', 'sed'):
        return None, 'outside prospectively recognized read-only inspection commands'
    if not any(t in files for t in tokens[1:]): return False, 'does not target an existing fixture file'
    if any(t.startswith('/') or '..' in t.split('/') or '=' in t for t in tokens[1:]):
        return None, 'scope or mutation ambiguity'
    if any(t in ('-i', '--in-place', '--files', '-l', '--files-with-matches') or t.startswith('--in-place=') for t in tokens[1:]):
        return False, 'mutation or filename-only output does not qualify'
    if tokens[0] == 'sed':
        import re
        if any(t.startswith('-') and t not in ('-n','--') for t in tokens[1:]):
            return None, 'sed option could alter files or scope'
        scripts = [t for t in tokens[1:] if t not in files and not t.startswith('-')]
        if len(scripts) != 1 or not re.fullmatch(r'(?:\d+(?:,\d+|,\$)?)?p', scripts[0]):
            return None, 'sed program is not recognized as printing only'
    if tokens[0] in ('grep','rg') and any(t.startswith('-') and t not in ('-n','-H','-h','-i','-E','-F','-e','--') for t in tokens[1:]):
        return None, 'search option could change execution or file scope'
    if tokens[0] in ('cat', 'head', 'tail'):
        if any(t not in files and not t.startswith('-') and not t.isdigit() for t in tokens[1:]):
            return None, 'file scope not fully recognized'
    return True, 'targeted read-only fixture inspection; actual result not observed'

