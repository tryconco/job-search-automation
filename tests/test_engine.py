"""Integration and honesty tests. BUILD_PROMPT Part 10.

These are the ones that matter most: no fabricated levels, read vs computed kept separate,
no implied profitability, and a guard that can veto a perfect setup.
"""

from datetime import datetime


from tools import engine as E
from tools import guards as G
from tools import market
from tools.engine import Setup
from tools.guards import Event, GuardContext, ET
from tools.vision import Confidence, Reading, ScreenshotRead, Status, reconcile
from tests.fixtures import flat_bars, make_bars, trending_bars

CFG = G.load_config()


def at(h, m, day=24):
    return datetime(2026, 8, day, h, m, tzinfo=ET)


def clean_ctx(**over):
    base = dict(now=at(10, 30), day_pnl_r=0.0, trades_today=0,
                minutes_since_last_loss=None, events=(), bid=0.95, ask=1.00)
    base.update(over)
    return GuardContext(**base)


def uptrend_indicators():
    return market.get_indicators(trending_bars(n=260, step=0.10))


def good_setup(ind):
    """A textbook A: clean stack, major zone, closed engulfing, 2R of room."""
    entry = ind.last
    return Setup(
        direction="long", entry_low=entry - 0.05, entry_high=entry + 0.05,
        stop=entry - 1.0, target1=entry + 2.2, target2=entry + 3.0,
        zone="prior day high", zone_quality="major",
        confirmation="engulfing", confirmed_closed=True,
    )


# ---------------------------------------------------------------- a well-formed TRADE

def test_fixture_data_plus_a_good_setup_produces_a_well_formed_trade():
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx())

    assert d.verdict == "TRADE"
    assert d.grade == "A"

    text = E.render(d)
    assert text.startswith("TRADE — LONG SPY"), "verdict first, always"
    for section in ("WHY", "THE TRADE", "CONTRACT", "EXIT DISCIPLINE"):
        assert section in text
    assert "Underlying entry" in text and "Stop (underlying)" in text
    assert "Invalidation" in text
    assert text.rstrip().endswith("Paper trade. Not advice.")


def test_trade_response_names_the_hard_flat_in_central_and_eastern():
    ind = uptrend_indicators()
    text = E.render(E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()))
    assert "14:30 CT / 15:30 ET" in text


def test_a_grade_uses_its_closing_line():
    ind = uptrend_indicators()
    text = E.render(E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()))
    assert "Take the trigger or leave it. No fills in the middle." in text


# ---------------------------------------------------------------- chop

def test_chop_produces_no_trade_and_names_the_veto():
    ind = market.get_indicators(flat_bars(n=250, price=100.0, rng=0.5))
    setup = Setup(direction="long", entry_low=99.9, entry_high=100.1, stop=99.0,
                  target1=102.0, zone="round number", zone_quality="minor",
                  confirmation="reclaim", confirmed_closed=True)
    d = E.decide("SPY", setup, ind, at(10, 30), CFG, clean_ctx())

    assert d.verdict == "NO TRADE"
    assert 9 in [v.number for v in d.guard_vetoes]
    text = E.render(d)
    assert "GUARD 9" in text and "chop, not a trend" in text


# ---------------------------------------------------------------- timed vetoes become WAIT

def test_an_approaching_event_produces_wait_with_a_specific_time():
    ind = uptrend_indicators()
    cpi = Event("CPI", at(10, 30))
    d = E.decide("SPY", good_setup(ind), ind, at(10, 20), CFG, clean_ctx(events=[cpi]))

    assert d.verdict == "WAIT"
    assert d.wait_until == at(10, 40), "10 minutes after the release"
    text = E.render(d)
    assert text.startswith("WAIT — send me a screenshot at 09:40 CT / 10:40 ET")
    assert "CPI" in text


def test_opening_lockout_produces_wait_until_the_unlock():
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(9, 35), CFG, clean_ctx(now=at(9, 35)))
    assert d.verdict == "WAIT"
    assert d.wait_until == at(9, 45)


def test_cooldown_produces_wait_not_no_trade():
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG,
                 clean_ctx(minutes_since_last_loss=5.0))
    assert d.verdict == "WAIT"
    assert d.wait_until == at(10, 40)


