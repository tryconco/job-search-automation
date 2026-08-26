"""Indicators must match hand-computed values. BUILD_PROMPT Part 10."""

import math

import pandas as pd
import pytest

from tools import market as m
from tests.fixtures import make_bars, flat_bars, trending_bars


# ---------------------------------------------------------------- EMA

def test_ema_matches_hand_computation():
    """alpha = 2/(n+1) = 0.5 for n=3; ema[0] = x[0], then a*x + (1-a)*prev."""
    x = pd.Series([10.0, 12.0, 14.0, 13.0, 11.0])
    got = m.ema(x, 3).tolist()

    a = 0.5
    want = [10.0]
    for v in x[1:]:
        want.append(a * v + (1 - a) * want[-1])

    assert want == pytest.approx([10.0, 11.0, 12.5, 12.75, 11.875])
    assert got == pytest.approx(want)


def test_ema_seeds_on_first_value_not_nan():
    x = pd.Series([5.0, 6.0, 7.0])
    assert m.ema(x, 21).iloc[0] == pytest.approx(5.0)


def test_sma_matches_hand_computation():
    x = pd.Series([1.0, 2.0, 3.0, 4.0])
    got = m.sma(x, 2)
    assert math.isnan(got.iloc[0])
    assert got.iloc[1:].tolist() == pytest.approx([1.5, 2.5, 3.5])


# ---------------------------------------------------------------- ATR

def test_true_range_uses_prior_close():
    df = make_bars([
        (100.0, 101.0, 99.0, 100.5, 1000),   # first bar: high-low = 2.0
        (100.5, 102.0, 100.0, 101.5, 1000),  # max(2.0, |102-100.5|=1.5, |100-100.5|=0.5) = 2.0
        (101.5, 105.0, 101.0, 104.0, 1000),  # max(4.0, |105-101.5|=3.5, |101-101.5|=0.5) = 4.0
    ])
    assert m.true_range(df).tolist() == pytest.approx([2.0, 2.0, 4.0])


def test_atr_sma_is_mean_of_true_range():
    df = make_bars([
        (100.0, 101.0, 99.0, 100.5, 1000),
        (100.5, 102.0, 100.0, 101.5, 1000),
        (101.5, 105.0, 101.0, 104.0, 1000),
    ])
    got = m.atr(df, length=3, method="sma")
    assert got.iloc[-1] == pytest.approx((2.0 + 2.0 + 4.0) / 3)


def test_atr_wilder_matches_recursion():
    df = trending_bars(n=30)
    tr = m.true_range(df)
    alpha = 1 / 14
    want = tr.iloc[0]
    for v in tr.iloc[1:]:
        want = alpha * v + (1 - alpha) * want
    assert m.atr(df, 14, "wilder").iloc[-1] == pytest.approx(float(want))


def test_atr_rejects_unknown_method():
    with pytest.raises(ValueError):
        m.atr(trending_bars(n=5), method="magic")


# ---------------------------------------------------------------- VWAP

def test_vwap_matches_hand_computation():
    df = make_bars([
        (100.0, 102.0, 100.0, 101.0, 100),  # typical = 101
        (101.0, 104.0, 102.0, 103.0, 300),  # typical = 103
    ])
    want_first = 101.0
    want_second = (101 * 100 + 103 * 300) / 400
    got = m.vwap(df)
    assert got.iloc[0] == pytest.approx(want_first)
    assert got.iloc[1] == pytest.approx(want_second)


def test_vwap_resets_each_session_day():
    day1 = make_bars([(100.0, 100.0, 100.0, 100.0, 1000)], start="2026-08-24 09:30")
    day2 = make_bars([(200.0, 200.0, 200.0, 200.0, 1000)], start="2026-08-25 09:30")
    got = m.vwap(pd.concat([day1, day2]))
    assert got.iloc[-1] == pytest.approx(200.0), "day 2 must not inherit day 1 volume"


# ---------------------------------------------------------------- volume / range

def test_volume_ratio_excludes_the_current_bar_from_its_own_baseline():
    rows = [(100.0, 100.5, 99.5, 100.0, 1000.0)] * 20 + [(100.0, 100.5, 99.5, 100.0, 2000.0)]
    assert m.volume_ratio(make_bars(rows), lookback=20) == pytest.approx(2.0)


def test_volume_ratio_is_nan_without_history():
    assert math.isnan(m.volume_ratio(make_bars([(1.0, 1.0, 1.0, 1.0, 1.0)])))


def test_bar_range_stats():
    stats = m.bar_range_stats(flat_bars(n=20, rng=0.5), lookback=20)
    assert stats["mean_range"] == pytest.approx(0.5)
    assert stats["sigma_range"] == pytest.approx(0.0, abs=1e-9)
    assert stats["bars"] == 20


# ---------------------------------------------------------------- indicators bundle

