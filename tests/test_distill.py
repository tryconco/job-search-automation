"""The promotion bar holds. BUILD_PROMPT Part 10.

The headline test: the pass refuses to promote at n=29 and promotes the same effect at n=31.
"""

from datetime import date, datetime, timedelta

import pytest

from tools import distill as d
from tools.distill import ET, Record

CFG = {
    "min_sample": 30, "bootstrap_iterations": 2000, "confidence": 0.95,
    "max_active_rules": 25, "recency_halflife_days": 90,
}


def records(n, r_value=1.0, jitter=0.05, start=date(2026, 1, 5), grade="A"):
    """n graded calls with a consistent effect and a little spread, one per weekday."""
    out, day = [], start
    for i in range(n):
        while day.weekday() >= 5:
            day += timedelta(days=1)
        val = r_value + (jitter if i % 2 else -jitter)
        out.append(Record(
            call_id=f"c{i}", when=datetime(day.year, day.month, day.day, 10, 0, tzinfo=ET),
            r_multiple=val, ticker="SPY", verdict="TRADE", direction="long", grade=grade,
        ))
        day += timedelta(days=1)
    return out


# ---------------------------------------------------------------- the headline test

def test_refuses_to_promote_at_29_and_promotes_at_31():
    """Same effect size, same spread. Only the sample size differs."""
    at29 = d.evaluate_bucket("setup grade", "grade A", records(29), CFG)
    at31 = d.evaluate_bucket("setup grade", "grade A", records(31), CFG)

    assert at29.mean_r == pytest.approx(at31.mean_r, abs=0.05), "same effect size"

    assert at29.passes_sample is False
    assert at29.promotable is False
    assert "below the 30-call minimum" in "; ".join(at29.failure_reasons())

    assert at31.passes_sample is True
    assert at31.passes_ci is True
    assert at31.passes_halves is True
    assert at31.promotable is True


def test_thirty_exactly_is_the_boundary():
    assert d.evaluate_bucket("x", "y", records(29), CFG).passes_sample is False
    assert d.evaluate_bucket("x", "y", records(30), CFG).passes_sample is True


# ---------------------------------------------------------------- bootstrap

def test_bootstrap_ci_excludes_zero_for_a_consistent_effect():
    lo, hi = d.bootstrap_ci([1.0, 0.9, 1.1] * 15)
    assert lo > 0 and hi > 0
    assert d.ci_excludes_zero((lo, hi)) is True


def test_bootstrap_ci_contains_zero_for_noise():
    values = [1.0, -1.0] * 25
    assert d.ci_excludes_zero(d.bootstrap_ci(values)) is False


def test_bootstrap_is_deterministic():
    v = [0.5, -0.2, 1.4, -1.0, 0.3] * 10
    assert d.bootstrap_ci(v) == d.bootstrap_ci(v), "a rule change must be reproducible"


def test_ci_excludes_zero_handles_nan():
    assert d.ci_excludes_zero(d.bootstrap_ci([1.0])) is False


def test_a_noisy_bucket_with_a_big_sample_still_does_not_promote():
    """n alone is never enough."""
    noisy = []
    day = date(2026, 1, 5)
    for i in range(60):
        noisy.append(Record(f"c{i}", datetime(day.year, day.month, day.day, 10, tzinfo=ET),
                            2.0 if i % 2 else -2.0, grade="A"))
        day += timedelta(days=1)
    f = d.evaluate_bucket("setup grade", "grade A", noisy, CFG)
    assert f.passes_sample is True
    assert f.promotable is False


# ---------------------------------------------------------------- both halves

def test_both_halves_rejects_an_effect_confined_to_one_stretch():
    early = records(20, r_value=2.0, jitter=0.1)
    late = records(20, r_value=0.0, jitter=0.1, start=date(2026, 6, 1))
    ok, detail = d.both_halves_hold(early + late)
    assert ok is False
    assert "near zero" in detail or "sign flips" in detail


def test_both_halves_rejects_a_sign_flip():
    early = records(20, r_value=1.0, jitter=0.1)
    late = records(20, r_value=-1.2, jitter=0.1, start=date(2026, 6, 1))
    assert d.both_halves_hold(early + late)[0] is False


def test_both_halves_accepts_a_stable_effect():
    ok, detail = d.both_halves_hold(records(40, r_value=1.0))
    assert ok is True
    assert "first half" in detail and "second half" in detail


def test_both_halves_needs_enough_records():
    assert d.both_halves_hold(records(2))[0] is False


# ---------------------------------------------------------------- falsifiability

