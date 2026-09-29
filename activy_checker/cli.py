"""Command-line entry point for activy-checker."""
from __future__ import annotations

import argparse
import datetime
import getpass
import json
import sys

from .activy import ActivyClient, ActivyError
from .compare import compare
from .garmin import GarminClient, GarminError
from .models import Activity
from .report import render_comparison, render_summary, summarize


def _default_since() -> str:
    return (datetime.date.today() - datetime.timedelta(days=30)).isoformat()


def _prompt(label: str, value: str | None) -> str:
    return value if value else input(label).strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="activy-checker",
        description="Compare your Garmin activities against what Activy imported.",
    )
    p.add_argument("--since", default=_default_since(),
                   help="Start date YYYY-MM-DD (default: 30 days ago)")
    p.add_argument("--until", default=datetime.date.today().isoformat(),
                   help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--activy-email", default=None, help="Activy email (else prompted)")
    p.add_argument("--garmin-email", default=None, help="Garmin email (else prompted)")
    p.add_argument("--activy-only", action="store_true",
                   help="Only fetch and summarize Activy (skip Garmin and comparison)")
    p.add_argument("--garmin-tokenstore", default=None,
                   help="Path to cache the Garmin session (avoids repeated MFA)")
    p.add_argument("--json", dest="json_out", default=None,
                   help="Write the full result as JSON to this path")
    return p


def _activity_dict(a: Activity) -> dict:
    return {
        "source": a.source, "id": a.id, "date": a.date, "start": a.start,
        "kind": a.kind, "raw_type": a.raw_type,
        "distance_km": a.distance_km, "duration_s": a.duration_s,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # --- Activy ---
    print(f"Fetching Activy activities since {args.since} ...", file=sys.stderr)
    activy = ActivyClient()
    try:
        email = _prompt("Activy email: ", args.activy_email)
        password = getpass.getpass("Activy password (hidden): ")
        activy.login(email, password)
        activy_acts = activy.get_activities(args.since)
    except ActivyError as e:
        print(f"Activy error: {e}", file=sys.stderr)
        return 2
    activy_acts = [a for a in activy_acts if args.since <= a.date <= args.until]
    print(render_summary("Activy", activy_acts))

    if args.activy_only:
        if args.json_out:
            _write_json(args.json_out, activy_acts, None, None)
        return 0

    # --- Garmin ---
    print(f"\nFetching Garmin activities since {args.since} ...", file=sys.stderr)
    garmin = GarminClient(tokenstore=args.garmin_tokenstore)
    try:
        gemail = _prompt("Garmin email: ", args.garmin_email)
        gpass = getpass.getpass("Garmin password (hidden): ") if not args.garmin_tokenstore else None
        garmin.login(gemail, gpass)
        garmin_acts = garmin.get_activities(args.since, args.until)
    except GarminError as e:
        print(f"Garmin error: {e}", file=sys.stderr)
        return 3
    garmin_acts = [a for a in garmin_acts if args.since <= a.date <= args.until]
    print()
    print(render_summary("Garmin", garmin_acts))

    # --- comparison ---
    result = compare(activy_acts, garmin_acts)
    print()
    print(render_comparison(result))

    if args.json_out:
        _write_json(args.json_out, activy_acts, garmin_acts, result)
        print(f"\nJSON written to {args.json_out}", file=sys.stderr)
    return 0


def _write_json(path, activy_acts, garmin_acts, result) -> None:
    out = {
        "activy": {
            "summary": summarize(activy_acts),
            "activities": [_activity_dict(a) for a in activy_acts],
        }
    }
    if garmin_acts is not None:
        out["garmin"] = {
            "summary": summarize(garmin_acts),
            "activities": [_activity_dict(a) for a in garmin_acts],
        }
    if result is not None:
        out["comparison"] = {
            "matched": len(result.matched),
            "missing_in_activy": [_activity_dict(g) for g in result.only_garmin],
            "missing_in_garmin": [_activity_dict(a) for a in result.only_activy],
            "distance_mismatches": [
                {"date": m.activy.date, "activy_km": m.activy.distance_km,
                 "garmin_km": m.garmin.distance_km, "delta_km": m.distance_delta_km}
                for m in result.distance_mismatches
            ],
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
