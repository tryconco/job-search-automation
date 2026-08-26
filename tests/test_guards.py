"""Every guard fires correctly at its boundary, on both sides. BUILD_PROMPT Part 10."""

from datetime import datetime

import pytest

from tools import guards as g
from tools.guards import ET, Event, GuardContext

CFG = g.load_config()


def et(h, m, day=24):
    """A weekday (Mon 2026-08-24) at the given ET time."""
    return datetime(2026, 8, day, h, m, tzinfo=ET)


# ---------------------------------------------------------------- 1. time cutoff

@pytest.mark.parametrize("h,m,expected", [
    (14, 59, True),
    (15, 0, False),   # boundary: cutoff is inclusive
    (15, 29, False),
    (15, 30, False),  # hard flat
])
def test_guard_time_cutoff_boundaries(h, m, expected):
    passed, reason = g.guard_time_cutoff(et(h, m))
    assert passed is expected
    if not passed:
        assert "GUARD 1" in reason


def test_time_cutoff_distinguishes_flat_from_no_entry():
    _, cutoff_reason = g.guard_time_cutoff(et(15, 10))
    _, flat_reason = g.guard_time_cutoff(et(15, 40))
    assert "no new" in cutoff_reason.lower()
    assert "flat" in flat_reason.lower()


def test_time_cutoff_vetoes_a_perfect_setup_past_three():
    """BUILD_PROMPT Part 10: being past 15:00 ET vetoes a textbook-perfect A setup."""
    ctx = GuardContext(
        now=et(15, 5), ema9=770.0, ema21=768.0, ema50=765.0, atr=0.50,
        mean_bar_range=0.40, stop_distance=0.80, bid=0.95, ask=1.00,
    )
    failed = g.vetoes(g.run_all(ctx, CFG))
    assert [r.number for r in failed] == [1], "only the clock should stop this one"


# ---------------------------------------------------------------- 2. opening lockout

@pytest.mark.parametrize("h,m,expected", [
    (9, 29, False),   # premarket
    (9, 30, False),   # open, still locked
    (9, 44, False),
    (9, 45, True),    # boundary: lockout clears
])
def test_guard_opening_lockout_boundaries(h, m, expected):
    passed, reason = g.guard_opening_lockout(et(h, m), 15)
    assert passed is expected
    if not passed:
        assert "GUARD 2" in reason


def test_opening_lockout_names_premarket_specifically():
    _, reason = g.guard_opening_lockout(et(8, 0))
    assert "premarket" in reason.lower()


# ---------------------------------------------------------------- 3. event lockout

def test_event_lockout_boundaries():
    cpi = Event("CPI", et(10, 0))
    assert g.guard_event_lockout(et(9, 44), [cpi])[0] is True   # 16 min before: clear
    assert g.guard_event_lockout(et(9, 45), [cpi])[0] is False  # 15 min before: locked
    assert g.guard_event_lockout(et(10, 10), [cpi])[0] is False  # 10 min after: locked
    assert g.guard_event_lockout(et(10, 11), [cpi])[0] is True   # 11 min after: clear


def test_event_lockout_names_the_event_and_the_distance():
    _, reason = g.guard_event_lockout(et(9, 52), [Event("CPI", et(10, 0))])
    assert "CPI" in reason and "8 min before" in reason


def test_event_lockout_passes_with_no_events():
    assert g.guard_event_lockout(et(11, 0), [])[0] is True


# ---------------------------------------------------------------- 4. daily loss limit

@pytest.mark.parametrize("pnl,expected", [
    (-1.99, True),
    (-2.0, False),   # boundary: at the limit, closed
    (-2.01, False),
    (1.0, True),
])
def test_guard_daily_loss_limit_boundaries(pnl, expected):
    passed, reason = g.guard_daily_loss_limit(pnl, -2.0)
    assert passed is expected
    if not passed:
        assert "GUARD 4" in reason and "does not get overridden" in reason


# ---------------------------------------------------------------- 5. max trades

@pytest.mark.parametrize("taken,expected", [(2, True), (3, False), (4, False)])
def test_guard_max_trades_boundaries(taken, expected):
    assert g.guard_max_trades(taken, 3)[0] is expected


def test_confirmed_daily_limits_come_from_config():
    """CJ confirmed 2026-08-26: 5 trades a day, desk closes at -4R."""
    assert CFG["risk"]["max_trades_per_day"] == 5
    assert CFG["risk"]["daily_loss_limit_r"] == -4.0
    assert g.guard_max_trades(4, CFG["risk"]["max_trades_per_day"])[0] is True
    assert g.guard_max_trades(5, CFG["risk"]["max_trades_per_day"])[0] is False
    assert g.guard_daily_loss_limit(-3.9, CFG["risk"]["daily_loss_limit_r"])[0] is True
    assert g.guard_daily_loss_limit(-4.0, CFG["risk"]["daily_loss_limit_r"])[0] is False


# ---------------------------------------------------------------- 6. cooldown

