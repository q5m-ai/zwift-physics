import contextlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import ROOT
from zwift_physics.__main__ import main
from zwift_physics._io import save


class CliTests(unittest.TestCase):
    def call(self,args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):code=main(args)
        return code,out.getvalue(),err.getvalue()
    def test_default_collection_is_offline_dry_run(self):
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Network forbidden')) as op:
            code,out,err=self.call(['collect-gopher','--plan',str(ROOT/'experiments/gopher-flat-v1.json')])
        self.assertEqual(code,0);self.assertEqual(err,'');self.assertFalse(op.called)
        result=json.loads(out);self.assertEqual(result['network_requests_sent'],0);self.assertEqual(result['expected_requests'],168)
    def test_live_mode_needs_retention_acknowledgement(self):
        with patch('zwift_physics.gopher.collect') as collect:
            code,out,err=self.call(['collect-gopher','--plan',str(ROOT/'experiments/gopher-flat-v1.json'),'--execute'])
        self.assertEqual(code,2);self.assertFalse(collect.called);self.assertIn('retention',err)
    def test_small_budget_fails_before_any_network(self):
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Network forbidden')) as op:
            code,out,err=self.call(['collect-gopher','--plan',str(ROOT/'experiments/gopher-flat-v1.json'),'--max-requests','10'])
        self.assertEqual(code,2);self.assertFalse(op.called);self.assertIn('budget',err)
    def fixture(self):
        return dict(schema_version=1,kind='effective-flat',cubic_law=dict(family='power_law',coefficients=[math.log(.15),.6,.8]),
            linear_law=dict(family='mass_linear',coefficients=[3,.8]),draft_factors=[1,.8,.7],context={'team_size':3},
            domain=dict(mass_kg=[55,95],height_cm=[160,200],speed_kph=[25,50]),validation={'accepted':True})
    def test_offline_prediction_and_extrapolation_label(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.json';save(path,self.fixture())
            args=['predict','--model',str(path),'--mass-kg','75','--height-cm','180','--position','2','--speed-kph','36']
            with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Network forbidden')):
                code,out,err=self.call(args)
            self.assertEqual(code,0);self.assertAlmostEqual(json.loads(out)['power_watts'],150)
            args[-1]='60';code,out,err=self.call(args)
            self.assertEqual(code,2)
            code,out,err=self.call(args+['--allow-extrapolation'])
            self.assertEqual(code,0);self.assertFalse(json.loads(out)['within_calibration_envelope'])

if __name__=='__main__':unittest.main()
