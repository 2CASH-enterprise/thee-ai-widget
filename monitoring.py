from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db
from app.models.errorlog import ErrorLog
from app.models.lead import Lead
from app.models.prospect import Prospect
from app.models.pageview import PageView

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/errors")
async def list_errors(
    resolved: bool | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Liste les erreurs récentes, les plus récentes en premier."""
    query = select(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(limit)
    if resolved is not None:
        query = query.where(ErrorLog.resolved == resolved)

    result = await db.execute(query)
    errors = result.scalars().all()

    return {
        "errors": [
            {
                "id": e.id,
                "source": e.source,
                "error_type": e.error_type,
                "message": e.message,
                "context": e.context,
                "resolved": e.resolved,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in errors
        ]
    }


@router.patch("/errors/{error_id}/resolve")
async def resolve_error(error_id: str, db: AsyncSession = Depends(get_db)):
    """Marque une erreur comme résolue."""
    result = await db.execute(select(ErrorLog).where(ErrorLog.id == error_id))
    error = result.scalar_one_or_none()
    if not error:
        return {"success": False, "error": "Erreur non trouvée"}
    error.resolved = True
    await db.commit()
    return {"success": True}


@router.get("/health-summary")
async def health_summary(db: AsyncSession = Depends(get_db)):
    """
    Vue d'ensemble santé système pour le dashboard :
    erreurs récentes, volumes d'activité des dernières 24h.
    """
    since_24h = datetime.utcnow() - timedelta(hours=24)
    since_1h = datetime.utcnow() - timedelta(hours=1)

    # Erreurs non résolues
    unresolved_result = await db.execute(
        select(func.count(ErrorLog.id)).where(ErrorLog.resolved == False)
    )
    unresolved_count = unresolved_result.scalar() or 0

    # Erreurs dernière heure (signal d'alerte immédiate)
    errors_1h_result = await db.execute(
        select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= since_1h)
    )
    errors_1h = errors_1h_result.scalar() or 0

    # Erreurs dernières 24h
    errors_24h_result = await db.execute(
        select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= since_24h)
    )
    errors_24h = errors_24h_result.scalar() or 0

    # Activité : conversations (leads) dernières 24h
    leads_24h_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= since_24h)
    )
    leads_24h = leads_24h_result.scalar() or 0

    # Activité : pageviews landing dernières 24h
    views_24h_result = await db.execute(
        select(func.count(PageView.id)).where(
            PageView.created_at >= since_24h, PageView.event == "pageview"
        )
    )
    views_24h = views_24h_result.scalar() or 0

    # Statut global simple : OK / ATTENTION / CRITIQUE
    if errors_1h >= 5:
        status = "critique"
    elif errors_1h >= 1 or unresolved_count >= 10:
        status = "attention"
    else:
        status = "ok"

    return {
        "status": status,
        "unresolved_errors": unresolved_count,
        "errors_last_hour": errors_1h,
        "errors_last_24h": errors_24h,
        "leads_last_24h": leads_24h,
        "pageviews_last_24h": views_24h,
    }