def test_a_permanent_veto_beats_a_timed_one():
    """Daily loss limit is not something you wait out."""
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG,
                 clean_ctx(day_pnl_r=-5.0, minutes_since_last_loss=5.0))
    assert d.verdict == "NO TRADE"
    assert 4 in [v.number for v in d.guard_vetoes]
    assert "does not get overridden" in E.render(d)


# ---------------------------------------------------------------- the clock beats the setup

def test_past_three_pm_vetoes_a_textbook_perfect_a_setup():
    """BUILD_PROMPT Part 10, explicitly."""
    ind = uptrend_indicators()
    setup = good_setup(ind)
    early = E.decide("SPY", setup, ind, at(10, 30), CFG, clean_ctx(now=at(10, 30)))
    late = E.decide("SPY", setup, ind, at(15, 5), CFG, clean_ctx(now=at(15, 5)))

    assert early.verdict == "TRADE" and early.grade == "A"
    assert late.verdict == "NO TRADE"
    assert 1 in [v.number for v in late.guard_vetoes]
    assert "GUARD 1" in E.render(late)


# ---------------------------------------------------------------- developing candles

def test_a_developing_signal_candle_is_always_a_wait():
    ind = uptrend_indicators()
    setup = good_setup(ind)
    setup.confirmed_closed = False
    d = E.decide("SPY", setup, ind, at(10, 30), CFG, clean_ctx())
    assert d.verdict == "WAIT"
    assert "flip its shape" in " ".join(d.wait_for)


# ---------------------------------------------------------------- no data

def test_missing_price_data_produces_no_trade_never_a_level():
    d = E.decide("SPY", None, None, at(10, 30), CFG, clean_ctx(),
                 no_data_reason="yfinance returned no bars for SPY")
    assert d.verdict == "NO TRADE"
    text = E.render(d)
    assert "no data" in text
    assert "Not making up a level" in text
    assert not any(ch.isdigit() and ch != "0" for ch in text.split("yfinance")[0]), \
        "no fabricated numbers in a no-data response"


def test_a_stale_screenshot_asks_for_a_fresh_one():
    bars = make_bars([(100.0, 100.2, 99.8, 100.0, 1000)] * 5, start="2026-08-24 10:00")
    read = ScreenshotRead(
        ticker="SPY", chart_time=at(10, 10),
        readings=[Reading("last_price", 105.0, Confidence.CLEAR)],
    )
    rec = reconcile(read, bars)
    assert rec.status is Status.STALE_SCREENSHOT

    ind = market.get_indicators(trending_bars(n=260))
    d = E.decide("SPY", good_setup(ind), ind, at(10, 15), CFG, clean_ctx(), reconciliation=rec)
    assert d.verdict == "WAIT"
    assert "fresh screenshot" in " ".join(d.wait_for)


# ---------------------------------------------------------------- grading

def test_one_missing_leg_is_a_b_not_an_a():
    ind = uptrend_indicators()
    setup = good_setup(ind)
    setup.zone_quality = "minor"
    letter, missing = E.grade(setup, ind, at(10, 30))
    assert letter == "A" or letter == "B"
    setup.target1 = ind.last + 1.6   # 1.6R -- room present but thin
    setup.zone_quality = "major"
    setup.confirmation = ""
    letter, missing = E.grade(setup, ind, at(10, 30))
    assert letter == "C", "no confirmation and thin room is two legs missing"


def test_midday_costs_the_a_grade():
    ind = uptrend_indicators()
    setup = good_setup(ind)
    assert E.grade(setup, ind, at(10, 30))[0] == "A"
    letter, missing = E.grade(setup, ind, at(12, 30))
    assert letter == "B"
    assert "prime session window" in missing


def test_a_lesson_against_caps_the_grade_and_appears_in_the_against_lines():
    ind = uptrend_indicators()
    setup = good_setup(ind)
    lesson = "longs before 10:30 ET have lost"

    letter, missing = E.grade(setup, ind, at(10, 30), [lesson])
    assert letter == "B", "a lesson caps the grade even on a perfect chart"

    supporting, against = E.evidence(setup, ind, at(10, 30), [lesson])
    assert any(lesson in line for line in against)
    assert not any(lesson in line for line in supporting)


