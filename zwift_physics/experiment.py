"""Predeclared synthetic experiment design and response allowlisting."""
from __future__ import annotations
import re
from ._io import digest, number


class ContractError(ValueError):
    """Stop collection; never silently reinterpret an unexpected response."""


def validate_plan(plan):
    fields = {"schema_version", "experiment_id", "expected_calculator_version", "synthetic_only", "context",
              "probe_ftp_w", "active_pull_seconds", "fit_speeds_kph", "blind_speeds_kph", "body_candidates",
              "linear_candidates", "selection_tolerance_w", "acceptance_max_error_w", "batches", "ftp_invariance"}
    if set(plan) != fields:
        raise ValueError("Unknown or missing experiment fields; personal metadata is not permitted")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", plan["experiment_id"]):
        raise ValueError("Use a simple public experiment identifier")
    if type(plan.get("schema_version")) is not int or plan.get("schema_version") != 1 or plan.get("synthetic_only") is not True:
        raise ValueError("Only version-1, explicitly synthetic experiments are supported")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", plan.get("expected_calculator_version", "")):
        raise ValueError("Pin an observed calculator version")
    context = plan["context"]
    if set(context) != {"route_signature", "route_name", "laps", "efficiency", "intensity", "team_size"}:
        raise ValueError("Unknown or missing context fields")
    if not re.fullmatch(r"[0-9]{1,10}", context["route_signature"]):
        raise ValueError("Use an explicit game route signature, never a moving 'next race' alias")
    if context["laps"] != 1 or context["team_size"] != 5:
        raise ValueError("This milestone measures one-lap, five-rider contexts only")
    if context["efficiency"] != 0 or context["intensity"] != 0:
        raise ValueError("Version-1 protocol pins manual efficiency and intensity to zero")
    if not 100 <= number(plan["probe_ftp_w"]) <= 600 or plan["active_pull_seconds"] != 120:
        raise ValueError("Unsupported probe normalization or pull duration")
    fit_speeds = plan["fit_speeds_kph"]
    blind_speeds = plan["blind_speeds_kph"]
    if len(fit_speeds) < 2 or not blind_speeds or set(fit_speeds) & set(blind_speeds):
        raise ValueError("Separate fit and blind speeds are required")
    speeds = fit_speeds + blind_speeds
    if len(set(speeds)) != len(speeds) or any(not 10 <= number(v) <= 60 for v in speeds):
        raise ValueError("Invalid or duplicate speeds")
    profiles = {}
    for batch in plan["batches"]:
        if len(batch) != 5 or len({p["id"] for p in batch}) != 5:
            raise ValueError("Each batch must have five distinct synthetic profiles")
        for p in batch:
            if set(p) != {"id", "mass_kg", "height_cm", "split"}:
                raise ValueError("Profile fields must exclude names, IDs and personal metadata")
            if not re.fullmatch(r"m[0-9]+(?:p[0-9]+)?_h[0-9]+(?:p[0-9]+)?", p["id"]):
                raise ValueError("Use synthetic mass/height labels, not real identities")
            if not 35 <= number(p["mass_kg"]) <= 150 or not 130 <= number(p["height_cm"]) <= 220:
                raise ValueError("Profile outside the experiment's bounded input range")
            if p["split"] not in {"train", "selection", "test"}:
                raise ValueError("Unknown profile partition")
            if p["id"] in profiles and profiles[p["id"]] != p:
                raise ValueError("Repeated profiles must keep geometry and partition")
            profiles[p["id"]] = p
    for split in ["train", "selection", "test"]:
        if not any(p["split"] == split for p in profiles.values()):
            raise ValueError("Training, selection and test geometries are all required")
    if set(plan["body_candidates"]) - {"power_law", "affine", "quadratic"} or not plan["body_candidates"]:
        raise ValueError("Unsupported cubic-law candidates")
    if set(plan["linear_candidates"]) - {"mass_linear", "affine"} or not plan["linear_candidates"]:
        raise ValueError("Unsupported linear-law candidates")
    if number(plan["acceptance_max_error_w"]) <= 0 or number(plan["selection_tolerance_w"]) < 0:
        raise ValueError("Invalid acceptance criteria")
    control = plan["ftp_invariance"]
    if set(control) != {"batch_index", "profile_id", "ftp_w", "speed_kph"}:
        raise ValueError("Unknown FTP-control fields")
    if type(control["batch_index"]) is not int or not 0 <= control["batch_index"] < len(plan["batches"]):
        raise ValueError("Invalid FTP-control batch")
    if not control["ftp_w"] or len(set(control["ftp_w"])) != len(control["ftp_w"]) or plan["probe_ftp_w"] in control["ftp_w"]:
        raise ValueError("FTP controls must be distinct perturbations of the baseline")
    batch = plan["batches"][control["batch_index"]]
    if control["profile_id"] not in {p["id"] for p in batch}:
        raise ValueError("Invariance profile is absent from its batch")
    if control["speed_kph"] != speeds[-1]:
        raise ValueError("Invariance test must reuse the final measured speed")
    if any(not 100 <= number(f) <= 600 for f in control["ftp_w"]):
        raise ValueError("Invalid invariance normalization")
    return profiles


