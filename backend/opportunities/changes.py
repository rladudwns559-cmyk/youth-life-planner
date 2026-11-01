"""Notification-ready public change events; no subscriptions, scheduler, or delivery."""
from datetime import datetime
import hashlib,json
from .catalog import Catalog
from .matching import program_revision,intake

def diff_catalogs(previous:Catalog,current:Catalog,*,previous_at:datetime,current_at:datetime):
    if previous_at.tzinfo is None or current_at.tzinfo is None or current_at<previous_at:raise ValueError('INVALID_EVENT_TIME')
    before={p.program_id:p for p in previous.programs};after={p.program_id:p for p in current.programs}
    events=[]
    for identifier in sorted(before.keys()|after.keys()):
        old,new=before.get(identifier),after.get(identifier)
        if old is None:kind='PROGRAM_ADDED'
        elif new is None:kind='PROGRAM_REMOVED'
        elif program_revision(old)!=program_revision(new):kind='PROGRAM_UPDATED'
        elif intake(old,previous,previous_at)['status']!=intake(new,current,current_at)['status']:kind='INTAKE_STATUS_CHANGED'
        else:continue
        payload=dict(schema_version='asset-program-events-v1',kind=kind,program_id=identifier,
            edition=(new or old).edition,previous_revision=program_revision(old) if old else None,
            current_revision=program_revision(new) if new else None,
            previous_status=intake(old,previous,previous_at)['status'] if old else None,
            current_status=intake(new,current,current_at)['status'] if new else None)
        event_id=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        events.append(payload|dict(event_id=event_id,observed_at=current_at.isoformat(),delivery_status='NOT_SENT'))
    return tuple(events)
