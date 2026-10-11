"""Offline regression suite excluding functional/comparison execution fixtures."""
import json
import socket
import unittest
from urllib.request import OpenerDirector


def no_network(*args, **kwargs):
    raise AssertionError('offline verification attempted network I/O')


OpenerDirector.open = no_network
socket.create_connection = no_network
excluded_prefixes = ('tests.test_benchmark_real_offline.', 'tests.test_functional_public.')
excluded_names = {
    'tests.test_benchmark_launcher.LauncherTests.test_full_cli_downstream_binding_with_offline_provider_evaluator',
    'tests.test_response_measurements.ResponseMeasurementTests.test_prepared_execution_path_uses_real_loop_and_archives_before_adapter',
}
selected = unittest.TestSuite(); excluded = []


def add(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            add(test)
        elif test.id().startswith(excluded_prefixes) or test.id() in excluded_names:
            excluded.append(test.id())
        else:
            selected.addTest(test)


add(unittest.defaultTestLoader.discover('tests', top_level_dir='.'))
print(json.dumps({'selected_tests':selected.countTestCases(),
                  'excluded_execution_fixtures':excluded,
                  'reason':'User forbids functional confirmation reruns and SWE-bench/comparison execution. Pure offline unit/admission tests retained.',
                  'provider_network_guard':True}), flush=True)
result = unittest.TextTestRunner(verbosity=2).run(selected)
raise SystemExit(0 if result.wasSuccessful() else 1)
