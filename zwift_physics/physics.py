"""Effective steady-flat mechanics only. No physiological inputs or state."""
from __future__ import annotations
from dataclasses import dataclass
from .engine import CyclingModel
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

    def engine(self) -> CyclingModel:
        return CyclingModel(self.alpha, self.beta)

    def draft_factor(self, position: int) -> float:
        if isinstance(position, bool) or not isinstance(position, int) or not 1 <= position <= len(self.draft_factors):
            raise ValueError("Position is one-based and must have a calibrated factor")
        return self.draft_factors[position - 1]

    def power(self, speed_mps: float, position: int = 1) -> PowerComponents:
        a, b, _, _ = self.engine().components_w(speed_mps, draft_factor=self.draft_factor(position))
        return PowerComponents(a, b)

    def speed_for_power(self, watts: float, position: int = 1) -> float:
        """Monotone inverse in m/s; coefficient-level, not a domain guarantee."""
        return self.engine().steady_speed_mps(watts, draft_factor=self.draft_factor(position))
