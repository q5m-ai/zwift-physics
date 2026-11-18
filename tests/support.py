"""Entirely synthetic fake calculator. Never calls a service or uses accounts."""
import copy
import json
import math
from pathlib import Path
from zwift_physics._io import load
from zwift_physics.gopher import Budget

ROOT = Path(__file__).resolve().parents[1]


def plan():
    return load(ROOT / "experiments/gopher-flat-v1.json")


class Clock:
    def __init__(self):self.now=0.
    def __call__(self):return self.now
    def sleep(self, seconds):self.now+=seconds


def budget(maximum=200):
    c=Clock()
    return Budget(maximum,2,clock=c,sleep=c.sleep)


def coefficients(weight,height):
    return .15*(weight/75)**.6*(height/180)**.8, .034*(weight+8)


class FakeSession:
    def __init__(self, limiter):
        self.budget=limiter;self.riders={};self.order=[];self.speed=40.;self.route=None
        self.efficiency=0;self.manual=False;self.intensity=0;self.finishers=5;self.calls=[]

    def request(self,path="",data=None,*,expect_json=True):
        self.budget.take()
        if data is not None:
            self.budget.take();self.budget.take()  # observed POST -> GET -> canonical GET
            self.route=data['courseSelect']
        return None

    def call(self,action,**fields):
        self.budget.take();self.calls.append((action,copy.deepcopy(fields)))
        if action=='displayTeam':return {'success':True,'race':{'empty':not self.riders}}
        if action=='addRider':
            i=len(self.riders)
            self.riders[str(i)]=dict(name=fields['riderName'],weight=str(fields['riderWeight']),height=str(fields['riderHeight']),
                ftp=str(fields['riderFTP']),pull_duration=30,adjustment=100,effort=1,order=i)
            return dict(added=[i],updated=[],pending=[],not_found=[])
        if action=='moveAllToRace':self.order=list(range(len(self.riders)))
        elif action=='setEfficiency':self.efficiency=fields['efficiency'];self.manual=True
        elif action=='setIntensity':self.intensity=fields['intensity']
        elif action=='setMinimumFinishers':self.finishers=fields['minimum_finishers']
        elif action=='setTargetSpeed':self.speed=fields['targetSpeed']
        elif action=='updateRaceOrder':self.order=list(fields['order[]'])
        elif action=='applyEdits':
            for edit in json.loads(fields['edits']):
                r=self.riders[edit['rider']];r['pull_duration']=edit['pull_duration'];r['adjustment']=edit['adjustment']
        elif action=='updateRacer':self.riders[fields['rider']]['ftp']=str(fields['riderFTP'])
        elif action=='exportJson':return dict(success=True,content=json.dumps(self.export()))
        return dict(success=True)

    def export(self):
        rs=copy.deepcopy(self.riders);v=self.speed/3.6;draft=[1,.82,.76,.70,.70]
        for pos,i in enumerate(self.order):
            r=rs[str(i)];a,b=coefficients(float(r['weight']),float(r['height']));watts=a*draft[pos]*v**3+b*v
            r.update(order=pos,pull_speed=self.speed,pull_power=round(a*v**3+b*v,2),flat_if=round(100*watts/float(r['ftp']),2),
                     wheel_power={'2':999.},fatigue={'discard_me':'synthetic-only'})
        return dict(source='zwiftgopher-ttt',version=plan()['expected_calculator_version'],riders=rs,target_speed=str(self.speed),
            efficiency=self.efficiency,efficiency_manual=self.manual,intensity=self.intensity,minimum_finishers=self.finishers,
            unrelated='DO_NOT_PERSIST_SENTINEL',plan=dict(course_id=self.route,route='Tempus Fugit',laps=1,distance_km=19.59,
            elevation_m=31.8,share_link='DO_NOT_PERSIST_SENTINEL'))
