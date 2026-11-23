from pathlib import Path
import json
import unittest

from zwift_physics import RiderGeometry
from zwift_physics.equipment_fit import fit_reference
from zwift_physics.profiles import equipment_model

ROOT = Path(__file__).resolve().parents[1]


class ReferenceTests(unittest.TestCase):
    def test_reproducible_coefficients(self):
        ref = fit_reference(ROOT/'experiments/speedlab-reference-v1.json', ROOT/'data/speedlab-reference-v1.json')
        self.assertEqual(ref,json.loads((ROOT/'zwift_physics/resources/speedlab-reference-v1.json').read_text()))
        self.assertEqual(len(ref['profiles']),8)

    def test_exact_lookup(self):
        kw=dict(level=0,rider=RiderGeometry(75,180),source='speedlab')
        with self.assertRaises(ValueError): equipment_model('zwift_tt','cadex_42',**kw)
        m=equipment_model('cervelo_p_5_2026','cadex_42',allow_exploratory=True,**kw)
        self.assertAlmostEqual(m.steady_speed_mps(250)*3.6,39.62,delta=.02)
        self.assertIsNone(m.inertia_kg)
        with self.assertRaises(ValueError): equipment_model('zwift_tt','cadex_65',allow_exploratory=True,**kw)
