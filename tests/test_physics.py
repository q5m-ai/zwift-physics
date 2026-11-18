import math
import unittest
from zwift_physics.physics import FlatCoefficients, RiderGeometry
from zwift_physics.model import CalibrationModel, OutsideCalibration


class MechanicsTests(unittest.TestCase):
    def setUp(self):self.c=FlatCoefficients(.15,3.,(1.,.8,.7))
    def test_units_and_components(self):
        p=self.c.power(10,2)
        self.assertAlmostEqual(p.cubic_watts,120);self.assertAlmostEqual(p.linear_watts,30);self.assertAlmostEqual(p.total_watts,150)
    def test_draft_does_not_reduce_linear_term(self):
        self.assertEqual(self.c.power(10,1).linear_watts,self.c.power(10,3).linear_watts)
        self.assertGreater(self.c.power(10,3).total_watts/self.c.power(10).total_watts,.7)
    def test_zero_power_and_speed(self):
        self.assertEqual(self.c.power(0).total_watts,0);self.assertEqual(self.c.speed_for_power(0),0)
    def test_inverse_and_monotonicity(self):
        for pos in [1,2,3]:
            previous=-1
            for v in [1,4,8,12,16,20]:
                p=self.c.power(v,pos).total_watts
                self.assertGreater(p,previous);previous=p
                self.assertAlmostEqual(self.c.speed_for_power(p,pos),v,places=10)
    def test_position_is_one_based_and_bounded(self):
        for pos in [0,-1,4,True,1.5]:
            with self.assertRaises(ValueError):self.c.power(10,pos)
    def test_nonfinite_negative_and_bool_rejected(self):
        for x in [float('nan'),float('inf'),-1,True,'10']:
            with self.assertRaises(ValueError):self.c.power(x)
            with self.assertRaises(ValueError):self.c.speed_for_power(x)
    def test_invalid_coefficients(self):
        for args in [(0,1,(1,)),(1,-1,(1,)),(1,1,(.9,)),(1,1,(1,0)),(1,1,(1,1.1))]:
            with self.assertRaises(ValueError):FlatCoefficients(*args)
    def test_geometry_has_no_physiology(self):
        r=RiderGeometry(75,180);self.assertFalse(hasattr(r,'ftp'));self.assertFalse(hasattr(r,'cp'))
        for m,h in [(0,180),(75,0),(float('nan'),180),(75,True)]:
            with self.assertRaises(ValueError):RiderGeometry(m,h)


class ModelTests(unittest.TestCase):
    def spec(self):return dict(schema_version=1,kind='effective-flat',cubic_law=dict(family='power_law',coefficients=[math.log(.15),.6,.8]),
        linear_law=dict(family='mass_linear',coefficients=[3,.8]),draft_factors=[1,.8,.7],context={'team_size':3},
        domain=dict(mass_kg=[55,95],height_cm=[160,200],speed_kph=[25,50]),validation={'accepted':True})
    def test_prediction_and_inverse(self):
        m=CalibrationModel(self.spec());r=RiderGeometry(75,180)
        self.assertAlmostEqual(m.power_watts(r,36,2),150)
        self.assertAlmostEqual(m.speed_kph(r,150,2),36)
    def test_domain_requires_explicit_extrapolation(self):
        m=CalibrationModel(self.spec());r=RiderGeometry(75,180)
        for body,v in [(RiderGeometry(100,180),36),(RiderGeometry(75,210),36),(r,60),(r,0)]:
            with self.assertRaises(OutsideCalibration):m.power_watts(body,v)
            self.assertGreaterEqual(m.power_watts(body,v,allow_extrapolation=True),0)
    def test_unaccepted_model_refused(self):
        x=self.spec();x['validation']['accepted']=False
        with self.assertRaises(ValueError):CalibrationModel(x)
    def test_unknown_laws_and_wrong_shape_refused(self):
        x=self.spec();x['cubic_law']['family']='evaluate arbitrary code'
        with self.assertRaises(ValueError):CalibrationModel(x)
        x=self.spec();x['linear_law']['coefficients']=[1]
        with self.assertRaises(ValueError):CalibrationModel(x)
        x=self.spec();x['context']['team_size']=5
        with self.assertRaises(ValueError):CalibrationModel(x)

if __name__=='__main__':unittest.main()
