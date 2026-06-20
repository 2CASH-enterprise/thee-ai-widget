from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import get_db
from app.models.pageview import PageView

router = APIRouter(prefix="/track", tags=["tracking"])


class TrackEvent(BaseModel):
    session_id: str
    page: str = "landing"
    event: str
    referrer: str | None = None
    user_agent: str | None = None
    duration_seconds: int | None = None


@router.post("")
async def track_event(data: TrackEvent, db: AsyncSession = Depends(get_db)):
    """Enregistre un événement de tracking (vue de page, scroll, clic CTA)."""
    pv = PageView(
        session_id=data.session_id,
        page=data.page,
        event=data.event,
        referrer=data.referrer,
        user_agent=data.user_agent,
        duration_seconds=data.duration_seconds,
    )
    db.add(pv)
    await db.commit()
    return {"success": True}


@router.get("/stats")
async def get_tracking_stats(page: str = "landing", db: AsyncSession = Depends(get_db)):
    """Statistiques agrégées de fréquentation pour le dashboard."""
    # Visites uniques (sessions distinctes ayant fait un pageview)
    unique_result = await db.execute(
        select(func.count(func.distinct(PageView.session_id)))
        .where(PageView.page == page, PageView.event == "pageview")
    )
    unique_visitors = unique_result.scalar() or 0

    # Total pageviews
    total_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page == page, PageView.event == "pageview")
    )
    total_views = total_result.scalar() or 0

    # Clics CTA
    cta_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page == page, PageView.event == "cta_click")
    )
    cta_clicks = cta_result.scalar() or 0

    # Scroll 90% (engagement profond)
    scroll_result = await db.execute(
        select(func.count(func.distinct(PageView.session_id)))
        .where(PageView.page == page, PageView.event == "scroll_90")
    )
    deep_scroll = scroll_result.scalar() or 0

    # Démo widget lancée
    demo_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page == page, PageView.event == "demo_started")
    )
    demo_started = demo_result.scalar() or 0

    return {
        "unique_visitors": unique_visitors,
        "total_views": total_views,
        "cta_clicks": cta_clicks,
        "cta_rate": round(cta_clicks / unique_visitors * 100, 1) if unique_visitors else 0,
        "deep_scroll": deep_scroll,
        "deep_scroll_rate": round(deep_scroll / unique_visitors * 100, 1) if unique_visitors else 0,
        "demo_started": demo_started,
    }
