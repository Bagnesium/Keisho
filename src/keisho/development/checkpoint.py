"""Public-only continuation eligibility; failure analysis is a separate question."""

import json

from keisho.core import require


def assess(trajectory,public_results,mode='prospective',tool_budget=12):
    require(mode in ('prospective','user','retrospective-development'),'unsupported checkpoint selection mode')
    calls={};completed=[];useful=[];writes=[];failed_approaches=[];finished=False
    for event in trajectory.events:
        payload=json.loads(event.payload_json)
        if event.kind.value=='final_answer':finished=True
        if event.kind.value=='tool_call':calls[event.id]=payload.get('action',{})
        if event.kind.value=='tool_result':
            linked=[key for key in event.parent_ids if key in calls]
            completed.extend(linked)
            action=payload.get('action',{})
            if payload.get('content') or payload.get('results') or action.get('tool')=='write_file':useful.append(event.id)
            if action.get('tool')=='write_file':writes.append((event.id,payload.get('source_hashes_after',{})))
            if any(row.get('passed') is False for row in payload.get('results',[])):
                for write_id,hashes in reversed(writes):
                    if hashes and hashes==payload.get('source_hashes_after',{}):
                        failed_approaches.append({'write_event':write_id,'failure_event':event.id,'scope':hashes});break
    boundary=bool(completed) and len(completed)==len(calls)
    public_complete=bool(public_results) and all(row['passed'] for row in public_results)
    unfinished=bool(public_results) and not public_complete and not finished
    checks={'completed_boundary':boundary,'work_budget_reached':len(completed)==tool_budget if mode=='prospective' else True,
            'useful_observable_information':bool(useful),'unfinished_public_acceptance':unfinished}
    return {'version':'checkpoint/2.0','mode':mode,'retrospective':mode=='retrospective-development','uses_hidden_evaluator_information':False,
            'continuation_eligible':all(checks.values()),'checks':checks,'completed_tools':len(completed),
            'outcome':'public_acceptance_complete_or_finished' if public_complete or finished else 'low_information_or_ineligible' if not all(checks.values()) else 'eligible',
            'repeated_failure_analysis':{'applicable':bool(failed_approaches),'qualifying_failures':failed_approaches,
                                         'metric_if_no_opportunity':None,'limitation':'A scoped failed implementation candidate is needed; baseline diagnostic failure alone is not a failed fix'},
            'limitations':['Public completion is not hidden acceptance proof','No checkpoint resampling or gold hypothesis/command requirements']}
