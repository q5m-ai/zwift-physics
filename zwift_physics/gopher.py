"""Opt-in, bounded adapter for the public calculator UI, not a private API client.

No account, existing browser session, credential, rider lookup, remote optimizer,
image export or share-link request. The normal JSON export is a server-retained
operation: only explicitly fictional profiles are allowed here. Raw responses,
including generated links in exports, are never saved or logged.
"""
from __future__ import annotations
from datetime import datetime, timezone
import http.cookiejar
import json
from pathlib import Path
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from ._io import digest, loads, save
from .experiment import ContractError, estimated_requests, extract_frame, validate_dataset, validate_plan

BASE = "https://zwiftgopher.com/TTT/"
LIGHT = dict(render=1, light=1, skipFatigue=1, skipRoute=1)


class CollectionStopped(RuntimeError):
    pass


class Budget:
    def __init__(self, maximum=200, interval_seconds=2., *, clock=time.monotonic, sleep=time.sleep):
        if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 250:
            raise ValueError("A request budget of 1–250 is required")
        if not 2 <= interval_seconds <= 60:
            raise ValueError("Requests must be spaced by at least two seconds")
        self.maximum = maximum
        self.interval = interval_seconds
        self.clock = clock
        self.sleep = sleep
        self.count = 0
        self.last = None

    def take(self):
        if self.count >= self.maximum:
            raise CollectionStopped("Request budget exhausted; no further request was sent")
        if self.last is not None:
            self.sleep(max(0., self.interval-(self.clock()-self.last)))
        self.last = self.clock()
        self.count += 1


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, budget):
        super().__init__()
        self.budget = budget

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        if url.scheme != "https" or url.netloc != "zwiftgopher.com" or url.path not in {"/TTT", "/TTT/"} or url.query:
            raise CollectionStopped("Refusing an unexpected calculator redirect")
        if req.data is not None:
            # The normal course form uses POST -> 302 -> GET. Read the result,
            # without replaying the POST. Never follow a 307/308 write replay.
            if code not in (302, 303) or url.path.rstrip("/") != "/TTT" or url.query:
                raise CollectionStopped("Refusing to replay or unexpectedly redirect a calculator write")
        follow = super().redirect_request(req, fp, code, msg, headers, newurl)
        self.budget.take()
        return follow


