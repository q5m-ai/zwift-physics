"""Offline prediction and fitting; explicitly opt-in live collection."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from ._io import load, save
from .experiment import estimated_requests, validate_dataset, validate_plan
from .model import CalibrationModel
from .physics import RiderGeometry


def emit(value):
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("collect-gopher", help="Plan a bounded synthetic experiment; offline unless --execute")
    probe.add_argument("--plan", required=True, type=Path)
    probe.add_argument("--output", type=Path, default=Path("data/gopher-flat-v1.json"))
    probe.add_argument("--max-requests", type=int, default=200)
    probe.add_argument("--interval-seconds", type=float, default=2.)
    probe.add_argument("--execute", action="store_true")
    probe.add_argument("--acknowledge-server-retention", action="store_true")
    fit = commands.add_parser("fit", help="Fit and audit a model using a completed archived dataset, offline")
    fit.add_argument("--data", type=Path, required=True)
    fit.add_argument("--model", type=Path, required=True)
    fit.add_argument("--report", type=Path, required=True)
    check = commands.add_parser("validate-data", help="Offline schema and experimental coverage check")
    check.add_argument("--data", type=Path, required=True)
    predict = commands.add_parser("predict", help="Predict watts or invert for speed using an accepted model")
    predict.add_argument("--model", type=Path, required=True)
    predict.add_argument("--mass-kg", type=float, required=True)
    predict.add_argument("--height-cm", type=float, required=True)
    predict.add_argument("--position", type=int, default=1)
    values = predict.add_mutually_exclusive_group(required=True)
    values.add_argument("--speed-kph", type=float)
    values.add_argument("--watts", type=float)
    predict.add_argument("--allow-extrapolation", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "collect-gopher":
            from .gopher import Budget, collect
            plan = load(args.plan)
            profiles = validate_plan(plan)
            Budget(args.max_requests, args.interval_seconds)  # validation, no networking
            expected = estimated_requests(plan)
            if expected > args.max_requests:
                raise ValueError("The declared request budget is smaller than this experiment")
            if not args.execute:
                emit(dict(mode="dry-run", network_requests_sent=0, expected_requests=expected,
                          max_requests=args.max_requests, interval_seconds=args.interval_seconds,
                          unique_synthetic_profiles=len(profiles), context=plan["context"],
                          note="JSON exports are retained by Gopher. No real profiles, accounts or IDs are used."))
                return 0
            if not args.acknowledge_server_retention:
                raise ValueError("Live collection requires --acknowledge-server-retention as well as --execute")
            result = collect(plan, args.output, maximum=args.max_requests, interval_seconds=args.interval_seconds,
                             progress=lambda message: print(message, file=sys.stderr))
            emit(dict(status=result["status"], requests=result["request_count"], frames=len(result["frames"]), output=str(args.output)))
        elif args.command == "fit":
            from .calibration import fit_dataset, markdown_report
            paths = (args.data, args.model, args.report)
            for index, first in enumerate(paths):
                for second in paths[index+1:]:
                    if first.resolve() == second.resolve() or (first.exists() and second.exists() and first.samefile(second)):
                        raise ValueError("Data, model and report must be distinct files; source observations cannot be overwritten")
            model, report = fit_dataset(load(args.data))
            save(args.model, model)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(markdown_report(model, report), encoding="utf-8")
            emit(model["validation"])
            return 0 if model["validation"]["accepted"] else 1
        elif args.command == "validate-data":
            data = load(args.data)
            profiles = validate_dataset(data)
            emit(dict(valid=True, profiles=len(profiles), frames=len(data["frames"]), context=data["frames"][0]["context"]))
        elif args.command == "predict":
            model = CalibrationModel.from_file(args.model)
            rider = RiderGeometry(args.mass_kg, args.height_cm)
            if args.speed_kph is not None:
                speed = args.speed_kph
                watts = model.power_watts(rider, speed, args.position, allow_extrapolation=args.allow_extrapolation)
            else:
                watts = args.watts
                speed = model.speed_kph(rider, watts, args.position, allow_extrapolation=args.allow_extrapolation)
            components = model.coefficients(rider, allow_extrapolation=args.allow_extrapolation).power(speed/3.6, args.position)
            domain = model.specification["domain"]
            in_domain = all(lo <= value <= hi for (lo, hi), value in [
                (domain["mass_kg"], args.mass_kg), (domain["height_cm"], args.height_cm), (domain["speed_kph"], speed)])
            emit(dict(speed_kph=speed, power_watts=watts, position=args.position, cubic_watts=components.cubic_watts,
                      linear_watts=components.linear_watts, within_calibration_envelope=in_domain,
                      context=model.specification["context"],
                      caveat="Calculator-calibrated steady-flat mechanics, not independent in-game or physiological validation."))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
