from app.templating import spark_paths


def test_spark_paths_skips_gaps_and_scales_to_box():
    p = spark_paths([10, None, 20, 15], width=30, height=20)
    assert p["line"] == "M0.0 17.0 L20.0 3.0 L30.0 10.0"
    assert p["area"].endswith("L30.0 20 L0.0 20 Z")


def test_spark_paths_needs_two_points():
    assert spark_paths([None, 5, None]) is None
    assert spark_paths([]) is None


def test_spark_paths_flat_line():
    assert spark_paths([5, 5], width=10, height=10)["line"] == "M0.0 3.0 L10.0 3.0"
