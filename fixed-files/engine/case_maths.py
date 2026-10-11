#!/usr/bin/env python3
"""Case maths for the Tidewick bot. Paper money only; fictional pounds.

Python 3.9+, standard library only. Charts use Pillow (PNG) when it is installed, otherwise a
plain SVG file is written instead. No network, no live prices.

Commands
  price   --kind call|put --spot S --strike K --days D --vol 0.40 [--rate 0]
          Black-Scholes price per unit, plus delta and vega (sensitivity estimates, not forecasts).
  payoff  --legs JSON --at PRICE [--at PRICE ...]
          Result at the end date for a position, breakeven(s), most you can make / lose.
  check   CHAPTER.md [CHAPTER.md ...]
          Recompute every number a chapter's case block claims. Exit 1 on any mismatch.
  receipt CHAPTER.md --choice ID
          The receipt text the bot shows after the player chooses (maths shown).
  chart   CHAPTER.md --choice ID --out FILE.png
          A labelled payoff chart (result at the end date against the price), British pounds.

Legs (JSON list). premium is per unit; basis is the per-unit cost of goods already owned.
  {"kind": "long_call"|"short_call"|"long_put"|"short_put", "units": 10, "strike": 10, "premium": 0.8}
  {"kind": "goods", "units": 10, "basis": 10}
Covered call = goods + short_call. Cash-secured put = short_put (the full agreed price is set aside).
A short call without enough goods to cover it is refused: the game never sells uncovered calls.

Plain words used in receipts (market words in brackets): fee (premium), agreed price (strike),
end date (expiry), promise (obligation), the right is used (exercise / assignment).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MINUS = "\u2212"
EPS = 1e-9

# ---------------------------------------------------------------- money helpers

def gbp_round(x: float) -> float:
    """Round to whole pence (half away from zero), returning a float."""
    v = math.floor(abs(x) * 100 + 0.5 + 1e-9) / 100
    return v if x >= 0 else -v


def fmt_gbp(x: float, sign: bool = False) -> str:
    """£8, £9.20, −£22, +£8 (sign=True). Whole pounds drop the pence."""
    v = gbp_round(x)
    a = abs(v)
    body = f"£{a:,.0f}" if abs(a - round(a)) < 0.005 else f"£{a:,.2f}"
    if v < 0:
        return MINUS + body
    return ("+" + body) if (sign and v > 0) else body


def is_money(n) -> bool:
    """Non-negative, at most whole pence, at most £1,000,000 (ledger.ts used whole pounds;
    this port allows pence so modelled fees can be used)."""
    if isinstance(n, bool) or not isinstance(n, (int, float)) or math.isnan(n):
        return False
    return 0 <= n <= 1_000_000 and abs(n * 100 - round(n * 100)) < 1e-6

# ---------------------------------------------------------------- Black-Scholes

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d12(S, K, T, r, sigma):
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def bs_price(kind: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    """European Black-Scholes price per unit. T in years, sigma and r annual (0.40 = 40%).
    At or after the end date (T <= 0) the value is what the right is worth if used now."""
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    if S <= 0 or K <= 0:
        raise ValueError("spot and strike must be positive")
    if T <= 0:
        return max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)
    if sigma <= 0:
        fwd = S - K * math.exp(-r * T)
        return max(fwd, 0.0) if kind == "call" else max(-fwd, 0.0)
    d1, d2 = _d12(S, K, T, r, sigma)
    if kind == "call":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def bs_delta(kind: str, S, K, T, r, sigma) -> float:
    """How much the option value moves per £1 move in the price, other inputs fixed.
    A sensitivity estimate. It is NOT an exact probability of anything."""
    if T <= 0 or sigma <= 0:
        itm = (S > K) if kind == "call" else (S < K)
        return (1.0 if kind == "call" else -1.0) if itm else 0.0
    d1, _ = _d12(S, K, T, r, sigma)
    return norm_cdf(d1) if kind == "call" else norm_cdf(d1) - 1.0


def bs_vega(S, K, T, r, sigma) -> float:
    """Value change per unit for a 1 percentage-point rise in implied volatility (same for calls and puts)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1, _ = _d12(S, K, T, r, sigma)
    return S * norm_pdf(d1) * math.sqrt(T) / 100.0


def itm_prob(kind: str, S, K, T, r, sigma) -> float:
    """Model (risk-neutral) chance of finishing past the agreed price. Ported from the source engine.
    It depends entirely on the model's inputs; never present it as a real-world forecast."""
    if T <= 0:
        return 1.0 if ((S > K) if kind == "call" else (S < K)) else 0.0
    _, d2 = _d12(S, K, T, r, sigma)
    return norm_cdf(d2) if kind == "call" else norm_cdf(-d2)

