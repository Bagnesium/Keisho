"""Interpreter-level test injection. Never installed or imported by production.

Loaded only when tests explicitly add this directory to PYTHONPATH. The actual
public script executes normally; injection replaces provider transport and host
fixture paths at main(), never the parser, agent loop or Docker tools.
"""
import json
import os
from pathlib import Path
import sys

settings_path = os.environ.get('KEISHO_TEST_LAUNCH_SETTINGS')
if settings_path:
    settings = json.loads(Path(settings_path).read_text())
    def trace(frame, event, arg):
        if event == 'call' and frame.f_code.co_name == 'main' and Path(frame.f_code.co_filename).resolve() == Path(settings['public_entry']).resolve():
            sys.settrace(None)
            if settings.get('kind') == 'benchmark_v27':
                from rehearsal_v27_injection import inject
            elif settings.get('kind') == 'benchmark_v26':
                from rehearsal_v26_injection import inject
            elif settings.get('kind') == 'benchmark':
                from benchmark_injection import inject
            else:
                from functional_injection import inject
            inject(frame.f_globals, settings)
        return trace
    sys.settrace(trace)
