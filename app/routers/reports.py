from fastapi import APIRouter, Depends
from ..auth import require_role
from ..firestore import db
from ..models import ReportQuery

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/worker-load", dependencies=[Depends(require_role('admin','manager','worker'))])
async def worker_load(q: ReportQuery):
    docs = db.collection('assignments').stream()
    load = {}
    for d in docs:
        a = d.to_dict()
        for wid in a.get('workerIds', []):
            load[wid] = load.get(wid, 0) + 1
    return load

@router.post("/project-status", dependencies=[Depends(require_role('admin','manager'))])
async def project_status(q: ReportQuery):
    if not q.projectId:
        return {}
    docs = db.collection('assignments').where('projectId','==', q.projectId).stream()
    stats = {'in_progress':0,'done_pending':0,'done_approved':0,'extend_requested':0}
    for d in docs:
        s = d.to_dict().get('state','in_progress')
        stats[s] = stats.get(s,0)+1
    return stats
