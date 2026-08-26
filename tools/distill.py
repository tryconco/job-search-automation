"""The learning pass. BUILD_PROMPT Part 6b.

Runs weekly. This is where rules change, so this is where the guardrails live -- a learning
loop without them just curve-fits to noise.

**Be straight about what this is.** The model does not learn here and nothing is retrained.
What happens is *evidence accumulation and rule evolution*: outcomes are measured, and the
desk's own operating rules are rewritten from that evidence. The model stays fixed; the context
it reasons over gets sharper.

A pattern becomes a rule only if **all four** hold:

1. at least 30 graded calls in the bucket
2. the 95% bootstrap CI on expectancy excludes zero
3. it holds in **both halves** of the sample split by date
4. it is stated as a falsifiable rule, not a vibe

Anything that fails goes to ``lessons/candidates.md`` and is rechecked next week. Nothing is
promoted early because it looks promising.

Prints its reasoning, not just its conclusions, so CJ can audit why a rule changed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Callable, Optional, Sequence
from zoneinfo import ZoneInfo

# Running as a script (``python3 tools/grade.py``) puts tools/ on sys.path, not the repo root,
# so the package imports below would fail. Put the root on the path first.
if __package__ in (None, ""):  # pragma: no cover
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from tools import session

ET = ZoneInfo("America/New_York")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS = os.path.join(ROOT, "lessons", "LESSONS.md")
CHANGELOG = os.path.join(ROOT, "lessons", "CHANGELOG.md")
CANDIDATES = os.path.join(ROOT, "lessons", "candidates.md")

VAGUE = {
    "careful", "cautious", "sometimes", "often", "generally", "usually", "tends",
    "maybe", "probably", "risky", "good", "bad", "better", "worse", "vibes",
}


# --------------------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------------------

@dataclass
class Record:
    """One graded call, joined from ``calls.csv`` and ``outcomes.csv``."""

    call_id: str
    when: datetime
    r_multiple: float
    ticker: str = ""
    verdict: str = ""
    direction: str = ""
    grade: str = ""
    outcome: str = ""
    ambiguous_bar: bool = False

    @property
    def day(self) -> date:
        return self.when.date()

    @property
    def hour_et(self) -> int:
        return self.when.astimezone(ET).hour

    @property
    def weekday(self) -> str:
        return self.when.strftime("%A")


def load_records(calls_path: str = session.CALLS_CSV,
                 outcomes_path: str = session.OUTCOMES_CSV) -> list[Record]:
    calls = {c["call_id"]: c for c in session.read_calls(calls_path)}
    out: list[Record] = []
    for o in session.read_outcomes(outcomes_path):
        c = calls.get(o["call_id"])
        if not c:
            continue
        try:
            r = float(o["r_multiple"])
            when = datetime.fromisoformat(c["timestamp_et"])
        except (TypeError, ValueError):
            continue  # unknown stays unknown -- never impute an outcome
        out.append(Record(
            call_id=o["call_id"], when=when, r_multiple=r, ticker=c.get("ticker", ""),
            verdict=c.get("verdict", ""), direction=c.get("direction", ""),
            grade=c.get("grade", ""), outcome=o.get("outcome", ""),
            ambiguous_bar=o.get("ambiguous_bar") == "yes",
        ))
    return sorted(out, key=lambda r: r.when)


# --------------------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------------------

def bootstrap_ci(values: Sequence[float], iterations: int = 2000, confidence: float = 0.95,
                 seed: int = 20260826) -> tuple[float, float]:
    """Percentile bootstrap CI on the mean. Seeded, so a rule change is reproducible."""
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo_i = int((1 - confidence) / 2 * iterations)
    hi_i = min(iterations - 1, int((1 + confidence) / 2 * iterations))
    return (means[lo_i], means[hi_i])


def ci_excludes_zero(ci: tuple[float, float]) -> bool:
    lo, hi = ci
    if any(x != x for x in ci):  # NaN
        return False
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


def both_halves_hold(records: Sequence[Record], min_share: float = 0.25) -> tuple[bool, str]:
    """Split by date at the median and require the effect to survive in **both** halves.

    A pattern that only worked in one stretch is not a pattern -- it is a stretch. Each half
    must share the overall sign and carry at least ``min_share`` of the overall magnitude, so a
    half that is really just noise cannot be waved through.
    """
    if len(records) < 4:
        return False, "too few records to split"
    ordered = sorted(records, key=lambda r: r.when)
    mid = len(ordered) // 2
    first, second = ordered[:mid], ordered[mid:]
    overall = statistics.fmean(r.r_multiple for r in ordered)
    m1 = statistics.fmean(r.r_multiple for r in first)
    m2 = statistics.fmean(r.r_multiple for r in second)

    same_sign = (m1 > 0) == (overall > 0) and (m2 > 0) == (overall > 0)
    strong = abs(m1) >= abs(overall) * min_share and abs(m2) >= abs(overall) * min_share
    detail = (f"first half n={len(first)} mean {m1:+.3f}R, "
              f"second half n={len(second)} mean {m2:+.3f}R, overall {overall:+.3f}R")
    if not same_sign:
        return False, f"sign flips between halves — {detail}"
    if not strong:
        return False, f"one half is near zero — {detail}"
    return True, detail


def recency_weight(when: datetime, now: Optional[datetime] = None, halflife_days: int = 90) -> float:
    """Weight recent evidence more heavily. **Old data is never dropped** -- the both-halves
    test needs it, and dropping it is how a desk forgets that the market changed."""
    now = now or datetime.now(ET)
    days = max(0.0, (now.astimezone(ET) - when.astimezone(ET)).total_seconds() / 86400.0)
    return 0.5 ** (days / halflife_days)


def weighted_expectancy(records: Sequence[Record], now: Optional[datetime] = None,
                        halflife_days: int = 90) -> float:
    if not records:
        return float("nan")
    num = sum(recency_weight(r.when, now, halflife_days) * r.r_multiple for r in records)
    den = sum(recency_weight(r.when, now, halflife_days) for r in records)
    return num / den if den else float("nan")


def is_falsifiable(statement: str) -> bool:
    """A rule names a measurable condition. "Longs below VWAP before 10:30 ET" is a rule.
    "Be careful in the morning" is not."""
    if not statement or len(statement.split()) < 4:
        return False
    low = statement.lower()
    if any(word in low.split() for word in VAGUE):
        return False
    measurable = bool(re.search(r"\d", statement)) or any(
        k in low for k in ("above", "below", "before", "after", "between", "grade ",
                           "long", "short", "within", "outside")
    )
    return measurable


# --------------------------------------------------------------------------------------
# buckets
# --------------------------------------------------------------------------------------

def _session_window(r: Record) -> str:
    h, m = r.when.astimezone(ET).hour, r.when.astimezone(ET).minute
    minutes = h * 60 + m
    if minutes < 9 * 60 + 45:
        return "open 09:30-09:45 ET"
    if minutes < 11 * 60 + 30:
        return "prime 09:45-11:30 ET"
    if minutes < 13 * 60 + 30:
        return "midday 11:30-13:30 ET"
    if minutes < 15 * 60:
        return "afternoon 13:30-15:00 ET"
    return "late after 15:00 ET"


BUCKETERS: dict[str, Callable[[Record], Optional[str]]] = {
    "setup grade": lambda r: f"grade {r.grade}" if r.grade else None,
    "session window": _session_window,
    "direction": lambda r: r.direction.lower() or None,
    "day of week": lambda r: r.weekday,
    "ticker": lambda r: r.ticker or None,
    "verdict": lambda r: r.verdict or None,
}


@dataclass
class Finding:
    dimension: str
    bucket: str
    n: int
    mean_r: float
    weighted_r: float
    ci: tuple[float, float]
    passes_sample: bool
    passes_ci: bool
    passes_halves: bool
    halves_detail: str
    statement: str
    passes_falsifiable: bool

    @property
    def promotable(self) -> bool:
        return all((self.passes_sample, self.passes_ci, self.passes_halves,
                    self.passes_falsifiable))

    def failure_reasons(self) -> list[str]:
        out = []
        if not self.passes_sample:
            out.append(f"n={self.n}, below the 30-call minimum")
        if not self.passes_ci:
            out.append(f"95% CI [{self.ci[0]:+.3f}, {self.ci[1]:+.3f}] contains zero")
        if not self.passes_halves:
            out.append(f"both-halves test failed: {self.halves_detail}")
        if not self.passes_falsifiable:
            out.append("statement is not falsifiable")
        return out

    def as_dict(self) -> dict:
        d = asdict(self)
        d["promotable"] = self.promotable
        return d


def phrase(dimension: str, bucket: str, mean_r: float) -> str:
    verb = "have made" if mean_r > 0 else "have lost"
    return f"{bucket} ({dimension}) {verb} {mean_r:+.2f}R per call on this desk"


def evaluate_bucket(dimension: str, bucket: str, records: Sequence[Record],
                    cfg: dict, now: Optional[datetime] = None) -> Finding:
    values = [r.r_multiple for r in records]
    mean_r = statistics.fmean(values) if values else float("nan")
    ci = bootstrap_ci(values, cfg["bootstrap_iterations"], cfg["confidence"])
    halves_ok, halves_detail = both_halves_hold(records)
    statement = phrase(dimension, bucket, mean_r)
    return Finding(
        dimension=dimension, bucket=bucket, n=len(records), mean_r=round(mean_r, 4),
        weighted_r=round(weighted_expectancy(records, now, cfg["recency_halflife_days"]), 4),
        ci=(round(ci[0], 4), round(ci[1], 4)),
        passes_sample=len(records) >= cfg["min_sample"],
        passes_ci=ci_excludes_zero(ci),
        passes_halves=halves_ok, halves_detail=halves_detail,
        statement=statement, passes_falsifiable=is_falsifiable(statement),
    )


def analyse(records: Sequence[Record], cfg: dict, now: Optional[datetime] = None) -> list[Finding]:
    findings: list[Finding] = []
    for dimension, keyfn in BUCKETERS.items():
        groups: dict[str, list[Record]] = {}
        for r in records:
            key = keyfn(r)
            if key:
                groups.setdefault(key, []).append(r)
        for bucket, rows in sorted(groups.items()):
            findings.append(evaluate_bucket(dimension, bucket, rows, cfg, now))
    return sorted(findings, key=lambda f: (not f.promotable, -abs(f.mean_r)))


# --------------------------------------------------------------------------------------
# lessons file
# --------------------------------------------------------------------------------------

RULE_LINE = re.compile(
    r"^- \*\*(?P<id>L\d+)\*\*\s+`(?P<key>[^`]+)`\s+—\s+(?P<text>.+?)\s+—\s+"
    r"_n=(?P<n>\d+), mean (?P<mean>[-+][\d.]+)R, 95% CI \[(?P<lo>[-+][\d.]+), "
    r"(?P<hi>[-+][\d.]+)\], promoted (?P<promoted>[\d-]+)_",
    re.M,
)

DEPRECATED_LINE = re.compile(
    r"^- ~~\*\*(?P<id>L\d+)\*\* `(?P<key>[^`]+)` — (?P<text>.+?)~~ — "
    r"_deprecated (?P<date>[\d-]+): (?P<reason>.+?)_",
    re.M,
)


def rule_key(dimension: str, bucket: str) -> str:
    """A **stable** identity for a rule, independent of its measured effect.

    Matching rules by their prose statement would be a bug: the statement embeds the mean R,
    so a rule drifting from +0.50R to +0.52R would look like a brand new rule and be promoted
    a second time alongside itself.
    """
    return f"{dimension}/{bucket}"


def read_active_rules(path: str = LESSONS) -> list[dict]:
    if not os.path.exists(path):
        return []
    active = open(path).read().split("## Deprecated")[0]
    return [{
        "id": m.group("id"), "key": m.group("key"), "text": m.group("text"),
        "n": int(m.group("n")), "mean_r": float(m.group("mean")),
        "ci": (float(m.group("lo")), float(m.group("hi"))), "promoted": m.group("promoted"),
    } for m in RULE_LINE.finditer(active)]


def read_deprecated_rules(path: str = LESSONS) -> list[dict]:
    """Deprecated rules are **never deleted** -- CJ needs to see when the market changed."""
    if not os.path.exists(path):
        return []
    body = open(path).read()
    if "## Deprecated" not in body:
        return []
    return [{"id": m.group("id"), "key": m.group("key"), "text": m.group("text"),
             "date": m.group("date"), "reason": m.group("reason")}
            for m in DEPRECATED_LINE.finditer(body.split("## Deprecated")[1])]


def next_rule_id(active: list[dict], deprecated: list[dict]) -> str:
    """IDs are never reused. A retired L004 must not come back as a different rule --
    the changelog would then point at two things at once."""
    nums = [int(r["id"][1:]) for r in list(active) + list(deprecated)] or [0]
    return f"L{max(nums) + 1:03d}"


def render_lessons(rules: list[dict], deprecated: list[dict], cap: int) -> str:
    lines = [
        "# LESSONS",
        "",
        "Rules earned from **graded outcomes**. Loaded on every call. These **override** generic",
        "trading logic -- a lesson beats a textbook-perfect chart.",
        "",
        f"Active rules: **{len(rules)} / {cap}**. To add one past the cap, one must be demoted.",
        "",
        "Every rule here has a `CHANGELOG.md` entry naming the evidence that created it. A rule",
        "with no changelog entry is a bug -- delete it and say so.",
        "",
        "## Active",
        "",
    ]
    if not rules:
        lines.append("_None yet. Nothing has cleared the promotion bar._")
    for r in rules:
        lines.append(
            f"- **{r['id']}** `{r['key']}` — {r['text']} — "
            f"_n={r['n']}, mean {r['mean_r']:+.2f}R, "
            f"95% CI [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}], promoted {r['promoted']}_"
        )
    lines += ["", "## Deprecated", ""]
    if not deprecated:
        lines.append("_None._")
    for r in deprecated:
        lines.append(
            f"- ~~**{r['id']}** `{r['key']}` — {r['text']}~~ — "
            f"_deprecated {r['date']}: {r['reason']}_"
        )
    lines += ["", "_Paper trading. Counts are this desk's record, never probabilities._"]
    return "\n".join(lines) + "\n"


def render_candidates(findings: list[Finding], when: date) -> str:
    lines = [
        "# CANDIDATES",
        "",
        "Patterns under observation. **Not rules.** Nothing here may influence a call.",
        "",
        f"Last checked: {when}. Rechecked every distillation pass.",
        "",
        "| dimension | bucket | n | mean R | 95% CI | why it did not promote |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings:
        lines.append(
            f"| {f.dimension} | {f.bucket} | {f.n} | {f.mean_r:+.2f} | "
            f"[{f.ci[0]:+.2f}, {f.ci[1]:+.2f}] | {'; '.join(f.failure_reasons())} |"
        )
    if not findings:
        lines.append("| — | — | — | — | — | nothing accumulating yet |")
    return "\n".join(lines) + "\n"


def append_changelog(entries: list[str], path: str = CHANGELOG) -> None:
    """Every promotion and demotion writes here. A rule with no entry is untraceable."""
    if not entries:
        return
    header = ""
    if not os.path.exists(path):
        header = (
            "# CHANGELOG\n\n"
            "Every rule change, with the evidence that caused it. Append-only.\n"
            "No rule enters `LESSONS.md` without an entry here.\n"
        )
    with open(path, "a") as fh:
        if header:
            fh.write(header)
        fh.write("\n" + "\n".join(entries) + "\n")


# --------------------------------------------------------------------------------------
# the pass
# --------------------------------------------------------------------------------------

def run(calls_path: str = session.CALLS_CSV, outcomes_path: str = session.OUTCOMES_CSV,
        lessons_path: str = LESSONS, changelog_path: str = CHANGELOG,
        candidates_path: str = CANDIDATES, config: Optional[dict] = None,
        now: Optional[datetime] = None, write: bool = True) -> dict:
    from tools.guards import load_config
    cfg = (config or load_config())["distill"]
    now = now or datetime.now(ET)
    today = now.date()

    records = load_records(calls_path, outcomes_path)
    findings = analyse(records, cfg, now)
    promotable = [f for f in findings if f.promotable]
    rejected = [f for f in findings if not f.promotable]

    findings_by_key = {rule_key(f.dimension, f.bucket): f for f in findings}
    existing = read_active_rules(lessons_path)
    deprecated = read_deprecated_rules(lessons_path)

    active: list[dict] = []
    promoted: list[dict] = []
    demoted: list[dict] = []
    changelog: list[str] = []

    # --- re-test every existing rule. Demotion matters as much as promotion.
    for rule in existing:
        f = findings_by_key.get(rule["key"])
        if f is None:
            deprecated.append({**rule, "date": str(today),
                               "reason": "bucket no longer present in the graded record"})
            demoted.append(rule)
            changelog.append(
                f"- **{today} — deprecated {rule['id']}.** \"{rule['text']}\"\n"
                f"  - reason: that bucket no longer appears in the graded record\n"
                f"  - rule is retired, not deleted; its id is never reused"
            )
            continue
        if not f.promotable:
            deprecated.append({**rule, "date": str(today),
                               "reason": "; ".join(f.failure_reasons())})
            demoted.append(rule)
            changelog.append(
                f"- **{today} — deprecated {rule['id']}.** \"{rule['text']}\"\n"
                f"  - it stopped holding: {'; '.join(f.failure_reasons())}\n"
                f"  - now n={f.n}, mean {f.mean_r:+.3f}R, "
                f"95% CI [{f.ci[0]:+.3f}, {f.ci[1]:+.3f}]\n"
                f"  - rule is retired, not deleted; its id is never reused"
            )
            continue
        # still holds -- refresh the measured evidence, keep the original promotion date
        active.append({**rule, "text": f.statement, "n": f.n, "mean_r": f.mean_r, "ci": f.ci})

    active_keys = {r["key"] for r in active}
    retired_keys = {r["key"] for r in deprecated}

    # --- promote anything new that clears every gate
    for f in promotable:
        key = rule_key(f.dimension, f.bucket)
        if key in active_keys or key in retired_keys:
            continue
        if len(active) >= cfg["max_active_rules"]:
            changelog.append(
                f"- **{today} — NOT promoted (cap reached).** \"{f.statement}\" cleared every "
                f"test (n={f.n}, mean {f.mean_r:+.2f}R) but LESSONS.md is at its "
                f"{cfg['max_active_rules']}-rule cap. Demote something first."
            )
            continue
        rid = next_rule_id(active, deprecated)
        active.append({"id": rid, "key": key, "text": f.statement, "n": f.n,
                       "mean_r": f.mean_r, "ci": f.ci, "promoted": str(today)})
        active_keys.add(key)
        promoted.append({"id": rid, **f.as_dict()})
        changelog.append(
            f"- **{today} — promoted {rid}.** \"{f.statement}\"\n"
            f"  - sample: n={f.n} graded calls\n"
            f"  - measured effect: mean {f.mean_r:+.3f}R per call "
            f"(recency-weighted {f.weighted_r:+.3f}R)\n"
            f"  - 95% bootstrap CI: [{f.ci[0]:+.3f}, {f.ci[1]:+.3f}], excludes zero\n"
            f"  - both-halves: {f.halves_detail}"
        )

    report = {
        "date": str(today),
        "records": len(records),
        "findings": len(findings),
        "promoted": promoted,
        "demoted": demoted,
        "rejected": [f.as_dict() for f in rejected],
        "active_rules": len(active),
        "cap": cfg["max_active_rules"],
    }

    if write:
        os.makedirs(os.path.dirname(lessons_path), exist_ok=True)
        with open(lessons_path, "w") as fh:
            fh.write(render_lessons(active, deprecated, cfg["max_active_rules"]))
        with open(candidates_path, "w") as fh:
            fh.write(render_candidates(rejected, today))
        append_changelog(changelog, changelog_path)

    return report


def summarise(report: dict) -> str:
    """The weekly GitHub issue body. "No rule changes this week" is a valid, useful report."""
    lines = [
        f"# Distillation — {report['date']}",
        "",
        f"Graded records analysed: **{report['records']}** across {report['findings']} buckets.",
        f"Active rules: {report['active_rules']} / {report['cap']}.",
        "",
    ]
    if report.get("demoted"):
        lines += ["## Demoted", "",
                  "These stopped holding. Retired, not deleted.", ""]
        for d_ in report["demoted"]:
            lines.append(f"- **{d_['id']}** {d_['text']}")
        lines.append("")

    if report["promoted"]:
        lines += ["## Promoted", ""]
        for p in report["promoted"]:
            lines.append(
                f"- **{p['id']}** {p['statement']} — n={p['n']}, mean {p['mean_r']:+.2f}R, "
                f"95% CI [{p['ci'][0]:+.2f}, {p['ci'][1]:+.2f}]"
            )
    elif report.get("demoted"):
        lines += ["## No promotions this week", ""]
    else:
        lines += [
            "## No rule changes this week",
            "",
            "Nothing met the promotion bar. Here is what is still accumulating:",
            "",
        ]
        near = sorted(report["rejected"], key=lambda f: -f["n"])[:10]
        if near:
            lines += ["| bucket | n | mean R | blocked by |", "|---|---|---|---|"]
            for f in near:
                reasons = []
                if not f["passes_sample"]:
                    reasons.append(f"n={f['n']} < 30")
                if not f["passes_ci"]:
                    reasons.append("CI contains zero")
                if not f["passes_halves"]:
                    reasons.append("fails both-halves")
                if not f["passes_falsifiable"]:
                    reasons.append("not falsifiable")
                lines.append(f"| {f['bucket']} | {f['n']} | {f['mean_r']:+.2f} | "
                             f"{', '.join(reasons)} |")
        else:
            lines.append("_Nothing graded yet._")
    lines += [
        "",
        "---",
        "",
        "_The model did not learn anything. Rules were re-measured against graded outcomes._",
        "_Paper trading. No evidence has established that this method is profitable._",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the weekly learning pass.")
    ap.add_argument("--dry-run", action="store_true", help="analyse without writing files")
    ap.add_argument("--summary", action="store_true", help="print the issue body instead of JSON")
    ap.add_argument("--verbose", action="store_true", help="print the reasoning for every bucket")
    args = ap.parse_args()

    report = run(write=not args.dry_run)
    if args.verbose:
        print("# Reasoning\n")
        for f in report["promoted"]:
            print(f"PROMOTE  {f['dimension']:<18} {f['bucket']:<28} n={f['n']:<4} "
                  f"mean {f['mean_r']:+.3f}R  CI [{f['ci'][0]:+.3f}, {f['ci'][1]:+.3f}]")
        for f in report["rejected"]:
            print(f"reject   {f['dimension']:<18} {f['bucket']:<28} n={f['n']:<4} "
                  f"mean {f['mean_r']:+.3f}R  -> {'; '.join(Finding(**{k: v for k, v in f.items() if k != 'promotable'}).failure_reasons())}")
        print()
    print(summarise(report) if args.summary else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