def estimated_requests(plan):
    validate_plan(plan)
    speeds = len(plan["fit_speeds_kph"] + plan["blind_speeds_kph"])
    # GET, empty-session check, route form + two redirect GETs, efficiency, intensity,
    # five additions, move all, finishers. Each rotation: order + edits;
    # each sample: speed + export. Redirects count against the same budget.
    return len(plan["batches"]) * (14 + 5*(2 + 2*speeds)) + 3*len(plan["ftp_invariance"]["ftp_w"])


def _close(actual, expected, label, tolerance=1e-8):
    if abs(number(actual, label, strings=True) - expected) > tolerance:
        raise ContractError(f"Calculator did not retain the requested {label}")


def extract_frame(export, plan, batch_index, order, ids, speed_kph, ftps, purpose="calibration"):
    """Allowlist numeric observations; drop names, account fields, links and fatigue."""
    if not isinstance(export, dict) or export.get("source") != "zwiftgopher-ttt":
        raise ContractError("Unexpected calculator export source")
    version = export.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ContractError("Unknown calculator version format")
    if version != plan["expected_calculator_version"]:
        raise ContractError("Calculator version changed; use a new declared experiment")
    expected = plan["context"]
    route = export.get("plan", {})
    if str(route.get("course_id")) != expected["route_signature"] or route.get("route") != expected["route_name"]:
        raise ContractError("Export route does not match the pinned route")
    _close(route.get("laps"), expected["laps"], "lap count")
    _close(export.get("efficiency"), expected["efficiency"], "efficiency")
    if export.get("efficiency_manual") is not True:
        raise ContractError("Automatic team efficiency must be disabled")
    _close(export.get("intensity"), expected["intensity"], "intensity")
    _close(export.get("target_speed"), speed_kph, "target speed")
    _close(export.get("minimum_finishers"), 5, "finishers")
    batch = plan["batches"][batch_index]
    riders = export.get("riders")
    if not isinstance(riders, dict) or set(riders) != {str(i) for i in ids}:
        raise ContractError("Export roster differs from this anonymous synthetic batch")
    rows = []
    for position, index in enumerate(order, 1):
        p = batch[index]
        r = riders[str(ids[index])]
        if r.get("name") != "Synthetic " + p["id"]:
            raise ContractError("Unexpected rider label; refusing unrelated calculator data")
        _close(r.get("weight"), p["mass_kg"], "mass")
        _close(r.get("height"), p["height_cm"], "height")
        _close(r.get("ftp"), ftps[index], "normalization FTP")
        _close(r.get("order"), position-1, "position")
        _close(r.get("pull_duration"), plan["active_pull_seconds"] if position == 1 else 0, "static pull duration")
        _close(r.get("adjustment"), 100, "power adjustment")
        _close(r.get("pull_speed"), speed_kph, "rider speed")
        _close(r.get("effort"), 1, "effort")
        flat_if = number(r.get("flat_if"), "flat IF")
        lead_w = number(r.get("pull_power"), "counterfactual lead watts")
        if flat_if < 0 or lead_w < 0 or abs(round(flat_if, 2)-flat_if) > 1e-8 or abs(round(lead_w, 2)-lead_w) > 1e-8:
            raise ContractError("Power/IF units or export precision changed")
        watts = flat_if*ftps[index]/100
        uncertainty = .005*ftps[index]/100  # assumed 0.01-percentage-point rounding
        if position == 1 and abs(watts-lead_w) > uncertainty+.005+1e-8:
            raise ContractError("Constant leader flat IF does not reproduce exported lead watts")
        rows.append(dict(profile_id=p["id"], mass_kg=p["mass_kg"], height_cm=p["height_cm"], split=p["split"],
                         position=position, speed_kph=speed_kph, power_w=watts,
                         power_rounding_half_width_w=uncertainty, lead_power_w=lead_w,
                         normalization_ftp_w=ftps[index], flat_if_percent=flat_if))
    context = dict(expected, calculator_version=version, efficiency_manual=True,
                   distance_km=number(route.get("distance_km")), elevation_m=number(route.get("elevation_m")),
                   equipment="not separately exposed by the web JSON export")
    return dict(batch_index=batch_index, purpose=purpose, order=[batch[i]["id"] for i in order],
                speed_kph=speed_kph, context=context, observations=rows)