@pytest.mark.parametrize("text", [
    "Longs below VWAP before 10:30 ET have lost -0.40R per call on this desk",
    "grade C (setup grade) have lost -0.80R per call on this desk",
    "midday 11:30-13:30 ET (session window) have lost -0.35R per call on this desk",
])
def test_falsifiable_statements_pass(text):
    assert d.is_falsifiable(text) is True


@pytest.mark.parametrize("text", [
    "Be careful in the morning",
    "usually a bad idea",
    "trade well",
    "",
])
def test_vibes_are_not_rules(text):
    assert d.is_falsifiable(text) is False


# ---------------------------------------------------------------- recency

def test_recency_weight_halves_at_the_halflife():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=ET)
    assert d.recency_weight(now, now, 90) == pytest.approx(1.0)
    assert d.recency_weight(now - timedelta(days=90), now, 90) == pytest.approx(0.5)
    assert d.recency_weight(now - timedelta(days=180), now, 90) == pytest.approx(0.25)


def test_old_data_is_downweighted_but_never_dropped():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=ET)
    old = Record("old", now - timedelta(days=365), -2.0)
    new = Record("new", now, 1.0)
    w = d.weighted_expectancy([old, new], now, 90)
    assert w < 1.0, "the old loss still counts"
    assert w > 0.5, "but it counts less than the recent win"


# ---------------------------------------------------------------- end to end

@pytest.fixture
def files(tmp_path):
    return {
        "calls": str(tmp_path / "calls.csv"), "outcomes": str(tmp_path / "outcomes.csv"),
        "lessons": str(tmp_path / "LESSONS.md"), "changelog": str(tmp_path / "CHANGELOG.md"),
        "candidates": str(tmp_path / "candidates.md"),
    }


def _seed(files, n, r_value=1.0, grade="A"):
    from tools import session as sess
    day = date(2026, 1, 5)
    for i in range(n):
        while day.weekday() >= 5:
            day += timedelta(days=1)
        cid = f"c{i:03d}"
        sess.append_call({
            "call_id": cid, "timestamp_et": f"{day}T10:00:00-05:00", "ticker": "SPY",
            "verdict": "TRADE", "direction": "long", "grade": grade, "conviction": "70",
        }, files["calls"])
        sess.append_outcome({
            "call_id": cid, "r_multiple": r_value + (0.05 if i % 2 else -0.05),
            "outcome": "win" if r_value > 0 else "loss", "ambiguous_bar": "no",
        }, files["outcomes"])
        day += timedelta(days=1)


def test_run_writes_a_changelog_entry_for_every_promotion(files):
    """No rule enters LESSONS.md without a CHANGELOG.md entry naming its evidence."""
    _seed(files, 40)
    report = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})

    assert report["promoted"], "40 consistent calls should promote something"
    lessons = open(files["lessons"]).read()
    changelog = open(files["changelog"]).read()

    for p in report["promoted"]:
        assert p["id"] in lessons
        assert p["id"] in changelog
        assert f"n={p['n']}" in changelog
        assert "95% bootstrap CI" in changelog
        assert "both-halves" in changelog


def test_run_writes_failures_to_candidates_not_lessons(files):
    _seed(files, 12)
    d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
          files["candidates"], config={"distill": CFG})

    lessons = open(files["lessons"]).read()
    candidates = open(files["candidates"]).read()
    assert "None yet" in lessons, "nothing cleared the bar"
    assert "below the 30-call minimum" in candidates
    assert "Not rules" in candidates


def test_run_on_an_empty_ledger_is_a_valid_report(files):
    report = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})
    assert report["records"] == 0
    assert report["promoted"] == []
    assert "No rule changes this week" in d.summarise(report)


def test_lessons_file_is_capped_at_25(files):
    _seed(files, 40)
    tight = {**CFG, "max_active_rules": 1}
    report = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": tight})
    assert report["active_rules"] <= 1
    changelog = open(files["changelog"]).read()
    if len(report["promoted"]) < len([f for f in report["rejected"]]) + 1:
        assert "cap reached" in changelog or report["active_rules"] == 1


def test_summary_says_so_plainly_when_nothing_promoted(files):
    _seed(files, 10)
    report = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})
    text = d.summarise(report)
    assert "No rule changes this week" in text
    assert "still accumulating" in text
    assert "The model did not learn anything" in text