@pytest.mark.parametrize("since,expected", [
    (None, True),   # no loss today
    (14.0, False),
    (15.0, True),   # boundary: cooldown served
    (16.0, True),
])
def test_guard_cooldown_boundaries(since, expected):
    assert g.guard_cooldown(since, 15)[0] is expected


# ---------------------------------------------------------------- 7. minimum stop

@pytest.mark.parametrize("stop,expected", [
    (0.59, False),
    (0.60, True),   # boundary: exactly 1.5 x 0.40
    (0.61, True),
])
def test_guard_min_stop_boundaries(stop, expected):
    assert g.guard_min_stop_distance(stop, 0.40, 1.5)[0] is expected


def test_min_stop_vetoes_when_data_is_missing():
    assert g.guard_min_stop_distance(0.8, float("nan"), 1.5)[0] is False
    assert g.guard_min_stop_distance(float("nan"), 0.4, 1.5)[0] is False
    assert g.guard_min_stop_distance(0.0, 0.4, 1.5)[0] is False


# ---------------------------------------------------------------- 8. liquidity

def test_guard_liquidity_boundaries():
    # mid 1.00, 10% limit -> a 0.10 spread is exactly at the line
    assert g.guard_liquidity(0.95, 1.05, 0.10)[0] is True
    assert g.guard_liquidity(0.94, 1.06, 0.10)[0] is False


def test_liquidity_vetoes_missing_or_crossed_quotes():
    assert g.guard_liquidity(0, 0, 0.10)[0] is False
    assert g.guard_liquidity(1.10, 1.00, 0.10)[0] is False


# ---------------------------------------------------------------- 9. chop

def test_guard_chop_boundaries():
    # ATR 0.40, fraction 0.25 -> threshold 0.10
    assert g.guard_chop(100.00, 100.04, 100.09, 0.40, 0.25)[0] is False  # spread 0.09
    assert g.guard_chop(100.00, 100.05, 100.10, 0.40, 0.25)[0] is True   # spread 0.10


def test_chop_veto_names_every_ma_value():
    _, reason = g.guard_chop(766.21, 766.18, 766.30, 0.60, 0.25)
    assert "GUARD 9" in reason
    for value in ("766.21", "766.18", "766.30"):
        assert value in reason
    assert "chop, not a trend" in reason


def test_chop_vetoes_when_atr_is_unavailable():
    assert g.guard_chop(1.0, 2.0, 3.0, float("nan"), 0.25)[0] is False


# ---------------------------------------------------------------- runner

def _clean_ctx(**over):
    base = dict(
        now=et(10, 30), ema9=770.0, ema21=768.0, ema50=765.0, atr=0.50,
        mean_bar_range=0.40, stop_distance=0.80, bid=0.95, ask=1.00,
        day_pnl_r=0.0, trades_today=0, minutes_since_last_loss=None, events=(),
    )
    base.update(over)
    return GuardContext(**base)


def test_run_all_clean_context_passes_everything():
    results = g.run_all(_clean_ctx(), CFG)
    assert len(results) == 9
    assert g.vetoes(results) == []
    assert g.summarise(results) == "All nine guards clear."


def test_run_all_does_not_short_circuit():
    """CJ sees everything that would have stopped the trade, not just the first thing."""
    ctx = _clean_ctx(now=et(15, 30), day_pnl_r=-5.0, trades_today=9)
    failed = g.vetoes(g.run_all(ctx, CFG))
    assert {r.number for r in failed} >= {1, 4, 5}


def test_summarise_lists_each_veto_on_its_own_line():
    ctx = _clean_ctx(day_pnl_r=-5.0, trades_today=9)
    text = g.summarise(g.run_all(ctx, CFG))
    assert text.count("\n") == 1
    assert "GUARD 4" in text and "GUARD 5" in text


def test_guard_numbers_and_names_are_stable():
    names = [(r.number, r.name) for r in g.run_all(_clean_ctx(), CFG)]
    assert names == [
        (1, "time cutoff"), (2, "opening lockout"), (3, "event lockout"),
        (4, "daily loss limit"), (5, "max trades"), (6, "cooldown"),
        (7, "minimum stop"), (8, "liquidity"), (9, "chop"),
    ]


def test_every_veto_reason_names_its_guard():
    """When a guard vetoes, the response names the guard. BUILD_PROMPT Part 7."""
    ctx = _clean_ctx(
        now=et(9, 31), day_pnl_r=-5.0, trades_today=9, minutes_since_last_loss=1.0,
        stop_distance=0.01, bid=0.5, ask=1.5, ema9=100.0, ema21=100.0, ema50=100.0,
        events=[Event("CPI", et(9, 35))],
    )
    for r in g.vetoes(g.run_all(ctx, CFG)):
        assert f"GUARD {r.number}" in r.reason


def test_guards_are_pure_no_wall_clock():
    """The same context gives the same answer forever. A guard that reads the clock is unprovable."""
    ctx = _clean_ctx()
    assert [r.passed for r in g.run_all(ctx, CFG)] == [r.passed for r in g.run_all(ctx, CFG)]
