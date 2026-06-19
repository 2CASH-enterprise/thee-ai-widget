from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import get_db
from app.models.prospect import Prospect

router = APIRouter(prefix="/prospects", tags=["prospects"])


class ProspectIn(BaseModel):
    name: str
    address: str | None = None
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
    Import en masse — évite les doublons par nom + adresse.
    Résilient : une ligne défaillante (champ trop long, etc.) est ignorée
    sans faire échouer tout le lot.
    """
    added = 0
    skipped = 0
    errors = 0

    for p in data.prospects:
        try:
            # Déduplication précise : nom + adresse (deux agences au même nom
            # mais adresses différentes sont bien deux prospects distincts).
            query = select(Prospect).where(Prospect.name == (p.name or "")[:500])
            if p.address:
                query = query.where(Prospect.address == p.address[:500])
            elif p.ville:
                query = query.where(Prospect.ville == p.ville[:150])
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            # Troncature défensive — évite tout dépassement de colonne,
            # peu importe la longueur de la donnée source (ex: URL avec UTM).
            prospect = Prospect(
                name=(p.name or "")[:500],
                address=(p.address or None) and p.address[:500],
                contact=(p.contact or None) and p.contact[:150],
                email=(p.email or None) and p.email[:255],
                phone=(p.phone or None) and p.phone[:50],
                ville=(p.ville or None) and p.ville[:150],
                website=(p.website or None) and p.website[:1000],
                rating=(p.rating or None) and str(p.rating)[:10],
                place_id=(p.place_id or None) and p.place_id[:255],
                source=p.source,
                status="contacte",
                seq="À envoyer",
                ouvert=False,
            )
            db.add(prospect)
            await db.flush()  # détecte une éventuelle erreur SQL ligne par ligne
            added += 1
        except Exception:
            await db.rollback()
            errors += 1
            continue

    await db.commit()
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total_submitted": len(data.prospects),
    }


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
                "address": p.address,
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
