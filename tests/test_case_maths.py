"""Unit tests for case_maths.py: Black-Scholes, payoffs, breakevens, ledger, money formatting."""
import math
import unittest

import _path  # noqa: F401
import case_maths as m


def legs(*ds):
    return m.legs_from(list(ds))


class BlackScholes(unittest.TestCase):
    def test_textbook_at_the_money(self):
        # S=100, K=100, T=1, r=5%, sigma=20%: call 10.4506, put 5.5735 (standard textbook values)
        self.assertAlmostEqual(m.bs_price("call", 100, 100, 1, 0.05, 0.2), 10.4506, places=4)
        self.assertAlmostEqual(m.bs_price("put", 100, 100, 1, 0.05, 0.2), 5.5735, places=4)

    def test_textbook_hull_example(self):
        # S=42, K=40, T=0.5, r=10%, sigma=20%: call 4.76, put 0.81 (Hull's worked example)
        self.assertAlmostEqual(m.bs_price("call", 42, 40, 0.5, 0.10, 0.2), 4.7594, places=4)
        self.assertAlmostEqual(m.bs_price("put", 42, 40, 0.5, 0.10, 0.2), 0.8086, places=4)

    def test_put_call_parity(self):
        for S, K, T, r, s in [(10, 10, 30 / 365, 0, 0.4), (12, 10, 0.25, 0.03, 0.5), (8, 11, 2, 0.05, 0.25)]:
            c, p = m.bs_price("call", S, K, T, r, s), m.bs_price("put", S, K, T, r, s)
            self.assertAlmostEqual(c - p, S - K * math.exp(-r * T), places=10)

    def test_at_expiry_is_intrinsic(self):
        self.assertEqual(m.bs_price("call", 12, 10, 0, 0, 0.3), 2)
        self.assertEqual(m.bs_price("put", 12, 10, 0, 0, 0.3), 0)
        self.assertEqual(m.bs_price("put", 7, 10, 0, 0, 0.3), 3)

    def test_more_time_and_more_volatility_cost_more(self):
        a = m.bs_price("put", 10, 10, 30 / 365, 0, 0.4)
        b = m.bs_price("put", 10, 10, 90 / 365, 0, 0.4)
        c = m.bs_price("put", 10, 10, 90 / 365, 0, 0.5)
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertLess(b, 3 * a)  # three times the time is not three times the fee

    def test_vega_matches_one_point_bump(self):
        T = 90 / 365
        bump = m.bs_price("call", 10, 10, T, 0, 0.31) - m.bs_price("call", 10, 10, T, 0, 0.30)
        self.assertAlmostEqual(m.bs_vega(10, 10, T, 0, 0.30), bump, places=4)

    def test_delta_is_not_the_itm_probability(self):
        T = 30 / 365
        d = m.bs_delta("call", 10, 10, T, 0, 0.4)
        p = m.itm_prob("call", 10, 10, T, 0, 0.4)
        self.assertAlmostEqual(d, 0.5229, places=4)
        self.assertAlmostEqual(p, 0.4771, places=4)
        self.assertNotAlmostEqual(d, p, places=2)
        self.assertAlmostEqual(m.bs_delta("put", 10, 10, T, 0, 0.4), d - 1, places=12)

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            m.bs_price("straddle", 10, 10, 1, 0, 0.2)
        with self.assertRaises(ValueError):
            m.bs_price("call", 0, 10, 1, 0, 0.2)


