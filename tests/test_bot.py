import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from bot.market import Bar,aggregate,validate
from bot.signals import analyze,pivots,line,decide,NAMES
from bot.news import FileNews
from bot.risk import Contract,size_lots,gate,Journal
from bot.backtest import run,exit_price,evaluate
from bot.mt5_adapter import MT5Adapter
from bot.__main__ import load_config

ROOT=Path(__file__).resolve().parents[1]
def cfg():
    c=load_config(ROOT/'config.example.json'); c['strategy']['trend_frames']=[]; c['risk']['kill_file']=str(ROOT/'tests'/'NO_STOP'); return c
def bars(n=150): return [Bar(1735689600+i*60,100,102,98,100+(i%3-1)*.5,.2) for i in range(n)]
def buy(history,cfg,enabled): return 1,{'fixture':True}

class Tests(unittest.TestCase):
    def test_01_validate(self): self.assertEqual(len(validate(bars(2))),2)
    def test_02_duplicate(self):
        with self.assertRaises(ValueError): validate([bars(1)[0]]*2)
    def test_03_nan(self):
        with self.assertRaises(ValueError): validate([Bar(0,1,2,1,float('nan'),0)])
    def test_04_aggregate_incomplete(self): self.assertEqual(aggregate(bars(14),15),[])
    def test_05_aggregate_complete(self): self.assertEqual(len(aggregate(bars(30),15)),2)
    def test_06_pivot_delay(self):
        bs=[Bar(i*60,2,5 if i==3 else 3,1,2,0) for i in range(8)]; self.assertIn((3,5,'H',5),pivots(bs[:6],2))
    def test_07_line(self): self.assertEqual(line([(1,3),(2,5),(3,7)]),(2,1))
    def test_08_detectors(self): self.assertEqual(set(analyze(bars(),cfg()['strategy'])),set(NAMES))
    def test_09_future_blind(self):
        c=cfg()['strategy']; bs=bars(); before=[decide(bs[:i],c) for i in range(60,80)]; bs[80:]=[Bar(b.time,1000,1100,900,1000,10) for b in bs[80:]]; self.assertEqual(before,[decide(bs[:i],c) for i in range(60,80)])
    def test_10_news_missing(self): self.assertFalse(FileNews(None).allowed(100,['USD'])[0])
    def test_11_news_optional(self): self.assertTrue(FileNews(None,required=False).allowed(100,['USD'])[0])
    def test_12_contract(self): self.assertAlmostEqual(Contract('USD',100,1,.01,10,.01,0,1000,7).loss(10,9),107)
    def test_13_sizing(self): self.assertEqual(size_lots(1,337,Contract('USD',100,1,.01,100,.01,0,1000,7),5000),0)
    def test_14_gate(self): self.assertIsNone(gate(now=120,bar_close=120,spread=.2,equity=10000,day_start=10000,positions=0,open_risk=0,cfg={**cfg()['risk'],'max_spread':1}))
    def test_15_kill(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'STOP'; p.touch(); r={**cfg()['risk'],'kill_file':str(p),'max_spread':1}; self.assertEqual(gate(now=120,bar_close=120,spread=.2,equity=10000,day_start=10000,positions=0,open_risk=0,cfg=r),'emergency_stop')
    def test_16_journal(self):
        with tempfile.TemporaryDirectory() as td:
            j=Journal(Path(td)/'s.db'); self.assertTrue(j.reserve('x')); self.assertFalse(j.reserve('x')); j.close()
    def test_17_stop_priority(self): self.assertEqual(exit_price({'side':1,'stop':98,'target':104},Bar(0,100,105,97,100,.2),.1)[1],'stop')
    def test_18_replay(self): self.assertGreater(run({'gold':bars()},cfg(),FileNews(None,required=False),signal_fn=buy)['metrics']['trades'],0)
    def test_19_evaluate(self): self.assertIn('comparisons',evaluate({'gold':bars()},cfg(),FileNews(None,required=False)))
    def test_20_real_account_blocked(self):
        api=NS(ACCOUNT_TRADE_MODE_DEMO=0,account_info=lambda:NS(trade_mode=1)); a=MT5Adapter(api)
        with self.assertRaises(RuntimeError): a.account()
    def test_21_order_send_blocked(self):
        a=MT5Adapter(NS())
        with self.assertRaisesRegex(RuntimeError,'deshabilitado'): a.execute(send_demo=True)

if __name__=='__main__': unittest.main()
