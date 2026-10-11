"""Candidate evidence and open human adjudication, including equivalent test sets."""

import json


def review_candidates(prepared_path,raw,task):
    archive=json.loads((prepared_path/'audit/session.json').read_text())
    predecessors=[];claims=[]
    for event in archive['events']:
        payload=json.loads(event['payload_json'])
        if event['kind']=='tool_result':predecessors.append((event['id'],payload))
        if event['kind']=='model_response':
            try:content=json.loads(payload.get('text','{}'))
            except ValueError:continue
            if isinstance(content,dict):claims += [(event['id'],claim) for claim in content.get('claims',[])]
    def equivalent(action):
        if action.get('tool')=='run_tests':
            ids=action.get('test_ids',[])
            return ('tests',tuple(sorted(case['id'] for case in task.cases))) if ids==['full'] else ('tests',tuple(sorted(ids)))
        return (action.get('tool'),action.get('path'),action.get('content'))
    actions=[];candidates=[]
    for event in raw.load_frozen().events:
        payload=json.loads(event.payload_json)
        if event.kind.value=='tool_result':
            actions.append({'event_id':event.id,'action':payload.get('action'),'human_disposition':None,'equivalent_approach_review':None,
                            'purpose_dependency_configuration_evidence_review':None,'legitimate_verification_or_unnecessary_repetition':None})
            for pred_id,pred in predecessors:
                if equivalent(pred.get('action',{}))==equivalent(payload.get('action',{})) and pred.get('source_hashes_after')==payload.get('source_hashes_before'):
                    candidates.append({'type':'potential_repetition','predecessor_event':pred_id,'successor_event':event.id,'judgment':'unresolved; unchanged named source hashes do not establish equivalent dependencies or purpose'})
        if event.kind.value=='model_response':
            try:parsed=json.loads(payload.get('text','{}'))
            except ValueError:continue
            if not isinstance(parsed,dict):continue
            for claim in parsed.get('claims',[]):
                if claim.get('basis')=='predecessor' and claim.get('status') in ('VERIFIED','OBSERVED'):
                    candidates.append({'type':'unsupported_inherited_claim_candidate','successor_event':event.id,'statement':claim.get('statement'),
                                       'judgment':'requires semantic support review; no inheritance causation claim'})
    return {'version':'continuation-review/1.0','rule_candidates':candidates,'actions':actions,'human_adjudicated_counts':None,'human_review_complete':False,
            'rubric':['Compare purpose, equivalent actions, applicable scope, configuration, dependencies and changed evidence',
                      'Distinguish legitimate validation from waste; identical commands alone are insufficient',
                      'Preserve uncertain judgments; source links are not semantic truth',
                      'Unsupported inherited-claim candidates do not establish causal inheritance'],
            'no_failure_opportunity_metric':None}
