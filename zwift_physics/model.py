"""Versioned body-size interpolation and explicit calibration boundaries."""
from __future__ import annotations
from dataclasses import dataclass
import math
from ._io import load, number
from .physics import FlatCoefficients, RiderGeometry

FAMILIES = {"mass_linear": 2, "affine": 3, "quadratic": 6, "power_law": 3}


def features(rider: RiderGeometry, family: str):
    m = (rider.mass_kg - 75.) / 25.
    h = (rider.height_cm - 180.) / 25.
    if family == "mass_linear":
        return [1., m]
    if family == "affine":
        return [1., m, h]
    if family == "quadratic":
        return [1., m, h, m*m, m*h, h*h]
    if family == "power_law":
        return [1., math.log(rider.mass_kg/75.), math.log(rider.height_cm/180.)]
    raise ValueError("Unsupported interpolation family")


def law_value(law, rider):
    family = law["family"]
    value = sum(a*b for a, b in zip(law["coefficients"], features(rider, family)))
    try:
        return math.exp(value) if family == "power_law" else value
    except OverflowError as exc:
        raise ValueError("Geometry extrapolation overflow") from exc


class OutsideCalibration(ValueError):
    pass


@dataclass(frozen=True)
class CalibrationModel:
    specification: dict

    def __post_init__(self):
        x = self.specification
        if x.get("schema_version") != 1 or x.get("kind") != "effective-flat":
            raise ValueError("Unsupported calibration model schema")
        for key in ["cubic_law", "linear_law"]:
            law = x[key]
            if law.get("family") not in FAMILIES:
                raise ValueError("Unsupported model family")
            if len(law.get("coefficients", [])) != FAMILIES[law["family"]]:
                raise ValueError("Wrong number of coefficients")
            for c in law["coefficients"]:
                number(c, "coefficient")
        for key in ["mass_kg", "height_cm", "speed_kph"]:
            lo, hi = x["domain"][key]
            if not 0 < number(lo) <= number(hi):
                raise ValueError("Invalid calibration domain")
        factors = tuple(x["draft_factors"])
        FlatCoefficients(1., 0., factors)
        if x["context"]["team_size"] != len(factors):
            raise ValueError("Draft factors and calibrated team size disagree")
        if x.get("validation", {}).get("accepted") is not True:
            raise ValueError("Model has not passed its declared blind-test acceptance criterion")

    @classmethod
    def from_file(cls, path):
        return cls(load(path))

    def _geometry_check(self, rider, allow_extrapolation):
        for key, value in [("mass_kg", rider.mass_kg), ("height_cm", rider.height_cm)]:
            lo, hi = self.specification["domain"][key]
            if not lo <= value <= hi and not allow_extrapolation:
                raise OutsideCalibration(f"{key} is outside the observed calibration envelope")

    def coefficients(self, rider: RiderGeometry, *, allow_extrapolation=False):
        self._geometry_check(rider, allow_extrapolation)
        x = self.specification
        return FlatCoefficients(law_value(x["cubic_law"], rider), law_value(x["linear_law"], rider),
                                tuple(x["draft_factors"]))

    def power_watts(self, rider, speed_kph, position=1, *, allow_extrapolation=False):
        speed = number(speed_kph, "speed_kph")
        if speed < 0:
            raise ValueError("Speed must be nonnegative")
        lo, hi = self.specification["domain"]["speed_kph"]
        if not lo <= speed <= hi and not allow_extrapolation:
            raise OutsideCalibration("Speed is outside the observed calibration envelope")
        return self.coefficients(rider, allow_extrapolation=allow_extrapolation).power(speed/3.6, position).total_watts

    def speed_kph(self, rider, watts, position=1, *, allow_extrapolation=False):
        speed = self.coefficients(rider, allow_extrapolation=allow_extrapolation).speed_for_power(watts, position)*3.6
        lo, hi = self.specification["domain"]["speed_kph"]
        if not lo <= speed <= hi and not allow_extrapolation:
            raise OutsideCalibration("Implied speed is outside the observed calibration envelope")
        return speed
