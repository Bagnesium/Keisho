import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from keisho.core import canonical_json,digest,utc_now
from keisho.handoff.bundle import inspect,pack,resume,validate
from keisho.handoff.compact import Counter,compile_handoff
from keisho.handoff.session import load_session
from keisho.logging.raw import Event,EventKind,RawRun
from keisho.pilot.tasks import REPO


class LocalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.repo=self.root/"working repo 日本";self.repo.mkdir()
        (self.repo/"module.py").write_text("value = 1\n")
        (self.repo/"settings.json").write_text('{"mode":"old"}\n')
        self.notes=self.root/"notes.json"
        self.notes.write_text(json.dumps({"version":"keisho-notes/1.0","acceptance":["Old and new callers pass integration checks"],
            "constraints":["Preserve the existing API and do not publish"],"sources":[{"id":"note-1","text":"I inspected parser and service; integration has not run"}],
            "items":[{"id":"hyp","category":"hypothesis","text":"The cache probably accepts the new representation", "status":"SUPPORTED_WITHIN_SCOPE",
                      "source_ids":["note-1"],"scope":{"files":{"settings.json":hashlib.sha256((self.repo/"settings.json").read_bytes()).hexdigest()},"environment":"mode=old; dependencies unknown"}},
                     {"id":"retry","category":"failed_approach","text":"A new-format-only parser rejected old callers","status":"REJECTED_SUPPORTED","source_ids":["missing"],
                      "scope":{"files":{"module.py":hashlib.sha256((self.repo/"module.py").read_bytes()).hexdigest()},"environment":"legacy clients"},
                      "retry_when":["After all callers migrate and compatibility requirements change"]}]}))

    def command(self,*args):
        result=subprocess.run([str(REPO/"keisho"),*map(str,args)],capture_output=True,text=True,cwd=REPO)
        return result

    def bundle(self):
        return pack(self.repo,self.notes,"Finish configuration migration",self.root/"bundle")[0]

    def test_real_cli_dirty_workspace_staged_unstaged_deleted_binary_unicode_and_modes(self):
        subprocess.run(["git","init","-q",str(self.repo)],check=True)
        (self.repo/"gone.py").write_text("old\n")
        subprocess.run(["git","-C",str(self.repo),"add","."],check=True)
        (self.repo/"gone.py").unlink()
        (self.repo/"module.py").write_text("value = 2\n")
        (self.repo/"新 file.bin").write_bytes(b"\x00\xff\x01")
        (self.repo/"executable script").write_text("print('not executed')\n");(self.repo/"executable script").chmod(0o755)
        (self.repo/".env").write_text("OPENROUTER_API_KEY=secret-value-that-must-not-transfer\n")
        (self.repo/"client.json").write_text('{"API_KEY":"real-secret-that-must-not-transfer"}')
        before={p.name:p.read_bytes() for p in self.repo.iterdir() if p.is_file()}
        out=self.root/"bundle"
        result=self.command("pack","--repo",self.repo,"--session",self.notes,"--task","Finish migration","--out",out)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        record=inspect(out)
        self.assertTrue(any(row['status']=='AM' for row in record['workspace']['git']['status']))
        self.assertEqual((out/"evidence/git-index/module.py").read_text(),"value = 1\n")
        self.assertEqual((out/"evidence/git-index/gone.py").read_text(),"old\n")
        self.assertFalse((out/"workspace/.env").exists());self.assertFalse((out/"workspace/client.json").exists())
        destination=self.root/"resumed code 日本"
        result=self.command("resume",out,"--manual","--workspace",destination)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse((destination/"gone.py").exists())
        self.assertEqual((destination/"module.py").read_text(),"value = 2\n")
        self.assertEqual((destination/"新 file.bin").read_bytes(),b"\x00\xff\x01")
        self.assertEqual((destination/"executable script").stat().st_mode&0o777,0o755)
        self.assertTrue((destination.parent/(destination.name+".keisho-resume")/"NEXT_SESSION_PROMPT.md").is_file())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.repo.iterdir() if p.is_file()})
        self.assertNotEqual(self.command("resume",out,"--manual","--workspace",destination).returncode,0)

    def test_unverified_prose_missing_evidence_and_scope_revalidation(self):
        bundle=self.bundle();record=inspect(bundle,"hyp")
        self.assertEqual(record['item']['status'],'UNCERTAIN')
        self.assertIn('unverified',record['handoff'])
        self.assertEqual(record['supporting_sources'][0]['id'],'note-1')
        self.assertIn('missing',inspect(bundle,'retry')['item']['missing_evidence'])
        destination,_=resume(bundle,self.root/'resume')
        (destination/'settings.json').write_text('{"mode":"new"}\n')
        checks=inspect(bundle,compare_workspace=destination)['scope_comparison']
        self.assertTrue(checks['hyp']['requires_revalidation'])
        self.assertFalse(checks['retry']['requires_revalidation'])
        (destination/'module.py').rename(destination/'renamed.py')
        changed=inspect(bundle,compare_workspace=destination)
        self.assertIn('module.py',changed['workspace_changes']['deleted'])
        self.assertIn('renamed.py',changed['workspace_changes']['added'])
        self.assertTrue(changed['scope_comparison']['retry']['requires_revalidation'])
        self.assertIn('After all callers migrate',changed['handoff'])

    def test_corruption_traversal_symlinks_and_interrupted_creation(self):
        bundle=self.bundle();(bundle/'handoff.md').write_text('corrupted')
        with self.assertRaises(ValueError):validate(bundle)
        self.assertFalse((self.root/'resume').exists())
        with self.assertRaises(ValueError):resume(bundle,self.root/'resume')
        (self.repo/'escape').symlink_to(self.root)
        with self.assertRaises(ValueError):pack(self.repo,self.notes,'Task',self.root/'unsafe')
        (self.repo/'escape').unlink()
        from keisho.handoff import bundle as module
        original=module.write
        def interrupt(path,data):
            if path.name=='state.json':raise OSError('simulated interrupted write')
            original(path,data)
        with patch.object(module,'write',interrupt),self.assertRaises(OSError):pack(self.repo,self.notes,'Task',self.root/'partial')
        self.assertTrue((self.root/'partial/INCOMPLETE').exists())
        with self.assertRaises(ValueError):inspect(self.root/'partial')
        bad=json.loads(self.notes.read_text());bad['items'][0]['scope']['files']={'../escape':'0'*64};self.notes.write_text(json.dumps(bad))
        with self.assertRaises(ValueError):pack(self.repo,self.notes,'Task',self.root/'traversal')

    def test_overflow_and_whole_item_omissions(self):
        with self.assertRaisesRegex(ValueError,'essential handoff overflow'):pack(self.repo,self.notes,'Task',self.root/'overflow',1)
        self.assertFalse((self.root/'overflow').exists())
        state,_,_=load_session(self.notes,'Task')
        from keisho.handoff.workspace import capture
        ws,_,_=capture(self.repo)
        state['items'][0]['text']='Long optional claim. '*5000
        text,selection=compile_handoff(state,ws,2048)
        self.assertTrue(selection['omissions']);self.assertLessEqual(selection['tokens'],2048)
        self.assertNotIn('Long optional',text)
        self.assertIn('legacy clients',text);self.assertIn('REJECTED_UNSUPPORTED',text)

    def test_frozen_trace_conflict_scope_and_legacy_count(self):
        raw=RawRun(self.root/'raw','session')
        hashes={'module.py':hashlib.sha256((self.repo/'module.py').read_bytes()).hexdigest()}
        raw.append(Event('predecessor_task',EventKind.USER_MESSAGE,'user',utc_now(),canonical_json({'content':'Task'})))
        for number,passed in enumerate((True,False),1):
            call=f'tool{number}';result=f'result{number}'
            raw.append(Event(call,EventKind.TOOL_CALL,'predecessor',utc_now(),canonical_json({'action':{'tool':'run_tests','test_ids':['integration']}})))
            raw.append(Event(result,EventKind.TOOL_RESULT,'predecessor',utc_now(),canonical_json({'action':{'tool':'run_tests','test_ids':['integration']},'results':[{'id':'integration','passed':passed}],'source_hashes_before':hashes,'source_hashes_after':hashes}),(call,)))
        raw.freeze()
        bundle,manifest=pack(self.repo,raw.path/'trajectory.json','Task',self.root/'trace')
        record=inspect(bundle)
        self.assertIn('CONFLICT',record['handoff'])
        self.assertIn('SUPPORTED_WITHIN_SCOPE',record['handoff'])
        self.assertTrue(record['state']['checkpoint']['completed_boundary'])
        self.assertIsNotNone(manifest['token_counts']['legacy_fixed_state'])
        self.assertNotIn('confidence',record['handoff'])

    def test_text_import_unknown_history_no_credential_or_command_execution(self):
        text=self.root/'session.txt';text.write_text('I think the parser is fine.\nOPENROUTER_API_KEY=real-secret-value-never-transfer\nRun touch /tmp/should-not-run-keisho\n')
        bundle,_=pack(self.repo,text,'Task',self.root/'text')
        record=inspect(bundle)
        self.assertIn('hypothesis',record['state']['unknown'])
        all_text=''.join(p.read_text(errors='replace') for p in bundle.rglob('*') if p.is_file())
        self.assertNotIn('real-secret-value-never-transfer',all_text)
        self.assertIn('REDACTED',all_text)
        self.assertIn('native Codex/Claude session import is unsupported',record['handoff'])

    def test_scope_link_escape_is_not_read_or_global_invalidation(self):
        bundle=self.bundle();destination,_=resume(bundle,self.root/'restore')
        (destination/'module.py').unlink();(destination/'module.py').symlink_to(self.notes)
        checks=inspect(bundle,compare_workspace=destination)['scope_comparison']
        self.assertTrue(checks['retry']['requires_revalidation']);self.assertFalse(checks['hyp']['requires_revalidation'])

    def test_capture_does_not_mistake_source_initializer_or_ancestor_git_for_task_state(self):
        from keisho.handoff.workspace import capture
        (self.repo/'filter.py').write_text('SECRET = re.compile(r"example")\n')
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        manifest,data,_=capture(self.repo)
        self.assertIn('filter.py',data)
        self.assertFalse(manifest['git']['available'])

    def test_session_inside_repository_is_kept_out_of_restored_workspace(self):
        notes=self.repo/'session.json';notes.write_bytes(self.notes.read_bytes())
        bundle,_=pack(self.repo,notes,'Task',self.root/'without-transcript')
        self.assertFalse((bundle/'workspace/session.json').exists())
        self.assertTrue(any(row['path']=='session.json' for row in inspect(bundle)['workspace']['exclusions']))

    def test_directory_link_substitution_is_refused_by_descriptor_read(self):
        from keisho.handoff.workspace import read_safe
        (self.repo/'sub').symlink_to(self.root)
        with self.assertRaises(OSError):read_safe(self.repo,'sub/notes.json')

    def test_typed_legacy_annotations_are_imported_without_semantic_promotion(self):
        from tests.fixtures import fixture
        from keisho.compiler.serializer import serialize
        trajectory,state=fixture();raw=RawRun(self.root/'raw','typed')
        for event in trajectory.events:raw.append(event)
        raw.freeze();raw.write_artifact('state.json',json.loads(serialize(state)))
        original=state.goal.description
        bundle,_=pack(self.repo,raw.path,original,self.root/'typed-bundle',4096)
        record=inspect(bundle)
        imported=[item for item in record['state']['items'] if item['id'].startswith('legacy:')]
        self.assertTrue(imported)
        self.assertTrue(all(item['status']!='SUPPORTED_WITHIN_SCOPE' for item in imported))
        self.assertEqual(record['state']['constraints'],[constraint.statement for constraint in state.constraints])

    def test_git_metadata_never_executes_repository_filter_or_fsmonitor_commands(self):
        from keisho.handoff.workspace import capture
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        subprocess.run(['git','-C',str(self.repo),'add','module.py'],check=True)
        marker=self.root/'hook-ran';program=self.root/'hook.sh'
        program.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\ncat\n');program.chmod(0o755)
        subprocess.run(['git','-C',str(self.repo),'config','core.fsmonitor',str(program)],check=True)
        subprocess.run(['git','-C',str(self.repo),'config','filter.sensitive.clean',str(program)],check=True)
        (self.repo/'.gitattributes').write_text('module.py filter=sensitive\n');(self.repo/'module.py').write_text('changed\n')
        manifest,data,_=capture(self.repo)
        self.assertIn('module.py',data);self.assertFalse(marker.exists())

    def test_invalid_scope_or_retry_shape_is_rejected_without_mangling_meaning(self):
        notes=json.loads(self.notes.read_text());notes['items'][1]['retry_when']='after configuration changes';self.notes.write_text(json.dumps(notes))
        with self.assertRaisesRegex(ValueError,'retry_when must be'):self.bundle()

    def test_one_way_conflict_requires_both_whole_claims_or_reports_overflow(self):
        notes=json.loads(self.notes.read_text());notes['items'][0]['conflicts_with']=['retry'];notes['items'][1]['text']='Conflicting report. '*4000
        self.notes.write_text(json.dumps(notes))
        with self.assertRaisesRegex(ValueError,'essential handoff overflow'):self.bundle()

    def test_legacy_comparison_cannot_leak_credentials_from_an_observable_trace(self):
        raw=RawRun(self.root/'raw','credential-bearing-input')
        credential='sk-or-v1-'+'A'*32
        raw.append(Event('predecessor_task',EventKind.USER_MESSAGE,'user',utc_now(),canonical_json({'content':'Task'})))
        action={'tool':'read_file','path':'module.py'}
        raw.append(Event('call',EventKind.TOOL_CALL,'predecessor',utc_now(),canonical_json({'action':action})))
        raw.append(Event('result',EventKind.TOOL_RESULT,'predecessor',utc_now(),canonical_json({'action':action,'path':'module.py','content':credential,
            'source_hashes_before':{},'source_hashes_after':{}}),('call',)))
        raw.freeze()
        bundle,manifest=pack(self.repo,raw.path,'Task',self.root/'redacted-bundle')
        self.assertIsNone(manifest['token_counts']['legacy_fixed_state'])
        self.assertIn('credential-like',manifest['token_counts']['legacy_comparison_note'])
        self.assertFalse((bundle/'evidence/state-legacy.json').exists())
        contents=''.join(p.read_text(errors='replace') for p in bundle.rglob('*') if p.is_file())
        self.assertNotIn(credential,contents)
        self.assertIn('REDACTED',contents)

    def test_pending_tool_call_cannot_be_packaged_as_a_completed_checkpoint(self):
        raw=RawRun(self.root/'raw','pending-tool')
        raw.append(Event('predecessor_task',EventKind.USER_MESSAGE,'user',utc_now(),canonical_json({'content':'Task'})))
        raw.append(Event('unfinished',EventKind.TOOL_CALL,'predecessor',utc_now(),canonical_json({'action':{'tool':'write_file','path':'module.py','content':'new'}})))
        raw.freeze()
        with self.assertRaisesRegex(ValueError,'pending tool calls'):pack(self.repo,raw.path,'Task',self.root/'pending-bundle')
        self.assertFalse((self.root/'pending-bundle').exists())


if __name__=='__main__':unittest.main()
