from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.lead import Lead
from app.services.email import build_lead_summary_html

router = APIRouter(prefix="/leads", tags=["leads-pdf"])


@router.get("/{lead_id}/pdf")
async def get_lead_summary_pdf(lead_id: str, db: AsyncSession = Depends(get_db)):
    """
    Génère un PDF imprimable du résumé structuré d'un lead.
    Utile pour l'agence qui veut imprimer la fiche avant un rendez-vous.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")

    html_content = build_lead_summary_html(lead)
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"/>
    <style>
        @page {{ size: A4; margin: 30mm 20mm; }}
        body {{ font-family: -apple-system, sans-serif; }}
    </style>
    </head>
    <body>{html_content}</body>
    </html>
    """

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=full_html).write_pdf()
    except ImportError:
        raise HTTPException(status_code=501, detail="Génération PDF non disponible sur ce serveur")

    nom = (lead.first_name or "lead").replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fiche-{nom}.pdf"},
    )
