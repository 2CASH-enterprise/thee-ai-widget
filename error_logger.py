from sqlalchemy.ext.asyncio import AsyncSession
from app.models.errorlog import ErrorLog
import json
import traceback


async def log_error(db: AsyncSession, source: str, error: Exception, context: dict | None = None):
    """
    Enregistre une erreur en base pour qu'elle soit visible depuis le
    dashboard de monitoring. N'interrompt jamais le flux principal —
    si le logging échoue, on l'ignore silencieusement plutôt que de
    faire planter la requête originale.
    """
    try:
        entry = ErrorLog(
            source=source,
            error_type=type(error).__name__,
            message=str(error)[:2000],
            context=json.dumps(context, default=str)[:2000] if context else None,
        )
        db.add(entry)
        await db.commit()
    except Exception:
        pass  # le logging d'erreur ne doit jamais lui-même faire planter l'app
