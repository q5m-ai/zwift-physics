"""Offline release checks against the archived, sanitized synthetic experiment."""
import math
import unittest
from support import ROOT
from zwift_physics._io import load
from zwift_physics.calibration import fit_dataset
from zwift_physics.experiment import validate_dataset
from zwift_physics.model import CalibrationModel
from zwift_physics.physics import RiderGeometry


class ArchivedReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load(ROOT/'data/gopher-flat-v1.json')
        cls.model=load(ROOT/'models/gopher-flat-v1.json')
    def assert_near_json(self,a,b):
        if isinstance(a,dict):
            self.assertEqual(set(a),set(b))
            for key in a:self.assert_near_json(a[key],b[key])
        elif isinstance(a,list):
            self.assertEqual(len(a),len(b))
            for x,y in zip(a,b):self.assert_near_json(x,y)
        elif isinstance(a,(int,float)) and not isinstance(a,bool):
            self.assertTrue(math.isfinite(a) and math.isfinite(b));self.assertAlmostEqual(a,b,delta=1e-9)
        else:self.assertEqual(a,b)
    def test_archived_data_is_complete_public_safe_and_pinned(self):
        profiles=validate_dataset(self.data)
        self.assertEqual(len(profiles),13);self.assertEqual(self.data['request_count'],168)
        self.assertEqual(self.data['plan']['expected_calculator_version'],'1.39.1')
    def test_offline_refit_reproduces_accepted_model(self):
        fitted,_=fit_dataset(self.data)
        self.assert_near_json(fitted,self.model)
        self.assertTrue(fitted['validation']['accepted'])
        self.assertLess(fitted['validation']['blind_positions']['max_abs_w'],.27)
        self.assertLess(fitted['validation']['blind_lead']['max_abs_w'],.27)
    def test_known_context_and_inverse_work_without_network(self):
        model=CalibrationModel(self.model);rider=RiderGeometry(75,180)
        watts=model.power_watts(rider,45,3)
        self.assertAlmostEqual(watts,262.6606542435617,places=7)
        self.assertAlmostEqual(model.speed_kph(rider,watts,3),45,places=8)
        self.assertEqual(self.model['draft_factors'][3],self.model['draft_factors'][4])

if __name__=='__main__':unittest.main()
