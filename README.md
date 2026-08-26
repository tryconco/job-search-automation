# Trycon Desk

A Claude Code project that turns a TradingView screenshot into one of three answers:
**TRADE**, **NO TRADE**, or **WAIT UNTIL `<time>`** — with reasons and proof.

Built for 0DTE SPY/QQQ options, **long calls and long puts only, never spreads**, in a paper
account, by an operator with a full-time job who checks in from his phone.

**A and B setups are both tradeable, separated by size:** A risks $350 (3.5R), B risks $100
(1.0R), 1R is always $100. Up to 5 trades a day; the desk closes at −4R. There is no conviction
score — the grade carries the judgement and the WHY/AGAINST lines carry the reasons.

```
screenshot ──► read it ──► verify against live bars ──► today's session context
                                                              │
        lessons ──► live market context ──► decision engine ──┤
                                                              ▼
                                            nine guards ──► verdict ──► ledger
```

---

## Read this before you trade anything

**No evidence has established that this method is profitable.**

The published research on intraday technical rules is discouraging. Large studies testing
thousands of trading rules have found none that survived correction for data snooping, and
short-horizon index moves tend to mean-revert rather than continue.

This system is built to apply a method **consistently** and to measure itself **honestly**, so
that the question can eventually be answered with evidence instead of feel. It is not built on
a proven edge and it must not be described as one.

It is paper trading. It places no orders, holds no credentials, and connects to no broker.

---

## Does it get better over time?

Yes, but not the way people usually mean, and the difference matters.

Anthropic improves Claude by retraining the model on enormous datasets with enormous compute.
**That is not something a repo can replicate, and this system does not do it. The model never
changes.**

What this system does instead is **evidence accumulation and rule evolution**:

1. Every call is logged — including the skips.
2. Every call is graded against what actually happened.
3. Patterns are measured across the graded record.
4. Patterns that clear a strict statistical bar are promoted into `lessons/LESSONS.md`, which
   is loaded on every subsequent call.
5. Rules that stop holding are demoted.

The model stays fixed; **the context it reasons over gets sharper.** That is how most production
AI systems actually improve, and it is the part that matters here. Nothing in this repo learns,
trains, or fine-tunes.

### The promotion bar

A pattern becomes a rule only when **all four** hold:

| Gate | Requirement |
|---|---|
| Sample | ≥ 30 graded calls in that bucket. Below that, luck and skill look identical. |
| Significance | 95% bootstrap CI on expectancy (2,000 resamples) excludes zero |
| Stability | Holds in **both halves** of the sample split by date |
| Falsifiability | Stated as a testable rule. "Longs below VWAP before 10:30 ET" is a rule. "Be careful in the morning" is not. |

Failures go to `lessons/candidates.md` and are rechecked weekly. Every promotion writes to
`lessons/CHANGELOG.md` with its sample size, effect and confidence interval — **no rule exists
without traceable evidence.** `LESSONS.md` is capped at 25 active rules; adding a 26th requires
demoting one.

Guards against the obvious failure modes: the 30-call minimum blocks overfitting; only graded
outcomes feed the loop, so opinion is never evidence; recent data is weighted more heavily but
old data is never dropped; and **skipped trades are graded too**, so the desk cannot quietly
learn to trade less and call that improvement.

---

## Layout

```
CLAUDE.md              operating instructions — the pipeline and the response contract
config.json            every tunable number — risk tiers, limits, the promotion bar

knowledge/             how CJ thinks
  _INDEX.md            ← START HERE. What each file governs, and where they contradict.
  00-persona.md        voice, the layer rules, forbidden claims
  01-decision-engine.md grades, sizing by grade, verdict selection
  02-trycon-mas.md     how to read his chart          (his file, verbatim)
  03-options-playbook.md price action and mechanics   (his file, verbatim + scope note)
  04-risk-rules.md     the nine guards, sizing, exits
  05-mistake-log.md    repeated failures — deliberately near-empty until earned
  06-mentor-engine.md  the teaching half              (his file, verbatim)
  07-journal-protocol.md result vocabulary and review (his file, verbatim + scope note)

sessions/              ONE file per trading day, rebuilt fresh each morning
ledger/                calls.csv (every call, permanent) · outcomes.csv · screenshots/
lessons/               LESSONS.md · CHANGELOG.md · candidates.md
tools/                 market · vision · session · engine · grade · distill · guards
tests/                 187 tests, no network
```

