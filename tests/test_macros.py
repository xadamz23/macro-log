from app.services.macros import MACRO_KEYS, Macros, build_bars, calories_from


def test_calories_from_uses_4_4_9():
    assert calories_from(protein=30, fat=10, carbs=50) == 410


def test_add_and_scale():
    a = Macros(200, 20, 10, 30)
    assert a + Macros(100, 5.5, 0, 10) == Macros(300, 25.5, 10, 40)
    assert a.scaled(1.5) == Macros(300, 30.0, 15.0, 45.0)


def test_is_zero():
    assert Macros().is_zero()
    assert not Macros(carbs=1).is_zero()


def test_bars_under_target():
    bars = build_bars(Macros(1500, 100, 50, 150), Macros(2000, 150, 70, 200))
    assert [b.key for b in bars] == list(MACRO_KEYS)
    cal = bars[0]
    assert cal.label == "Calories" and cal.unit == "kcal"
    assert cal.pct == 75.0
    assert cal.remaining == 500
    assert not cal.over


def test_bars_over_target_caps_pct():
    cal = build_bars(Macros(2500), Macros(2000))[0]
    assert cal.pct == 100.0
    assert cal.remaining == -500
    assert cal.over


def test_bars_without_targets():
    cal = build_bars(Macros(500), None)[0]
    assert cal.target is None
    assert cal.pct == 0.0
    assert cal.remaining is None
    assert not cal.over


def test_zero_target_does_not_divide_by_zero():
    carbs = build_bars(Macros(carbs=10), Macros(2000, 150, 70, 0))[3]
    assert carbs.pct == 0.0
    assert carbs.over
