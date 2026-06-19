from sqlalchemy import String, Text, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(500), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    contact: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    ville: Mapped[str | None] = mapped_column(String(150))
    website: Mapped[str | None] = mapped_column(String(1000))
    rating: Mapped[str | None] = mapped_column(String(10))
    place_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="contacte")  # contacte | relance | rdv | signe
    seq: Mapped[str | None] = mapped_column(String(100), default="À envoyer")
    ouvert: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str | None] = mapped_column(String(50))  # google | import | manuel
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
