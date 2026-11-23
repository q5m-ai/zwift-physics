"""Compatibility constructor for the original solo TT coefficient API."""
from dataclasses import dataclass
from .engine import CyclingModel


@dataclass(frozen=True)
class SoloTT(CyclingModel):
    def __post_init__(self):
        super().__post_init__()
        if self.gravity_n is None or self.inertia_kg is None:
            raise ValueError('SoloTT requires both gravity and inertia coefficients')
