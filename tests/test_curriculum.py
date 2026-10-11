"""The numbers quoted in fixed-files/chapters/CURRICULUM.md, recomputed."""
import unittest

import _path  # noqa: F401
import case_maths as m


def L(*ds):
    return m.legs_from(list(ds))


def sp(units, strike, prem):
    return {"kind": "short_put", "units": units, "strike": strike, "premium": prem}


class Curriculum(unittest.TestCase):
    def test_ch03_assignment(self):
        b = m.ledger_balances(480, [{"type": "open", "units": 10, "strike": 10, "premium_total": 8}, {"type": "expiry", "price": 7}])
        self.assertEqual((b["cash"], b["goods_value"], b["wealth"]), (388, 70, 458))
        self.assertEqual(m.result_at(L(sp(10, 10, 0.8)), 7), -22)
        self.assertEqual(m.result_at(L(sp(20, 10, 0.8)), 7), -44)
        self.assertEqual(m.result_at(L(sp(10, 10, 0.8)), 0), -92)

    def test_ch04_time(self):
        a = m.bs_price("put", 10, 10, 30 / 365, 0, 0.4)
        b = m.bs_price("put", 10, 10, 90 / 365, 0, 0.4)
        self.assertEqual((m.gbp_round(a), m.gbp_round(10 * a)), (0.46, 4.57))
        self.assertEqual((m.gbp_round(b), m.gbp_round(10 * b)), (0.79, 7.91))

    def test_ch05_basis(self):
        b = m.ledger_balances(480, [{"type": "open", "units": 10, "strike": 10, "premium_total": 8}, {"type": "expiry", "price": 7}])
        self.assertEqual((b["goods"]["basis"], b["unrealised"]), (92, -22))

    def test_ch06_long_call_and_delta(self):
        c = L({"kind": "long_call", "units": 10, "strike": 10, "premium": 1})
        self.assertEqual([m.result_at(c, s) for s in (9, 10.5, 13)], [-10, -5, 20])
        self.assertEqual(m.breakevens(c), [11])
        self.assertEqual(round(m.bs_delta("call", 10, 10, 30 / 365, 0, 0.4), 2), 0.52)
        self.assertEqual(round(m.itm_prob("call", 10, 10, 30 / 365, 0, 0.4), 2), 0.48)

    def test_ch07_covered_call(self):
        cc = L({"kind": "goods", "units": 10, "basis": 10}, {"kind": "short_call", "units": 10, "strike": 12, "premium": 1})
        self.assertEqual((m.result_at(cc, 15), m.result_at(cc, 5)), (30, -40))
        self.assertEqual(m.max_gain_loss(cc)[0], 30)

    def test_ch08_closing(self):
        b = m.ledger_balances(480, [{"type": "open", "units": 10, "strike": 10, "premium_total": 8}, {"type": "close", "cost": 12}])
        self.assertEqual(b["realised"], -4)  # £11 buy-back + £1 cost
        self.assertEqual(7 - 1 - 10, -4)     # bought for £10, sold for £7 less £1 cost

    def test_ch09_realised(self):
        ev = [{"type": "open", "units": 10, "strike": 10, "premium_total": 8}, {"type": "expiry", "price": 7}]
        before = m.ledger_balances(480, ev)
        after = m.ledger_balances(480, ev + [{"type": "sell-goods", "price": 7}])
        self.assertEqual((before["wealth"], after["wealth"], after["cash"], after["realised"]), (458, 458, 458, -22))

    def test_ch10_two_endings(self):
        p = L(sp(10, 10, 0.8))
        self.assertEqual((m.result_at(p, 12), m.result_at(p, 7)), (8, -22))

    def test_ch11_time_value(self):
        T = 90 / 365
        prices = [m.gbp_round(m.bs_price("call", 12, 10, T, 0, s)) for s in (0.3, 0.4, 0.5)]
        self.assertEqual(prices, [2.09, 2.21, 2.36])
        self.assertEqual(m.bs_price("call", 12, 10, 0, 0, 0.4), 2)
        self.assertEqual(m.gbp_round(m.bs_vega(10, 10, T, 0, 0.30)), 0.02)

    def test_ch12_sizing(self):
        both = m.fee_net(L(sp(10, 10, 0.8), sp(10, 15, 1.2)))
        res = m.reserve(L(sp(10, 10, 0.8), sp(10, 15, 1.2)))
        self.assertEqual((300 + both, res, 300 + both - res), (320, 250, 70))
        self.assertEqual(300 + 8 - 100, 208)
        self.assertEqual(300 + 12 - 150, 162)

    def test_ch14_many_small_wins(self):
        self.assertEqual(9 * 5 - 80, -35)
        self.assertAlmostEqual(0.9 * 5 - 0.1 * 80, -3.5)

    def test_ch15_shock(self):
        a = m.result_at(L(sp(10, 10, 0.8)), 6)
        b = m.result_at(L(sp(10, 15, 1.2)), 9)
        self.assertEqual((a, b, a + b), (-32, -48, -80))

    def test_ch16_balance_sheet(self):
        self.assertEqual(20 + 60 - 30, 50)
        self.assertEqual((20 + 25 + 60 - 30, 20 + 25), (75, 45))


if __name__ == "__main__":
    unittest.main()