## Tools

| Module | Does |
|---|---|
| `market.py` | yfinance bars, the five Trycon MAs, ATR, VWAP, volume ratio, levels, the clock. Caches to `.cache/`. |
| `vision.py` | Structures for what was read off the image, with confidence, and the reconciliation against live bars. |
| `session.py` | Today's file: create, append, compress, carry forward. Plus the ledger. |
| `guards.py` | The nine hard vetoes. Pure functions, no I/O, tested at both sides of every boundary. |
| `engine.py` | Setup → grade → guards → sizing → verdict → rendered response. **Addition to the original scaffold** — see below. |
| `grade.py` | Walk-forward grading of resolved calls, including skips. |
| `distill.py` | The weekly learning pass and the promotion bar. |

`engine.py` is not in the original BUILD_PROMPT scaffold. It exists because Part 10 asks for
integration tests — *"chop produces NO TRADE and names the veto"*, *"missing data produces NO
TRADE, never a fabricated level"* — and none of those can be tested if the verdict only ever
exists as prose in a chat reply. The model handles perception and proposes a setup; the engine
grades, guards, sizes and renders it, so the honesty rules are enforced by something that cannot
be talked out of them.

## Running it

```bash
pip install -r requirements.txt

python3 tools/market.py SPY                    # live snapshot
python3 tools/session.py create                # today's session file
python3 tools/session.py state --date 2026-08-26
python3 tools/grade.py --date 2026-08-26 --summary
python3 tools/distill.py --verbose --summary   # prints its reasoning, not just conclusions
python3 -m pytest -q
```

## Automation

- `.github/workflows/grade.yml` — weekdays after the close. Grades the day, commits
  `outcomes.csv`, opens an issue summarising calls, outcomes and the running record.
- `.github/workflows/distill.yml` — Sundays. Runs the learning pass, commits any `LESSONS.md`
  and `CHANGELOG.md` changes, opens an issue explaining what changed and on what evidence. If
  nothing met the bar it says so — *"no rule changes this week, here's what's still
  accumulating"* is a valid and useful report.

Both use the built-in `GITHUB_TOKEN`. No secrets. GitHub's free scheduler fires late and
irregularly; neither job is time-critical, so that is fine.

---

## Known limitations

Stated plainly, because a system that hides these is worse than no system.

1. **No proven edge.** See the top of this file.
2. **yfinance intraday data is delayed and imperfect.** It is free, unofficial and can gap or
   return nothing. When it returns nothing the answer is `NO TRADE — no data`, never a guess.
3. **The option chain is best-effort.** yfinance option data is often stale. The desk will not
   quote you a fill it cannot see — it says to check your chain. A price chart cannot show a
   bid, ask, spread, delta or open interest.
4. **No market-holiday calendar.** There is no free one in this stack. On a holiday the clock
   says the market is open and the data fetch returns nothing, which lands on `NO TRADE — no
   data`. Blunt, but not dishonest.
5. **Grading is on the underlying, not the contract.** Contract P&L depends on fills and spreads
   this desk never sees. R multiples are underlying R.
6. **Ambiguous bars are recorded as losses.** When one bar touches both stop and target, bar
   data cannot reveal the order. Assuming the good fill is how a backtest lies, so the loss is
   recorded and the bar is flagged.
7. **Counterfactual skip grading is approximate.** It uses a synthetic stop and a 2R target to
   ask "what would that trade have done". It is a check on over-caution, not a P&L.
8. **The 200-period lines need 200 bars.** With less history they are flagged `warmup_ok=False`
   and must be reported as approximate rather than quoted as levels.
9. **Screenshot reading is done by the model, not by OCR.** Confidence is recorded per value,
   and an unreadable value is reported as unreadable — but a confident misread is still
   possible. This is exactly why no level ever comes from a pixel.
10. **Position size varies 3.5× between an A and a B** ($350 vs $100), at CJ's instruction. One
    A-grade loss erases three and a half B-grade wins, so on a method with no established edge
    this amplifies swings faster than returns. It is one config line to compress. Three smaller
    questions are still open — see the table in `knowledge/_INDEX.md`.

---

_Paper trading. Not financial advice. Nothing here predicts the market; it applies rules and
measures itself._
