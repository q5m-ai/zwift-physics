"""Effective steady-flat mechanics only. No physiological inputs or state."""
from __future__ import annotations
from dataclasses import dataclass
import math
from ._io import number


@dataclass(frozen=True)
class RiderGeometry:
    mass_kg: float
    height_cm: float

    def __post_init__(self):
        if number(self.mass_kg, "mass_kg") <= 0 or number(self.height_cm, "height_cm") <= 0:
            raise ValueError("Mass and height must be positive")


@dataclass(frozen=True)
class PowerComponents:
    cubic_watts: float
    linear_watts: float

    @property
    def total_watts(self):
        return self.cubic_watts + self.linear_watts


@dataclass(frozen=True)
class FlatCoefficients:
    """Crank-watt coefficients: alpha*v^3*d(position) + beta*v, v in m/s.

    These are effective coefficients. They do not uniquely identify physical
    CdA, Crr, bike mass, air density or drivetrain efficiency.
    """
    alpha: float
    beta: float
    draft_factors: tuple[float, ...]

    def __post_init__(self):
        if number(self.alpha, "alpha") <= 0 or number(self.beta, "beta") < 0:
            raise ValueError("alpha must be positive and beta nonnegative")
        if not isinstance(self.draft_factors, tuple) or not self.draft_factors:
            raise ValueError("draft_factors must be a nonempty tuple")
        if self.draft_factors[0] != 1:
            raise ValueError("The front aero factor must be exactly 1")
        for d in self.draft_factors:
            if not 0 < number(d, "draft factor") <= 1:
                raise ValueError("Draft factors must be in (0,1]")

    def power(self, speed_mps: float, position: int = 1) -> PowerComponents:
        v = number(speed_mps, "speed_mps")
        if v < 0:
            raise ValueError("Speed must be nonnegative")
        if isinstance(position, bool) or not isinstance(position, int) or not 1 <= position <= len(self.draft_factors):
            raise ValueError("Position is one-based and must have a calibrated factor")
        try:
            cubic = self.alpha * self.draft_factors[position - 1] * v**3
            linear = self.beta * v
        except OverflowError as exc:
            raise ValueError("Power overflow") from exc
        if not math.isfinite(cubic + linear):
            raise ValueError("Power overflow")
        return PowerComponents(cubic, linear)

    def speed_for_power(self, watts: float, position: int = 1) -> float:
        """Monotone inverse in m/s; coefficient-level, not a domain guarantee."""
        target = number(watts, "watts")
        if target < 0:
            raise ValueError("Power must be nonnegative")
        self.power(0, position)
        if target == 0:
            return 0.
        lo, hi = 0., 1.
        while self.power(hi, position).total_watts < target:
            hi *= 2
            if hi > 1024:
                raise ValueError("Requested power is outside the inverse solver's safety bound")
        for _ in range(80):
            mid = (lo + hi) / 2
            if self.power(mid, position).total_watts > target:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
