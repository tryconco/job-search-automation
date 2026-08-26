"""Grading never assumes the favourable fill. BUILD_PROMPT Part 10."""

from datetime import datetime

import pytest

from tools import grade
from tools.grade import ET
from tests.fixtures import make_bars

ENTRY_TIME = datetime(2026, 8, 24, 10, 0, tzinfo=ET)


def bars_from(rows, start="2026-08-24 10:00", freq=5):
    return make_bars(rows, start=start, freq_minutes=freq)


# ---------------------------------------------------------------- the ambiguous bar

def test_bar_touching_both_stop_and_target_grades_as_a_loss():
    """THE rule. Bar data does not reveal which came first, so the loss is recorded."""
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),   # 10:00 -- entry bar, excluded (index > entry_time)
        (100.0, 102.0, 98.0, 100.0, 1000),   # 10:05 -- touches target 101 AND stop 99
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", entry=100.0, stop=99.0, target=101.0)
    assert got.outcome == "loss"
    assert got.r_multiple == -1.0
    assert got.ambiguous_bar is True
    assert "order unknowable" in got.note


def test_ambiguous_bar_rule_applies_to_shorts_too():
    bars = bars_from([
        (100.0, 100.1, 99.9, 100.0, 1000),
        (100.0, 102.0, 98.0, 100.0, 1000),
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "short", entry=100.0, stop=101.0, target=99.0)
    assert got.outcome == "loss"
    assert got.ambiguous_bar is True


def test_clean_target_hit_is_a_win_and_is_not_flagged_ambiguous():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 101.5, 99.8, 101.2, 1000),   # target 101 hit, stop 99 untouched
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 99.0, 101.0)
    assert got.outcome == "win"
    assert got.r_multiple == pytest.approx(1.0)
    assert got.ambiguous_bar is False


def test_clean_stop_hit_is_minus_one_r():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.1, 98.5, 98.6, 1000),
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 99.0, 101.0)
    assert got.outcome == "loss"
    assert got.r_multiple == -1.0
    assert got.ambiguous_bar is False


# ---------------------------------------------------------------- first-touch ordering

def test_earlier_bar_wins_over_a_later_one():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.1, 98.5, 98.6, 1000),   # 10:05 stop first
        (98.6, 105.0, 98.5, 104.0, 1000),   # 10:10 target later -- must not count
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 99.0, 101.0)
    assert got.outcome == "loss"
    assert got.minutes_to_resolution == pytest.approx(5.0)


def test_r_multiple_scales_with_the_target_distance():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 102.5, 99.9, 102.4, 1000),
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", entry=100.0, stop=99.0, target=102.0)
    assert got.r_multiple == pytest.approx(2.0), "2 points of reward on 1 point of risk"


# ---------------------------------------------------------------- unresolved

def test_neither_level_reached_is_flat_at_close_with_a_real_r():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.4, 99.8, 100.3, 1000),
        (100.3, 100.5, 99.9, 100.5, 1000),
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 99.0, 101.0)
    assert got.outcome == "flat_at_close"
    assert got.r_multiple == pytest.approx(0.5)


def test_grading_stops_at_the_hard_flat_time():
    """0DTE is flat by 15:30 ET. A target hit at 15:45 is not CJ's -- he is out."""
    bars = make_bars([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.3, 99.9, 100.2, 1000),
    ], start="2026-08-24 15:20", freq_minutes=5)
    late = make_bars([(100.0, 110.0, 99.9, 109.0, 1000)], start="2026-08-24 15:45")
    import pandas as pd
    got = grade.walk_forward(pd.concat([bars, late]),
                             datetime(2026, 8, 24, 15, 20, tzinfo=ET), "long", 100.0, 99.0, 101.0)
    assert got.outcome == "flat_at_close", "the 15:45 spike is after the hard flat"


def test_no_bars_after_the_call_is_not_graded():
    bars = bars_from([(100.0, 100.2, 99.9, 100.0, 1000)])
    got = grade.walk_forward(bars, datetime(2026, 8, 24, 14, 0, tzinfo=ET), "long", 100.0, 99.0, 101.0)
    assert got.outcome == "no_bars"
    assert got.r_multiple is None, "unknown stays unknown"


def test_zero_risk_is_ungradeable_not_a_win():
    bars = bars_from([(100.0, 105.0, 99.0, 104.0, 1000)] * 3)
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 100.0, 101.0)
    assert got.outcome == "no_bars"
    assert "zero risk" in got.note