class Payoffs(unittest.TestCase):
    def test_long_call(self):
        L = legs({"kind": "long_call", "units": 10, "strike": 10, "premium": 1})
        self.assertEqual([m.result_at(L, s) for s in (9, 10.5, 13)], [-10, -5, 20])
        self.assertEqual(m.breakevens(L), [11])
        self.assertEqual(m.max_gain_loss(L), (None, 10))
        self.assertEqual(m.fee_net(L), -10)

    def test_short_call_needs_goods(self):
        with self.assertRaises(ValueError):
            legs({"kind": "short_call", "units": 10, "strike": 12, "premium": 1})

    def test_long_put(self):
        L = legs({"kind": "long_put", "units": 10, "strike": 10, "premium": 0.8})
        self.assertEqual([m.result_at(L, s) for s in (12, 7, 0)], [-8, 22, 92])
        self.assertEqual(m.breakevens(L), [9.2])
        self.assertEqual(m.max_gain_loss(L), (92, 8))

    def test_short_put(self):
        L = legs({"kind": "short_put", "units": 10, "strike": 10, "premium": 0.8})
        self.assertEqual([m.result_at(L, s) for s in (12, 10, 7, 0)], [8, 8, -22, -92])
        self.assertEqual(m.breakevens(L), [9.2])
        self.assertEqual(m.max_gain_loss(L), (8, 92))
        self.assertEqual(m.reserve(L), 100)

    def test_covered_call(self):
        L = legs({"kind": "goods", "units": 10, "basis": 10},
                 {"kind": "short_call", "units": 10, "strike": 12, "premium": 1})
        self.assertEqual(m.result_at(L, 15), 30)
        self.assertEqual(m.result_at(L, 5), -40)
        self.assertEqual(m.breakevens(L), [9])
        self.assertEqual(m.max_gain_loss(L), (30, 90))
        own = legs({"kind": "goods", "units": 10, "basis": 10})
        self.assertEqual(m.result_at(own, 15) - m.result_at(L, 15), 20)  # upside given up

    def test_cash_secured_put_breakeven_and_reserve(self):
        L = legs({"kind": "short_put", "units": 10, "strike": 12, "premium": 0.9})
        self.assertEqual(m.breakevens(L), [11.1])
        self.assertEqual(m.reserve(L), 120)
        self.assertEqual(m.max_gain_loss(L), (9, 111))

    def test_no_position(self):
        self.assertEqual(m.breakevens([]), [])
        self.assertEqual(m.max_gain_loss([]), (0, 0))
        self.assertEqual(m.result_at([], 12), 0)

    def test_two_breakevens(self):
        # long call + long put at the same agreed price (not taught in v1; checks the solver)
        L = legs({"kind": "long_call", "units": 1, "strike": 10, "premium": 1},
                 {"kind": "long_put", "units": 1, "strike": 10, "premium": 1})
        self.assertEqual(m.breakevens(L), [8, 12])


class Ledger(unittest.TestCase):
    OPEN = {"type": "open", "units": 10, "strike": 10, "premium_total": 8}

    def test_expires_unused(self):
        b = m.ledger_balances(480, [self.OPEN])
        self.assertEqual((b["cash"], b["reserved"], b["available"]), (488, 100, 388))
        b = m.ledger_balances(480, [self.OPEN, {"type": "expiry", "price": 12}])
        self.assertEqual((b["cash"], b["reserved"], b["available"], b["realised"]), (488, 0, 488, 8))

    def test_assigned_then_marked_then_sold(self):
        ev = [self.OPEN, {"type": "expiry", "price": 7}]
        b = m.ledger_balances(480, ev)
        self.assertEqual((b["cash"], b["goods_value"], b["wealth"], b["unrealised"]), (388, 70, 458, -22))
        self.assertEqual(b["goods"]["basis"], 92)
        b = m.ledger_balances(480, ev + [{"type": "sell-goods", "price": 7}])
        self.assertEqual((b["cash"], b["realised"], b["wealth"]), (458, -22, 458))  # not £558, no double count
        b = m.ledger_balances(480, ev + [{"type": "mark", "price": 0}])
        self.assertEqual(b["unrealised"], -92)

    def test_close_early(self):
        b = m.ledger_balances(480, [self.OPEN, {"type": "close", "cost": 11}])
        self.assertEqual((b["cash"], b["realised"], b["reserved"]), (477, -3, 0))

    def test_pence_allowed(self):
        b = m.ledger_balances(200, [{"type": "open", "units": 10, "strike": 10, "premium_total": 4.57}])
        self.assertEqual(b["cash"], 204.57)

    def test_rules_enforced(self):
        bad = [
            (480, [{"type": "open", "units": 10, "strike": 100, "premium_total": 8}]),   # can't fund £1,000
            (480, [self.OPEN, self.OPEN]),                                               # one promise only
            (480, [{"type": "close", "cost": 1}]),                                       # nothing to close
            (480, [{"type": "mark", "price": 5}]),                                       # no goods
            (480, [{"type": "open", "units": 10, "strike": 10, "premium_total": 8.001}]),  # sub-penny
            (480, [{"type": "teleport"}]),
            (-1, []),
        ]
        for cash, ev in bad:
            with self.assertRaises(m.LedgerError, msg=str(ev)):
                m.ledger_balances(cash, ev)


class Money(unittest.TestCase):
    def test_format(self):
        self.assertEqual(m.fmt_gbp(8), "£8")
        self.assertEqual(m.fmt_gbp(9.2), "£9.20")
        self.assertEqual(m.fmt_gbp(-22), "\u2212£22")
        self.assertEqual(m.fmt_gbp(8, sign=True), "+£8")
        self.assertEqual(m.fmt_gbp(1234.5), "£1,234.50")

    def test_rounding(self):
        self.assertEqual(m.gbp_round(0.125), 0.13)
        self.assertEqual(m.gbp_round(-0.125), -0.13)
        self.assertEqual(m.gbp_round(10 * 0.8), 8)


if __name__ == "__main__":
    unittest.main()
