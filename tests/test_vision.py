"""The screenshot is context, not measurement. BUILD_PROMPT Part 3, Step 2."""

from datetime import datetime

import pytest

from tools import market
from tools.vision import (
    Confidence, Reading, ScreenshotRead, Status, developing_candle_block, reconcile,
)
from tools.guards import ET
from tests.fixtures import make_bars, trending_bars


def at(h, m):
    return datetime(2026, 8, 24, h, m, tzinfo=ET)


def bars():
    return make_bars([
        (100.0, 100.4, 99.8, 100.2, 1000),   # 10:00
        (100.2, 100.6, 100.0, 100.5, 1000),  # 10:05
        (100.5, 100.9, 100.3, 100.8, 1000),  # 10:10
    ], start="2026-08-24 10:00")


def read_at(price, when=None, **kw):
    return ScreenshotRead(
        ticker="SPY", timeframe="5m", chart_time=when or at(10, 12),
        readings=[Reading("last_price", price, Confidence.CLEAR)], **kw
    )


# ---------------------------------------------------------------- reconciliation

def test_agreement_when_the_screenshot_sits_inside_its_own_bar():
    rec = reconcile(read_at(100.7), bars())
    assert rec.status is Status.AGREE
    assert rec.ok is True


def test_stale_screenshot_is_flagged_not_silently_trusted():
    rec = reconcile(read_at(105.0), bars())
    assert rec.status is Status.STALE_SCREENSHOT
    assert rec.ok is False
    assert "may be stale" in rec.message


def test_a_screenshot_newer_than_the_bars_is_lag_not_staleness():
    """yfinance intraday runs behind. That is expected, not an error."""
    rec = reconcile(read_at(103.0, when=at(11, 0)), bars())
    assert rec.status is Status.DATA_LAG
    assert rec.ok is True
    assert "data lag, not a stale chart" in rec.message


def test_comparison_uses_the_bar_at_the_screenshot_time_not_the_newest_bar():
    """A 10:02 screenshot must be checked against the 10:00 bar."""
    rec = reconcile(read_at(100.2, when=at(10, 2)), bars())
    assert rec.status is Status.AGREE
    assert rec.checks[0].data_value == pytest.approx(100.2), "the 10:00 close, not the 10:10 one"


def test_unreadable_price_is_unverifiable_not_a_guess():
    read = ScreenshotRead(
        ticker="SPY", chart_time=at(10, 12),
        readings=[Reading("last_price", None, Confidence.UNREADABLE, "price box cropped")],
    )
    rec = reconcile(read, bars())
    assert rec.status is Status.UNVERIFIABLE
    assert "last price" in rec.message
    assert "every level" in rec.trust_data_for


def test_missing_bars_is_unverifiable():
    import pandas as pd
    rec = reconcile(read_at(100.5), pd.DataFrame())
    assert rec.status is Status.UNVERIFIABLE


def test_screenshot_predating_history_is_unverifiable():
    rec = reconcile(read_at(100.5, when=at(8, 0)), bars())
    assert rec.status is Status.UNVERIFIABLE


# ---------------------------------------------------------------- the authority split

def test_the_split_is_explicit_in_every_reconciliation():
    rec = reconcile(read_at(100.7), bars())
    assert "current price" in rec.trust_screenshot_for
    assert "current time" in rec.trust_screenshot_for
    for level in ("EMA 9/21/50/200", "ATR", "VWAP", "prior day H/L/C", "opening range"):
        assert level in rec.trust_data_for


def test_a_disagreeing_chart_tag_loses_to_the_computed_value():
    df = trending_bars(n=260)
    ind = market.get_indicators(df)
    read = ScreenshotRead(
        ticker="SPY", chart_time=df.index[-1].to_pydatetime(),
        readings=[
            Reading("last_price", float(df["Close"].iloc[-1]), Confidence.CLEAR),
            Reading("ema21", ind.ema21 + 5.0, Confidence.PROBABLE, "tag partly overlapped"),
        ],
    )
    rec = reconcile(read, df, ind)
    ema_check = [c for c in rec.checks if c.field == "ema21"][0]
    assert ema_check.status is Status.DISAGREE
    assert ema_check.data_value == pytest.approx(round(ind.ema21, 4))
    assert "using computed" in ema_check.note
    assert "Computed values are authoritative" in rec.message


def test_a_matching_chart_tag_does_not_promote_a_pixel_to_a_level():
    df = trending_bars(n=260)
    ind = market.get_indicators(df)
    read = ScreenshotRead(
        ticker="SPY", chart_time=df.index[-1].to_pydatetime(),
        readings=[
            Reading("last_price", float(df["Close"].iloc[-1]), Confidence.CLEAR),
            Reading("ema21", round(ind.ema21, 2), Confidence.CLEAR),
        ],
    )
    rec = reconcile(read, df, ind)
    check = [c for c in rec.checks if c.field == "ema21"][0]
    assert check.status is Status.AGREE
    assert check.data_value == pytest.approx(round(ind.ema21, 4)), \
        "the computed value is the level even when the pixel agrees"


# ---------------------------------------------------------------- unreadable fields

def test_unreadable_fields_are_named_in_the_message():
    read = read_at(100.7)
    read.readings.append(Reading("sma200", None, Confidence.UNREADABLE, "line not tagged"))
    rec = reconcile(read, bars())
    assert "Not readable on this image: sma200" in rec.message


def test_value_helper_refuses_to_return_an_unreadable_number():
    read = ScreenshotRead(readings=[Reading("ema9", 123.0, Confidence.UNREADABLE)])
    assert read.value("ema9") is None, "an unreadable tag is not a number"
    assert read.unreadable() == ["ema9"]


# ---------------------------------------------------------------- developing candles

def test_developing_candle_block_quotes_the_countdown():
    read = ScreenshotRead(signal_candle_developing=True, candle_countdown_seconds=95)
    text = developing_candle_block(read)
    assert "1m 35s" in text
    assert "flip its shape" in text


def test_no_block_when_the_candle_has_closed():
    assert developing_candle_block(ScreenshotRead(signal_candle_developing=False)) is None


def test_developing_without_a_countdown_still_warns():
    read = ScreenshotRead(signal_candle_developing=True)
    assert "still printing" in developing_candle_block(read)


# ---------------------------------------------------------------- serialisation

def test_screenshot_read_serialises_its_confidence_and_unreadables():
    read = read_at(100.7, alerts=[767.30], drawings=["trendline off the 09:45 low"],
                   volume_visible=True, operator_text="thinking long here")
    d = read.as_dict()
    assert d["readings"][0]["confidence"] == "clear"
    assert d["readings"][0]["source"] == "screenshot"
    assert d["alerts"] == [767.30]
    assert d["volume_visible"] is True
    assert d["unreadable"] == []
