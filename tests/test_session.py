"""Session files create, append and compress correctly. BUILD_PROMPT Part 10."""

from datetime import date, datetime

import pytest

from tools import session as s
from tools.session import ET

DAY = date(2026, 8, 24)


@pytest.fixture
def desk(tmp_path):
    """An isolated sessions dir + ledger, so tests never touch the real repo files."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    return {
        "sessions": str(sessions),
        "calls": str(ledger / "calls.csv"),
        "outcomes": str(ledger / "outcomes.csv"),
    }


def _entry(n, call="NO TRADE — chop", levels="767.30 untested resistance", words=0):
    body = s.format_entry(
        when=datetime(2026, 8, 24, 11, 20, tzinfo=ET), number=n, price=766.55,
        ema9=766.4, ema21=766.2, ema50=766.8, ema200=764.1, vwap=765.9, atr=0.48,
        read="reclaimed 21, holding " + ("padding " * words), levels=levels, call=call,
    )
    return body


# ---------------------------------------------------------------- create

def test_create_session_fills_the_template(desk):
    path = s.create_session(DAY, desk["sessions"])
    body = open(path).read()
    assert path.endswith("2026-08-24.md")
    assert "2026-08-24" in body and "Monday" in body
    assert "{DATE}" not in body and "{WEEKDAY}" not in body


def test_create_session_is_idempotent(desk):
    path = s.create_session(DAY, desk["sessions"])
    with open(path, "a") as fh:
        fh.write("\nmy notes\n")
    s.create_session(DAY, desk["sessions"])
    assert "my notes" in open(path).read(), "must never clobber a live day file"


def test_create_session_overwrite_when_asked(desk):
    path = s.create_session(DAY, desk["sessions"])
    with open(path, "a") as fh:
        fh.write("\nmy notes\n")
    s.create_session(DAY, desk["sessions"], overwrite=True)
    assert "my notes" not in open(path).read()


# ---------------------------------------------------------------- entries

def test_format_entry_leads_with_central_and_marks_vwap_computed():
    body = _entry(4)
    assert body.startswith("\n### 10:20 CT / 11:20 ET — screenshot 4")
    assert "VWAP*" in body, "VWAP is computed, not on CJ's chart"


def test_append_entry_creates_the_day_then_appends(desk):
    assert not s.session_exists(DAY, desk["sessions"])
    s.append_entry(_entry(1), DAY, desk["sessions"])
    s.append_entry(_entry(2), DAY, desk["sessions"])
    assert s.entry_count(DAY, desk["sessions"]) == 2


def test_entry_count_zero_for_missing_day(desk):
    assert s.entry_count(date(2020, 1, 1), desk["sessions"]) == 0


# ---------------------------------------------------------------- compression

def test_no_compression_below_the_word_limit(desk):
    for i in range(1, 8):
        s.append_entry(_entry(i), DAY, desk["sessions"])
    assert s.maybe_compress(DAY, desk["sessions"]) is False
    assert s.entry_count(DAY, desk["sessions"]) == 7


def test_compression_keeps_the_last_five_in_full(desk):
    for i in range(1, 13):
        s.append_entry(_entry(i, call=f"WAIT until 11:{i:02d}", words=300),
                       DAY, desk["sessions"], auto_compress=False)
    assert s.entry_count(DAY, desk["sessions"]) == 12
    assert s.word_count(DAY, desk["sessions"]) > s.COMPRESS_WORD_LIMIT

    assert s.maybe_compress(DAY, desk["sessions"]) is True
    body = open(s.session_path(DAY, desk["sessions"])).read()

    full = [l for l in body.splitlines() if l.startswith("### ") and "screenshot" in l]
    assert len(full) == 5, "exactly the last five stay in full after a fold"
    assert "screenshot 12" in body and "screenshot 8" in body
    assert "screenshot 7" not in " ".join(full), "screenshot 7 was folded"


def test_compression_is_a_sawtooth_not_a_cap(desk):
    """After a fold the file grows again -- entries are not capped at five."""
    for i in range(1, 13):
        s.append_entry(_entry(i, words=300), DAY, desk["sessions"])
    body = open(s.session_path(DAY, desk["sessions"])).read()
    assert s.COMPRESSED_HEADING in body, "a fold happened along the way"
    live = [l for l in body.splitlines() if l.startswith("### ") and "screenshot" in l]
    assert len(live) > 5, "entries accumulate again after the fold"
    assert s.word_count(DAY, desk["sessions"]) < 2 * s.COMPRESS_WORD_LIMIT


def test_compression_preserves_levels_and_calls_from_folded_entries(desk):
    for i in range(1, 13):
        s.append_entry(
            _entry(i, call=f"WAIT until 11:{i:02d}", levels=f"level-{i} held", words=300),
            DAY, desk["sessions"], auto_compress=False,
        )
    s.maybe_compress(DAY, desk["sessions"])
    body = open(s.session_path(DAY, desk["sessions"])).read()
    assert "level-1 held" in body, "folded levels must survive -- later screenshots refer back"
    assert "WAIT until 11:01" in body, "folded calls must survive"
    assert "padding" not in body.split(s.COMPRESSED_HEADING)[1].split("### ")[0], \
        "the narrative read is what gets dropped"


def test_compression_is_idempotent_and_does_not_re_fold(desk):
    for i in range(1, 13):
        s.append_entry(_entry(i, words=300), DAY, desk["sessions"], auto_compress=False)
    s.maybe_compress(DAY, desk["sessions"])
    first = open(s.session_path(DAY, desk["sessions"])).read()
    s.maybe_compress(DAY, desk["sessions"])
    assert first.count(s.COMPRESSED_HEADING) == 1
    assert open(s.session_path(DAY, desk["sessions"])).read().count(s.COMPRESSED_HEADING) == 1


# ---------------------------------------------------------------- carry-forward

def test_carry_forward_lifts_levels_from_yesterday(desk):
    y = date(2026, 8, 21)
    s.append_entry(_entry(1, levels="767.30 untested resistance. 765.70 support held twice"),
                   y, desk["sessions"])
    got = s.carry_forward_levels(y, desk["sessions"])
    assert "767.30 untested resistance" in got
    assert "765.70 support held twice" in got


def test_carry_forward_empty_when_yesterday_has_no_file(desk):
    assert s.carry_forward_levels(date(2020, 1, 1), desk["sessions"]) == []


def test_previous_trading_day_skips_the_weekend():
    assert s.previous_trading_day(date(2026, 8, 24)) == date(2026, 8, 21)  # Mon -> Fri
    assert s.previous_trading_day(date(2026, 8, 25)) == date(2026, 8, 24)


# ---------------------------------------------------------------- ledger

def _call(verdict="TRADE", cid="20260824-103000-SPY", r_stamp="2026-08-24T10:30:00-04:00"):
    return {
        "call_id": cid, "timestamp_et": r_stamp, "timestamp_ct": "2026-08-24T09:30:00-05:00",
        "ticker": "SPY", "interval": "5m", "verdict": verdict, "direction": "long",
        "grade": "B", "conviction": "68", "stop": "765.70", "target1": "767.30",
    }


def test_every_verdict_is_logged_including_skips(desk):
    """Skipped trades are training data too. BUILD_PROMPT Part 3, Step 8."""
    s.append_call(_call("TRADE", "a"), desk["calls"])
    s.append_call(_call("NO TRADE", "b"), desk["calls"])
    s.append_call(_call("WAIT", "c"), desk["calls"])
    rows = s.read_calls(desk["calls"])
    assert [r["verdict"] for r in rows] == ["TRADE", "NO TRADE", "WAIT"]
    assert all(r["graded"] == "no" for r in rows)


def test_append_call_rejects_an_unknown_verdict(desk):
    with pytest.raises(ValueError, match="verdict"):
        s.append_call(_call("MAYBE", "x"), desk["calls"])


def test_append_call_requires_an_id(desk):
    row = _call()
    row["call_id"] = ""
    with pytest.raises(ValueError, match="call_id"):
        s.append_call(row, desk["calls"])


def test_make_call_id_is_sortable_and_names_the_ticker():
    got = s.make_call_id(datetime(2026, 8, 24, 10, 30, 5, tzinfo=ET), "spy")
    assert got == "20260824-103005-SPY"


def test_mark_graded_flips_only_the_named_calls(desk):
    s.append_call(_call("TRADE", "a"), desk["calls"])
    s.append_call(_call("TRADE", "b"), desk["calls"])
    assert s.mark_graded({"a"}, desk["calls"]) == 1
    rows = {r["call_id"]: r["graded"] for r in s.read_calls(desk["calls"])}
    assert rows == {"a": "yes", "b": "no"}


def test_day_state_counts_trades_and_sums_r(desk):
    s.append_call(_call("TRADE", "a"), desk["calls"])
    s.append_call(_call("TRADE", "b"), desk["calls"])
    s.append_call(_call("NO TRADE", "c"), desk["calls"])
    s.append_outcome({"call_id": "a", "r_multiple": "-1.0"}, desk["outcomes"])
    s.append_outcome({"call_id": "b", "r_multiple": "2.0"}, desk["outcomes"])

    state = s.day_state(DAY, desk["calls"], desk["outcomes"])
    assert state["trades_today"] == 2, "a NO TRADE is not a trade against the daily limit"
    assert state["calls_today"] == 3
    assert state["day_pnl_r"] == pytest.approx(1.0)
    assert state["last_loss_at"] is not None


def test_day_state_ignores_ungraded_calls(desk):
    s.append_call(_call("TRADE", "a"), desk["calls"])
    state = s.day_state(DAY, desk["calls"], desk["outcomes"])
    assert state["day_pnl_r"] == 0.0
    assert state["last_loss_at"] is None, "unknown stays unknown (07-journal-protocol.md)"


# ---------------------------------------------------------------- config drift

def test_session_file_takes_its_risk_numbers_from_config(desk):
    """These were hardcoded in the template once and went stale the moment CJ changed the
    limits. A wrong number in front of him at 08:32 is exactly what this test prevents."""
    from tools import guards as G
    cfg = G.load_config()
    path = s.create_session(DAY, desk["sessions"])
    body = open(path).read()

    assert f"0 / {cfg['risk']['max_trades_per_day']}" in body
    assert f"{abs(cfg['risk']['daily_loss_limit_r']):.2f}R" in body
    assert f"${cfg['risk']['unit_r_usd']:g}" in body
    for token in ("{UNIT_R}", "{MAX_TRADES}", "{LOSS_LIMIT}", "{A_RISK}", "{B_RISK}"):
        assert token not in body, f"{token} left unfilled"


def test_template_hardcodes_no_risk_numbers():
    """The template must express limits as placeholders, never as literals."""
    import re
    body = open(s.TEMPLATE).read()
    risk_block = body.split("## Risk budget")[1].split("##")[0]
    assert "{UNIT_R}" in risk_block and "{MAX_TRADES}" in risk_block
    assert not re.search(r"0 / \d", risk_block), "trade cap must not be a literal"