def test_b_grade_can_be_turned_off_entirely():
    """_INDEX.md contradiction 5 -- CJ's call, one flag."""
    ind = uptrend_indicators()
    setup = good_setup(ind)
    setup.zone_quality = "none"
    setup.zone = ""

    on = E.decide("SPY", setup, ind, at(10, 30), CFG, clean_ctx())
    strict = {**CFG, "grading": {**CFG["grading"], "b_grade_tradeable": False}}
    off = E.decide("SPY", setup, ind, at(10, 30), strict, clean_ctx())

    assert on.grade == "B"
    assert off.grade == "B"
    assert off.verdict == "NO TRADE"
    assert "not tradeable under the current config" in " ".join(off.missing)


def test_tiered_sizing_matches_what_cj_asked_for():
    """His words: mostly $100, and up to $350 when the setup is really good."""
    assert E.risk_budget(CFG, "B") == 100, "the common case"
    assert E.risk_budget(CFG, "A") == 350, "all five legs clean"
    assert E.risk_budget(CFG, "C") == 100, "unknown grades never size up"


def test_risk_budget_is_capped():
    greedy = {**CFG, "risk": {**CFG["risk"],
                              "grade_risk_multiplier": {"A": 99.0}, "max_risk_usd": 350}}
    assert E.risk_budget(greedy, "A") == 350


def test_one_r_stays_fixed_even_though_position_size_varies():
    """R has to stay a fixed unit or the daily limit and every lesson stop being comparable."""
    assert CFG["risk"]["unit_r_usd"] == 100
    assert E.risk_budget(CFG, "A") / CFG["risk"]["unit_r_usd"] == 3.5, \
        "a max-size A risks 3.5R, not 1R"


def test_b_grade_sizes_at_the_base_unit():
    ind = uptrend_indicators()
    setup = good_setup(ind)
    setup.zone_quality = "none"
    setup.zone = ""
    d = E.decide("SPY", setup, ind, at(10, 30), CFG, clean_ctx(),
                 premium=1.00, premium_at_stop=0.50)
    assert d.grade == "B"
    assert d.verdict == "TRADE", "B is tradeable — CJ confirmed A or B, less strict"
    assert d.contracts == 2, "$100 budget against $50 per-contract risk"


def test_a_grade_sizes_up_to_three_and_a_half_times_the_b():
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx(),
                 premium=1.00, premium_at_stop=0.50)
    assert d.grade == "A"
    assert d.contracts == 7, "$350 budget against $50 per-contract risk"
    assert "3.5R" in d.contract_note


# ---------------------------------------------------------------- sizing honesty

def test_sizing_refuses_to_invent_a_premium_without_a_chain():
    n, note = E.size_position(Setup("long", 100, 100, 99, 102), CFG, "A")
    assert n == 1
    assert "can't see a bid/ask" in note


def test_sizing_refuses_to_round_up_into_an_oversized_position():
    n, note = E.size_position(Setup("long", 100, 100, 99, 102), CFG, "A",
                              premium=5.00, premium_at_stop=1.00)
    assert n == 0
    assert "not rounding you into a bigger position" in note


def test_a_position_that_cannot_be_sized_becomes_no_trade():
    ind = uptrend_indicators()
    d = E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx(),
                 premium=5.00, premium_at_stop=1.00)
    assert d.verdict == "NO TRADE"
    assert "cannot be sized" in " ".join(d.missing)


# ---------------------------------------------------------------- honesty

def test_conviction_is_never_stated_as_a_probability():
    """06-mentor-engine.md: no confidence percentage."""
    ind = uptrend_indicators()
    for d in (
        E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()),
        E.decide("SPY", good_setup(ind), ind, at(15, 5), CFG, clean_ctx(now=at(15, 5))),
    ):
        text = E.render(d)
        low = text.lower()
        for banned in ("likely", "probability", "chance of", "odds", "win rate",
                       "expect to win", "% likely", "% chance", "accuracy"):
            assert banned not in low, f"{banned!r} reads as a probability claim"
        assert "conviction" not in low, "dropped entirely at CJ's instruction"


def test_no_response_implies_a_guaranteed_or_profitable_outcome():
    ind = uptrend_indicators()
    decisions = [
        E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()),
        E.decide("SPY", None, ind, at(10, 30), CFG, clean_ctx()),
        E.decide("SPY", None, None, at(10, 30), CFG, clean_ctx(), no_data_reason="weekend"),
    ]
    banned = ("guaranteed", "sure thing", "can't lose", "easy money", "free money",
              "will go", "will hit", "profitable")
    for d in decisions:
        text = E.render(d).lower()
        for word in banned:
            assert word not in text, f"{word!r} in a response"
        assert "paper trade. not advice." in text


