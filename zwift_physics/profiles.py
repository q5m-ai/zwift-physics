"""Exact-match exploratory setup lookup. No network or geometry fallback."""
from importlib.resources import files
from ._io import loads
from .engine import CyclingModel
from .physics import RiderGeometry


_TABLES = {'speedlab': 'speedlab-reference-v1.json', 'gopher': 'profiles.json'}


def equipment_model(frame: str, wheels: str, *, level: int, rider: RiderGeometry,
                    source: str, aero_socks: bool = False, allow_exploratory: bool = False):
    if allow_exploratory is not True:
        raise ValueError('Equipment estimates require allow_exploratory=True')
    if source not in _TABLES or type(level) is not int or type(aero_socks) is not bool:
        raise ValueError('Invalid source, level or socks selection')
    table = loads(files('zwift_physics').joinpath('resources', _TABLES[source]).read_text(encoding='utf-8'))
    matches = [p for p in table['profiles'] if (p['frame'],p['wheels'],p['level'],p['aero_socks']) ==
               (frame,wheels,level,aero_socks) and RiderGeometry(**p['reference_rider']) == rider]
    if len(matches) != 1 or matches[0]['status'] != 'exploratory':
        raise ValueError('No unique exploratory profile for this exact source, setup and rider')
    return CyclingModel(**matches[0]['coefficients'])