def test_get_indicators_flags_warmup():
    short = m.get_indicators(trending_bars(n=50))
    assert short.warmup_ok is False
    assert math.isnan(short.sma200), "SMA200 on 50 bars is not a level, it is a guess"

    long = m.get_indicators(trending_bars(n=260))
    assert long.warmup_ok is True
    assert not math.isnan(long.sma200)


def test_get_indicators_stack_order_in_an_uptrend():
    ind = m.get_indicators(trending_bars(n=260, step=0.10))
    assert ind.last > ind.ema9 > ind.ema21 > ind.ema50 > ind.ema200
    assert ind.source == "computed", "every indicator must be labelled computed, never read"


def test_get_indicators_raises_on_empty():
    with pytest.raises(m.NoDataError):
        m.get_indicators(pd.DataFrame())


# ---------------------------------------------------------------- levels

def test_opening_range_first_fifteen_minutes():
    rows = [
        (100.0, 101.0, 99.0, 100.0, 1000),   # 09:30 in range
        (100.0, 102.0, 99.5, 101.0, 1000),   # 09:35 in range
        (101.0, 101.5, 100.5, 101.0, 1000),  # 09:40 in range
        (101.0, 110.0, 90.0, 105.0, 1000),   # 09:45 OUTSIDE the range
    ]
    got = m.opening_range(make_bars(rows), minutes=15)
    assert got["or_high"] == pytest.approx(102.0)
    assert got["or_low"] == pytest.approx(99.0)
    assert got["complete"] is True


def test_opening_range_incomplete_is_flagged():
    rows = [(100.0, 101.0, 99.0, 100.0, 1000), (100.0, 102.0, 99.5, 101.0, 1000)]
    got = m.opening_range(make_bars(rows), minutes=15)
    assert got["complete"] is False, "a range still printing is not a level"


def test_regular_session_excludes_premarket():
    pre = make_bars([(90.0, 95.0, 85.0, 90.0, 10)], start="2026-08-24 08:00")
    reg = make_bars([(100.0, 101.0, 99.0, 100.0, 1000)], start="2026-08-24 09:30")
    got = m.session_levels(pd.concat([pre, reg]))
    assert got["session_high"] == pytest.approx(101.0)
    assert got["session_low"] == pytest.approx(99.0), "premarket must not set the session low"


def test_overnight_levels_from_prepost_bars():
    prev = make_bars([(100.0, 100.0, 100.0, 100.0, 1)], start="2026-08-24 16:05")
    onh = make_bars([(100.0, 103.0, 97.0, 100.0, 1)], start="2026-08-25 04:00")
    reg = make_bars([(100.0, 101.0, 99.0, 100.0, 1000)], start="2026-08-25 09:30")
    got = m.overnight_levels(pd.concat([prev, onh, reg]))
    assert got["overnight_high"] == pytest.approx(103.0)
    assert got["overnight_low"] == pytest.approx(97.0)


def test_overnight_levels_nan_without_extended_bars():
    reg = make_bars([(100.0, 101.0, 99.0, 100.0, 1000)], start="2026-08-25 09:30")
    got = m.overnight_levels(reg)
    assert math.isnan(got["overnight_high"]), "no bars means no level, never a guess"


def test_prior_day_levels():
    daily = make_bars([
        (100.0, 105.0, 95.0, 102.0, 1),
        (102.0, 108.0, 101.0, 107.0, 1),
    ], start="2026-08-24 00:00", freq_minutes=1440)
    got = m.prior_day_levels(daily)
    assert (got["pdh"], got["pdl"], got["pdc"]) == pytest.approx((108.0, 101.0, 107.0))


def test_prior_day_levels_nan_with_insufficient_history():
    got = m.prior_day_levels(None)
    assert math.isnan(got["pdh"])


# ---------------------------------------------------------------- clock

def test_market_open_boundaries():
    from datetime import datetime
    assert m.is_market_open(datetime(2026, 8, 24, 9, 29, tzinfo=m.ET)) is False
    assert m.is_market_open(datetime(2026, 8, 24, 9, 30, tzinfo=m.ET)) is True
    assert m.is_market_open(datetime(2026, 8, 24, 15, 59, tzinfo=m.ET)) is True
    assert m.is_market_open(datetime(2026, 8, 24, 16, 0, tzinfo=m.ET)) is False
    assert m.is_market_open(datetime(2026, 8, 22, 12, 0, tzinfo=m.ET)) is False  # Saturday


def test_minutes_until_close():
    from datetime import datetime
    assert m.minutes_until_close(datetime(2026, 8, 24, 15, 30, tzinfo=m.ET)) == pytest.approx(30.0)


def test_fmt_time_leads_with_central():
    from datetime import datetime
    got = m.fmt_time(datetime(2026, 8, 24, 10, 45, tzinfo=m.ET))
    assert got == "09:45 CT / 10:45 ET", "CJ reads Central first (02-trycon-mas.md)"
