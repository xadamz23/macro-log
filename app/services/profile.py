"""The one-row "about me" profile that gives exported data its context."""

from dataclasses import dataclass, fields

from sqlalchemy.orm import Session

from app.models import Profile

_ROW_ID = 1

SEXES = {"male": "Male", "female": "Female"}
GOALS = {
    "lean_bulk": "Lean bulk (build muscle, slow gain)",
    "recomp": "Recomp (build muscle, hold weight)",
    "maintain": "Maintain",
    "cut": "Cut (lose fat, keep muscle)",
}
TRAINING_PLACEHOLDER = "Lifting ~4 h/week, hypertrophy focus"


@dataclass(frozen=True)
class ProfileData:
    sex: str | None = None
    birth_year: int | None = None
    height_in: float | None = None
    goal: str | None = None
    training: str | None = None
    activity: str | None = None
    notes: str | None = None

    def is_empty(self) -> bool:
        return all(getattr(self, f.name) is None for f in fields(self))


def get_profile(db: Session) -> ProfileData:
    row = db.get(Profile, _ROW_ID)
    if row is None:
        return ProfileData()
    return ProfileData(**{f.name: getattr(row, f.name) for f in fields(ProfileData)})


def save_profile(db: Session, data: ProfileData) -> None:
    row = db.get(Profile, _ROW_ID)
    if row is None:
        row = Profile(id=_ROW_ID)
        db.add(row)
    for f in fields(ProfileData):
        setattr(row, f.name, getattr(data, f.name))
    db.commit()
