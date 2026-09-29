"""Human-readable summaries and comparison output."""
from __future__ import annotations

from collections import defaultdict

from .compare import CompareResult
from .models import Activity, KIND_LABEL, format_duration


def summarize(activities: list[Activity]) -> dict:
    """Aggregate counts, distance and duration per kind, plus totals."""
    by_kind: dict[str, dict] = defaultdict(lambda: {"count": 0, "distance_km": 0.0, "duration_s": 0})
    for a in activities:
        b = by_kind[a.kind]
        b["count"] += 1
        b["distance_km"] += a.distance_km
        b["duration_s"] += a.duration_s
    total = {
        "count": len(activities),
        "distance_km": round(sum(a.distance_km for a in activities), 2),
        "duration_s": sum(a.duration_s for a in activities),
    }
    for b in by_kind.values():
        b["distance_km"] = round(b["distance_km"], 2)
    return {"by_kind": dict(by_kind), "total": total}


def render_summary(title: str, activities: list[Activity]) -> str:
    s = summarize(activities)
    lines = [f"== {title} ==", ""]
    lines.append(f"{'Kind':<10} {'Count':>5} {'Distance':>12} {'Time':>10}")
    lines.append("-" * 40)
    for kind, b in sorted(s["by_kind"].items(), key=lambda kv: -kv[1]["count"]):
        lines.append(
            f"{KIND_LABEL.get(kind, kind):<10} {b['count']:>5} "
            f"{b['distance_km']:>9.1f} km {format_duration(b['duration_s']):>10}"
        )
    lines.append("-" * 40)
    t = s["total"]
    lines.append(
        f"{'TOTAL':<10} {t['count']:>5} {t['distance_km']:>9.1f} km "
        f"{format_duration(t['duration_s']):>10}"
    )
    return "\n".join(lines)


def render_comparison(result: CompareResult) -> str:
    lines = ["== Comparison: Activy vs Garmin ==", ""]
    lines.append(
        f"Matched: {len(result.matched)} | "
        f"Missing in Activy: {len(result.only_garmin)} | "
        f"Missing in Garmin: {len(result.only_activy)} | "
        f"Distance mismatches: {len(result.distance_mismatches)}"
    )

    lines.append("")
    lines.append(f"-- Missing in Activy (present in Garmin, not imported) [{len(result.only_garmin)}] --")
    if result.only_garmin:
        for g in sorted(result.only_garmin, key=lambda x: x.start or ""):
            lines.append(f"  {g.date}  {g.raw_type:<18} {g.distance_km:>7.2f} km  {g.duration_hms}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(f"-- Missing in Garmin (present in Activy only) [{len(result.only_activy)}] --")
    if result.only_activy:
        for a in sorted(result.only_activy, key=lambda x: x.start or ""):
            lines.append(f"  {a.date}  {a.raw_type:<18} {a.distance_km:>7.2f} km  {a.duration_hms}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(f"-- Distance mismatches (same activity, different distance) [{len(result.distance_mismatches)}] --")
    if result.distance_mismatches:
        for m in sorted(result.distance_mismatches, key=lambda x: x.activy.start or ""):
            lines.append(
                f"  {m.activy.date}  Activy {m.activy.distance_km:>7.2f} km  "
                f"vs Garmin {m.garmin.distance_km:>7.2f} km  (Δ {m.distance_delta_km:+.2f} km)"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)