# ---------------------------------------------------------------- positions and payoffs

KINDS = ("long_call", "short_call", "long_put", "short_put", "goods")


@dataclass
class Leg:
    kind: str
    units: float
    strike: float = 0.0
    premium: float = 0.0   # per unit
    basis: float = 0.0     # per unit, goods only

    @staticmethod
    def from_dict(d: dict) -> "Leg":
        k = d.get("kind")
        if k not in KINDS:
            raise ValueError(f"unknown leg kind {k!r}")
        units = d.get("units")
        if not isinstance(units, (int, float)) or units <= 0:
            raise ValueError("units must be positive")
        if k == "goods":
            return Leg(k, float(units), basis=float(d.get("basis", 0)))
        if not d.get("strike", 0) > 0:
            raise ValueError("an option leg needs a positive strike")
        return Leg(k, float(units), strike=float(d["strike"]), premium=float(d.get("premium", 0)))

    def at(self, S: float) -> float:
        """Result of this leg at the end date if the price is S (fees included, costs excluded)."""
        u = self.units
        if self.kind == "goods":
            return u * (S - self.basis)
        if self.kind == "long_call":
            return u * (max(S - self.strike, 0.0) - self.premium)
        if self.kind == "short_call":
            return u * (self.premium - max(S - self.strike, 0.0))
        if self.kind == "long_put":
            return u * (max(self.strike - S, 0.0) - self.premium)
        return u * (self.premium - max(self.strike - S, 0.0))  # short_put


def legs_from(data) -> list[Leg]:
    legs = [Leg.from_dict(d) for d in (data or [])]
    goods = sum(l.units for l in legs if l.kind == "goods")
    short_calls = sum(l.units for l in legs if l.kind == "short_call")
    if short_calls > goods + EPS:
        raise ValueError("uncovered short call: this game only sells calls on goods already owned")
    return legs


def result_at(legs: list[Leg], S: float) -> float:
    return gbp_round(sum(l.at(S) for l in legs))


def fee_net(legs: list[Leg]) -> float:
    """Fees received minus fees paid (positive = money in)."""
    t = 0.0
    for l in legs:
        if l.kind in ("short_call", "short_put"):
            t += l.units * l.premium
        elif l.kind in ("long_call", "long_put"):
            t -= l.units * l.premium
    return gbp_round(t)


def reserve(legs: list[Leg]) -> float:
    """Cash set aside while open: every short put is cash-secured at units x agreed price."""
    return gbp_round(sum(l.units * l.strike for l in legs if l.kind == "short_put"))


def _kinks(legs):
    return sorted({0.0, *(l.strike for l in legs if l.kind != "goods")})


def _slope_beyond(legs) -> float:
    s = 0.0
    for l in legs:
        if l.kind in ("goods", "long_call"):
            s += l.units
        elif l.kind == "short_call":
            s -= l.units
    return s


def breakevens(legs: list[Leg]) -> list[float]:
    """End-date prices where the result crosses zero (piecewise-linear, so solved exactly)."""
    if not legs:
        return []
    pts = _kinks(legs)
    out = []
    f = lambda x: sum(l.at(x) for l in legs)
    segs = list(zip(pts, pts[1:]))
    for a, b in segs:
        fa, fb = f(a), f(b)
        if abs(fa) < EPS and a not in out and not (abs(fb) < EPS):
            out.append(a)
        if fa * fb < 0:
            out.append(a + (b - a) * (-fa) / (fb - fa))
    last = pts[-1]
    fl, s = f(last), _slope_beyond(legs)
    if abs(fl) < EPS and abs(s) > EPS:
        out.append(last)
    elif abs(s) > EPS and fl * s < 0:
        out.append(last - fl / s)
    return sorted({gbp_round(x) for x in out})


def max_gain_loss(legs: list[Leg]):
    """(most you can make, most you can lose) at the end date; None means no upper limit.
    The loss is returned as a positive number (0 if the position has no downside)."""
    if not legs:
        return 0.0, 0.0
    vals = [sum(l.at(x) for l in legs) for x in _kinks(legs)]
    s = _slope_beyond(legs)
    hi = None if s > EPS else max(vals)
    lo_val = min(vals) if s >= -EPS else None
    gain = None if hi is None else gbp_round(max(hi, 0.0))
    loss = None if lo_val is None else gbp_round(max(-lo_val, 0.0))
    return gain, loss

# ---------------------------------------------------------------- ledger (ported from the source game's practice ledger)

class LedgerError(ValueError):
    pass


