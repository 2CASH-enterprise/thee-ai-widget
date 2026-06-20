from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.conversation import Message
from app.models.lead import Lead
from app.core.llm import chat_completion, detect_intent, generate_lead_summary
from app.core.prompts import build_system_prompt, SAMPLE_LISTINGS
from app.services.email import notify_agency_new_lead
from app.core.error_logger import log_error
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    agency_id: str = "default"
    agency_name: str = "Notre Agence Immobilière"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    intent: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await _handle_chat(req, db)
    except Exception as e:
        await log_error(db, source="chat", error=e, context={"session_id": req.session_id, "agency_id": req.agency_id})
        raise HTTPException(status_code=500, detail="Une erreur est survenue, réessayez dans un instant.")


async def _handle_chat(req: ChatRequest, db: AsyncSession) -> ChatResponse:
    # 1. Récupérer l'historique de la session (20 derniers messages)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == req.session_id)
        .order_by(Message.created_at.asc())
        .limit(20)
    )
    history = result.scalars().all()

    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": req.message})

    # 2. Détecter l'intention (en parallèle pour ne pas ralentir)
    intent = await detect_intent(req.message)

    # 3. Construire le system prompt avec les annonces de l'agence
    system_prompt = build_system_prompt(
        agency_name=req.agency_name,
        listings=SAMPLE_LISTINGS,  # TODO: charger depuis DB selon agency_id
        agency_info="",
        calendly_url=settings.calendly_event_url,
    )

    # 4. Appel LLM
    reply = await chat_completion(messages=messages, system_prompt=system_prompt)

    # 5. Persister user message + réponse
    db.add(Message(session_id=req.session_id, role="user", content=req.message, agency_id=req.agency_id))
    db.add(Message(session_id=req.session_id, role="assistant", content=reply, agency_id=req.agency_id))

    # 6. Créer ou mettre à jour le lead
    lead_result = await db.execute(
        select(Lead).where(Lead.session_id == req.session_id)
    )
    lead = lead_result.scalar_one_or_none()
    if not lead:
        lead = Lead(session_id=req.session_id, agency_id=req.agency_id, intent=intent)
        db.add(lead)
    elif intent and intent != "question":
        lead.intent = intent

    await db.commit()

    # 7. Si un email apparaît dans ce message et qu'on n'a pas encore généré
    #    de résumé structuré pour ce lead, on le fait maintenant (Plan Pro).
    import re
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', req.message)
    if email_match and not lead.email:
        lead.email = email_match.group(0)

        # Génère le résumé structuré à partir de toute la conversation
        full_conversation = "\n".join([f"{m['role']}: {m['content']}" for m in messages] + [f"assistant: {reply}"])
        summary = await generate_lead_summary(full_conversation)

        if summary.get("prenom"):
            lead.first_name = summary["prenom"]
        if summary.get("telephone"):
            lead.phone = summary["telephone"]
        if summary.get("type_projet"):
            lead.intent = summary["type_projet"]
        if summary.get("budget"):
            lead.budget = summary["budget"]
        if summary.get("secteur"):
            lead.location_pref = summary["secteur"]
        if summary.get("type_bien"):
            lead.property_type = summary["type_bien"]
        if summary.get("delai"):
            lead.delai = summary["delai"]
        if summary.get("notes_libres"):
            lead.notes = summary["notes_libres"]

        await db.commit()

        # Notifie l'agence avec le résumé structuré
        await notify_agency_new_lead(lead)

    return ChatResponse(reply=reply, session_id=req.session_id, intent=intent)
