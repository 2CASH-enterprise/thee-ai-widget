from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(100))  # chat | prospects | tracking | pdf | autre
    error_type: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)  # JSON stringifié, infos additionnelles
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