def ledger_balances(start_cash: float, events: list[dict]) -> dict:
    """One practice purse with at most one cash-secured put promise, then any goods it brings.

    Events (same rules as the source ledger; money may now be pence, not only whole pounds):
      {"type": "open", "units": U, "strike": K, "premium_total": P}   must be the first event
      {"type": "close", "cost": C}            buy the promise back before the end date
      {"type": "expiry", "price": X}          end date: below the agreed price, the goods are bought
      {"type": "mark", "price": X}            re-value goods held
      {"type": "sell-goods", "price": X}      sell goods held
    Teaching convention, not tax accounting: the fee is carried into the goods' basis."""
    if not is_money(start_cash) or not isinstance(events, list):
        raise LedgerError("Invalid practice ledger.")
    b = {"cash": float(start_cash), "reserved": 0.0, "fee_received": 0.0, "realised": 0.0,
         "position": None, "goods": None}
    for i, e in enumerate(events):
        t = e.get("type") if isinstance(e, dict) else None
        if t == "open":
            u, k, p = e.get("units"), e.get("strike"), e.get("premium_total")
            ok = (i == 0 and isinstance(u, int) and not isinstance(u, bool) and u > 0 and is_money(k) and k > 0
                  and is_money(p) and is_money(u * k) and p <= u * k and b["cash"] >= u * k)
            if not ok:
                raise LedgerError("Cannot open this promise.")
            b["position"] = {"units": u, "strike": k, "premium_total": p}
            b["cash"] += p
            b["fee_received"] = p
            b["reserved"] = u * k
        elif t == "close":
            c = e.get("cost")
            if not b["position"] or not is_money(c) or c > b["cash"]:
                raise LedgerError("Cannot close this promise.")
            b["cash"] -= c
            b["realised"] = b["position"]["premium_total"] - c
            b["position"], b["reserved"] = None, 0.0
        elif t == "expiry":
            x = e.get("price")
            if not b["position"] or not is_money(x):
                raise LedgerError("Cannot settle this promise.")
            pos = b["position"]
            if x < pos["strike"]:
                cost = pos["units"] * pos["strike"]
                b["cash"] -= cost
                b["goods"] = {"units": pos["units"], "purchase_cost": cost,
                              "basis": cost - pos["premium_total"], "unit_mark": x}
            else:
                b["realised"] = pos["premium_total"]
            b["position"], b["reserved"] = None, 0.0
        elif t in ("mark", "sell-goods"):
            x = e.get("price")
            if not b["goods"] or not is_money(x):
                raise LedgerError("No goods to value or sell.")
            if t == "mark":
                b["goods"]["unit_mark"] = x
            else:
                proceeds = b["goods"]["units"] * x
                b["cash"] += proceeds
                b["realised"] = proceeds - b["goods"]["basis"]
                b["goods"] = None
        else:
            raise LedgerError("Unknown transaction.")
    g = b["goods"]
    b["goods_value"] = g["units"] * g["unit_mark"] if g else 0.0
    b["unrealised"] = b["goods_value"] - g["basis"] if g else 0.0
    b["available"] = b["cash"] - b["reserved"]
    b["wealth"] = b["cash"] + b["goods_value"]
    for k in ("cash", "reserved", "fee_received", "realised", "goods_value", "unrealised", "available", "wealth"):
        b[k] = gbp_round(b[k])
    return b

# ---------------------------------------------------------------- chapter files

REQUIRED_META = ["id", "season", "chapter", "title", "concept", "status", "concept_ids", "clue_id"]
REQUIRED_SECTIONS = ["Learning objectives", "Scene", "Case", "Choices", "Reason prompt", "Expected maths", "Outcome",
                     "Companion line", "Learn panel", "Clue",
                     "Recap questions"]


