"""Explicit opt-in demo execution. Never closes positions or trades real accounts."""
import argparse
import json
from pathlib import Path
import time

from .__main__ import load_config
from .mt5_adapter import MT5Adapter
from .news import FileNews
from .risk import Journal
from .signals import decide


def check_session(adapter, identity):
    account = adapter.account()  # Reject real/unknown accounts on every call.
    if (account.login, account.server) != identity:
        raise RuntimeError('Cuenta o servidor cambiado; reinicie y verifique la cuenta demo')
    terminal = adapter.api.terminal_info()
    if terminal is None or not terminal.connected:
        raise RuntimeError('Terminal desconectado')
    if not terminal.trade_allowed or terminal.tradeapi_disabled:
        raise RuntimeError('MT5 bloquea trading algorítmico o la API Python')
    if not account.trade_allowed or not account.trade_expert:
        raise RuntimeError('Cuenta no permite trading automático')
    return account


def send_demo(adapter, identity, journal, key, request, kill_file):
    check_session(adapter, identity)
    if Path(kill_file).exists(): raise RuntimeError('STOP activo')
    positions = adapter.api.positions_get()
    orders = adapter.api.orders_get()
    if positions is None or orders is None or positions or orders:
        raise RuntimeError('Cuenta ocupada o estado desconocido; no se envía')
    if not journal.reserve(key):
        raise RuntimeError('Señal duplicada o envío pendiente de reconciliar')
    try:
        check_session(adapter, identity)
        if Path(kill_file).exists(): raise RuntimeError('STOP activo')
        result = adapter.api.order_send(request)
        # Partial fills, missing responses and all other statuses stop the runner.
        # No automatic retries: a timeout is not proof that no order was filled.
        if result is None or result.retcode != adapter.api.TRADE_RETCODE_DONE:
            journal.finish(key, 'uncertain')
            raise RuntimeError(f'Resultado requiere revisión en MT5: {getattr(result,"retcode",None)}')
        journal.finish(key, 'filled')
        return {'order': result.order, 'deal': result.deal,
                'volume': result.volume, 'price': result.price}
    except Exception:
        journal.finish(key, 'uncertain')
        raise


def main():
    parser = argparse.ArgumentParser(description='Prueba XAUUSD en cuenta DEMO; nunca cuenta real')
    parser.add_argument('--config', default='config.example.json')
    parser.add_argument('--state-dir', default='demo-state')
    parser.add_argument('--send-demo', action='store_true', help='Habilita órdenes únicamente demo')
    args = parser.parse_args()
    cfg = load_config(args.config)
    if cfg['strategy']['timeout_enabled']:
        parser.error('Este ejecutor no cierra por tiempo; configure timeout_enabled=false')
    state = Path(args.state_dir).resolve(); state.mkdir(parents=True, exist_ok=True)
    # Shared state directory and exclusive process lock prevent concurrent runners.
    import msvcrt
    lock = (state/'runner.lock').open('a+b')
    if lock.tell() == 0: lock.write(b'0'); lock.flush()
    lock.seek(0)
    try: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError: raise RuntimeError('Ya hay un ejecutor usando este directorio')
    def log(event, **fields):
        record = {'time': int(time.time()), 'event': event, **fields}
        line = json.dumps(record, ensure_ascii=False, allow_nan=False)
        print(line, flush=True)
        with (state/'events.jsonl').open('a', encoding='utf-8') as f: f.write(line+'\n')
    adapter = MT5Adapter(); journal = None
    try:
        adapter.connect_demo()
        account = adapter.account(); identity = (account.login, account.server)
        if account.currency != cfg['account_currency']:
            raise RuntimeError('Moneda de cuenta distinta de la configuración')
        sc = cfg['symbols']['gold']; symbol = sc['broker_symbol']
        if not symbol or not adapter.api.symbol_select(symbol, True):
            raise RuntimeError('Símbolo configurado no disponible')
        journal = Journal(state/f'intents-{account.login}.db')
        if journal.unresolved(): raise RuntimeError('Envío incierto anterior; revisar MT5 antes de reiniciar')
        news = FileNews(**cfg['news']); seen = None
        log('connected', account=adapter.account_snapshot(), symbol=symbol,
            sending=args.send_demo, stop_loss_enabled=cfg['strategy']['stop_loss_enabled'],
            timeout_enabled=False, config=cfg)
        if args.send_demo: check_session(adapter, identity)
        while not Path(cfg['risk']['kill_file']).exists():
            account = adapter.account()
            if (account.login, account.server) != identity: raise RuntimeError('Cuenta cambiada')
            positions = adapter.api.positions_get(); orders = adapter.api.orders_get()
            if positions is None or orders is None: raise RuntimeError('Estado de posiciones desconocido')
            now = int(time.time())
            if now//60 == seen: time.sleep(1); continue
            seen = now//60
            log('account', equity=account.equity, balance=account.balance,
                margin=account.margin, margin_free=account.margin_free,
                floating=account.profit, positions=len(positions))
            # Do not add to, close, hedge or modify any existing/manual position.
            if positions or orders:
                log('waiting_existing_position'); continue
            bars = adapter.bars(symbol, count=cfg['history_bars'])
            if len(bars) < cfg['strategy']['warmup']:
                log('blocked', reason='history_insufficient'); continue
            bar_close = bars[-1].time+60
            if not 0 <= now-bar_close <= cfg['risk']['max_age_seconds']:
                log('blocked', reason='stale_data_or_market_closed'); continue
            side, explanation = decide(bars, cfg['strategy'])
            log('signal', bar_close=bar_close, side=side, explanation=explanation)
            if not side: continue
            info = adapter.api.symbol_info(symbol)
            if info is None: raise RuntimeError('Contrato desconocido')
            distance = max(sum(b.high-b.low for b in bars[-14:])/14*cfg['strategy']['stop_atr'],
                           sc['contract']['min_stop'], info.trade_stops_level*info.point)
            try:
                request = adapter.prepare(symbol=symbol, side=side, stop_distance=distance,
                    reward_risk=cfg['strategy']['reward_risk'], bar_close=bar_close,
                    news=news, currencies=sc['news_currencies'],
                    risk_cfg={**cfg['risk'], 'max_spread':sc['max_spread']},
                    slippage=sc['slippage'], commission_roundtrip=sc['contract']['commission_roundtrip'],
                    stop_loss_enabled=cfg['strategy']['stop_loss_enabled'])
            except (ValueError, RuntimeError) as exc:
                log('blocked', reason=str(exc)); continue
            log('prepared', request=request)
            if args.send_demo:
                key = f'{identity[1]}:{identity[0]}:{symbol}:{bar_close}'
                result = send_demo(adapter, identity, journal, key, request, cfg['risk']['kill_file'])
                log('filled', **result)
        log('stopped', note='No se cierran posiciones existentes')
    except KeyboardInterrupt:
        log('stopped', note='Ctrl+C; posiciones existentes permanecen abiertas')
    except Exception as exc:
        log('error', reason=str(exc)); raise
    finally:
        if journal is not None: journal.close()
        adapter.close(); lock.close()


if __name__ == '__main__': main()