# ---------------------------------------------------------------- excursions

def test_mfe_and_mae_are_recorded_in_r():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.8, 99.5, 100.1, 1000),   # +0.8 favourable, -0.5 adverse
        (100.1, 101.2, 100.0, 101.1, 1000),  # target
    ])
    got = grade.walk_forward(bars, ENTRY_TIME, "long", 100.0, 99.0, 101.0)
    assert got.mfe_r == pytest.approx(1.2)
    assert got.mae_r == pytest.approx(0.5)


# ---------------------------------------------------------------- skips

def test_skips_are_graded_as_counterfactuals():
    """A desk that only grades its own trades learns to trade less and calls it improvement."""
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 101.2, 99.9, 101.1, 1000),
    ])
    got = grade.grade_skip(bars, ENTRY_TIME, "long", entry=100.0, stop_distance=0.5,
                           reward_multiple=2.0)
    assert got.outcome == "win", "skipping this one cost 2R"
    assert got.note.startswith("counterfactual skip:")


def test_counterfactual_skip_can_also_be_a_loss():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 100.1, 99.0, 99.1, 1000),
    ])
    got = grade.grade_skip(bars, ENTRY_TIME, "long", 100.0, 0.5)
    assert got.outcome == "loss", "the skip was correct -- that is evidence too"


# ---------------------------------------------------------------- wait conditions

def test_wait_condition_checked_against_what_actually_happened():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 101.5, 99.9, 101.4, 1000),
    ])
    until = datetime(2026, 8, 24, 10, 45, tzinfo=ET)
    assert grade.check_wait_condition(bars, until, 101.0, "above")["occurred"] is True
    assert grade.check_wait_condition(bars, until, 102.0, "above")["occurred"] is False


def test_wait_condition_unknown_without_bars():
    bars = bars_from([(100.0, 100.2, 99.9, 100.0, 1000)], start="2026-08-24 14:00")
    got = grade.check_wait_condition(bars, datetime(2026, 8, 24, 10, 45, tzinfo=ET), 101.0, "above")
    assert got["occurred"] is None


# ---------------------------------------------------------------- ledger rows

def _row(**over):
    base = {
        "call_id": "20260824-100000-SPY", "timestamp_et": "2026-08-24T10:00:00-04:00",
        "ticker": "SPY", "verdict": "TRADE", "direction": "long",
        "entry_low": "100.0", "stop": "99.0", "target1": "101.0", "graded": "no",
    }
    base.update(over)
    return base


def test_grade_call_row_walks_a_trade():
    bars = bars_from([
        (100.0, 100.2, 99.9, 100.0, 1000),
        (100.0, 101.5, 99.9, 101.2, 1000),
    ])
    assert grade.grade_call_row(_row(), bars).outcome == "win"


def test_grade_call_row_refuses_an_incomplete_trade_row():
    bars = bars_from([(100.0, 100.2, 99.9, 100.0, 1000)] * 3)
    got = grade.grade_call_row(_row(stop=""), bars)
    assert got.outcome == "no_bars"
    assert "missing entry, stop or target" in got.note


def test_grade_call_row_returns_none_for_wait():
    bars = bars_from([(100.0, 100.2, 99.9, 100.0, 1000)] * 3)
    assert grade.grade_call_row(_row(verdict="WAIT"), bars) is None


def test_grade_call_row_handles_a_bad_timestamp():
    bars = bars_from([(100.0, 100.2, 99.9, 100.0, 1000)] * 3)
    got = grade.grade_call_row(_row(timestamp_et="not-a-date"), bars)
    assert got.outcome == "no_bars"


# ---------------------------------------------------------------- reporting

def test_summary_surfaces_ambiguous_bars_explicitly():
    report = {
        "day": "2026-08-24", "graded": 1, "ungraded": 1, "errors": [],
        "results": [{
            "call_id": "x", "outcome": "loss", "r_multiple": -1.0,
            "minutes_to_resolution": 5.0, "mfe_r": 1.0, "mae_r": 1.0,
            "ambiguous_bar": True, "note": "both touched",
        }],
    }
    text = grade.summarise_day(report)
    assert "1 ambiguous bar(s)" in text
    assert "recorded as losses" in text
    assert "Paper trading" in text
