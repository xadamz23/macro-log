from dataclasses import dataclass

MACRO_KEYS = ("calories", "protein", "fat", "carbs")
MACRO_META = {
    "calories": ("Calories", "kcal"),
    "protein": ("Protein", "g"),
    "fat": ("Fat", "g"),
    "carbs": ("Carbs", "g"),
}


def calories_from(protein: float, fat: float, carbs: float) -> int:
    return round(4 * protein + 4 * carbs + 9 * fat)


@dataclass(frozen=True)
class Macros:
    calories: int = 0
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0

    def __add__(self, other: "Macros") -> "Macros":
        return Macros(
            self.calories + other.calories,
            round(self.protein + other.protein, 1),
            round(self.fat + other.fat, 1),
            round(self.carbs + other.carbs, 1),
        )

    def scaled(self, factor: float) -> "Macros":
        return Macros(
            round(self.calories * factor),
            round(self.protein * factor, 1),
            round(self.fat * factor, 1),
            round(self.carbs * factor, 1),
        )

    def is_zero(self) -> bool:
        return not any((self.calories, self.protein, self.fat, self.carbs))


@dataclass(frozen=True)
class MacroBar:
    key: str
    label: str
    unit: str
    consumed: float
    target: float | None

    @property
    def pct(self) -> float:
        if not self.target:
            return 0.0
        return min(self.consumed / self.target * 100, 100.0)

    @property
    def remaining(self) -> float | None:
        if self.target is None:
            return None
        return round(self.target - self.consumed, 1)

    @property
    def over(self) -> bool:
        return self.target is not None and self.consumed > self.target


def build_bars(consumed: Macros, target: Macros | None) -> list[MacroBar]:
    return [
        MacroBar(
            key,
            *MACRO_META[key],
            consumed=getattr(consumed, key),
            target=None if target is None else getattr(target, key),
        )
        for key in MACRO_KEYS
    ]
