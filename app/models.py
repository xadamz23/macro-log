from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.services.macros import Macros


class MacroColumns:
    calories: Mapped[int] = mapped_column(Integer, default=0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)

    @property
    def macros(self) -> Macros:
        return Macros(self.calories, self.protein, self.fat, self.carbs)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64))


class Target(MacroColumns, Base):
    __tablename__ = "targets"
    __table_args__ = (UniqueConstraint("effective_date", name="uq_targets_effective_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class QuickFood(MacroColumns, Base):
    __tablename__ = "quick_foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    serving_label: Mapped[str] = mapped_column(String(50), default="")


class Entry(MacroColumns, Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    name: Mapped[str | None] = mapped_column(String(100))
    servings: Mapped[float] = mapped_column(Float, default=1.0)
    quick_food_id: Mapped[int | None] = mapped_column(
        ForeignKey("quick_foods.id", ondelete="SET NULL")
    )