def parse_chapter(path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError(f"{path}: no frontmatter")
    meta = {}
    for line in m.group(1).splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"')
    body = text[m.end():]
    sections, cur = {}, None
    for line in body.splitlines():
        h = re.match(r"^## (.+?)\s*$", line)
        if h:
            cur = h.group(1)
            sections[cur] = []
        elif cur:
            sections[cur].append(line)
    sections = {k: "\n".join(v).strip() for k, v in sections.items()}
    cm = re.search(r"```case-json\n(.*?)\n```", body, re.S)
    if not cm:
        raise ValueError(f"{path}: no ```case-json block")
    case = json.loads(cm.group(1))
    return {"meta": meta, "sections": sections, "case": case, "path": str(path)}


def _num_key(k):
    return float(k)


def check_chapter(path) -> list[tuple[bool, str]]:
    """Recompute every claim in the chapter's expected block. Returns (ok, line) pairs."""
    out = []
    try:
        ch = parse_chapter(path)
    except Exception as e:  # noqa: BLE001
        return [(False, f"cannot read chapter: {e}")]
    meta, sec, case = ch["meta"], ch["sections"], ch["case"]
    for k in REQUIRED_META:
        out.append((k in meta and meta[k] != "", f"frontmatter has {k}"))
    for s in REQUIRED_SECTIONS:
        out.append((s in sec and sec[s] != "", f"section '{s}' present"))
    positions = case.get("positions", {})
    for cid in case.get("choices", []):
        out.append((cid in positions, f"choice {cid} has a position"))
    outcome = case.get("outcome_price")
    start_cash = case.get("start_cash")
    for pid, exp in case.get("expected", {}).items():
        if pid not in positions:
            out.append((False, f"{pid}: expected numbers for an unknown position"))
            continue
        try:
            legs = legs_from(positions[pid]["legs"])
        except ValueError as e:
            out.append((False, f"{pid}: {e}"))
            continue
        def cmp(label, got, want):
            if want is None or got is None or isinstance(want, str) or isinstance(got, str):
                ok = got == want or (want == "unlimited" and got is None)
            else:
                ok = abs(got - want) < 0.005
            show = lambda v: "unlimited" if v is None else (fmt_gbp(v) if isinstance(v, (int, float)) else v)
            out.append((ok, f"{pid} {label}: expected {show(want)}, computed {show(got)}"))
        if "fee_net" in exp:
            cmp("fee in (+) / out (−)", fee_net(legs), exp["fee_net"])
        if "reserve" in exp:
            cmp("money set aside", reserve(legs), exp["reserve"])
        if "breakevens" in exp:
            got, want = breakevens(legs), [float(x) for x in exp["breakevens"]]
            ok = len(got) == len(want) and all(abs(a - b) < 0.005 for a, b in zip(got, want))
            out.append((ok, f"{pid} breakeven(s): expected {[fmt_gbp(x) for x in want]}, computed {[fmt_gbp(x) for x in got]}"))
        g, l = max_gain_loss(legs)
        if "max_gain" in exp:
            cmp("most you can make", g, None if exp["max_gain"] == "unlimited" else exp["max_gain"])
        if "max_loss" in exp:
            cmp("most you can lose", l, None if exp["max_loss"] == "unlimited" else exp["max_loss"])
        for price, want in exp.get("result_at", {}).items():
            cmp(f"result at {fmt_gbp(_num_key(price))}", result_at(legs, _num_key(price)), want)
        if "ledger" in exp:
            ev = positions[pid].get("ledger_events")
            if start_cash is None or ev is None:
                out.append((False, f"{pid}: ledger numbers need start_cash and ledger_events"))
                continue
            for stage, fields in exp["ledger"].items():
                n = {"after_open": 1 if ev else 0, "at_end": len(ev)}.get(stage)
                if n is None:
                    out.append((False, f"{pid}: unknown ledger stage {stage}"))
                    continue
                try:
                    bal = ledger_balances(start_cash, ev[:n])
                except LedgerError as e:
                    out.append((False, f"{pid} ledger {stage}: {e}"))
                    continue
                for f, want in fields.items():
                    cmp(f"ledger {stage} {f}", bal.get(f), want)
            if pid in case.get("choices", []) and ev and ev[-1].get("type") == "expiry" and outcome is not None:
                out.append((abs(ev[-1]["price"] - outcome) < EPS, f"{pid} ledger ends at the chapter's outcome price"))
    return out

# ---------------------------------------------------------------- receipt text

def _leg_line(l: Leg, S: float, unit: str) -> str:
    u = int(l.units) if float(l.units).is_integer() else l.units
    if l.kind == "goods":
        return (f"Goods you own: {u} {unit} bought at {fmt_gbp(l.basis)}, now {fmt_gbp(S)}: "
                f"{fmt_gbp(l.at(S), sign=True)}")
    K, prem = l.strike, l.premium
    fee_txt = f"fee {u} \u00d7 {fmt_gbp(prem)} = {fmt_gbp(u * prem)}"
    if l.kind == "short_put":
        if S < K:
            return (f"Your promise to buy at {fmt_gbp(K)}: the price ended below it, so the right is used. "
                    f"You pay {u} \u00d7 {fmt_gbp(K)} = {fmt_gbp(u * K)} for {unit} worth {u} \u00d7 {fmt_gbp(S)} = "
                    f"{fmt_gbp(u * S)}: {fmt_gbp(-u * (K - S))}. Plus the {fee_txt} you kept. "
                    f"Net {fmt_gbp(l.at(S), sign=True)}")
        return (f"Your promise to buy at {fmt_gbp(K)}: the price ended at or above it, so the right is not used. "
                f"You keep the {fee_txt}. Net {fmt_gbp(l.at(S), sign=True)}")
    if l.kind == "long_put":
        if S < K:
            return (f"Your right to sell at {fmt_gbp(K)}: worth using. {u} \u00d7 ({fmt_gbp(K)} {MINUS} {fmt_gbp(S)}) = "
                    f"{fmt_gbp(u * (K - S))}, less the {fee_txt} you paid. Net {fmt_gbp(l.at(S), sign=True)}")
        return f"Your right to sell at {fmt_gbp(K)}: not worth using. You paid the {fee_txt}. Net {fmt_gbp(l.at(S), sign=True)}"
    if l.kind == "long_call":
        if S > K:
            return (f"Your right to buy at {fmt_gbp(K)}: worth using. {u} \u00d7 ({fmt_gbp(S)} {MINUS} {fmt_gbp(K)}) = "
                    f"{fmt_gbp(u * (S - K))}, less the {fee_txt} you paid. Net {fmt_gbp(l.at(S), sign=True)}")
        return f"Your right to buy at {fmt_gbp(K)}: not worth using. You paid the {fee_txt}. Net {fmt_gbp(l.at(S), sign=True)}"
    # short_call
    if S > K:
        return (f"Your promise to sell at {fmt_gbp(K)}: the price ended above it, so the right is used. "
                f"You give up {u} \u00d7 ({fmt_gbp(S)} {MINUS} {fmt_gbp(K)}) = {fmt_gbp(u * (S - K))} of rise. "
                f"Plus the {fee_txt} you kept. Net {fmt_gbp(l.at(S), sign=True)}")
    return f"Your promise to sell at {fmt_gbp(K)}: the right is not used. You keep the {fee_txt}. Net {fmt_gbp(l.at(S), sign=True)}"


def receipt(path, choice: str) -> str:
    ch = parse_chapter(path)
    case, meta = ch["case"], ch["meta"]
    pos = case["positions"].get(choice)
    if pos is None or choice not in case["choices"]:
        raise ValueError(f"no choice {choice!r} in {path}")
    legs = legs_from(pos["legs"])
    unit = case.get("unit", "units")
    S = case["outcome_price"]
    lines = [f"RECEIPT \u00b7 Chapter {meta['chapter']}: {meta['title']} \u00b7 your choice {choice} ({pos['label']})",
             f"End-date price: {fmt_gbp(S)} per {unit.rstrip('s')} (fictional)."]
    if not legs:
        lines.append(f"You made no promise, so nothing changes: {fmt_gbp(0)}.")
        for oid in case["choices"]:
            ol = legs_from(case["positions"][oid]["legs"])
            if ol:
                lines.append(f"Had you chosen {oid} ({case['positions'][oid]['label']}): "
                             f"{fmt_gbp(result_at(ol, S), sign=True)} at {fmt_gbp(S)}; "
                             + "; ".join(f"{fmt_gbp(result_at(ol, p), sign=True)} at {fmt_gbp(p)}"
                                         for p in case.get("what_if_prices", []) if p != S) + ".")
    else:
        fee = fee_net(legs)
        res = reserve(legs)
        if fee:
            lines.append(("Fee received" if fee > 0 else "Fee paid") + f": {fmt_gbp(abs(fee))}.")
        if res:
            lines.append(f"Money set aside while the promise was open: {fmt_gbp(res)}.")
        for l in legs:
            lines.append("\u2022 " + _leg_line(l, S, unit))
        lines.append(f"YOUR RESULT: {fmt_gbp(result_at(legs, S), sign=True)}, before any costs.")
        if case.get("start_cash") is not None and pos.get("ledger_events"):
            b = ledger_balances(case["start_cash"], pos["ledger_events"])
            lines.append(f"Cash {fmt_gbp(case['start_cash'])} \u2192 {fmt_gbp(b['cash'])}; set aside now {fmt_gbp(b['reserved'])}; "
                         f"free to use {fmt_gbp(b['available'])}" + (f"; goods worth {fmt_gbp(b['goods_value'])}" if b["goods"] else "") + ".")
        bes = breakevens(legs)
        if bes:
            lines.append("Breakeven: " + " and ".join(f"{fmt_gbp(x)} per {unit.rstrip('s')}" for x in bes) + ".")
        g, lo = max_gain_loss(legs)
        lines.append(f"Most you could make: {'no upper limit' if g is None else fmt_gbp(g)}. "
                     f"Most you could lose: {'no upper limit' if lo is None else fmt_gbp(lo)}.")
    whatifs = [p for p in case.get("what_if_prices", []) if p != S]
    if whatifs and legs:
        lines.append("If the price had ended elsewhere: " + "; ".join(
            f"at {fmt_gbp(p)} \u2192 {fmt_gbp(result_at(legs, p), sign=True)}" for p in whatifs) + ".")
    lines.append("Paper money only. Fictional pounds, not a market price.")
    return "\n".join(lines)

# ---------------------------------------------------------------- charts

def _nice_step(span, target=8):
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class _PilCanvas:
    def __init__(self, w, h):
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
        self.Image, self.ImageFont = Image, ImageFont
        self.im = Image.new("RGB", (w, h), "white")
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self._fonts = {}

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
                     "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
                     "Arial Bold.ttf" if bold else "Arial.ttf"]
            f = None
            for n in names:
                try:
                    f = self.ImageFont.truetype(n, size)
                    break
                except OSError:
                    continue
            if f is None:
                try:
                    f = self.ImageFont.load_default(size=size)
                except TypeError:
                    f = self.ImageFont.load_default()
            self._fonts[key] = f
        return self._fonts[key]

    def poly(self, pts, fill):
        self.d.polygon(pts, fill=fill)

    def line(self, pts, colour, width=2, dash=False):
        if not dash:
            self.d.line(pts, fill=colour, width=width, joint="curve")
            return
        (x1, y1), (x2, y2) = pts
        n = max(int(math.hypot(x2 - x1, y2 - y1) // 10), 1)
        for i in range(0, n, 2):
            a, b = i / n, min((i + 1) / n, 1)
            self.d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)],
                        fill=colour, width=width)

    def circle(self, x, y, r, fill, outline="white"):
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=outline, width=2)

    def text(self, x, y, s, size=16, colour="#222222", anchor="la", bold=False, box=False):
        f = self.font(size, bold)
        if box:
            bb = self.d.textbbox((x, y), s, font=f, anchor=anchor)
            self.d.rounded_rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], radius=6,
                                     fill=(255, 255, 255, 235), outline=colour, width=2)
        self.d.text((x, y), s, fill=colour, font=f, anchor=anchor)

    def save(self, path):
        self.im.save(path, "PNG", optimize=True)


