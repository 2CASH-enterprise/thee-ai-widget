import httpx
from app.config import settings


def build_lead_summary_html(lead) -> str:
    """
    Construit le HTML du résumé structuré — réutilisé pour l'email
    et pour la génération PDF (même contenu, deux formats de sortie).
    """
    nom_complet = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Non renseigné"

    def row(label, value):
        display = value if value else '<span style="color:#999">Non renseigné</span>'
        return f"""
        <tr>
            <td style="padding:10px 16px;border-bottom:1px solid #eee;color:#666;font-size:13px;width:140px">{label}</td>
            <td style="padding:10px 16px;border-bottom:1px solid #eee;color:#1a1a2e;font-size:14px;font-weight:500">{display}</td>
        </tr>
        """

    intent_label = {"achat": "Achat", "location": "Location"}.get(lead.intent, lead.intent or None)

    return f"""
    <div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#1a56db;color:#fff;padding:20px 24px;border-radius:12px 12px 0 0">
            <div style="font-size:12px;opacity:.8;text-transform:uppercase;letter-spacing:1px">Nouveau lead qualifié — Sarah AI</div>
            <div style="font-size:20px;font-weight:700;margin-top:4px">{nom_complet}</div>
        </div>
        <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px;overflow:hidden">
            {row("Email", lead.email)}
            {row("Téléphone", lead.phone)}
            {row("Projet", intent_label)}
            {row("Budget", lead.budget)}
            {row("Secteur", lead.location_pref)}
            {row("Type de bien", lead.property_type)}
            {row("Délai", lead.delai)}
            {row("RDV pris", "✅ Oui" if lead.rdv_scheduled else "Pas encore")}
        </table>
        {f'<div style="margin-top:12px;padding:14px 16px;background:#f8f9fb;border-radius:8px;font-size:13px;color:#555"><strong>Notes :</strong> {lead.notes}</div>' if lead.notes else ''}
    </div>
    """


async def notify_agency_new_lead(lead) -> None:
    """Envoie un email à l'agence quand un nouveau lead est qualifié."""
    if not settings.sendgrid_api_key:
        print(f"[EMAIL SKIPPED] Nouveau lead : {lead.email}")
        return

    body = build_lead_summary_html(lead)

    payload = {
        "personalizations": [{"to": [{"email": settings.from_email}]}],
        "from": {"email": settings.from_email},
        "subject": f"🏠 Nouveau lead qualifié — {lead.first_name or lead.email}",
        "content": [{"type": "text/html", "value": body}],
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            timeout=10,
        )
