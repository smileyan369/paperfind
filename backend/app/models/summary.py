import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), unique=True
    )
    summary_cn: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points_cn: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")

    # Full-text extraction metadata
    source_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="pdf / html / abstract / metadata"
    )
    source_chars: Mapped[int] = mapped_column(Integer, default=0,
        comment="Number of characters extracted from the source"
    )

    generated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True, default=func.now()
    )

    paper = relationship("Paper", back_populates="summary")
