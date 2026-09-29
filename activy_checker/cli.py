"""Command-line entry point for activy-checker."""
from __future__ import annotations

import argparse
import datetime
import getpass
import json
import sys

from .activy import ActivyClient, ActivyError
from .compare import compare
from .garmin import GarminClient
from .models import KIND_STEPS, Activity
from .progress import Spinner
from .report import render_comparison, render_summary, summarize


DEFAULT_SINCE = "2026-09-01"


def _prompt(label: str, value: str | None) -> str:
    """Return ``value`` or ask for it. The prompt goes to stderr so stdout stays a clean report."""
    if value:
        return value
    sys.stderr.write(label)
    sys.stderr.flush()
    return input().strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="activy-checker",
        description="Compare your Garmin activities against what Activy imported.",
    )
    p.add_argument("--since", default=DEFAULT_SINCE,
                   help=f"Start date YYYY-MM-DD (default: {DEFAULT_SINCE})")
    p.add_argument("--until", default=datetime.date.today().isoformat(),
                   help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--activy-email", default=None, help="Activy email (else prompted)")
    p.add_argument("--garmin-email", default=None, help="Garmin email (else prompted)")
    p.add_argument("--activy-only", action="store_true",
                   help="Only fetch and summarize Activy (skip Garmin and comparison)")
    p.add_argument("--garmin-tokenstore", default=None,
                   help="Directory or .json file to cache the Garmin session (avoids repeated MFA)")
    p.add_argument("--include-steps", action="store_true",
                   help="Keep Activy step-count entries (excluded by default: they have no Garmin activity)")
    p.add_argument("--duration-tolerance", type=int, default=8, metavar="SECONDS",
                   help="Max duration difference for two activities to match (default: 8)")
    p.add_argument("--distance-tolerance", type=float, default=0.5, metavar="KM",
                   help="Distance difference above which a match is reported as a mismatch (default: 0.5)")
    p.add_argument("--json", dest="json_out", default=None,
                   help="Write the full result as JSON to this path")
    p.add_argument("--verbose", action="store_true",
                   help="Show the Garmin library's sign-in messages (hidden by default)")
    return p


MFA_PROMPT = ("Garmin has sent you a verification code (check your email).\n"
              "Enter the code to continue: ")


def _activy_progress(p: dict, since: str) -> str:
    contest = f" (contest {p['contest']}/{p['contests']})" if p["contests"] > 1 else ""
    reached = f", reached {p['reached']}" if p["reached"] else ""
    return (f"Scanning Activy feed{contest}: page {p['page']}, "
            f"{p['found']} of yours so far{reached} (going back to {since}) ...")


def _activity_dict(a: Activity) -> dict:
    return {
        "source": a.source, "id": a.id, "date": a.date, "start": a.start,
        "kind": a.kind, "raw_type": a.raw_type,
        "distance_km": a.distance_km, "duration_s": a.duration_s,
    }


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


def _run(argv: list[str] | None) -> int:
    args = build_parser().parse_args(argv)

    # --- Activy ---
    print(f"Fetching Activy activities since {args.since}.", file=sys.stderr)
    activy = ActivyClient()
    try:
        email = _prompt("Activy email: ", args.activy_email)
        password = getpass.getpass("Activy password (hidden): ")
        with Spinner("Signing in to Activy ...") as sp:
            activy.login(email, password)
            sp.update("Looking up your Activy contests ...")
            activy_acts = activy.get_activities(
                args.since, progress=lambda p: sp.update(_activy_progress(p, args.since)))
    except (ActivyError, OSError, ValueError) as e:  # OSError covers network errors
        print(f"Activy error: {e}", file=sys.stderr)
        return 2
    activy_acts = [a for a in activy_acts if args.since <= a.date <= args.until]
    if not args.include_steps:
        activy_acts = [a for a in activy_acts if a.kind != KIND_STEPS]
    if not activy_acts:
        print("Warning: no Activy activities found in this date range. If you expected some, "
              "see docs/troubleshooting.md#activy-returns-no-activities", file=sys.stderr)
    print(render_summary("Activy", activy_acts))

    if args.activy_only:
        if args.json_out:
            _write_json(args.json_out, activy_acts, None, None)
        return 0

    # --- Garmin ---
    print(f"\nFetching Garmin activities since {args.since}.", file=sys.stderr)
    garmin = GarminClient(tokenstore=args.garmin_tokenstore, quiet=not args.verbose)
    try:
        with Spinner("Checking for a saved Garmin session ..."):
            resumed = garmin.try_resume()
        if resumed:
            print("Resumed saved Garmin session.", file=sys.stderr)
        else:
            gemail = _prompt("Garmin email: ", args.garmin_email)
            gpass = getpass.getpass("Garmin password (hidden): ")
            # No spinner here: garminconnect may ask for an MFA code and print
            # its own messages, which an animated line would overwrite.
            print("Signing in to Garmin (this can take a moment) ...", file=sys.stderr)
            garmin.login(gemail, gpass, mfa_prompt=lambda: _prompt(MFA_PROMPT, None))
        with Spinner(f"Fetching Garmin activities {args.since} .. {args.until} ..."):
            garmin_acts = garmin.get_activities(args.since, args.until)
    except Exception as e:  # garminconnect raises its own exception types
        print(f"Garmin error: {e}", file=sys.stderr)
        if garmin.log and not args.verbose:
            print("Garmin sign-in details:", file=sys.stderr)
            for line in garmin.log[-5:]:
                print(f"  {line}", file=sys.stderr)
        return 3
    garmin_acts = [a for a in garmin_acts if args.since <= a.date <= args.until]
    print()
    print(render_summary("Garmin", garmin_acts))

    # --- comparison ---
    result = compare(activy_acts, garmin_acts,
                     duration_tolerance_s=args.duration_tolerance,
                     distance_tolerance_km=args.distance_tolerance)
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
