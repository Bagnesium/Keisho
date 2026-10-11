import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator
from keisho.benchmark.listing import BoundedListing,VERSION
from keisho.benchmark.environment import RepositorySession
from keisho.core import canonical_json
from keisho.logging.raw import RawRun
from keisho.pilot.agent import Budgets,Recorder,run_agent,parse_output
from keisho.pilot.response_policy import AUXILIARY,agent_response_format
from keisho.pilot.tools import InvalidAction
from tests.test_agent_wire_contract import Counter,OfflineSession,native_response
from keisho.agents.providers.openrouter_chat import OpenRouterChatModel,MODEL_ALIASES

class ListingTests(unittest.TestCase):
    def inventory(self,n=1500):return {f'pkg/file_{i:04d}.py':{'sha256':str(i).zfill(64),'mode':420} for i in range(n)}
    def test_large_inventory_paging_is_complete_and_explicit(self):
        listing=BoundedListing();inventory=self.inventory();seen=[];action={'tool':'list_files'}
        for number in range(1,100):
            page=listing.page(inventory,action,number);seen+=page['files']
            self.assertLessEqual(len(page['files']),100)
            self.assertLessEqual(sum(len(p.encode())+4 for p in page['files']),8192)
            if not page['has_more']:break
            self.assertTrue(page['truncated']);self.assertIn('next_cursor',page['omission'])
            action={'tool':'list_files','cursor':page['next_cursor']}
        self.assertEqual(seen,sorted(inventory))
    def test_duplicate_page_references_retained_evidence_and_edits_invalidate(self):
        listing=BoundedListing();inventory=self.inventory()
        first=listing.page(inventory,{'tool':'list_files'},1)
        repeated=listing.page(inventory,{'tool':'list_files'},2)
        self.assertEqual(repeated['files'],[]);self.assertEqual(repeated['reused_listing_id'],first['listing_id'])
        self.assertEqual(repeated['reused_from_tool_action'],1)
        self.assertTrue(repeated['unchanged']);self.assertIn('History is retained',repeated['omission'])
        inventory['pkg/file_0000.py']['sha256']='f'*64
        stale=listing.page(inventory,{'tool':'list_files','cursor':first['next_cursor']},3)
        self.assertTrue(stale['cursor_stale']);self.assertEqual(stale['files'],[])
        self.assertIn('no action was replaced',stale['omission'])
        updated=listing.page(inventory,{'tool':'list_files'},4)
        self.assertTrue(updated['files']);self.assertNotIn('unchanged',updated)
    def test_prefix_discovery_and_runtime_safety(self):
        inventory=self.inventory();inventory['z/relevant.py']={'sha256':'a'*64,'mode':420}
        page=BoundedListing().page(inventory,{'tool':'list_files','prefix':'z/'},1)
        self.assertEqual(page['files'],['z/relevant.py'])
        session=RepositorySession.__new__(RepositorySession);session.listing_policy=VERSION
        for action in ({'tool':'list_files','prefix':'../'}, {'tool':'list_files','limit':True},
                       {'tool':'list_files','cursor':'bad'},{'tool':'list_files','prefix':'.git/'},
                       {'tool':'list_files','path':'pkg'}):
            with self.assertRaises(InvalidAction):session.validate_action(action)
        valid={'tool':'list_files','prefix':'pkg/','limit':7,'cursor':None}
        session.validate_action(valid)
        Draft202012Validator(agent_response_format('3.0')['json_schema']['schema']).validate({'action':valid,'claims':[]})
        parse_output(canonical_json({'action':valid,'claims':[]}),set(),AUXILIARY)
        legacy=RepositorySession.__new__(RepositorySession)
        with self.assertRaises(InvalidAction):legacy.validate_action(valid)
    def test_missing_tool_result_is_recorded_not_given_as_evidence(self):
        class Missing(OfflineSession):
            def execute(self,action):return None
        identity='openai/gpt-4.1-mini-2025-04-14';requests=[]
        def transport(body,key):requests.append(body);return native_response(identity,{'action':{'tool':'list_files'},'claims':[]}),None
        model=OpenRouterChatModel(identity,authorized=True,api_key='fixture-key',tokenizer=Counter(),transport=transport,response_model_ids=(MODEL_ALIASES[identity],identity))
        with tempfile.TemporaryDirectory() as t:
            raw=RawRun(Path(t),'missing');execution=run_agent(model,Missing(),Recorder(raw),'fixture','JSON','',1,Budgets(4,4,2048,180000,32000,128000),response_policy=AUXILIARY)
            self.assertEqual(execution.reason,'infrastructure_failure');self.assertEqual(len(requests),1)
            result=[json.loads(e.payload_json) for e in raw.freeze().events if e.kind.value=='tool_result'][0]
            self.assertIn('infrastructure_failure',result)
    def test_multi_turn_repeated_page_keeps_full_first_result(self):
        identity='openai/gpt-4.1-mini-2025-04-14';requests=[]
        class Session(OfflineSession):
            listing_policy=VERSION
            def __init__(self):super().__init__();self.listing=BoundedListing()
            def execute(self,action):self.actions.append(action);return {**self.listing.page(ListingTests().inventory(),action,len(self.actions)),'action':action}
        def transport(body,key):requests.append(body);return native_response(identity,{'action':{'tool':'list_files'},'claims':[]}),None
        model=OpenRouterChatModel(identity,authorized=True,api_key='fixture-key',tokenizer=Counter(),transport=transport,response_model_ids=(MODEL_ALIASES[identity],identity))
        with tempfile.TemporaryDirectory() as t:
            execution=run_agent(model,Session(),Recorder(RawRun(Path(t),'history')),'fixture','JSON','',1,Budgets(3,3,2048,180000,32000,128000),response_policy=AUXILIARY)
            self.assertEqual(execution.reason,'budget_exhausted')
            first=json.loads(requests[2]['messages'][4]['content'])['tool_result']
            repeated=json.loads(requests[2]['messages'][6]['content'])['tool_result']
            self.assertEqual(len(first['files']),100);self.assertEqual(repeated['files'],[])
            self.assertEqual(repeated['reused_listing_id'],first['listing_id'])
    def test_existing_scope_revalidation_matches_filesystem_policy(self):
        import hashlib
        from keisho.handoff.workspace import compare_scope,compare_scope_hashes
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);file=root/'source.py';file.write_text('old')
            sha=hashlib.sha256(file.read_bytes()).hexdigest()
            item={'scope':{'files':{'source.py':sha,'unknown.py':None}}}
            inventory={'source.py':{'sha256':sha}}
            self.assertEqual(compare_scope(item,root),compare_scope_hashes(item,inventory))
            file.write_text('new');inventory['source.py']['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
            result=compare_scope_hashes(item,inventory)
            self.assertEqual(result,compare_scope(item,root))
            self.assertEqual(result['changed_paths'],['source.py']);self.assertTrue(result['requires_revalidation'])

if __name__=='__main__':unittest.main()
