from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import get_db
from app.models.prospect import Prospect

router = APIRouter(prefix="/prospects", tags=["prospects"])


class ProspectIn(BaseModel):
    name: str
    contact: str | None = None
    email: str | None = None
    phone: str | None = None
    ville: str | None = None
    website: str | None = None
    rating: str | None = None
    place_id: str | None = None
    source: str | None = "import"


class ProspectBulkImport(BaseModel):
    prospects: list[ProspectIn]


class ProspectUpdate(BaseModel):
    status: str | None = None
    seq: str | None = None
    ouvert: bool | None = None
    email: str | None = None
    contact: str | None = None
    notes: str | None = None


@router.post("/import")
async def import_prospects(data: ProspectBulkImport, db: AsyncSession = Depends(get_db)):
    """
    Import en masse — évite les doublons par nom + ville.
    Utilisé par le dashboard pour pousser les résultats Google Places.
    """
    added = 0
    skipped = 0

    for p in data.prospects:
        # Vérifie l'existence par nom (et ville si fournie)
        query = select(Prospect).where(Prospect.name == p.name)
        if p.ville:
            query = query.where(Prospect.ville == p.ville)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        prospect = Prospect(
            name=p.name,
            contact=p.contact,
            email=p.email,
            phone=p.phone,
            ville=p.ville,
            website=p.website,
            rating=p.rating,
            place_id=p.place_id,
            source=p.source,
            status="contacte",
            seq="À envoyer",
            ouvert=False,
        )
        db.add(prospect)
        added += 1

    await db.commit()
    return {"success": True, "added": added, "skipped": skipped, "total_submitted": len(data.prospects)}


@router.get("")
async def list_prospects(
    status: str | None = None,
    search: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Liste paginée des prospects, avec filtres optionnels."""
    query = select(Prospect).order_by(Prospect.created_at.desc())

    if status and status != "tous":
        query = query.where(Prospect.status == status)
    if search:
        like = f"%{search}%"
        query = query.where((Prospect.name.ilike(like)) | (Prospect.ville.ilike(like)))

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    prospects = result.scalars().all()

    return {
        "prospects": [
            {
                "id": p.id,
                "name": p.name,
                "contact": p.contact,
                "email": p.email,
                "phone": p.phone,
                "ville": p.ville,
                "website": p.website,
                "rating": p.rating,
                "status": p.status,
                "seq": p.seq,
                "ouvert": p.ouvert,
                "source": p.source,
            }
            for p in prospects
        ]
    }


@router.get("/count")
async def count_prospects(db: AsyncSession = Depends(get_db)):
    """Compte total + par statut, pour les KPI du dashboard."""
    result = await db.execute(select(Prospect.status, func.count(Prospect.id)).group_by(Prospect.status))
    counts = dict(result.all())
    total_result = await db.execute(select(func.count(Prospect.id)))
    total = total_result.scalar()

    return {
        "total": total,
        "contacte": counts.get("contacte", 0),
        "relance": counts.get("relance", 0),
        "rdv": counts.get("rdv", 0),
        "signe": counts.get("signe", 0),
    }


@router.patch("/{prospect_id}")
async def update_prospect(prospect_id: str, data: ProspectUpdate, db: AsyncSession = Depends(get_db)):
    """Met à jour le statut/email/etc d'un prospect."""
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalar_one_or_none()
    if not prospect:
        return {"success": False, "error": "Prospect non trouvé"}

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prospect, field, value)

    await db.commit()
    return {"success": True}


@router.delete("/{prospect_id}")
async def delete_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalar_one_or_none()
    if not prospect:
        return {"success": False, "error": "Prospect non trouvé"}
    await db.delete(prospect)
    await db.commit()
    return {"success": True}
