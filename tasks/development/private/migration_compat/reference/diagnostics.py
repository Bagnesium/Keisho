from service import Service
from callers import legacy_options, modern_options
from parser import parse, serialize

def run_scenario(scenario):
    service=Service(); plans=[]; old=[]; modern=[]; errors=0; roundtrips=[]
    for index,raw in enumerate(scenario['configs']):
        try:
            plan=service.configure(raw);plans.append(plan);old.append(legacy_options(plan));modern.append(modern_options(plan))
            roundtrips.append(serialize(parse(serialize(parse(raw)))))
            if index==0 and scenario.get('mutate_after_first'): plan['attempt_deadlines_ms'][0]=999
        except (ValueError,TypeError,KeyError): errors+=1
    result={'plans':plans,'legacy':old,'modern':modern,'errors':errors,'cache_entries':len(service.cache.values),'roundtrips':roundtrips,'last_deadlines':plans[-1]['attempt_deadlines_ms'] if plans else []}
    return {key:result[key] for key in scenario['select']}
