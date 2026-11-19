"""Shared, coefficient-level solo and drafted cycling mechanics (SI units)."""
from dataclasses import dataclass
import math

from ._io import number


@dataclass(frozen=True)
class CyclingModel:
    """Effective rider + equipment terms, not bare frame properties.

    Missing gravity/inertia means unmeasured, not a zero coefficient.
    Grade is rise/run. A draft factor scales aerodynamic demand only.
    """
    aero: float
    rolling_n: float
    gravity_n: float | None = None
    inertia_kg: float | None = None

    def __post_init__(self):
        if number(self.aero) <= 0 or number(self.rolling_n) < 0:
            raise ValueError('Expected positive aero and nonnegative rolling force')
        for value in (self.gravity_n, self.inertia_kg):
            if value is not None and number(value) <= 0:
                raise ValueError('Gravity and inertia must be positive when supplied')

    def _a(self, draft_factor):
        if not 0 < number(draft_factor) <= 1:
            raise ValueError('draft_factor must be in (0,1]')
        return self.aero * draft_factor

    def _road(self, grade, surface_ratio):
        g = number(grade, 'grade')
        if number(surface_ratio) <= 0:
            raise ValueError('surface_ratio must be positive')
        if g and self.gravity_n is None:
            raise ValueError('No gravity calibration for nonzero grade')
        norm = math.hypot(1., g)
        return self.rolling_n * surface_ratio / norm, (self.gravity_n or 0.) * (g / norm)

    def components_w(self, speed_mps, grade=0., acceleration_mps2=0., *, surface_ratio=1., draft_factor=1.):
        """Aerodynamic, rolling, gravitational and kinetic power (W), in that order."""
        v = number(speed_mps, 'speed_mps')
        acc = number(acceleration_mps2)
        if v < 0 or (acc and self.inertia_kg is None):
            raise ValueError('Negative speed or missing inertia for acceleration')
        rolling, gravity = self._road(grade, surface_ratio)
        try:
            parts = (self._a(draft_factor) * v**3, rolling*v, gravity*v, (self.inertia_kg or 0.)*acc*v)
        except OverflowError as exc:
            raise ValueError('Power overflow') from exc
        number(sum(parts), 'power result')
        return parts

    def power_w(self, speed_mps, grade=0., acceleration_mps2=0., *, surface_ratio=1., draft_factor=1.):
        return sum(self.components_w(speed_mps, grade, acceleration_mps2,
                                     surface_ratio=surface_ratio, draft_factor=draft_factor))

    def acceleration_mps2(self, speed_mps, watts, grade=0., *, surface_ratio=1., draft_factor=1.):
        v, p = number(speed_mps), number(watts)
        if v <= 0 or p < 0 or self.inertia_kg is None:
            raise ValueError('Positive speed, nonnegative input power and known inertia required')
        resist = self.power_w(v, grade, surface_ratio=surface_ratio, draft_factor=draft_factor)
        return number((p-resist)/v/self.inertia_kg, 'acceleration result')

    def steady_speed_mps(self, watts, grade=0., *, surface_ratio=1., draft_factor=1.):
        """Positive stable equilibrium including zero-power downhill coasting."""
        p = number(watts)
        if p < 0:
            raise ValueError('Input power must be nonnegative')
        road = sum(self._road(grade, surface_ratio))
        a = self._a(draft_factor)
        lo = math.sqrt(max(0., -road/a))
        if p == 0:
            return number(lo, 'coasting speed')
        hi = max(1., lo)
        def power(v):
            return self.power_w(v, grade, surface_ratio=surface_ratio, draft_factor=draft_factor)
        while power(hi) < p:
            hi *= 2
            if hi > 1024:
                raise ValueError('Requested power exceeds inverse solver safety bound')
        for _ in range(80):
            mid = (lo+hi)/2
            if power(mid) > p:
                hi = mid
            else:
                lo = mid
        return (lo+hi)/2

    def mean_power_w(self, mean_cubic_speed, mean_rolling_speed, vertical_rate_mps, kinetic_rate, *, draft_factor=1.):
        """Mean(v³), mean(surface_ratio*v*cos(theta)), Δh/T, Δ(v²)/(2T); constant draft."""
        cubic, rolling = number(mean_cubic_speed), number(mean_rolling_speed)
        dh, dk = number(vertical_rate_mps), number(kinetic_rate)
        if min(cubic, rolling) < 0 or (dh and self.gravity_n is None) or (dk and self.inertia_kg is None):
            raise ValueError('Invalid mean speeds or missing vertical/kinetic calibration')
        return number(self._a(draft_factor)*cubic + self.rolling_n*rolling
                      + (self.gravity_n or 0.)*dh + (self.inertia_kg or 0.)*dk)
