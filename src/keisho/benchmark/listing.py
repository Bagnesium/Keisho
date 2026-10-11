"""Bounded, deterministic discovery. History is retained; omissions are explicit."""
import re

from keisho.core import digest
from keisho.environments.base import safe_relative_path
from keisho.pilot.tools import InvalidAction

VERSION = 'bounded-listing/1.0'
MAX_ENTRIES = 100
MAX_PATH_BYTES = 8192


def parameters(action):
    if not isinstance(action, dict) or action.get('tool') != 'list_files' or not set(action) <= {'tool','prefix','cursor','limit'}:
        raise InvalidAction('invalid bounded listing fields')
    prefix, cursor, limit = action.get('prefix',''), action.get('cursor'), action.get('limit',MAX_ENTRIES)
    try:
        if not isinstance(prefix,str) or len(prefix.encode()) > 1024: raise ValueError()
        if prefix:
            safe_relative_path(prefix[:-1] if prefix.endswith('/') else prefix)
            if '.git' in prefix.split('/') or any(ord(c)<32 for c in prefix):raise ValueError()
    except (TypeError,ValueError):raise InvalidAction('unsafe listing prefix') from None
    if type(limit) is not int or not 1 <= limit <= MAX_ENTRIES:
        raise InvalidAction('listing limit must be an integer from 1 to 100')
    if cursor is not None and (not isinstance(cursor,str) or not re.fullmatch(r'[0-9a-f]{64}:\d{1,8}',cursor)):
        raise InvalidAction('invalid listing cursor')
    return prefix,cursor,limit


class BoundedListing:
    def __init__(self):self.cache={}
    def page(self, inventory, action, action_number):
        prefix,cursor,limit=parameters(action)
        identity=digest({'inventory':inventory,'prefix':prefix})
        offset=0
        if cursor is not None:
            claimed,number=cursor.split(':');offset=int(number)
            if claimed!=identity:
                return {'files':[],'bounded':True,'listing_version':VERSION,'cursor_stale':True,
                    'inventory_sha256':digest(inventory),'prefix':prefix,'returned_count':0,
                    'has_more':None,'next_cursor':None,'truncated':True,
                    'omission':'No page produced: stale listing cursor after repository change. Restart with the same prefix and cursor null; no action was replaced.'}
        paths=sorted(p for p in inventory if p.startswith(prefix))
        if offset>len(paths):raise InvalidAction('listing cursor exceeds matching entries')
        page=[];size=0
        for path in paths[offset:offset+limit]:
            amount=len(path.encode())+4
            if size+amount>MAX_PATH_BYTES:break
            page.append(path);size+=amount
        if offset<len(paths) and not page:raise InvalidAction('one path exceeds the listing byte bound; use targeted inspection')
        end=offset+len(page);more=end<len(paths)
        key=(identity,offset,limit)
        listing_id=digest({'identity':identity,'offset':offset,'limit':limit,'files':page})
        result={'files':page,'bounded':True,'listing_version':VERSION,'listing_id':listing_id,
                'inventory_sha256':digest(inventory),'prefix':prefix,'offset':offset,
                'matching_count':len(paths),'returned_count':len(page),'has_more':more,
                'next_cursor':f'{identity}:{end}' if more else None,
                'truncated':more or offset>0,'ordering':'lexicographic',
                'omission':'This page only; request next_cursor or a narrower prefix for remaining entries.' if more or offset>0 else 'NONE'}
        if key in self.cache:
            result.update(files=[],returned_count=0,unchanged=True,reused_listing_id=listing_id,
                          reused_from_tool_action=self.cache[key],suppressed_duplicate_count=len(page),
                          omission='Exact page unchanged; filenames are in the earlier tool result with this listing_id. History is retained. Use next_cursor or prefix for new entries.')
        else:
            if len(self.cache)>=16:self.cache.pop(next(iter(self.cache)))
            self.cache[key]=action_number
        return result
