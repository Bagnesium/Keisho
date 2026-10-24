"""Offline tests for the proposed v2.2 STRUCTURED_NOTES_2K guarded reader (no network, no models)."""
import inspect
import json
import unittest

from keisho.benchmark import comparison as c
from keisho.benchmark.notes_reader import read_structured_notes
from keisho.core import ValidationError

FIELDS = json.loads(c.PROMPTS.read_text())['structured_fields']
NOTES = {k: 'value for ' + k for k in FIELDS}
OBJ = json.dumps(NOTES)


class NotesReader(unittest.TestCase):
    def ok(self, text):
        data, framing = read_structured_notes(text, FIELDS)
        self.assertEqual(data, NOTES)
        return framing

    def bad(self, text, pattern):
        with self.assertRaisesRegex(ValidationError, pattern):
            read_structured_notes(text, FIELDS)

    def test_bare_object(self):
        f = self.ok(OBJ)
        self.assertFalse(f['has_framing'])

    def test_prose_prefixed_and_suffixed(self):
        f = self.ok('Here are the notes, as "requested":\n\n' + OBJ + '\n\nHope this helps.')
        self.assertTrue(f['has_framing'])
        self.assertEqual(f['stripped_leading'], 'Here are the notes, as "requested":\n\n')
        self.assertEqual(f['stripped_trailing'], '\n\nHope this helps.')

    def test_fenced_with_and_without_tag_and_prose(self):
        f = self.ok('Notes:\n```json\n' + OBJ + '\n```\nDone.')
        self.assertTrue(f['is_fenced'] and f['has_framing'])
        self.assertFalse(self.ok('```\n' + OBJ + '\n```')['has_framing'])

    def test_braces_inside_string_values_allowed(self):
        notes = dict(NOTES, work_completed='edited f() { return [1] }')
        data, _ = read_structured_notes('x ' + json.dumps(notes), FIELDS)
        self.assertEqual(data, notes)

    def test_malformed(self):
        self.bad(OBJ[:-1], 'malformed outer JSON')
        self.bad('Prose ' + OBJ[:-1], 'malformed outer JSON')
        self.bad('```json\n' + OBJ[:-1] + '\n```', 'malformed JSON inside code fence')

    def test_ambiguous_multiple_candidates(self):
        self.bad(OBJ + '\n' + OBJ, 'ambiguous')
        self.bad('First ' + OBJ + ' or maybe {"x": 1}', 'ambiguous')
        self.bad('```json\n' + OBJ + '\n```\n```json\n' + OBJ + '\n```', 'exactly one code block')
        self.bad(OBJ + '\n```json\n' + OBJ + '\n```', 'ambiguous')
        self.bad('```json\n' + OBJ + '\n' + OBJ + '\n```', 'ambiguous trailing')
        self.bad('[' + OBJ + ']', 'ambiguous')
        self.bad('{"notes": ' + OBJ + '}', 'schema fields differ')  # no nested salvage

    def test_duplicate_keys(self):
        self.bad(OBJ[:-1] + ', "work_completed": "again"}', 'duplicate JSON key: work_completed')
        self.bad('```json\n' + OBJ[:-1] + ', "rollback_notes": "x"}\n```', 'duplicate')

    def test_nonfinite(self):
        for const in ('NaN', 'Infinity', '-Infinity'):
            self.bad(OBJ[:-1] + ', "x": ' + const + '}', 'non-JSON numeric constant: ' + const)

    def test_schema_violations(self):
        self.bad(json.dumps({k: v for k, v in NOTES.items() if k != 'rollback_notes'}), 'missing')
        self.bad(json.dumps(dict(NOTES, extra='x')), 'extra')
        self.bad(json.dumps(dict(NOTES, work_completed='  ')), 'non-empty string: work_completed')
        self.bad(json.dumps(dict(NOTES, work_completed=3)), 'non-empty string')
        self.bad('"just a string"', 'no JSON object|ambiguous')

    def test_prose_only_and_empty(self):
        self.bad('I could not produce notes.', 'prose only')
        self.bad('', 'prose only')


class Wiring(unittest.TestCase):
    def test_v22_uses_guarded_reader_and_logs_without_retry(self):
        src = inspect.getsource(c.make_handoffs)
        self.assertTrue("config.get('version') == 'swebench-handoff/2.2'" in src
                        or "config.get('version') in ('swebench-handoff/2.2', V23_VERSION)" in src
                        or "config.get('version') in ('swebench-handoff/2.2', V23_VERSION, V24_VERSION)" in src
                        or "config.get('version') in ('swebench-handoff/2.2', V23_VERSION, V24_VERSION, V25_VERSION)" in src)
        self.assertIn('read_structured_notes(response.text, fields)', src)
        self.assertIn("'-stripped-framing.json'", src)
        self.assertIn("'automatic_retry': False", src)
        self.assertEqual(src.count('logged_generate('), 1)  # one call per note kind, no retry loop

    def test_summary_path_has_no_json_parsing(self):
        src = inspect.getsource(c.make_handoffs)
        block = src[src.index("if kind == 'summary':"):src.index('else:', src.index("if kind == 'summary':"))]
        self.assertNotIn('json.loads', block)


if __name__ == '__main__':
    unittest.main()
