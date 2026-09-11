"""Herramientas de diagnóstico MT5 demo: solo lectura, sin order_send."""
import csv
from dataclasses import asdict
import json
from pathlib import Path
from .mt5_adapter import MT5Adapter


def inspect_demo(queries):
    adapter=MT5Adapter()
    adapter.connect_demo()
    try:
        result={'account':adapter.account_snapshot(),'queries':{}}
        for query in queries:
            candidates=adapter.symbol_candidates(query)[:20]
            result['queries'][query]=[adapter.symbol_snapshot(s) for s in candidates]
        return result
    finally:
        adapter.close()


def export_m1(symbol, path, count=7000):
    if count<1:
        raise ValueError('count debe ser positivo')
    adapter=MT5Adapter()
    adapter.connect_demo()
    try:
        bars=adapter.bars(symbol,count=count)
        out=Path(path)
        with out.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['time','open','high','low','close','spread'])
            w.writeheader()
            w.writerows(asdict(b) for b in bars)
        return {'symbol':symbol,'bars':len(bars),'path':str(out)}
    finally:
        adapter.close()


def write_json(data,path):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