def test_load_records_skips_ungraded_and_unparseable(files):
    from tools import session as sess
    sess.append_call({"call_id": "a", "timestamp_et": "2026-01-05T10:00:00-05:00",
                      "ticker": "SPY", "verdict": "TRADE"}, files["calls"])
    sess.append_call({"call_id": "b", "timestamp_et": "bogus", "ticker": "SPY",
                      "verdict": "TRADE"}, files["calls"])
    sess.append_outcome({"call_id": "a", "r_multiple": "1.0"}, files["outcomes"])
    sess.append_outcome({"call_id": "b", "r_multiple": "1.0"}, files["outcomes"])
    sess.append_outcome({"call_id": "c", "r_multiple": "1.0"}, files["outcomes"])  # no call row

    got = d.load_records(files["calls"], files["outcomes"])
    assert [r.call_id for r in got] == ["a"], "unknown stays unknown"


# ---------------------------------------------------------------- rule persistence

def test_a_rule_survives_a_round_trip_without_losing_its_evidence(tmp_path):
    """The second pass must not blank out the numbers that justified the rule."""
    path = str(tmp_path / "LESSONS.md")
    rule = {"id": "L001", "key": "setup grade/grade A", "text": "grade A has made +1.00R per call",
            "n": 42, "mean_r": 1.0, "ci": (0.8, 1.2), "promoted": "2026-08-26"}
    open(path, "w").write(d.render_lessons([rule], [], 25))

    got = d.read_active_rules(path)
    assert len(got) == 1
    assert got[0] == rule, "evidence must round-trip exactly"


def test_deprecated_rules_round_trip_and_are_never_deleted(tmp_path):
    path = str(tmp_path / "LESSONS.md")
    dep = {"id": "L001", "key": "direction/long", "text": "longs have made +0.50R per call",
           "date": "2026-09-01", "reason": "CI now contains zero"}
    open(path, "w").write(d.render_lessons([], [dep], 25))

    got = d.read_deprecated_rules(path)
    assert got == [dep]
    assert "~~" in open(path).read(), "shown struck through, not removed"


def test_rule_ids_are_never_reused(tmp_path):
    active = [{"id": "L003", "key": "a/b"}]
    deprecated = [{"id": "L007", "key": "c/d"}]
    assert d.next_rule_id(active, deprecated) == "L008", "must clear the highest id ever issued"
    assert d.next_rule_id([], deprecated) == "L008", "a retired id does not come back"


def test_rule_key_is_stable_when_the_measured_effect_drifts():
    """Matching on the prose statement would re-promote a rule alongside itself."""
    a = d.phrase("session window", "prime 09:45-11:30 ET", 0.50)
    b = d.phrase("session window", "prime 09:45-11:30 ET", 0.52)
    assert a != b, "the statement embeds the mean, so it drifts"
    assert d.rule_key("session window", "prime 09:45-11:30 ET") == \
           d.rule_key("session window", "prime 09:45-11:30 ET")


def test_a_rule_is_not_promoted_twice_when_its_mean_drifts(files):
    _seed(files, 40, r_value=1.0)
    first = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                  files["candidates"], config={"distill": CFG})
    assert first["promoted"]
    n_after_first = first["active_rules"]

    # another pass over the same ledger: nothing new, nothing duplicated
    second = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})
    assert second["promoted"] == [], "no rule may be promoted a second time"
    assert second["active_rules"] == n_after_first

    ids = [r["id"] for r in d.read_active_rules(files["lessons"])]
    assert len(ids) == len(set(ids)), "no duplicate ids"


def test_a_rule_that_stops_holding_is_demoted_with_a_reason(files):
    """BUILD_PROMPT Part 6b: demotion matters as much as promotion."""
    _seed(files, 40, r_value=1.0)
    first = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                  files["candidates"], config={"distill": CFG})
    promoted_ids = [p["id"] for p in first["promoted"]]
    assert promoted_ids

    # the edge dies: 40 more calls in the same buckets, now losing
    _seed(files, 40, r_value=-1.0)
    second = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})

    demoted_ids = [r["id"] for r in second["demoted"]]
    assert set(promoted_ids) & set(demoted_ids), "the rule that stopped holding must retire"

    lessons = open(files["lessons"]).read()
    changelog = open(files["changelog"]).read()
    for rid in demoted_ids:
        assert f"~~**{rid}**" in lessons, "struck through, never silently deleted"
        assert f"deprecated {rid}" in changelog, "and traceable in the changelog"
    assert "stopped holding" in changelog


def test_demotion_is_reported_in_the_weekly_summary(files):
    _seed(files, 40, r_value=1.0)
    d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
          files["candidates"], config={"distill": CFG})
    _seed(files, 40, r_value=-1.0)
    report = d.run(files["calls"], files["outcomes"], files["lessons"], files["changelog"],
                   files["candidates"], config={"distill": CFG})
    if report["demoted"]:
        text = d.summarise(report)
        assert "Demoted" in text
        assert "Retired, not deleted" in text
