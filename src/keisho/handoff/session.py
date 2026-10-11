"""Conservative imports of explicit notes or verified Keisho observable events."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from keisho.core import canonical_json, decode, digest, require
from keisho.logging.raw import EventKind, FrozenTrajectory, RawRun
from keisho.pilot.response_policy import AUXILIARY, parse_auxiliary
from .workspace import scrub

CATEGORIES = {"progress", "observation", "hypothesis", "failed_approach", "question", "next_action", "uncertainty", "change"}
STATUSES = {"OBSERVED", "SUPPORTED_WITHIN_SCOPE", "HYPOTHESIZED", "UNCERTAIN", "REJECTED_SUPPORTED", "REJECTED_UNSUPPORTED", "SUPERSEDED"}


def sanitize(value):
    if isinstance(value, str): return scrub(value)
    if isinstance(value, list): return [sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: "[REDACTED_CREDENTIAL]" if k.lower() in ("api_key", "password", "secret", "access_token") else sanitize(v) for k,v in value.items()}
    return value


def load_session(path, task, acceptance=(), constraints=()):
    path = Path(path)
    if path.is_dir(): trajectory = RawRun.open_existing(path.parent, path.name).load_frozen(); raw = asdict(trajectory)
    else:
        require(path.is_file() and not path.is_symlink(), "session must be an explicit regular file or sealed Keisho run")
        content = path.read_bytes(); require(len(content) <= 16*1024*1024, "session exceeds 16 MiB")
        if path.suffix == ".json":
            raw = json.loads(content)
            if "events" in raw and "sha256" in raw:
                trajectory = decode(FrozenTrajectory, raw); trajectory.validate()
            elif path.name == "trajectory.json" and "event_count" in raw:
                trajectory = RawRun.open_existing(path.parent.parent, path.parent.name).load_frozen(); raw = asdict(trajectory)
            else: trajectory = None
        else:
            raw = {"version": "keisho-notes/1.0", "notes": content.decode("utf-8"), "items": []}; trajectory = None
    safe = sanitize(json.loads(canonical_json(raw)))
    warnings, items, sources = [], [], []
    def add(category, text, status, source_ids, scope=None, **extra):
        item = {"id": f"S{len(items)+1}", "category": category, "text": scrub(text), "status": status,
                "source_ids": source_ids, "scope": scope or {"files": {}, "environment": "unknown"}, **extra}
        items.append(item); return item
    if trajectory is not None:
        kind = "keisho-frozen-trajectory/0.1.0"
        archive = {"format": kind, "original_trajectory_sha256": trajectory.sha256,
                   "redacted": safe != json.loads(canonical_json(raw)), "events": safe["events"]}
        for event in safe["events"]:
            sources.append({"id": event["id"], "kind": event["kind"], "location": f"evidence/session.json#event={event['id']}", "sha256": digest(event)})
        amended = any(e['kind'] == 'annotation' and json.loads(e['payload_json']).get('type') == 'response_policy'
                      and json.loads(e['payload_json']).get('version') == AUXILIARY for e in safe['events'])
        annotation_coverage = {'supplied': 0, 'validated': 0, 'rejected': 0, 'unparsed_responses': 0}
        available_results = set()
        pending = set(); useful = 0
        for event in safe["events"]:
            payload = json.loads(event["payload_json"]); sid = [event["id"]]
            if event["kind"] == "tool_call": pending.add(event["id"])
            if event["kind"] == "tool_result":
                rejected_action = any(k in payload for k in ('invalid_action', 'infrastructure_failure'))
                pending.difference_update(event["parent_ids"])
                if amended and rejected_action:
                    add('observation', 'Recorded action refusal/failure: ' + canonical_json(payload), 'OBSERVED', sid)
                    continue
                if not rejected_action:
                    available_results.add(event['id'])
                useful += 1
                action = payload.get("action", {}); hashes = payload.get("source_hashes_after", {})
                scope = {"files": hashes, "environment": "recorded tool workspace; dependency coverage unknown"}
                if payload.get('benchmark_observable') is True:
                    for changed_path in payload.get('changed_paths', []):
                        add('change', 'Recorded file content/mode change: ' + changed_path, 'OBSERVED', sid, scope)
                    if action.get('tool') == 'shell':
                        output = payload.get('output', '')
                        excerpt = output[-2000:]
                        add('observation', 'Command: ' + action.get('command', '') + '\nExit code: ' + str(payload.get('exit_code')) +
                            '\nRecorded output' + (' (last 2000 characters; preceding output omitted)' if len(output) > 2000 else '') + ':\n' + excerpt,
                            'OBSERVED', sid, scope)
                if action.get("tool") == "read_file" and "path" in payload:
                    scope = {"files": {payload["path"]: hashes.get(payload["path"])}, "environment": "recorded file contents only"}
                    add("observation", f"Inspected {payload['path']}", "OBSERVED", sid, scope)
                elif action.get("tool") == "write_file":
                    add("change", f"Updated {action.get('path', payload.get('path','unknown path'))}", "OBSERVED", sid, scope)
                else: add("progress", "Completed tool action: " + canonical_json(action or {"result_event": event["id"]}), "OBSERVED", sid, scope)
                for result in payload.get("results", []):
                    if type(result.get("passed")) is bool:
                        add("observation", f"Test {result['id']}: {'passed' if result['passed'] else 'failed'} at this recorded workspace; no broader subsystem claim",
                            "SUPPORTED_WITHIN_SCOPE", sid, scope, claim_key="test:"+result["id"], claim_value=result["passed"])
                failed=[result["id"] for result in payload.get("results",[]) if result.get("passed") is False]
                if failed:
                    add("failed_approach","The recorded test action failed: "+", ".join(failed)+". This rejects only a passing outcome at these inputs and files, not an entire approach or subsystem.",
                        "REJECTED_SUPPORTED",sid,scope, failure_kind="diagnostic_failure",
                        retry_when=["Relevant code/configuration changes, changed inputs or new evidence justify retesting"])
                if payload.get("execution_failure"):
                    add("failed_approach", "Tool execution failed: " + canonical_json(payload["execution_failure"]), "OBSERVED", sid, scope,
                        retry_when=["Relevant configuration changes or new diagnostic evidence justify another attempt"])
            if event["kind"] == "model_response":
                try:
                    claims = parse_auxiliary(payload.get('text', '{}'), available_results) if amended else json.loads(payload.get("text", "{}"))
                except (ValueError, TypeError): claims = {}
                if amended:
                    report = claims.get('annotation_report')
                    if report:
                        for key, value in report['coverage'].items(): annotation_coverage[key] += value
                        if report['diagnostics']:
                            warnings.append(event['id'] + ': malformed auxiliary claims retained in audit; excluded from state; annotation information unknown')
                    else:
                        annotation_coverage['unparsed_responses'] += 1
                if not isinstance(claims, dict): continue
                for claim in claims.get("claims", []):
                    if not isinstance(claim, dict) or not isinstance(claim.get("statement"), str): continue
                    declared = claim.get("status", "UNCERTAIN")
                    refs = [r for r in claim.get("evidence_ids", []) if isinstance(r, str)]
                    add("failed_approach" if declared == "FALSIFIED" else "hypothesis", claim["statement"],
                        "REJECTED_UNSUPPORTED" if declared == "FALSIFIED" else "HYPOTHESIZED", sid,
                        {"files": {}, "environment": "predecessor interpretation; scope not established"},
                        evidence_ids=refs, declared_status=declared, evidence_semantics="citation is traceability, not verified support",
                        retry_when=["Revisit after relevant scope changes or new evidence"] if declared == "FALSIFIED" else [])
            if event["kind"] == "annotation" and payload.get("type") == "local_task_state":
                require(isinstance(payload.get("acceptance",[]),list) and isinstance(payload.get("constraints",[]),list),"task criteria must be arrays")
                acceptance = tuple(dict.fromkeys((*acceptance,*payload.get("acceptance",[])))); constraints = tuple(dict.fromkeys((*constraints,*payload.get("constraints",[]))))
                for note in payload.get("next_actions", []): add("next_action", note, "UNCERTAIN", sid)
        boundary = {"completed_tool_results": useful, "pending_tool_calls": sorted(pending), "completed_boundary": useful > 0 and not pending,
                    "selection": "user-triggered at supplied current trace end; retrospective if selected from a longer completed trace"}
        warnings.append("Only supported visible events are extracted; unrecorded thoughts, failures and acceptance criteria remain unknown")
    else:
        require(isinstance(safe, dict) and safe.get("version") == "keisho-notes/1.0", "unsupported import; use keisho-notes/1.0 JSON or an explicit UTF-8 text export")
        kind = "explicit-notes/1.0"; archive = {"format": kind, "record": safe, "redacted": safe != raw}
        require(isinstance(safe.get("acceptance",[]),list) and isinstance(safe.get("constraints",[]),list),"notes criteria must be arrays")
        acceptance = tuple(dict.fromkeys((*acceptance,*safe.get("acceptance",[])))); constraints = tuple(dict.fromkeys((*constraints,*safe.get("constraints",[]))))
        sources = safe.get("sources", [])
        require(isinstance(sources, list), "notes sources must be an array")
        for source in sources:
            require(isinstance(source,dict) and isinstance(source.get("id"),str) and isinstance(source.get("text"),str), "notes source needs id and text")
            source.update(kind="imported_user_report", location=f"evidence/session.json#source={source['id']}", sha256=digest(source["text"]))
        require(len({source["id"] for source in sources}) == len(sources), "duplicate source ID")
        archive["record"]["sources"] = sources
        for note in safe.get("items", []):
            require(isinstance(note,dict) and note.get("category") in CATEGORIES and isinstance(note.get("text"),str), "unsupported note item")
            declared = note.get("status","UNCERTAIN"); require(declared in STATUSES, "unsupported epistemic status")
            status = "REJECTED_UNSUPPORTED" if declared.startswith("REJECTED") else "HYPOTHESIZED" if declared == "HYPOTHESIZED" else "SUPERSEDED" if declared == "SUPERSEDED" else "UNCERTAIN"
            scope = note.get("scope", {"files":{},"environment":"unknown"})
            require(isinstance(scope,dict) and isinstance(scope.get("files",{}),dict) and isinstance(scope.get("environment","unknown"),str), "invalid scope")
            import re
            require(all(value is None or isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) for value in scope.get('files',{}).values()),'scope hashes must be lowercase SHA-256 or null')
            for field in ('source_ids','evidence_ids','retry_when','conflicts_with'):
                require(isinstance(note.get(field,[]),list) and all(isinstance(value,str) for value in note.get(field,[])),field+' must be an array of text')
            item = add(note["category"], note["text"], status, note.get("source_ids",[]), scope,
                       declared_status=declared, imported_report=True, evidence_ids=note.get("evidence_ids",[]),
                       retry_when=note.get("retry_when",[]), conflicts_with=note.get("conflicts_with",[]))
            if note.get("id"): item["id"] = note["id"]
        if safe.get("notes"):
            sources.append({"id":"imported-text", "kind":"imported_user_report", "text":safe["notes"], "location":"evidence/session.json#notes", "sha256":digest(safe["notes"])})
            add("uncertainty", safe["notes"], "UNCERTAIN", ["imported-text"], imported_report=True)
        boundary = {"completed_boundary": None, "selection":"user supplied notes; tool boundary cannot be independently established"}
        warnings.append("Imported prose and notes are incomplete user reports, not independently verified tool traces; native Codex/Claude session import is unsupported")
        unsupported=set(safe)-{'version','goal','acceptance','constraints','sources','items','notes'}
        if unsupported:warnings.append('Unsupported note fields retained in audit but not extracted: '+', '.join(sorted(unsupported)))
    require(isinstance(task,str) and task.strip(), "an explicit unfinished task is required")
    require(all(isinstance(v,str) and v.strip() for v in (*acceptance,*constraints)), "acceptance criteria and constraints must be nonempty text")
    ids = {source["id"] for source in sources}; item_ids = {item["id"] for item in items}
    require(len(item_ids) == len(items), "duplicate state item ID")
    for item in items:
        require(isinstance(item["source_ids"],list) and all(isinstance(v,str) for v in item["source_ids"]), "source IDs must be text")
        missing = [ref for ref in item["source_ids"] + item.get("evidence_ids",[]) if ref not in ids]
        item["missing_evidence"] = missing
        if missing: warnings.append(f"{item['id']} has missing evidence: {', '.join(missing)}")
        for conflict in item.get("conflicts_with",[]): require(conflict in item_ids, "unknown conflict item")
    # Conflicting test results at identical recorded scope remain visible. Later scope differs: superseded, not a global refutation.
    for i,item in enumerate(items):
        for later in items[i+1:]:
            if item.get("claim_key") and item.get("claim_key") == later.get("claim_key") and item.get("claim_value") != later.get("claim_value"):
                if item["scope"] == later["scope"]:
                    item.setdefault("conflicts_with",[]).append(later["id"]); later.setdefault("conflicts_with",[]).append(item["id"])
                else: item.update(status="SUPERSEDED", superseded_by=later["id"])
    by_id={item['id']:item for item in items}
    for item in items:
        for other_id in list(item.get('conflicts_with',[])):
            reverse=by_id[other_id].setdefault('conflicts_with',[])
            if item['id'] not in reverse:reverse.append(item['id'])
    if archive.get('redacted'):warnings.append('Credential-like text was redacted from the supplied session; the audit records this alteration')
    unknown = {category: "unknown; not supplied or not extractable" for category in CATEGORIES if not any(item["category"] == category for item in items)}
    if not acceptance: warnings.append("Explicit acceptance criteria are missing; completion cannot be inferred")
    state = {"version":"local-state/1.0", "goal":scrub(task), "acceptance":list(map(scrub,acceptance)), "constraints":list(map(scrub,constraints)),
             "items":items,"sources":sources,"unknown":unknown,"warnings":warnings,"checkpoint":boundary,
             "extraction":{"version":"observable-import/1.0","format":kind,"semantic_review":"not independently adjudicated","hidden_state_access":False}}
    if trajectory is not None and amended:
        state['extraction'].update(version='observable-import/1.1', response_policy=AUXILIARY, annotation_coverage=annotation_coverage)
    if trajectory is not None:
        location=path if path.is_dir() else path.parent
        legacy_file=location/'state.json'
        if legacy_file.is_file() and not legacy_file.is_symlink():
            try:
                from keisho.compiler.serializer import deserialize
                from keisho.state.extractor import extract_state
                from keisho.core import primitive
                legacy=deserialize(legacy_file.read_text());extract_state(primitive(legacy),trajectory)
                archive['legacy_state']=sanitize(primitive(legacy))
                evidence_records={record.id:record for record in legacy.evidence}
                for record in legacy.evidence:
                    if record.id not in ids:
                        sources.append({'id':record.id,'kind':'imported_annotation_evidence','location':'evidence/session.json#legacy-evidence='+record.id,'sha256':digest(record)})
                        ids.add(record.id)
                mapping={'observations':'observation','verified_facts':'observation','hypotheses':'hypothesis','rejected_hypotheses':'failed_approach',
                         'actions':'progress','failed_attempts':'failed_approach','changes':'change','open_questions':'question','uncertainties':'uncertainty','current_plan':'next_action','next_actions':'next_action'}
                for constraint in legacy.constraints:
                    if constraint.statement not in state['constraints']:state['constraints'].append(scrub(constraint.statement))
                for category,target in mapping.items():
                    for old in getattr(legacy,category):
                        fields=primitive(old);prov=old.provenance;scope_files={}
                        try:
                            parsed=json.loads(prov.scope)
                            if isinstance(parsed,dict) and all(isinstance(k,str) and isinstance(v,str) and len(v)==64 for k,v in parsed.items()):scope_files=parsed
                        except (ValueError,TypeError):pass
                        details=[str(value) for key,value in fields.items() if key not in ('id','provenance','confidence','supporting_evidence','contradicting_evidence','retry_conditions')]
                        status='HYPOTHESIZED' if category=='hypotheses' else 'REJECTED_UNSUPPORTED' if category=='rejected_hypotheses' else 'SUPERSEDED' if prov.epistemic_status.value=='SUPERSEDED' else 'UNCERTAIN'
                        item=add(target,'; '.join(details),status,list(prov.source_ids),{'files':scope_files,'environment':'recorded named file state; dependency coverage unknown' if scope_files else prov.scope},
                                 imported_report=True,declared_status=prov.epistemic_status.value,evidence_ids=list(prov.evidence_ids),retry_when=list(getattr(old,'retry_conditions',())),
                                 annotation_report='Validated source binding, not independent semantic adjudication')
                        item['id']='legacy:'+old.id;item['missing_evidence']=[ref for ref in item['source_ids']+item['evidence_ids'] if ref not in ids]
                state['unknown']={category:'unknown; not supplied or not extractable' for category in CATEGORIES if not any(item['category']==category for item in items)}
                warnings.append('Typed legacy annotations are imported as trace-linked reports; validation does not independently establish their semantic truth')
            except (ValueError,KeyError,TypeError):warnings.append('Legacy state sidecar is unsupported or from another trajectory; not imported')
        calls_file=location/'calls.json'
        accounting={'complete':False,'reported_cost_usd':None,'source':'Keisho explicit calls sidecar, when present; reported usage is not invoice verification'}
        if calls_file.is_file() and not calls_file.is_symlink():
            try:
                from decimal import Decimal
                from keisho.agents.base import Usage
                calls=json.loads(calls_file.read_text());requests={event.id for event in trajectory.events if event.kind.value=='model_request'}
                complete=bool(calls) and {call['request_event_id'] for call in calls}==requests and len(calls)==len(requests)
                usages=[decode(Usage,call['usage']) for call in calls]
                for usage in usages:usage.validate()
                known=complete and all(usage.cost_usd is not None for usage in usages)
                accounting.update(complete=complete,reported_cost_usd=str(sum((Decimal(usage.cost_usd) for usage in usages),Decimal(0))) if known else None,calls=sanitize(calls))
            except (ValueError,KeyError,TypeError):warnings.append('Predecessor accounting sidecar is incomplete or unsupported; cost remains unknown')
        archive['accounting']=accounting
        state['predecessor_accounting']=accounting
    return state, archive, trajectory
