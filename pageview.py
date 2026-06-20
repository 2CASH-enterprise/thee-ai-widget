from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base
import uuid


class PageView(Base):
    __tablename__ = "page_views"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    page: Mapped[str] = mapped_column(String(100), default="landing")
    event: Mapped[str] = mapped_column(String(50))  # pageview | scroll_50 | scroll_90 | cta_click | demo_started
    referrer: Mapped[str | None] = mapped_column(String(500))
    user_agent: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
