from activy_checker.compare import compare

from .conftest import make_activity as mk


def test_all_matched():
    a = [mk("activy", "2026-09-01", 3600, 30.0)]
    g = [mk("garmin", "2026-09-01", 3600, 30.0)]
    r = compare(a, g)
    assert len(r.matched) == 1
    assert r.only_garmin == [] and r.only_activy == [] and r.distance_mismatches == []


def test_missing_in_activy():
    a = [mk("activy", "2026-09-27", 386, 2.4)]
    g = [mk("garmin", "2026-09-27", 386, 2.38), mk("garmin", "2026-09-27", 12003, 106.23)]
    r = compare(a, g)
    assert len(r.matched) == 1
    assert [x.distance_km for x in r.only_garmin] == [106.23]
    assert r.only_activy == []


def test_missing_in_garmin():
    a = [mk("activy", "2026-09-01", 3600, 10.0)]
    r = compare(a, [])
    assert len(r.only_activy) == 1
    assert r.only_garmin == []


def test_duration_tolerance():
    a = [mk("activy", "2026-09-01", 3600)]
    assert len(compare(a, [mk("garmin", "2026-09-01", 3608)]).matched) == 1
    assert len(compare(a, [mk("garmin", "2026-09-01", 3609)]).matched) == 0
    assert len(compare(a, [mk("garmin", "2026-09-01", 3609)], duration_tolerance_s=10).matched) == 1


def test_different_date_does_not_match():
    r = compare([mk("activy", "2026-09-01", 3600)], [mk("garmin", "2026-09-02", 3600)])
    assert r.matched == []
    assert len(r.only_activy) == 1 and len(r.only_garmin) == 1


def test_distance_mismatch_detected():
    a = [mk("activy", "2026-09-03", 7400, 3.6)]
    g = [mk("garmin", "2026-09-03", 7400, 11.14)]
    r = compare(a, g)
    assert len(r.matched) == 1
    assert len(r.distance_mismatches) == 1
    assert r.distance_mismatches[0].distance_delta_km == -7.54


def test_small_distance_difference_is_not_a_mismatch():
    r = compare([mk("activy", "2026-09-01", 3600, 3.1)], [mk("garmin", "2026-09-01", 3600, 3.06)])
    assert r.distance_mismatches == []


def test_each_garmin_activity_matched_only_once():
    a = [mk("activy", "2026-09-01", 600, id="a1"), mk("activy", "2026-09-01", 600, id="a2")]
    g = [mk("garmin", "2026-09-01", 600, id="g1")]
    r = compare(a, g)
    assert len(r.matched) == 1
    assert len(r.only_activy) == 1


def test_several_activities_same_day_are_paired_by_duration():
    a = [mk("activy", "2026-09-01", 609, id="short"), mk("activy", "2026-09-01", 3813, id="long")]
    g = [mk("garmin", "2026-09-01", 3813, id="g-long"), mk("garmin", "2026-09-01", 609, id="g-short")]
    r = compare(a, g)
    pairs = {m.activy.id: m.garmin.id for m in r.matched}
    assert pairs == {"short": "g-short", "long": "g-long"}


def test_empty_inputs():
    r = compare([], [])
    assert r.matched == [] and r.only_activy == [] and r.only_garmin == []
