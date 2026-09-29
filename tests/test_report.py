from activy_checker.compare import compare
from activy_checker.report import render_comparison, render_summary, summarize

from .conftest import make_activity as mk


def sample():
    return [
        mk("activy", "2026-09-01", 3600, 40.0, kind="bike"),
        mk("activy", "2026-09-02", 1800, 20.5, kind="bike"),
        mk("activy", "2026-09-02", 1200, 3.0, kind="run"),
        mk("activy", "2026-09-03", 600, 0.0, kind="exercise"),
    ]


def test_summarize_totals():
    s = summarize(sample())
    assert s["total"] == {"count": 4, "distance_km": 63.5, "duration_s": 7200}
    assert s["by_kind"]["bike"]["count"] == 2
    assert s["by_kind"]["bike"]["distance_km"] == 60.5
    assert s["by_kind"]["run"]["duration_s"] == 1200


def test_summarize_empty():
    s = summarize([])
    assert s["total"] == {"count": 0, "distance_km": 0, "duration_s": 0}
    assert s["by_kind"] == {}


def test_render_summary_contains_rows_and_total():
    out = render_summary("Activy", sample())
    assert "== Activy ==" in out
    assert "Bike" in out and "Run" in out and "Exercise" in out
    assert "TOTAL" in out
    assert "63.5 km" in out
    assert "2:00:00" in out


def test_render_comparison_lists_differences():
    a = [mk("activy", "2026-09-03", 7400, 3.6)]
    g = [mk("garmin", "2026-09-03", 7400, 11.14), mk("garmin", "2026-09-27", 12003, 106.23)]
    out = render_comparison(compare(a, g))
    assert "Missing in Activy: 1" in out
    assert "106.23 km" in out
    assert "3:20:03" in out
    assert "-7.54 km" in out


def test_render_comparison_no_differences():
    a = [mk("activy", "2026-09-01", 3600, 10.0)]
    g = [mk("garmin", "2026-09-01", 3600, 10.0)]
    out = render_comparison(compare(a, g))
    assert out.count("(none)") == 3
