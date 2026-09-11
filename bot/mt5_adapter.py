"""Adaptador MT5 demo. Lectura, validación y preparación simulada; nunca order_send."""
from datetime import datetime, timezone
import math
import time
from .market import Bar, validate
from .risk import Contract, gate, size_lots


class MT5Adapter:
    def __init__(self,api=None): self.api=api

    def connect_demo(self):
        if self.api is None:
            import MetaTrader5
            self.api=MetaTrader5
        if not self.api.initialize(): raise RuntimeError('MT5 initialize falló')
        try: self.account()
        except Exception:
            self.api.shutdown(); raise

    def account(self):
        a=self.api.account_info()
        if a is None or a.trade_mode!=self.api.ACCOUNT_TRADE_MODE_DEMO: raise RuntimeError('Solo cuentas demo; cuenta desconocida o real bloqueada')
        return a

    def symbols(self):
        self.account(); values=self.api.symbols_get()
        if values is None: raise RuntimeError('No se pudo leer símbolos')
        return [s.name for s in values]

    def bars(self,symbol,count=5000):
        self.account(); info=self.api.symbol_info(symbol)
        if info is None: raise ValueError('Símbolo exacto no disponible')
        if not self.api.symbol_select(symbol,True): raise RuntimeError('No se pudo seleccionar símbolo')
        rates=self.api.copy_rates_from_pos(symbol,self.api.TIMEFRAME_M1,1,count)
        if rates is None: raise RuntimeError('Error leyendo velas')
        return validate([Bar(int(r['time']),float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r['spread'])*info.point) for r in rates])

    def account_snapshot(self):
        a=self.account()
        return {'mode':'demo','server':getattr(a,'server',None),'currency':getattr(a,'currency',None),'leverage':getattr(a,'leverage',None),'balance':getattr(a,'balance',None),'equity':getattr(a,'equity',None),'margin_free':getattr(a,'margin_free',None)}

    def symbol_candidates(self,query):
        q=''.join(ch for ch in query.upper() if ch.isalnum()); aliases={'BITCOIN':('BTC','XBT','BITCOIN'),'BTC':('BTC','XBT','BITCOIN'),'GOLD':('XAU','GOLD'),'XAU':('XAU','GOLD')}; needles=aliases.get(q,(q,)); ranked=[]
        for name in self.symbols():
            normalized=''.join(ch for ch in name.upper() if ch.isalnum())
            if any(n in normalized for n in needles):
                score=sum(normalized.startswith(n) for n in needles)*10+sum(n in normalized for n in needles); ranked.append((-score,len(name),name))
        return [name for _,_,name in sorted(ranked)]

    def symbol_snapshot(self,symbol):
        self.account(); info=self.api.symbol_info(symbol); tick=self.api.symbol_info_tick(symbol)
        if info is None: raise ValueError('Símbolo exacto no disponible')
        return {'symbol':symbol,'description':getattr(info,'description',None),'currency_base':getattr(info,'currency_base',None),'currency_profit':getattr(info,'currency_profit',None),'currency_margin':getattr(info,'currency_margin',None),'digits':getattr(info,'digits',None),'point':getattr(info,'point',None),'trade_tick_size':getattr(info,'trade_tick_size',None),'trade_contract_size':getattr(info,'trade_contract_size',None),'volume_min':getattr(info,'volume_min',None),'volume_max':getattr(info,'volume_max',None),'volume_step':getattr(info,'volume_step',None),'trade_stops_level':getattr(info,'trade_stops_level',None),'filling_mode':getattr(info,'filling_mode',None),'bid':getattr(tick,'bid',None) if tick else None,'ask':getattr(tick,'ask',None) if tick else None,'tick_time':getattr(tick,'time',None) if tick else None}

    def prepare(self,*,symbol,side,stop_distance,reward_risk,bar_close,news,currencies,risk_cfg,slippage,commission_roundtrip):
        api=self.api; a=self.account(); now=int(time.time())
        if side not in (-1,1) or not all(math.isfinite(x) and x>0 for x in (stop_distance,reward_risk)): raise ValueError('Parámetros de orden inválidos')
        info=api.symbol_info(symbol); tick=api.symbol_info_tick(symbol); positions=api.positions_get(); orders=api.orders_get()
        if info is None or tick is None or positions is None or orders is None: raise RuntimeError('Estado MT5 incompleto')
        if orders: raise RuntimeError('Órdenes pendientes: reconciliar antes de continuar')
        if not (0<=now-tick.time<=risk_cfg['max_age_seconds']) or not (0<tick.bid<=tick.ask): raise RuntimeError('Cotización inválida u obsoleta')
        if not news.allowed(now,currencies)[0]: raise RuntimeError('Noticias bloquean entrada')
        midnight=datetime.fromtimestamp(now,timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0); deals=api.history_deals_get(midnight,datetime.fromtimestamp(now,timezone.utc))
        if deals is None: raise RuntimeError('Historial diario no disponible')
        day_cash=sum(d.profit+d.commission+d.swap+d.fee for d in deals); day_start=a.balance-day_cash; open_risk=0
        for p in positions:
            if p.sl<=0: raise RuntimeError('Posición sin stop: exposición desconocida')
            pt=api.symbol_info_tick(p.symbol)
            if pt is None or not 0<=now-pt.time<=risk_cfg['max_age_seconds']: raise RuntimeError('Cotización de cartera ausente')
            current=pt.bid if p.type==api.ORDER_TYPE_BUY else pt.ask; value=api.order_calc_profit(p.type,p.symbol,p.volume,current,p.sl)
            if value is None or not math.isfinite(value): raise RuntimeError('No se pudo valorar riesgo conjunto')
            open_risk+=max(0,-value)+commission_roundtrip*p.volume
        reason=gate(now=now,bar_close=bar_close,spread=tick.ask-tick.bid,equity=a.equity,day_start=day_start,positions=len(positions),open_risk=open_risk,cfg=risk_cfg)
        if reason: raise RuntimeError(reason)
        action=api.ORDER_TYPE_BUY if side>0 else api.ORDER_TYPE_SELL; entry=tick.ask if side>0 else tick.bid; step=info.trade_tick_size
        if step<=0: raise RuntimeError('Tick size desconocido')
        stop=round((entry-side*stop_distance)/step)*step; target=round((entry+side*stop_distance*reward_risk)/step)*step; reference=tick.bid if side>0 else tick.ask; minimum=info.trade_stops_level*info.point
        if stop<=0 or side*(reference-stop)<minimum or side*(target-reference)<minimum: raise RuntimeError('Stops inválidos según contrato/cotización')
        probe=info.volume_min; loss=api.order_calc_profit(action,symbol,probe,entry,stop-side*slippage); margin=api.order_calc_margin(action,symbol,probe,entry)
        if loss is None or margin is None or loss>=0 or margin<=0: raise RuntimeError('Valoración MT5 falló')
        c=Contract(a.currency,1,1,info.volume_min,info.volume_max,info.volume_step,minimum,margin/probe,commission_roundtrip); lots=size_lots(a.equity*risk_cfg['risk_per_trade'],-loss/probe+commission_roundtrip,c,a.margin_free)
        if lots<=0: raise RuntimeError('Riesgo insuficiente para lote mínimo')
        if info.filling_mode & 2: filling=api.ORDER_FILLING_IOC
        elif info.filling_mode & 1: filling=api.ORDER_FILLING_FOK
        else: raise RuntimeError('Modo de llenado no admitido')
        request={'action':api.TRADE_ACTION_DEAL,'symbol':symbol,'type':action,'volume':lots,'price':entry,'sl':stop,'tp':target,'deviation':int(slippage/info.point),'magic':260911,'comment':'research-demo','type_time':api.ORDER_TIME_GTC,'type_filling':filling}
        check=api.order_check(request)
        if check is None or check.retcode!=0: raise RuntimeError('order_check rechazó la orden')
        return request

    def execute(self,*,journal=None,send_demo=False,**parameters):
        if send_demo: raise RuntimeError('Envío de órdenes deshabilitado: esta versión es solo investigación/simulación')
        return {'mode':'simulation','request':self.prepare(**parameters)}

    def close(self):
        if self.api is not None: self.api.shutdown()