class _SvgCanvas:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    @staticmethod
    def _esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _col(c):
        if isinstance(c, tuple):
            r, g, b, *a = c
            return f"rgb({r},{g},{b})", (a[0] / 255 if a else 1)
        return c, 1

    def poly(self, pts, fill):
        c, op = self._col(fill)
        self.parts.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{c}" fill-opacity="{op:.2f}"/>')

    def line(self, pts, colour, width=2, dash=False):
        c, _ = self._col(colour)
        d = ' stroke-dasharray="8,8"' if dash else ""
        self.parts.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" '
                          f'stroke="{c}" stroke-width="{width}"{d}/>')

    def circle(self, x, y, r, fill, outline="white"):
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{outline}" stroke-width="2"/>')

    def text(self, x, y, s, size=16, colour="#222222", anchor="la", bold=False, box=False):
        ta = {"l": "start", "m": "middle", "r": "end"}[anchor[0]]
        base = {"a": "text-before-edge", "t": "text-before-edge", "m": "central", "s": "alphabetic",
                "b": "text-after-edge", "d": "text-after-edge"}.get(anchor[1], "alphabetic")
        w = "bold" if bold else "normal"
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{size}" '
                          f'font-weight="{w}" fill="{colour}" text-anchor="{ta}" dominant-baseline="{base}">{self._esc(s)}</text>')

    def save(self, path):
        Path(path).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                              f'viewBox="0 0 {self.w} {self.h}"><rect width="100%" height="100%" fill="white"/>'
                              + "".join(self.parts) + "</svg>", encoding="utf-8")


