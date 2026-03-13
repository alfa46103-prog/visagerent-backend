# Файл: app/models/report.py
# Назначение: Предрасчитанные отчёты для быстрой загрузки в админке.
# Содержат сводные данные по продажам, расходам и т.д.

from sqlalchemy import (
    String, Integer, Numeric, Date, ForeignKey, JSON, Enum, UniqueConstraint, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import date, datetime

from app.core.database import Base


class ReportType(str, enum.Enum):
    """Типы отчётов."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, name="report_type", create_type=False),
        nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    point_id: Mapped[int | None] = mapped_column(
        ForeignKey("points.id")
    )
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    expenses_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict] = mapped_column(JSON, default={})
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization")
    point = relationship("Point")

    __table_args__ = (
        UniqueConstraint("org_id", "report_type", "period_start", "point_id", name="uq_report_org_type_period_point"),
    )