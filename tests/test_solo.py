"""Pure mechanics checks; all coefficients and inputs are synthetic."""
import math
import unittest

from zwift_physics.solo import SoloTT


class SoloTests(unittest.TestCase):
    def setUp(self):
        self.model = SoloTT(.16, 3., 800., 90.)

    def test_flat_power_and_returns(self):
        self.assertAlmostEqual(self.model.power_w(10), 190.)
        for grade in [-.19, 0., .24]:
            for p in [1, 200, 600]:
                v = self.model.steady_speed_mps(p, grade)
                self.assertAlmostEqual(self.model.power_w(v, grade), p, places=8)
                self.assertAlmostEqual(self.model.acceleration_mps2(v, p, grade), 0)

    def test_grade_is_rise_over_run(self):
        # 3-4-5 triangle: 75% grade (NOT .75 degrees or .75 percent).
        self.assertAlmostEqual(self.model.power_w(5, .75), .16*125 + (3*.8 + 800*.6)*5)

    def test_surface_and_inertia_are_separate(self):
        v, a, g = 12, .25, -.06
        p = self.model.power_w(v, g, a, surface_ratio=1.6)
        self.assertAlmostEqual(self.model.acceleration_mps2(v, p, g, surface_ratio=1.6), a)
        delta = p - self.model.power_w(v, g, a)
        self.assertAlmostEqual(delta, 3*.6*v/math.hypot(1, g))

    def test_stable_coasting_root_and_signed_power(self):
        v = self.model.steady_speed_mps(0, -.04)
        self.assertGreater(v, 0)
        self.assertAlmostEqual(self.model.power_w(v, -.04), 0)
        self.assertLess(self.model.power_w(v/2, -.04), 0)
        self.assertEqual(self.model.steady_speed_mps(0, .02), 0)

    def test_integral_constant_acceleration_on_level(self):
        u,v,T = 8.,12.,20.
        cubic = (u**3 + u*u*v + u*v*v + v**3)/4
        mean = (u+v)/2
        expected = .16*cubic + 3*mean + 90*(v-u)/T*mean
        self.assertAlmostEqual(self.model.mean_power_w(cubic, mean, 0., (v*v-u*u)/(2*T)), expected)

    def test_invalid_inputs(self):
        m = self.model
        for fn in (lambda: SoloTT(0,1,1,1), lambda: SoloTT(1,-1,1,1), lambda: SoloTT(1,1,0,1),
                   lambda: SoloTT(1,1,1,False), lambda: m.acceleration_mps2(0,100),
                   lambda: m.power_w(-.01), lambda: m.power_w(10, float('nan')),
                   lambda: m.power_w(10, surface_ratio=0), lambda: m.steady_speed_mps(-1),
                   lambda: m.mean_power_w(-1,1,1,1), lambda: m.mean_power_w(1,1,1,float('inf'))):
            with self.assertRaises(ValueError):
                fn()
