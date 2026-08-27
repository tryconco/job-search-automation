"""Today's file, and the ledger.

**The daily reset.** Each trading day gets a fresh context holding that day's screenshots and
only that day's, so the desk never slows down as history accumulates (BUILD_PROMPT Part 5).
Yesterday is read exactly once, at the morning routine, to lift still-relevant levels. After
that it is never opened again.

Older days survive as rows in ``ledger/calls.csv`` and, where they taught something, as rules in
``lessons/LESSONS.md``. Nothing else from the past is ever loaded.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(ROOT, "sessions")
TEMPLATE = os.path.join(SESSIONS_DIR, "_template.md")
LEDGER_DIR = os.path.join(ROOT, "ledger")
CALLS_CSV = os.path.join(LEDGER_DIR, "calls.csv")
OUTCOMES_CSV = os.path.join(LEDGER_DIR, "outcomes.csv")

COMPRESS_WORD_LIMIT = 3000
KEEP_LAST_ENTRIES = 5

SCREENSHOT_HEADING = "## Screenshots"
COMPRESSED_HEADING = "### Compressed — earlier entries"

CALL_FIELDS = [
    "call_id", "timestamp_et", "timestamp_ct", "ticker", "interval", "verdict", "direction",
    "grade", "entry_low", "entry_high", "stop", "target1", "target2",
    "invalidation", "side", "strike", "est_premium", "contracts", "risk_usd", "risk_r",
    "guards_failed", "wait_until", "wait_condition", "screenshot", "notes", "graded",
]

OUTCOME_FIELDS = [
    "call_id", "graded_at", "outcome", "r_multiple", "minutes_to_resolution", "mfe_r", "mae_r",
    "ambiguous_bar", "rule_break", "bars_source", "notes",
]


# --------------------------------------------------------------------------------------
# paths and creation
# --------------------------------------------------------------------------------------

def today_et() -> date:
    return datetime.now(ET).date()


def session_path(day: Optional[date] = None, sessions_dir: str = SESSIONS_DIR) -> str:
    return os.path.join(sessions_dir, f"{day or today_et()}.md")


def session_exists(day: Optional[date] = None, sessions_dir: str = SESSIONS_DIR) -> bool:
    return os.path.exists(session_path(day, sessions_dir))


def _fill_risk_placeholders(body: str, config: Optional[dict] = None) -> str:
    """Fill the risk numbers from ``config.json`` rather than hardcoding them in the template.

    They were hardcoded once and silently went stale the moment CJ changed the limits, which is
    exactly the kind of drift that puts a wrong number in front of him at 08:32.
    """
    if config is None:
        with open(os.path.join(ROOT, "config.json")) as fh:
            config = json.load(fh)
    risk = config["risk"]
    unit = risk["unit_r_usd"]
    mult = risk["grade_risk_multiplier"]
    for token, value in (
        ("{UNIT_R}", f"{unit:g}"),
        ("{MAX_TRADES}", str(risk["max_trades_per_day"])),
        ("{LOSS_LIMIT}", f"{abs(risk['daily_loss_limit_r']):.2f}"),
        ("{A_RISK}", f"{min(unit * mult.get('A', 1.0), risk['max_risk_usd']):g}"),
        ("{B_RISK}", f"{min(unit * mult.get('B', 1.0), risk['max_risk_usd']):g}"),
    ):
        body = body.replace(token, value)
    return body


def create_session(
    day: Optional[date] = None,
    sessions_dir: str = SESSIONS_DIR,
    template_path: str = TEMPLATE,
    overwrite: bool = False,
) -> str:
    """Create today's file from the template. Never clobbers an existing day by accident."""
    day = day or today_et()
    path = session_path(day, sessions_dir)
    if os.path.exists(path) and not overwrite:
        return path
    with open(template_path) as fh:
        body = fh.read()
    body = body.replace("{DATE}", str(day)).replace("{WEEKDAY}", day.strftime("%A"))
    body = _fill_risk_placeholders(body)
    os.makedirs(sessions_dir, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(body)
    return path


# --------------------------------------------------------------------------------------
# entries
# --------------------------------------------------------------------------------------

def format_entry(
    when: datetime,
    number: int,
    price: float,
    ema9: float,
    ema21: float,
    ema50: float,
    ema200: float,
    vwap: float,
    atr: float,
    read: str,
    levels: str,
    call: str,
) -> str:
    """The compact block from BUILD_PROMPT Part 5. Target under 150 words.

    VWAP is printed as ``VWAP*`` because it is **computed, not on CJ's chart**
    (``_INDEX.md`` contradiction 3).
    """
    stamp = f"{when.astimezone(CT):%H:%M} CT / {when.astimezone(ET):%H:%M} ET"
    return (
        f"\n### {stamp} — screenshot {number}\n"
        f"Price {price:.2f} · 9:{ema9:.2f} 21:{ema21:.2f} 50:{ema50:.2f} 200:{ema200:.2f} · "
        f"VWAP* {vwap:.2f} · ATR {atr:.2f}\n"
        f"Read: {read}\n"
        f"Levels: {levels}\n"
        f"Call: {call}\n"
    )


def append_entry(
    text: str,
    day: Optional[date] = None,
    sessions_dir: str = SESSIONS_DIR,
    auto_compress: bool = True,
) -> str:
    """Append a screenshot block, then compress if the file has grown past the limit.

    Compression is a **sawtooth**, not a cap: when the file crosses the limit it folds down to
    the last five entries, then grows again until it next crosses. So the live entry count is
    only exactly five immediately after a fold.
    """
    day = day or today_et()
    path = session_path(day, sessions_dir)
    if not os.path.exists(path):
        create_session(day, sessions_dir)
    with open(path, "a") as fh:
        fh.write(text if text.startswith("\n") else "\n" + text)
    if auto_compress:
        maybe_compress(day, sessions_dir)
    return path


def entry_count(day: Optional[date] = None, sessions_dir: str = SESSIONS_DIR) -> int:
    path = session_path(day, sessions_dir)
    if not os.path.exists(path):
        return 0
    return len(re.findall(r"^### .*— screenshot \d+", open(path).read(), flags=re.M))


def word_count(day: Optional[date] = None, sessions_dir: str = SESSIONS_DIR) -> int:
    path = session_path(day, sessions_dir)
    if not os.path.exists(path):
        return 0
    return len(open(path).read().split())


# --------------------------------------------------------------------------------------
# compression
# --------------------------------------------------------------------------------------

def _split_entries(body: str) -> tuple[str, list[str]]:
    """Return (everything before the screenshot log, [entry blocks])."""
    idx = body.find(SCREENSHOT_HEADING)
    if idx == -1:
        return body, []
    head, tail = body[:idx], body[idx:]
    parts = re.split(r"(?=^### )", tail, flags=re.M)
    preamble = parts[0]
    entries = [p for p in parts[1:] if p.strip()]
    return head + preamble, entries


def maybe_compress(
    day: Optional[date] = None,
    sessions_dir: str = SESSIONS_DIR,
    word_limit: int = COMPRESS_WORD_LIMIT,
    keep_last: int = KEEP_LAST_ENTRIES,
) -> bool:
    """If the day file is over ~3,000 words, fold older entries into a summary block.

    The last ``keep_last`` screenshots stay in full. Compression keeps the **levels and the
    calls** from the folded entries, because those are the parts later screenshots refer back
    to; the narrative reads are what get dropped.
    """
    day = day or today_et()
    path = session_path(day, sessions_dir)
    if not os.path.exists(path):
        return False
    body = open(path).read()
    if len(body.split()) <= word_limit:
        return False

    head, entries = _split_entries(body)
    live = [e for e in entries if not e.startswith(COMPRESSED_HEADING)]
    already = [e for e in entries if e.startswith(COMPRESSED_HEADING)]
    if len(live) <= keep_last:
        return False

    fold, keep = live[:-keep_last], live[-keep_last:]
    lines = []
    for block in fold:
        title = block.splitlines()[0].replace("### ", "").strip()
        levels = re.search(r"^Levels:\s*(.+)$", block, flags=re.M)
        call = re.search(r"^Call:\s*(.+)$", block, flags=re.M)
        lines.append(
            f"- **{title}** — {call.group(1).strip() if call else 'no call recorded'}"
            f"{' · levels: ' + levels.group(1).strip() if levels else ''}"
        )

    prior = ""
    if already:
        prior = "\n".join(
            l for l in already[0].splitlines()[1:] if l.strip().startswith("-")
        )
        if prior:
            prior += "\n"

    summary = (
        f"{COMPRESSED_HEADING}\n\n"
        f"_{len(fold) + len(already and prior.splitlines() or [])} earlier screenshots, "
        f"folded. Levels and calls kept, narrative dropped._\n\n"
        + prior + "\n".join(lines) + "\n"
    )
    with open(path, "w") as fh:
        fh.write(head + summary + "\n" + "".join(keep))
    return True


# --------------------------------------------------------------------------------------
# carry-forward
# --------------------------------------------------------------------------------------

def carry_forward_levels(
    prev_day: date, sessions_dir: str = SESSIONS_DIR, max_levels: int = 8
) -> list[str]:
    """Lift still-relevant levels out of yesterday's file. **Called exactly once**, at the
    morning routine.

    Returns an empty list when yesterday has no file — a missing day is not an error, it is a
    day CJ did not trade.
    """
    path = session_path(prev_day, sessions_dir)
    if not os.path.exists(path):
        return []
    body = open(path).read()
    found: list[str] = []
    for match in re.findall(r"^Levels:\s*(.+)$", body, flags=re.M):
        for piece in re.split(r"[.;]\s+", match.strip()):
            piece = piece.strip().rstrip(".")
            if piece and piece not in found:
                found.append(piece)
    return found[-max_levels:]


def previous_trading_day(day: date) -> date:
    """Previous weekday. Holidays are not known -- that day's file simply will not exist."""
    d = day - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


# --------------------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------------------

def _ensure_csv(path: str, fields: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as fh:
            csv.DictWriter(fh, fieldnames=fields).writeheader()


def make_call_id(when: datetime, ticker: str) -> str:
    return f"{when.astimezone(ET):%Y%m%d-%H%M%S}-{ticker.upper()}"


def append_call(row: dict, path: str = CALLS_CSV) -> str:
    """Append one call. **Every** call is logged -- TRADE, NO TRADE and WAIT alike.

    The skipped trades are training data too. A desk that only logs its trades can never learn
    that it skips too much (BUILD_PROMPT Part 3, Step 8).
    """
    _ensure_csv(path, CALL_FIELDS)
    clean = {k: row.get(k, "") for k in CALL_FIELDS}
    if not clean["call_id"]:
        raise ValueError("call_id is required")
    if clean["verdict"] not in {"TRADE", "NO TRADE", "WAIT"}:
        raise ValueError(f"verdict must be TRADE, NO TRADE or WAIT, got {clean['verdict']!r}")
    clean.setdefault("graded", "")
    if clean["graded"] == "":
        clean["graded"] = "no"
    with open(path, "a", newline="") as fh:
        csv.DictWriter(fh, fieldnames=CALL_FIELDS).writerow(clean)
    return clean["call_id"]


def read_calls(path: str = CALLS_CSV) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def append_outcome(row: dict, path: str = OUTCOMES_CSV) -> None:
    _ensure_csv(path, OUTCOME_FIELDS)
    clean = {k: row.get(k, "") for k in OUTCOME_FIELDS}
    with open(path, "a", newline="") as fh:
        csv.DictWriter(fh, fieldnames=OUTCOME_FIELDS).writerow(clean)


def read_outcomes(path: str = OUTCOMES_CSV) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def mark_graded(call_ids: set[str], path: str = CALLS_CSV) -> int:
    rows = read_calls(path)
    n = 0
    for r in rows:
        if r["call_id"] in call_ids and r.get("graded") != "yes":
            r["graded"] = "yes"
            n += 1
    if n:
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CALL_FIELDS)
            w.writeheader()
            w.writerows(rows)
    return n


def calls_for_day(day: date, path: str = CALLS_CSV) -> list[dict]:
    return [r for r in read_calls(path) if r["timestamp_et"].startswith(str(day))]


def day_state(day: date, calls_path: str = CALLS_CSV, outcomes_path: str = OUTCOMES_CSV) -> dict:
    """Trades taken, P&L in R and time since the last loss -- the inputs guards 4, 5 and 6 need."""
    calls = calls_for_day(day, calls_path)
    taken = [c for c in calls if c["verdict"] == "TRADE"]
    by_id = {o["call_id"]: o for o in read_outcomes(outcomes_path)}

    pnl, last_loss_at = 0.0, None
    for c in taken:
        o = by_id.get(c["call_id"])
        if not o or not o.get("r_multiple"):
            continue
        try:
            r = float(o["r_multiple"])
        except ValueError:
            continue
        pnl += r
        if r < 0:
            stamp = datetime.fromisoformat(c["timestamp_et"])
            if last_loss_at is None or stamp > last_loss_at:
                last_loss_at = stamp
    return {
        "day": str(day),
        "trades_today": len(taken),
        "calls_today": len(calls),
        "day_pnl_r": round(pnl, 4),
        "last_loss_at": last_loss_at.isoformat() if last_loss_at else None,
    }


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Session file and ledger helpers.")
    ap.add_argument("command", choices=["create", "state", "carry", "count"])
    ap.add_argument("--date", default=str(today_et()))
    args = ap.parse_args()
    day = date.fromisoformat(args.date)

    if args.command == "create":
        print(create_session(day))
    elif args.command == "state":
        print(json.dumps(day_state(day), indent=2))
    elif args.command == "carry":
        print(json.dumps(carry_forward_levels(previous_trading_day(day)), indent=2))
    else:
        print(json.dumps({"entries": entry_count(day), "words": word_count(day)}, indent=2))