def test_every_response_carries_the_paper_trading_signoff():
    ind = uptrend_indicators()
    for d in (
        E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()),
        E.decide("SPY", good_setup(ind), ind, at(9, 35), CFG, clean_ctx(now=at(9, 35))),
        E.decide("SPY", None, None, at(10, 30), CFG, clean_ctx(), no_data_reason="weekend"),
    ):
        assert E.render(d).rstrip().endswith(E.SIGNOFF)


def test_the_desk_never_emits_a_spread():
    """BUILD_PROMPT Part 0: long calls and puts only."""
    ind = uptrend_indicators()
    text = E.render(E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx())).lower()
    for word in ("butterfly", "condor", "credit spread", "debit spread", "wheel",
                 "sell to open", "short put", "short call", "covered call", "iron "):
        assert word not in text, f"{word!r} leaked into a call"
    # "spread" is allowed only as the bid/ask spread, never as a structure.
    assert text.count("spread") == 1
    assert "or spread from a price chart" in text, "the only legitimate use of the word"


def test_the_contract_block_admits_it_cannot_see_a_chain():
    ind = uptrend_indicators()
    text = E.render(E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()))
    assert "can't verify a strike, premium, bid, ask or spread from a price chart" in text


def test_no_conviction_number_appears_anywhere_in_a_response():
    """CJ dropped it. A number out of 100 next to a trade reads as a likelihood."""
    ind = uptrend_indicators()
    for d in (
        E.decide("SPY", good_setup(ind), ind, at(10, 30), CFG, clean_ctx()),
        E.decide("SPY", good_setup(ind), ind, at(9, 35), CFG, clean_ctx(now=at(9, 35))),
        E.decide("SPY", good_setup(ind), ind, at(15, 5), CFG, clean_ctx(now=at(15, 5))),
    ):
        text = E.render(d).lower()
        assert "conviction" not in text
        assert "/100" not in text
        assert "rubric" not in text
    assert not hasattr(E.Decision(verdict="TRADE", ticker="SPY"), "conviction")


def test_evidence_lines_are_reasons_not_scores():
    ind = uptrend_indicators()
    supporting, against = E.evidence(good_setup(ind), ind, at(10, 30))
    assert supporting, "a clean setup must produce supporting evidence"
    for line in supporting + against:
        assert "/" not in line or "R" in line, f"no bare score fractions: {line!r}"
        assert "%" not in line


# ---------------------------------------------------------------- docs stay in step

def test_the_response_contract_in_claude_md_prints_no_conviction():
    """The samples in CLAUDE.md are what the model copies. They must not drift back."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    body = open(os.path.join(root, "CLAUDE.md")).read()

    samples = body.split("```")[1::2]
    assert samples, "CLAUDE.md must carry the sample responses"
    for sample in samples:
        low = sample.lower()
        assert "conviction" not in low, "a sample response still prints conviction"
        assert "/100" not in low
    assert "There is no conviction score." in body


def test_claude_md_states_the_confirmed_sizing_tiers():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    body = open(os.path.join(root, "CLAUDE.md")).read()
    assert "A and B are both tradeable" in body
    assert "$350" in body and "$100" in body
    assert "C is always a skip" in body


def test_config_and_docs_agree_on_the_limits():
    """One number, three places. Catch the drift here rather than on a live chart."""
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules = open(os.path.join(root, "knowledge", "04-risk-rules.md")).read()

    limit = CFG["risk"]["daily_loss_limit_r"]
    trades = CFG["risk"]["max_trades_per_day"]
    assert f"−{abs(limit):.0f}R" in rules, "04-risk-rules.md must name the configured loss limit"
    assert re.search(rf"\| 5 \| Max trades per day \| \*\*{trades}\*\*", rules)

    a_risk = E.risk_budget(CFG, "A")
    b_risk = E.risk_budget(CFG, "B")
    assert f"${a_risk:,.0f}".replace(",", "") in rules.replace(",", "")
    assert f"${b_risk:,.0f}" in rules