class Session:
    def __init__(self, budget):
        self.budget = budget
        # Fresh in-memory anonymous cookies only. Never load browser or disk cookies.
        self.opener = urllib.request.build_opener(SameOriginRedirect(budget),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path="", data=None, *, expect_json=True):
        if path not in {"", "ajax.php"}:
            raise ValueError("Only the observed public calculator paths are supported")
        self.budget.take()
        payload = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
        req = urllib.request.Request(BASE+path, data=payload, headers={
            "User-Agent": "zwift-physics/0.1 bounded synthetic calibration"})
        try:
            with self.opener.open(req, timeout=45) as response:
                content = response.read(2_000_001)
                if len(content) > 2_000_000:
                    raise CollectionStopped("Unexpectedly large calculator response")
        except urllib.error.HTTPError as exc:
            # Do not read/log error bodies or headers that could contain sessions.
            raise CollectionStopped(f"HTTP {exc.code}; stopped without retry or alternate transport") from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            raise CollectionStopped("Transport outcome uncertain; stopped without retrying the write") from None
        if not expect_json:
            return None
        try:
            value = loads(content.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise CollectionStopped("Calculator response is not the expected JSON; stopped") from None
        if not isinstance(value, dict) or value.get("success") is False:
            raise CollectionStopped("Calculator rejected the request; stopped without replay")
        return value

    def call(self, action, **fields):
        return self.request("ajax.php", dict(action=action, **fields))


class Calculator:
    def __init__(self, plan, batch_index, session):
        validate_plan(plan)
        self.plan = plan
        self.batch_index = batch_index
        self.batch = plan["batches"][batch_index]
        self.session = session
        self.ids = []
        self.ftps = [plan["probe_ftp_w"]]*5
        self.order = list(range(5))

    def setup(self):
        self.session.request(expect_json=False)
        reply = self.session.call("displayTeam", **LIGHT)
        if reply.get("race", {}).get("empty") is not True:
            raise CollectionStopped("Refusing to alter a nonempty calculator session")
        context = self.plan["context"]
        self.session.request(data=dict(courseSelect=context["route_signature"], laps=1), expect_json=False)
        self.session.call("setEfficiency", efficiency=context["efficiency"], **LIGHT)
        self.session.call("setIntensity", intensity=context["intensity"], **LIGHT)
        for p, ftp in zip(self.batch, self.ftps):
            reply = self.session.call("addRider", zwiftID="", riderName="Synthetic "+p["id"],
                                      riderWeight=p["mass_kg"], riderHeight=p["height_cm"], riderFTP=ftp)
            added = reply.get("added")
            if not isinstance(added, list) or len(added) != 1 or reply.get("updated") or reply.get("pending") or reply.get("not_found"):
                raise CollectionStopped("Unexpected manual-rider addition; not retrying")
            rider_id = added[0]
            if isinstance(rider_id, bool) or not isinstance(rider_id, int) or rider_id < 0 or rider_id in self.ids:
                raise CollectionStopped("Unexpected anonymous rider identifier")
            self.ids.append(rider_id)
        self.session.call("moveAllToRace", **LIGHT)
        self.session.call("setMinimumFinishers", minimum_finishers=5, **LIGHT)

    def rotate(self, phase):
        self.order = list(range(phase, 5))+list(range(phase))
        self.session.call("updateRaceOrder", **{"order[]": [self.ids[i] for i in self.order]}, **LIGHT)
        edits = [dict(rider=str(self.ids[i]), pull_duration=self.plan["active_pull_seconds"] if i == self.order[0] else 0,
                      adjustment=100) for i in range(5)]
        self.session.call("applyEdits", edits=json.dumps(edits), **LIGHT)

    def sample(self, speed_kph, purpose="calibration"):
        self.session.call("setTargetSpeed", targetSpeed=speed_kph, **LIGHT)
        reply = self.session.call("exportJson")
        if reply.get("success") is not True or not isinstance(reply.get("content"), str):
            raise ContractError("JSON export contract changed")
        # Only the allowlisted extracted frame escapes this function.
        export = loads(reply["content"])
        return extract_frame(export, self.plan, self.batch_index, self.order, self.ids,
                             speed_kph, self.ftps, purpose)

    def update_ftp(self, profile_id, ftp):
        index = next(i for i, p in enumerate(self.batch) if p["id"] == profile_id)
        p = self.batch[index]
        self.session.call("updateRacer", rider=str(self.ids[index]), riderName="Synthetic "+p["id"],
                          riderWeight=p["mass_kg"], riderHeight=p["height_cm"], riderFTP=ftp, **LIGHT)
        self.ftps[index] = ftp


def collect(plan, destination, *, maximum=200, interval_seconds=2., session_factory=Session,
            budget=None, progress=print):
    validate_plan(plan)
    needed = estimated_requests(plan)
    limiter = budget or Budget(maximum, interval_seconds)
    if needed > maximum or needed > limiter.maximum:
        raise ValueError(f"Design requires {needed} requests, exceeding the declared budget")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Claim a new output path. Never overwrite a prior experiment or resume an
    # uncertain session. On error, retain a clearly incomplete safe checkpoint.
    with destination.open("x", encoding="utf-8") as f:
        f.write("{}\n")
    data = dict(schema_version=1, status="incomplete", source=BASE,
                created_at=datetime.now(timezone.utc).isoformat(), plan=plan,
                plan_sha256=digest(plan), frames=[], request_count=0)
    save(destination, data)
    expected_context = None
    try:
        for batch_index in range(len(plan["batches"])):
            calculator = Calculator(plan, batch_index, session_factory(limiter))
            calculator.setup()
            for phase in range(5):
                calculator.rotate(phase)
                for speed in plan["fit_speeds_kph"]+plan["blind_speeds_kph"]:
                    frame = calculator.sample(speed)
                    key = digest(frame["context"])
                    if expected_context is not None and key != expected_context:
                        raise ContractError("Calculator context changed; stop and start a new experiment")
                    expected_context = key
                    data["frames"].append(frame)
                    data["request_count"] = limiter.count
                    save(destination, data)
                    progress(f"Batch {batch_index+1}, rotation {phase+1}, {speed:g} km/h: five numeric observations")
            control = plan["ftp_invariance"]
            if control["batch_index"] == batch_index:
                for ftp in control["ftp_w"]:
                    calculator.update_ftp(control["profile_id"], ftp)
                    frame = calculator.sample(control["speed_kph"], "ftp-invariance")
                    if digest(frame["context"]) != expected_context:
                        raise ContractError("Context changed during FTP-invariance test")
                    data["frames"].append(frame)
                    data["request_count"] = limiter.count
                    save(destination, data)
        data["status"] = "complete"
        data["completed_at"] = datetime.now(timezone.utc).isoformat()
        validate_dataset(data)
        save(destination, data)
        return data
    except (CollectionStopped, ContractError, ValueError, KeyError, TypeError, KeyboardInterrupt):
        data["status"] = "incomplete"
        data["request_count"] = limiter.count
        save(destination, data)
        raise
