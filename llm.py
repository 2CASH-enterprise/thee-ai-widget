from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def chat_completion(
    messages: list[dict],
    system_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 400,
) -> str:
    """
    Appelle l'API OpenAI avec l'historique complet de conversation.
    Retourne uniquement le texte de la réponse.
    """
    response = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages,
        ],
    )
    return response.choices[0].message.content


async def generate_lead_summary(conversation_text: str) -> dict:
    """
    Génère un résumé structuré (JSON) à partir d'une conversation,
    pour le Plan Pro. N'invente rien — met null si l'info n'a pas
    été explicitement donnée par le visiteur.
    """
    from app.core.prompts import SUMMARY_PROMPT
    import json

    prompt = SUMMARY_PROMPT.format(conversation=conversation_text)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=400,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Tu réponds uniquement en JSON valide, rien d'autre."},
            {"role": "user", "content": prompt},
        ],
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, AttributeError):
        return {
            "prenom": None, "email": None, "telephone": None,
            "type_projet": None, "budget": None, "secteur": None,
            "type_bien": None, "delai": None,
            "notes_libres": "Erreur lors de la génération du résumé.",
        }


async def detect_intent(user_message: str) -> str:
    """
    Détecte l'intention de l'utilisateur avec un LLM léger.
    Retourne : achat | location | visite | question | contact
    """
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=10,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classifie ce message immobilier en UN seul mot parmi : "
                    "achat, location, visite, question, contact. "
                    "Réponds uniquement avec ce mot, rien d'autre."
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip().lower()
