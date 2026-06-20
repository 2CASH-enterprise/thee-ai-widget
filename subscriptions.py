from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import get_db
from app.models.subscription import Subscription
from app.models.lead import Lead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

PLAN_PRICES = {"starter": 149.0, "pro": 349.0}


class SubscriptionIn(BaseModel):
    agency_id: str
    agency_name: str
    contact_email: str | None = None
    plan: str = "starter"
    calendly_url: str | None = None
    notes: str | None = None


class SubscriptionUpdate(BaseModel):
    plan: str | None = None
    status: str | None = None
    contact_email: str | None = None
    setup_fee_paid: bool | None = None
    notes: str | None = None


@router.post("")
async def create_subscription(data: SubscriptionIn, db: AsyncSession = Depends(get_db)):
    """Crée un nouvel abonnement client (après signature)."""
    sub = Subscription(
        agency_id=data.agency_id,
        agency_name=data.agency_name,
        contact_email=data.contact_email,
        plan=data.plan,
        monthly_price=PLAN_PRICES.get(data.plan, 149.0),
        calendly_url=data.calendly_url,
        notes=data.notes,
    )
    db.add(sub)
    await db.commit()
    return {"success": True, "id": sub.id}


@router.get("")
async def list_subscriptions(status: str | None = None, db: AsyncSession = Depends(get_db)):
    """Liste tous les abonnements, avec le nombre de leads générés pour chacun."""
    query = select(Subscription).order_by(Subscription.started_at.desc())
    if status:
        query = query.where(Subscription.status == status)

    result = await db.execute(query)
    subs = result.scalars().all()

    output = []
    for s in subs:
        leads_count_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.agency_id == s.agency_id)
        )
        leads_count = leads_count_result.scalar() or 0

        rdv_count_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.agency_id == s.agency_id, Lead.rdv_scheduled == True)
        )
        rdv_count = rdv_count_result.scalar() or 0

        output.append({
            "id": s.id,
            "agency_id": s.agency_id,
            "agency_name": s.agency_name,
            "contact_email": s.contact_email,
            "plan": s.plan,
            "status": s.status,
            "monthly_price": float(s.monthly_price) if s.monthly_price else 0,
            "setup_fee_paid": s.setup_fee_paid,
            "leads_count": leads_count,
            "rdv_count": rdv_count,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        })

    return {"subscriptions": output}


@router.get("/summary")
async def subscriptions_summary(db: AsyncSession = Depends(get_db)):
    """KPI agrégés pour le dashboard : MRR, nombre de clients par plan."""
    result = await db.execute(select(Subscription).where(Subscription.status == "active"))
    active_subs = result.scalars().all()

    mrr = sum(float(s.monthly_price or 0) for s in active_subs)
    starter_count = len([s for s in active_subs if s.plan == "starter"])
    pro_count = len([s for s in active_subs if s.plan == "pro"])

    return {
        "mrr": mrr,
        "arr": mrr * 12,
        "total_active": len(active_subs),
        "starter_count": starter_count,
        "pro_count": pro_count,
    }


@router.patch("/{sub_id}")
async def update_subscription(sub_id: str, data: SubscriptionUpdate, db: AsyncSession = Depends(get_db)):
    """Met à jour le plan, statut, ou autres infos d'un abonnement."""
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"success": False, "error": "Abonnement non trouvé"}

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(sub, field, value)

    if "plan" in update_data:
        sub.monthly_price = PLAN_PRICES.get(update_data["plan"], sub.monthly_price)

    await db.commit()
    return {"success": True}