def chart(path, choice: str, out: str) -> str:
    """Draw the payoff chart for one choice. Returns the file written (.png, or .svg without Pillow)."""
    ch = parse_chapter(path)
    case, meta = ch["case"], ch["meta"]
    pos = case["positions"][choice]
    legs = legs_from(pos["legs"])
    unit = case.get("unit", "units")
    one = unit.rstrip("s")
    cfg = case.get("chart", {})
    xmin, xmax = float(cfg.get("min", 0)), float(cfg.get("max", 20))
    W, H = 1400, 880
    L, R, T, B = 130, 60, 190, 170
    try:
        cv = _PilCanvas(W, H)
    except ImportError:
        cv = _SvgCanvas(W, H)
        out = str(Path(out).with_suffix(".svg"))
    xs = sorted({xmin, xmax, *[k for k in _kinks(legs) if xmin < k < xmax]})
    ys = [result_at(legs, x) for x in xs] if legs else [0.0, 0.0]
    if not legs:
        xs = [xmin, xmax]
    ylo, yhi = min(min(ys), 0), max(max(ys), 0)
    pad = max((yhi - ylo) * 0.12, 5)
    ylo, yhi = ylo - pad, yhi + pad
    px = lambda x: L + (x - xmin) / (xmax - xmin) * (W - L - R)
    py = lambda y: T + (yhi - y) / (yhi - ylo) * (H - T - B)
    GAIN, LOSS, INK, GRID = (46, 125, 50), (198, 40, 40), "#1b1b1b", "#e3e3e3"
    # title
    cv.text(L, 30, f"Chapter {meta['chapter']}: {meta['title']}", size=34, bold=True, colour=INK)
    cv.text(L, 80, f"Choice {choice}, {pos['label']}: your result on the end date, for each possible price",
            size=21, colour="#444444")
    # grid + y ticks
    ys_step = _nice_step(yhi - ylo)
    v = math.ceil(ylo / ys_step) * ys_step
    while v <= yhi:
        cv.line([(L, py(v)), (W - R, py(v))], GRID, 1)
        cv.text(L - 14, py(v), fmt_gbp(v), size=18, anchor="rm", colour="#555555")
        v += ys_step
    xs_step = _nice_step(xmax - xmin, 10)
    v = math.ceil(xmin / xs_step) * xs_step
    while v <= xmax + EPS:
        cv.line([(px(v), T), (px(v), H - B)], GRID, 1)
        cv.text(px(v), H - B + 14, fmt_gbp(v), size=18, anchor="ma", colour="#555555")
        v += xs_step
    # shaded gain/loss areas, split at zero crossings
    zero = py(0)
    fine = []
    for a, b in zip(xs, xs[1:]):
        fine.append(a)
        fa, fb = result_at(legs, a), result_at(legs, b)
        if fa * fb < 0:
            fine.append(a + (b - a) * (-fa) / (fb - fa))
    fine.append(xs[-1])
    for a, b in zip(fine, fine[1:]):
        fa, fb = result_at(legs, a), result_at(legs, b)
        mid = result_at(legs, (a + b) / 2)
        col = GAIN + (45,) if mid > 0 else LOSS + (45,)
        if abs(mid) > EPS:
            cv.poly([(px(a), zero), (px(a), py(fa)), (px(b), py(fb)), (px(b), zero)], col)
    # axes
    cv.line([(L, zero), (W - R, zero)], "#333333", 2)
    cv.line([(L, T), (L, H - B)], "#333333", 2)
    cv.text(L + 10, zero - 8, "£0: no gain, no loss", size=16, anchor="ld", colour="#333333")
    # other choices for comparison (thinner, dashed, labelled at the right edge)
    for j, cid in enumerate(cfg.get("compare", [])):
        cl = legs_from(case["positions"][cid]["legs"])
        cxs = sorted({xmin, xmax, *[k for k in _kinks(cl) if xmin < k < xmax]})
        pts = [(px(x), py(result_at(cl, x))) for x in cxs]
        for a, b in zip(pts, pts[1:]):
            cv.line([a, b], "#e65100", 4, dash=True)
        lx = L + 600 + 420 * j
        cv.line([(lx, 128), (lx + 50, 128)], "#e65100", 4, dash=True)
        cv.text(lx + 60, 128, f"{cid}: {case['positions'][cid]['label']}", size=18, colour="#e65100", anchor="lm", bold=True)
    # payoff line
    cv.line([(px(x), py(y)) for x, y in zip(fine, [result_at(legs, x) for x in fine])], "#0d47a1", 6)
    if cfg.get("compare"):
        cv.line([(L, 128), (L + 50, 128)], "#0d47a1", 6)
        cv.text(L + 60, 128, f"{choice}: {pos['label']} (your choice)", size=18, colour="#0d47a1", anchor="lm", bold=True)
    # area labels (text, so colour isn't the only signal)
    if legs:
        top = max(ys)
        bot = min(ys)
        if top > 0:
            cv.text(W - R - 14, (py(top) + zero) / 2, "GAIN", size=20, bold=True, colour="#2e7d32", anchor="rm")
        if bot < 0:
            xb = min((x for x in xs if result_at(legs, x) == bot), default=xmin)
            cv.text(px(xb) + 16, (py(bot) + zero) / 2 + 40, "LOSS", size=20, bold=True, colour="#c62828", anchor="lm")
    # markers: agreed prices, breakevens, outcome
    for l in legs:
        if l.kind != "goods" and xmin < l.strike < xmax:
            cv.line([(px(l.strike), T), (px(l.strike), H - B)], "#6a6a6a", 2, dash=True)
            cv.text(px(l.strike) + 6, H - B - 8, f"agreed price {fmt_gbp(l.strike)}", size=17, colour="#555555", anchor="ld")
    for be in breakevens(legs):
        if xmin <= be <= xmax:
            cv.circle(px(be), zero, 9, "#f9a825", "#1b1b1b")
            cv.text(px(be), zero + 22, f"breakeven {fmt_gbp(be)}", size=18, anchor="ma", bold=True, colour="#1b1b1b", box=True)
    S = case.get("outcome_price")
    for p in case.get("what_if_prices", []):
        if xmin <= p <= xmax and p != S and legs:
            y = result_at(legs, p)
            cv.circle(px(p), py(y), 8, "#757575")
            cv.text(px(p) + 12, py(y) + 12, f"if {fmt_gbp(p)}: {fmt_gbp(y, sign=True)}", size=17, colour="#424242", anchor="la", box=True)
    if S is not None and xmin <= S <= xmax:
        y = result_at(legs, S) if legs else 0
        cv.circle(px(S), py(y), 12, "#0d47a1")
        cv.text(px(S), py(y) - 22, f"what happened: {fmt_gbp(S)} \u2192 {fmt_gbp(y, sign=True)}", size=20,
                bold=True, colour="#0d47a1", anchor="md", box=True)
    # axis titles + footer
    cv.text((L + W - R) / 2, H - B + 50, f"Price per {one} on the end date (fictional £)", size=22, anchor="ma", colour=INK, bold=True)
    cv.text(20, T - 22, "Your result", size=20, anchor="ld", colour=INK, bold=True)
    g, lo = max_gain_loss(legs)
    summary = (f"Most you could make: {'no limit' if g is None else fmt_gbp(g)}   \u00b7   "
               f"Most you could lose: {'no limit' if lo is None else fmt_gbp(lo)}") if legs else "No promise made: nothing to gain or lose."
    cv.text(L, H - 62, summary, size=20, colour=INK)
    cv.text(L, H - 32, "Paper money only. Fictional pounds, not market prices. Before any costs. Not financial advice.",
            size=17, colour="#666666")
    cv.save(out)
    return out

# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Case maths for the Tidewick bot (paper money, fictional £).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("price")
    p.add_argument("--kind", choices=["call", "put"], required=True)
    p.add_argument("--spot", type=float, required=True)
    p.add_argument("--strike", type=float, required=True)
    p.add_argument("--days", type=float, required=True)
    p.add_argument("--vol", type=float, required=True, help="annual volatility, 0.40 = 40%%")
    p.add_argument("--rate", type=float, default=0.0)
    p.add_argument("--units", type=float, default=1)
    q = sub.add_parser("payoff")
    q.add_argument("--legs", required=True)
    q.add_argument("--at", type=float, action="append", default=[])
    c = sub.add_parser("check")
    c.add_argument("chapters", nargs="+")
    r = sub.add_parser("receipt")
    r.add_argument("chapter")
    r.add_argument("--choice", required=True)
    h = sub.add_parser("chart")
    h.add_argument("chapter")
    h.add_argument("--choice", required=True)
    h.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "price":
        T = a.days / 365.0
        pr = bs_price(a.kind, a.spot, a.strike, T, a.rate, a.vol)
        print(json.dumps({"per_unit": round(pr, 4), "per_unit_gbp": fmt_gbp(pr), "total_gbp": fmt_gbp(pr * a.units),
                          "delta": round(bs_delta(a.kind, a.spot, a.strike, T, a.rate, a.vol), 4),
                          "vega_per_vol_point": round(bs_vega(a.spot, a.strike, T, a.rate, a.vol), 4),
                          "note": "Model price from stated inputs. Not a market quote; delta is not an exact probability."},
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "payoff":
        legs = legs_from(json.loads(a.legs))
        g, lo = max_gain_loss(legs)
        print(json.dumps({"fee_net": fee_net(legs), "reserve": reserve(legs), "breakevens": breakevens(legs),
                          "max_gain": "unlimited" if g is None else g, "max_loss": "unlimited" if lo is None else lo,
                          "result_at": {str(x): result_at(legs, x) for x in a.at}}, indent=1))
        return 0
    if a.cmd == "check":
        bad = 0
        for path in a.chapters:
            res = check_chapter(path)
            n_bad = sum(1 for ok, _ in res if not ok)
            bad += n_bad
            print(f"{path}: {len(res) - n_bad}/{len(res)} checks pass")
            for ok, line in res:
                print(("  PASS  " if ok else "  FAIL  ") + line)
        return 1 if bad else 0
    if a.cmd == "receipt":
        print(receipt(a.chapter, a.choice))
        return 0
    if a.cmd == "chart":
        print(chart(a.chapter, a.choice, a.out))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
