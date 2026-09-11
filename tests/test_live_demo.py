import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from bot.live_demo import check_session, send_demo
from bot.mt5_adapter import MT5Adapter
from bot.risk import Journal


class DemoTests(unittest.TestCase):
    def setup_api(self):
        account=NS(login=12,server='demo',trade_mode=0,trade_allowed=True,trade_expert=True)
        api=NS(ACCOUNT_TRADE_MODE_DEMO=0,TRADE_RETCODE_DONE=10009,
            account_info=Mock(return_value=account),
            terminal_info=Mock(return_value=NS(connected=True,trade_allowed=True,tradeapi_disabled=False)),
            positions_get=Mock(return_value=()),orders_get=Mock(return_value=()),
            order_send=Mock(return_value=NS(retcode=10009,order=1,deal=2,volume=.01,price=100)))
        return api,MT5Adapter(api)

    def test_real_account_never_sends(self):
        api,a=self.setup_api(); api.account_info.return_value.trade_mode=2
        with self.assertRaises(RuntimeError): check_session(a,(12,'demo'))
        api.order_send.assert_not_called()

    def test_switch_or_disabled_terminal_blocks(self):
        api,a=self.setup_api()
        with self.assertRaises(RuntimeError): check_session(a,(13,'demo'))
        api.terminal_info.return_value.tradeapi_disabled=True
        with self.assertRaises(RuntimeError): check_session(a,(12,'demo'))
        api.order_send.assert_not_called()

    def test_one_send_per_signal(self):
        api,a=self.setup_api()
        with tempfile.TemporaryDirectory() as td:
            j=Journal(Path(td)/'journal.db')
            try:
                result=send_demo(a,(12,'demo'),j,'signal',{'sl':0.,'tp':104},Path(td)/'STOP')
                self.assertEqual(result['order'],1)
                with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'signal',{},Path(td)/'STOP')
                api.order_send.assert_called_once()
            finally: j.close()

    def test_uncertain_send_blocks_new_signals(self):
        for result in (None,NS(retcode=10010)):
            api,a=self.setup_api(); api.order_send.return_value=result
            with tempfile.TemporaryDirectory() as td:
                j=Journal(Path(td)/'journal.db')
                try:
                    with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'first',{},Path(td)/'STOP')
                    with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'second',{},Path(td)/'STOP')
                    api.order_send.assert_called_once()
                    self.assertTrue(j.unresolved())
                finally: j.close()

    def test_existing_positions_and_stop_block(self):
        api,a=self.setup_api()
        with tempfile.TemporaryDirectory() as td:
            j=Journal(Path(td)/'journal.db'); stop=Path(td)/'STOP'
            try:
                api.positions_get.return_value=(NS(),)
                with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'first',{},stop)
                api.positions_get.return_value=(); stop.touch()
                with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'first',{},stop)
                api.order_send.assert_not_called()
            finally: j.close()

    def test_account_switch_immediately_before_send(self):
        api,a=self.setup_api()
        api.account_info.side_effect=[api.account_info.return_value,NS(trade_mode=2)]
        with tempfile.TemporaryDirectory() as td:
            j=Journal(Path(td)/'journal.db')
            try:
                with self.assertRaises(RuntimeError): send_demo(a,(12,'demo'),j,'first',{},Path(td)/'STOP')
                api.order_send.assert_not_called()
                self.assertTrue(j.unresolved())
            finally: j.close()
