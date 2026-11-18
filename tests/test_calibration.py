import copy
import math
import tempfile
import unittest
from pathlib import Path
from support import plan,budget,FakeSession
from zwift_physics._io import digest
from zwift_physics.calibration import fit_dataset,least_squares,markdown_report
from zwift_physics.experiment import validate_dataset
from zwift_physics.gopher import collect
from zwift_physics.model import CalibrationModel
from zwift_physics.physics import RiderGeometry


class AlgebraTests(unittest.TestCase):
    def test_scaled_qr_recovers_known_coefficients(self):
        rows=[[1,x,x*x] for x in [-2,-1,0,1,2]]
        fit=least_squares(rows,[3+2*x-.5*x*x for x in [-2,-1,0,1,2]])
        for a,b in zip(fit,[3,2,-.5]):self.assertAlmostEqual(a,b,places=12)
    def test_different_units_are_safe(self):
        rows=[[v**3,v] for v in [25/3.6,50/3.6]]
        fit=least_squares(rows,[.15*a+3*b for a,b in rows])
        self.assertAlmostEqual(fit[0],.15,places=12);self.assertAlmostEqual(fit[1],3,places=12)
    def test_rank_deficiency_and_underdetermined_design_rejected(self):
        for rows,y in [([[1,1],[2,2]],[1,2]),([[1,2,3]],[1]),([],[])]:
            with self.assertRaises(ValueError):least_squares(rows,y)


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            cls.data=collect(plan(),Path(d)/'synthetic.json',budget=budget(),session_factory=FakeSession,progress=lambda _:None)
        cls.model,cls.report=fit_dataset(cls.data)
    def test_recovers_synthetic_law_with_rounding(self):
        m=self.model
        self.assertTrue(m['validation']['accepted'])
        self.assertEqual(m['cubic_law']['family'],'power_law')
        self.assertEqual(m['linear_law']['family'],'mass_linear')
        for a,b in zip(m['draft_factors'],[1,.82,.76,.70,.70]):self.assertAlmostEqual(a,b,places=4)
        self.assertLess(m['validation']['blind_positions']['max_abs_w'],.05)
    def test_declared_blind_counts(self):
        self.assertEqual(self.model['validation']['blind_positions']['count'],85)
        self.assertEqual(self.model['validation']['blind_lead']['count'],17)
        self.assertEqual(self.report['position_unique_count'],195)
        self.assertEqual(self.report['lead_unique_count'],39)
    def test_holdout_cannot_change_fitted_parameters(self):
        changed=copy.deepcopy(self.data)
        row=next(r for f in changed['frames'] if f['purpose']=='calibration' for r in f['observations'] if r['split']=='test' and r['position']==3)
        row['power_w']+=30;row['flat_if_percent']+=10
        other,_=fit_dataset(changed)
        for key in ['cubic_law','linear_law','draft_factors']:self.assertEqual(other[key],self.model[key])
        self.assertFalse(other['validation']['accepted'])
    def test_unseen_speed_is_not_used_for_fitting(self):
        changed=copy.deepcopy(self.data)
        row=next(r for f in changed['frames'] if f['purpose']=='calibration' for r in f['observations'] if r['split']=='train' and r['speed_kph']==40 and r['position']==2)
        row['power_w']+=30;row['flat_if_percent']+=10
        other,_=fit_dataset(changed)
        for key in ['cubic_law','linear_law','draft_factors']:self.assertEqual(other[key],self.model[key])
        self.assertFalse(other['validation']['accepted'])
    def test_repeatability_failure_cannot_be_averaged_away(self):
        changed=copy.deepcopy(self.data)
        row=next(r for f in changed['frames'] if f['batch_index']==2 and f['purpose']=='calibration' for r in f['observations'] if r['profile_id']=='m55_h160' and r['position']==3)
        row['power_w']+=.3;row['flat_if_percent']+=.1
        other,_=fit_dataset(changed)
        self.assertFalse(other['validation']['repeatability_pass']);self.assertFalse(other['validation']['accepted'])
    def test_ftp_dependence_blocks_mechanics_release(self):
        changed=copy.deepcopy(self.data)
        frame=next(f for f in changed['frames'] if f['purpose']=='ftp-invariance')
        row=frame['observations'][1];row['power_w']+=30;row['flat_if_percent']+=3000/row['normalization_ftp_w']
        other,_=fit_dataset(changed)
        self.assertFalse(other['validation']['ftp_invariance_pass']);self.assertFalse(other['validation']['accepted'])
    def test_duplicate_and_missing_coverage_rejected(self):
        changed=copy.deepcopy(self.data);changed['frames'].append(changed['frames'][0])
        with self.assertRaises(ValueError):fit_dataset(changed)
        changed=copy.deepcopy(self.data);changed['frames'].pop(0)
        with self.assertRaises(ValueError):fit_dataset(changed)
    def test_raw_extra_fields_and_context_tampering_refused(self):
        changed=copy.deepcopy(self.data);changed['frames'][0]['observations'][0]['name']='synthetic forbidden field'
        with self.assertRaises(ValueError):validate_dataset(changed)
        changed=copy.deepcopy(self.data);changed['frames'][0]['purpose']='unknown'
        with self.assertRaises(ValueError):validate_dataset(changed)
        changed=copy.deepcopy(self.data)
        for f in changed['frames']:f['context']['calculator_version']='99.0.0'
        with self.assertRaises(ValueError):validate_dataset(changed)
        changed=copy.deepcopy(self.data);changed['frames'][0]['observations'][0]['power_rounding_half_width_w']=100
        with self.assertRaises(ValueError):validate_dataset(changed)
    def test_fitting_is_deterministic_and_does_not_mutate_data(self):
        before=digest(self.data);other,report=fit_dataset(self.data)
        self.assertEqual(other,self.model);self.assertEqual(report,self.report);self.assertEqual(digest(self.data),before)
    def test_model_loads_and_predicts_unseen_body(self):
        m=CalibrationModel(self.model);r=RiderGeometry(80,175)
        watts=m.power_watts(r,45,3)
        self.assertGreater(watts,0);self.assertAlmostEqual(m.speed_kph(r,watts,3),45,places=9)
    def test_report_discloses_scope_and_source(self):
        report=markdown_report(self.model,self.report)
        for text in ['not actual in-game physics','FTP','0.015','five-rider','Dataset SHA-256','85']:
            self.assertIn(text,report)

if __name__=='__main__':unittest.main()