def validate_dataset(data):
    if data.get("schema_version") != 1 or data.get("status") != "complete":
        raise ValueError("A complete version-1 collection is required; partial data cannot fit a release model")
    root_fields = {"schema_version", "status", "source", "created_at", "completed_at", "plan", "plan_sha256", "frames", "request_count"}
    if set(data) != root_fields or data["source"] != "https://zwiftgopher.com/TTT/":
        raise ValueError("Unexpected dataset fields or source; raw exports are not accepted")
    if type(data["request_count"]) is not int or not 0 <= data["request_count"] <= 250:
        raise ValueError("Invalid collection request count")
    plan = data["plan"]
    profiles = validate_plan(plan)
    if data.get("plan_sha256") != digest(plan):
        raise ValueError("Experiment plan digest mismatch")
    frames = data["frames"]
    contexts = {digest(f["context"]) for f in frames}
    if len(contexts) != 1:
        raise ValueError("Calculator context changed during collection")
    context = frames[0]["context"]
    if set(context) != set(plan["context"]) | {"calculator_version", "efficiency_manual", "distance_km", "elevation_m", "equipment"}:
        raise ValueError("Unexpected context fields")
    if any(context[k] != v for k,v in plan["context"].items()) or context["calculator_version"] != plan["expected_calculator_version"] or context["efficiency_manual"] is not True:
        raise ValueError("Dataset does not match its pinned calculator context")
    if context["equipment"] != "not separately exposed by the web JSON export" or number(context["distance_km"]) <= 0 or number(context["elevation_m"]) < 0:
        raise ValueError("Invalid source-context metadata")
    expected = {(b, p["id"], v, pos) for b, batch in enumerate(plan["batches"]) for p in batch
                for v in plan["fit_speeds_kph"]+plan["blind_speeds_kph"] for pos in range(1,6)}
    seen = set(); control_values = set(); control = plan["ftp_invariance"]
    row_fields = {"profile_id", "mass_kg", "height_cm", "split", "position", "speed_kph", "power_w",
                  "power_rounding_half_width_w", "lead_power_w", "normalization_ftp_w", "flat_if_percent"}
    for f in frames:
        if set(f) != {"batch_index", "purpose", "order", "speed_kph", "context", "observations"} or f["purpose"] not in {"calibration", "ftp-invariance"}:
            raise ValueError("Unexpected frame fields or purpose")
        if type(f["batch_index"]) is not int or not 0 <= f["batch_index"] < len(plan["batches"]):
            raise ValueError("Invalid batch index")
        batch_ids = {p["id"] for p in plan["batches"][f["batch_index"]]}
        if len(f["observations"]) != 5 or len(f["order"]) != 5 or set(f["order"]) != batch_ids:
            raise ValueError("Malformed collected formation")
        is_control = f["purpose"] == "ftp-invariance"
        control_ftp = None
        if is_control:
            if f["batch_index"] != control["batch_index"] or f["speed_kph"] != control["speed_kph"]:
                raise ValueError("Unexpected FTP-control context")
            target = next((r for r in f["observations"] if r.get("profile_id") == control["profile_id"]), None)
            if target is None or target.get("normalization_ftp_w") not in control["ftp_w"]:
                raise ValueError("Unexpected FTP-control perturbation")
            control_ftp = target["normalization_ftp_w"]
            if control_ftp in control_values:raise ValueError("Duplicate FTP-control perturbation")
            control_values.add(control_ftp)
        for position,r in enumerate(f["observations"],1):
            if set(r) != row_fields:
                raise ValueError("Unexpected observation fields; raw/personal fields are forbidden")
            p = profiles[r["profile_id"]]
            if r["position"] != position or f["order"][position-1] != p["id"] or r["speed_kph"] != f["speed_kph"]:
                raise ValueError("Observation disagrees with its formation or target speed")
            if (r["mass_kg"], r["height_cm"], r["split"]) != (p["mass_kg"], p["height_cm"], p["split"]):
                raise ValueError("Observation changed a predeclared profile")
            ftp = control_ftp if is_control and p["id"] == control["profile_id"] else plan["probe_ftp_w"]
            if r["normalization_ftp_w"] != ftp:
                raise ValueError("Unplanned normalization FTP")
            for k in ["power_w", "lead_power_w", "normalization_ftp_w", "flat_if_percent", "power_rounding_half_width_w"]:
                if number(r[k]) < 0:raise ValueError("Negative measurement")
            if abs(r["power_w"]-r["flat_if_percent"]*ftp/100) > 1e-8 or abs(r["power_rounding_half_width_w"]-.005*ftp/100) > 1e-8:
                raise ValueError("Flat IF conversion or rounding interval is inconsistent")
            if position == 1 and abs(r["power_w"]-r["lead_power_w"]) > r["power_rounding_half_width_w"]+.005+1e-8:
                raise ValueError("Static leader control fails")
            if not is_control:
                key = (f["batch_index"], p["id"], r["speed_kph"], position)
                if key in seen:raise ValueError("Duplicate coverage cell")
                seen.add(key)
    if seen != expected:
        raise ValueError("Collection has missing or unexpected coverage cells")
    if control_values != set(control["ftp_w"]):
        raise ValueError("Missing predeclared FTP-invariance checks")
    return profiles
