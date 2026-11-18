import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from urllib.request import Request
from support import plan,budget,Clock,FakeSession
from zwift_physics._io import load,loads
from zwift_physics.experiment import ContractError,estimated_requests,extract_frame,validate_dataset,validate_plan
from zwift_physics.gopher import Budget,Calculator,CollectionStopped,Session,SameOriginRedirect,collect,BASE


class CollectionTests(unittest.TestCase):
    def sample(self):
        p=plan();s=FakeSession(budget());c=Calculator(p,0,s);c.setup();c.rotate(0)
        return p,s,c,c.sample(40)
    def test_public_safe_extraction(self):
        p,s,c,frame=self.sample();text=str(frame)
        for excluded in ['DO_NOT_PERSIST_SENTINEL','share_link','fatigue','wheel_power','name']:
            if excluded=='name':continue # route_name is intentional metadata
            self.assertNotIn(excluded,text)
        self.assertEqual(len(frame['observations']),5)
        self.assertNotEqual(frame['observations'][1]['power_w'],999.)
    def test_complete_mock_collection_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'data.json';lim=budget()
            data=collect(plan(),out,budget=lim,session_factory=FakeSession,progress=lambda _:None)
            self.assertEqual(data,load(out));validate_dataset(data)
            self.assertEqual(lim.count,estimated_requests(plan()));self.assertEqual(lim.count,168)
            self.assertEqual(len(data['frames']),47)
            self.assertEqual(sum(len(f['observations']) for f in data['frames'] if f['purpose']=='calibration'),225)
    def test_nonempty_session_is_not_modified(self):
        s=FakeSession(budget());s.riders={'0':{}}
        with self.assertRaises(CollectionStopped):Calculator(plan(),0,s).setup()
        self.assertEqual([a for a,k in s.calls],['displayTeam'])
    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'data.json';out.write_text('keep')
            with self.assertRaises(FileExistsError):collect(plan(),out,budget=budget(),session_factory=FakeSession)
            self.assertEqual(out.read_text(),'keep')
    def test_failed_collection_retains_incomplete_checkpoint(self):
        class Failing(FakeSession):
            def call(self,action,**fields):
                if action=='exportJson':raise CollectionStopped('synthetic failure')
                return super().call(action,**fields)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'partial.json'
            with self.assertRaises(CollectionStopped):collect(plan(),out,budget=budget(),session_factory=Failing,progress=lambda _:None)
            data=load(out);self.assertEqual(data['status'],'incomplete')
            with self.assertRaises(ValueError):validate_dataset(data)
    def test_contract_changes_stop(self):
        p,s,c,_=self.sample();export=s.export()
        mutations=[lambda x:x.update(version='99.0.0'),lambda x:x.update(efficiency_manual=False),
            lambda x:x['plan'].update(course_id='0'),lambda x:x['riders']['0'].update(name='Not synthetic'),
            lambda x:x['riders']['1'].update(pull_duration=15),lambda x:x['riders']['1'].update(order=4),
            lambda x:x['riders']['0'].update(flat_if=0),lambda x:x['riders']['0'].update(ftp='200'),
            lambda x:x['riders']['1'].update(flat_if=float('nan'))]
        for mutate in mutations:
            x=copy.deepcopy(export);mutate(x)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):extract_frame(x,p,0,c.order,c.ids,40,c.ftps)
    def test_plan_must_be_synthetic_and_partitioned(self):
        p=plan();p['synthetic_only']=False
        with self.assertRaises(ValueError):validate_plan(p)
        p=plan();p['batches'][0][0]['name']='private-name'
        with self.assertRaises(ValueError):validate_plan(p)
        p=plan();p['blind_speeds_kph']=[25]
        with self.assertRaises(ValueError):validate_plan(p)
    def test_json_nonfinite_and_duplicate_fields_refused(self):
        for value in ['{"x":NaN}','{"x":Infinity}','{"x":1e999}','{"x":-1e999}','{"x":1,"x":2}']:
            with self.assertRaises(ValueError):loads(value)


class TransportTests(unittest.TestCase):
    def test_bounded_serial_rate_gate(self):
        clock=Clock();b=Budget(3,2,clock=clock,sleep=clock.sleep)
        for _ in range(3):b.take()
        self.assertEqual(clock.now,4);self.assertEqual(b.count,3)
        with self.assertRaises(CollectionStopped):b.take()
        self.assertEqual(b.count,3)
    def test_no_unlimited_or_fast_requests(self):
        for maximum,interval in [(0,2),(251,2),(True,2),(10,1),(10,float('nan'))]:
            with self.assertRaises(ValueError):Budget(maximum,interval)
    def test_route_form_redirect_becomes_get_and_is_counted(self):
        b=budget();h=SameOriginRedirect(b);req=Request(BASE,data=b'courseSelect=2128890027')
        follow=h.redirect_request(req,None,302,'',{},BASE.rstrip('/'))
        self.assertEqual(follow.get_method(),'GET');self.assertIsNone(follow.data);self.assertEqual(b.count,1)
    def test_cross_origin_and_write_replay_refused(self):
        h=SameOriginRedirect(budget());req=Request(BASE,data=b'x=1')
        for code,url in [(302,'https://example.org/TTT/'),(307,BASE),(308,BASE),(302,BASE+'private')]:
            with self.assertRaises(CollectionStopped):h.redirect_request(req,None,code,'',{},url)
    def test_http_denial_never_retried_or_logged(self):
        for status in [401,403,429,500,503]:
            s=Session(budget());error=HTTPError(BASE,status,'',{},io.BytesIO(b'DO_NOT_PERSIST_SENTINEL'))
            with patch.object(s.opener,'open',side_effect=error) as op:
                with self.assertRaises(CollectionStopped) as caught:s.call('displayTeam')
                self.assertNotIn('DO_NOT_PERSIST',str(caught.exception));self.assertIn(str(status),str(caught.exception))
                self.assertEqual(op.call_count,1)
    def test_uncertain_write_not_retried(self):
        s=Session(budget())
        with patch.object(s.opener,'open',side_effect=URLError('DO_NOT_PERSIST_SENTINEL')) as op:
            with self.assertRaises(CollectionStopped) as caught:s.call('addRider')
            self.assertNotIn('DO_NOT_PERSIST',str(caught.exception));self.assertEqual(op.call_count,1)
    def test_paths_are_allowlisted(self):
        s=Session(budget())
        with self.assertRaises(ValueError):s.request('https://example.org/')
        self.assertEqual(s.budget.count,0)

if __name__=='__main__':unittest.main()
