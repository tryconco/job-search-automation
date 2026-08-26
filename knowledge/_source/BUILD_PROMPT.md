# BUILD PROMPT — Trycon Desk

**How to use this:** open a Claude Code session pointed at a new empty private
repo, paste this entire document as your first message, and let it work. It is
written to be handed to an AI agent, not read as documentation.

---

## PART 0 — WHAT YOU ARE BUILDING AND WHO FOR

You are building **Trycon Desk**: a Claude Code project that lives in a git
repo. Its operator is Josh (CJ), a Houston-based trader who day-trades **0DTE
SPY/QQQ options — long calls and puts only, never spreads** — in a paper
account, while working a full-time job.

The interaction is one thing, repeated:

> CJ sends a screenshot of his TradingView chart. He gets back a decision:
> **TRADE**, **NO TRADE**, or **WAIT UNTIL <time>**. With reasons and proof.
> When it's TRADE, he gets a complete plan he can execute in under a minute.

Everything else in this build exists to make that one response better.

### Hard constraints — do not negotiate these away

1. **CJ places every trade by hand.** This system never routes an order,
   never connects to a broker, never holds credentials. It produces a call.
2. **No paid APIs, no API keys.** Price data comes from `yfinance` (free, no
   account, no key). News and event context come from web search. If a data
   source needs a key, don't use it.
3. **This is paper trading.** Every output carries that framing. The system
   must never imply a guaranteed outcome.
4. **Phone-first.** CJ reads every response on an iPhone. Responses must be
   short, scannable, and lead with the verdict.
5. **The screenshot is context, not measurement.** See Part 3, Step 2 — this
   is the single most important design rule in the build.

---

## PART 1 — REPO SCAFFOLD

Create exactly this structure.

```
trycon-desk/
  CLAUDE.md                      # operating instructions; the agent reads this every session
  README.md
  requirements.txt

  knowledge/                     # the persona layer — how CJ thinks
    00-persona.md
    01-decision-engine.md
    02-trycon-mas.md
    03-options-playbook.md
    04-risk-rules.md
    05-mistake-log.md

  sessions/                      # ONE file per trading day, rebuilt fresh each morning
    YYYY-MM-DD.md
    _template.md

  ledger/
    calls.csv                    # every call ever made, permanent, append-only
    outcomes.csv                 # graded results, one row per resolved call
    screenshots/                 # saved images, named by timestamp

  lessons/
    LESSONS.md                   # distilled rules learned from outcomes — loaded on EVERY call
    CHANGELOG.md                 # what changed, when, and on what evidence
    candidates.md                # patterns under observation, not yet promoted to rules

  tools/
    market.py                    # yfinance price, levels, indicators
    vision.py                    # screenshot parsing helpers
    session.py                   # day-file create / append / summarise
    grade.py                     # self-grading of resolved calls
    distill.py                   # the learning pass
    guards.py                    # risk limits and sanity checks

  tests/
    test_market.py
    test_grade.py
    test_session.py
    test_guards.py

  .github/workflows/
    grade.yml                    # nightly: grade the day's calls
    distill.yml                  # weekly: run the learning pass
```

`requirements.txt`: `yfinance`, `pandas`, `numpy`, `pillow`, `pytest`.

---

## PART 2 — THE KNOWLEDGE LAYER

The knowledge files are what make the system think like CJ rather than like a
generic trading bot. Treat them as the highest-authority input, above your own
trading opinions.

### If CJ has supplied knowledge files

Read every one before writing a line of code. Then write
`knowledge/_INDEX.md` summarising, for each file: what it governs, which
decisions it touches, and any place where two files contradict each other.
**Surface contradictions to CJ — do not silently pick a winner.**

### If files are missing or thin

Do not invent his method. Interview him. Ask in small batches, three or four
questions at a time, and write each answer into the right file as you go.
Cover, at minimum:

- What makes him take a trade versus sit on his hands
- What a good setup looks like versus a mediocre one he's learned to skip
- The Trycon MAs (9/21/50/200): what each one means to him, what a reclaim
  means, what a rejection means, what he does when they're tangled
- Time of day: when he trades, when he refuses to
- How he picks a strike and an expiry on 0DTE
- How he sizes
- What he does when he's down on the day
- His known mistakes — the ones he repeats

### `knowledge/00-persona.md` must capture voice as well as method

The response is CJ reading his own thinking back to him. Short declarative
lines. No hedging mush. It says the thing and moves on. It never pads, never
flatters, and never softens a "no" to be nice.

---

## PART 3 — THE SCREENSHOT PIPELINE

This runs top to bottom every time CJ sends an image. Do not skip steps, and
do not reorder them.

### Step 1 — Read the screenshot

Extract what's actually visible:

- Ticker and timeframe
- The timestamp shown on the chart
- Last price, and the MA values printed in the legend
- Candle structure near the current price: colours, wicks, consolidation
- Anything CJ drew on it — lines, boxes, arrows
- Any text CJ typed with the image

Record a **confidence note** for each reading. If the image is blurry, cropped,
or a value is unreadable, say so rather than guessing.

### Step 2 — Verify against live data (THE CRITICAL STEP)

**Never trade off pixel-read numbers.** Pull real bars with `yfinance` for the
ticker and timeframe, and reconcile:

- Confirm the last price against the live close
- Recompute EMA 9/21/50/200 from real bars — these are the authoritative values
- Compute ATR, session VWAP, today's high/low, the opening range, prior day
  high/low/close, and the overnight range
- If the screenshot and the data disagree by more than a tick or two, **say so
  in the response and trust the data.** Common cause: the screenshot is stale.

The screenshot answers *what CJ is looking at and when*. The data answers
*what is actually true*. Keep that division absolutely clean.

If `yfinance` returns nothing (weekend, outage, bad ticker), say so plainly and
return **NO TRADE — no data**. Never fabricate levels.

### Step 3 — Load today's session context

Read `sessions/<today>.md`. It holds everything from today only:

- Every prior screenshot today, compressed to a few lines each
- Levels already identified and whether they've held or broken
- Calls already made today, and their status
- Current running bias and why
- Trades taken, P&L in R, and remaining risk budget

If the file doesn't exist, create it from `_template.md` and run the
**morning routine** (Part 5).

### Step 4 — Load the lessons layer

Read `lessons/LESSONS.md` in full. These are rules earned from graded
outcomes, and they **override** generic trading logic. If a lesson says "long
setups between 12:00 and 13:30 ET have lost across 41 graded calls," that
lesson wins over a textbook-perfect chart.

### Step 5 — Pull live market context

Web search for what's moving right now. Cache results in the session file with
a timestamp; re-search only if the cache is older than 30 minutes or CJ asks.

Look for:

- Breaking news on SPY/QQQ, the broad market, or mega-cap names that drag the index
- Today's economic calendar and the exact release times — CPI, PPI, PCE, jobs,
  FOMC, Fed speakers, Treasury auctions
- Whether a scheduled release is imminent (inside 30 minutes)
- Anything unusual: a gap, a halt, a VIX spike, an index rebalance

**Event proximity is a first-class input.** A perfect chart 8 minutes before
CPI is a NO TRADE, and the response must say that's why.

### Step 6 — Run the decision engine

Apply `knowledge/01-decision-engine.md` against everything gathered. Produce:

- A directional read, with the specific evidence behind it
- A setup grade: **A / B / C**
- An explicit list of what supports the trade and what argues against it
- A **conviction score** and the reason for it

Then apply `tools/guards.py`. The guards can veto anything, including an A
setup. See Part 7.

### Step 7 — Decide

Exactly one of three verdicts:

**TRADE** — the setup clears the engine and every guard.

**NO TRADE** — it doesn't, and it isn't going to soon. Say precisely what's
missing.

**WAIT UNTIL `<time>`** — it doesn't clear *yet*, but there's a specific,
nameable reason it might later. You must state:
  - The exact time to send the next screenshot
  - What specifically to look for at that time
  - What would make it a yes, and what would kill it

`WAIT` is the verdict CJ most needs and the one a lazy system never gives. Use
it whenever there's a real reason to check back — an approaching level, an
event about to clear, a range about to resolve. Never use it as a hedge to
avoid committing.

### Step 8 — Log everything

Append to `ledger/calls.csv`, update `sessions/<today>.md`, and save the image
to `ledger/screenshots/`. Every call must be logged — including NO TRADE and
WAIT. **The skipped trades are training data too**, and a system that only
logs its trades can never learn that it skips too much.

---

## PART 4 — THE RESPONSE CONTRACT

This is the product. Get it wrong and nothing else matters.

**Rules:** verdict first, always. Phone-readable. Every number exact. Every
claim backed by something checkable. No preamble, no throat-clearing, no
"great chart!" Never bury the answer.

### TRADE

```
TRADE — LONG SPY  ·  Grade B  ·  conviction 68

WHY
· Reclaimed 21 EMA at 766.40 and held it two closes
· Volume on the reclaim candle 1.6x the 20-bar average
· Above session VWAP (765.90) since 10:15
· No scheduled event until 14:00 ET

AGAINST
· 50 EMA overhead at 767.30 is the first real resistance
· Midday tape — lessons file shows 11:30-13:30 wins less

THE TRADE
Underlying entry   766.40 – 766.60
Stop (underlying)  765.70        risk 0.75
Target 1           767.30        take 50%
Target 2           768.10        runner
Invalidation       any 5m close below 765.70

CONTRACT
SPY 0DTE 767C  ·  ~$0.95  ·  1 contract  ·  risk $95
Cut the contract at ~$0.55 (underlying at your stop)
Scale at ~$1.45 (underlying at T1)

EXIT DISCIPLINE
· Hard flat by 15:30 ET regardless — 0DTE theta after that is a coin flip
· If it hasn't moved 0.3 in 20 minutes, close it. Dead trade, live theta.

Paper trade. Not advice.
```

### NO TRADE

```
NO TRADE — SPY

WHY NOT
· EMAs tangled: 9 at 766.21, 21 at 766.18, 50 at 766.30 — inside 0.12
  That's chop, not a trend. Your rules say sit out.
· Volume 0.7x average. Nobody's committing.
· CPI at 08:30 tomorrow has the tape in a holding pattern.

WHAT WOULD CHANGE IT
A 5m close above 767.00 on 1.3x volume with the 9 clearing the 21.

Nothing here. Wait for the setup.
```

### WAIT

```
WAIT — send me a screenshot at 10:45 ET

WHY
Price is grinding into 767.30, where the 50 EMA and yesterday's high stack up.
That level decides the session. Right now it's still 0.40 away and volume is
thin — entering here is paying to find out.

AT 10:45 I NEED TO SEE
· Whether 767.30 broke or rejected
· Volume on that candle
· Where the 9 and 21 sit after it

IF IT BREAKS with volume, that's a long and I'll size it.
IF IT REJECTS with a wick, that's a short back toward VWAP at 765.90.
```

Adapt wording to CJ's voice from the persona file. Keep the skeleton.

---

## PART 5 — SESSION CONTEXT (THE DAILY RESET)

**Requirement, stated by CJ:** each trading day gets a fresh context of that
day's screenshots and only that day's, so the system never slows down as
history accumulates.

### Morning routine — first interaction of each trading day

1. Create `sessions/<today>.md` from the template
2. Pull the overnight picture: futures direction, gap size, overnight high/low
3. Pull prior day high / low / close
4. Web-search today's economic calendar; write every release with its exact
   time
5. Read `lessons/LESSONS.md` and note any lessons that apply to today's shape
6. Read yesterday's session file **once**, extract only still-relevant levels,
   and write those into today's file. Then never read yesterday again.
7. Write an opening bias: direction lean, key levels, and what would change it

### On every subsequent screenshot

Append a compact block — target under 150 words:

```
### 11:20 ET — screenshot 4
Price 766.55 · 9:766.4 21:766.2 50:766.8 200:764.1 · VWAP 765.9 · ATR 0.48
Read: reclaimed 21, holding. Volume 1.4x.
Levels: 767.30 still untested resistance. 765.70 support held twice.
Call: WAIT until 11:45 — needs to clear 767.30 on volume.
```

### Why this stays fast

Only today's file loads into context. Older days compress into
`ledger/calls.csv` rows and, where they taught something, into
`lessons/LESSONS.md`. Nothing else from the past is ever loaded.

If today's file exceeds roughly 3,000 words, compress the older entries in it
into a summary block and keep the last five screenshots in full.

---

## PART 6 — THE LEARNING LOOP

CJ asked for something that gets better over time "like AI models do." Build
the honest version of that, and be straight with him about what it is.

### Say this plainly in the README

Anthropic improves Claude by retraining the model on enormous datasets with
enormous compute. **That is not something a repo can replicate, and this system
does not do it.** The model itself never changes.

What this system does instead is **evidence accumulation and rule evolution**:
it records every call and its outcome, measures which patterns actually work,
and rewrites its own operating rules from that evidence. The model stays fixed;
the context it reasons over gets sharper. That is how most production AI
systems actually improve, and it's the part that matters here.

Do not let the README or any response imply the model is learning or training.

### 6a. Self-grading (`tools/grade.py`)

Runs nightly, and on demand.

For every call in `calls.csv` not yet graded:

- Pull 1-minute bars for that day with `yfinance`
- Walk forward from the call timestamp to the session close
- Determine what happened **first**: stop or target
- **If a single bar touched both, record it as a loss.** Bar data does not
  reveal which came first, and assuming the good fill is how a backtest lies.
- Record: outcome, R multiple on the underlying, time to resolution, max
  favourable excursion, max adverse excursion

Grade the skips too:
- For a **NO TRADE**, compute what the trade *would* have done had it been
  taken in the obvious direction. This is how the system learns whether it's
  too cautious.
- For a **WAIT**, check whether the named condition actually occurred.

Write everything to `outcomes.csv`.

### 6b. The distillation pass (`tools/distill.py`)

Runs weekly. This is where rules change — and where the guardrails live,
because a learning loop without them just curve-fits to noise.

Analyse `outcomes.csv` across: setup grade, time of day, direction, MA
configuration, volume regime, ATR regime, day of week, event proximity.

**Promotion rules — all must hold before a pattern becomes a rule:**

1. **At least 30 graded calls** in that bucket. Below that, luck and skill look
   identical.
2. The effect survives a bootstrap: resample the bucket 2,000 times, and the
   95% confidence interval on expectancy must not contain zero.
3. It holds in **both halves** of the sample split by date. A pattern that only
   worked in one stretch is not a pattern.
4. It is stated as a **falsifiable rule**, not a vibe. "Longs below VWAP before
   10:30 ET" is a rule. "Be careful in the morning" is not.

Anything that fails goes to `lessons/candidates.md` with its current sample
size, and gets rechecked next week. Nothing gets promoted early because it
looks promising.

**Every promotion writes to `CHANGELOG.md`:** the rule, the date, the sample
size, the measured effect, the confidence interval. Every rule must be
traceable to the evidence that created it.

**Demotion matters as much as promotion.** Re-test existing rules every pass.
If a rule stops holding, mark it deprecated with the date and reason. Never
silently delete one — CJ needs to see when the market changed.

### 6c. Guarding against the failure modes

- **Overfitting**: enforce the 30-call minimum ruthlessly. Cap `LESSONS.md` at
  25 active rules; to add the 26th, something must be demoted.
- **Feedback poisoning**: only graded outcomes feed the loop. CJ's opinion
  about a trade never becomes evidence.
- **Drift**: weight the last 90 days more heavily than older data, but never
  drop the old data — you need it for the both-halves test.
- **Survivorship**: skipped trades are graded too. A system that only sees its
  own trades will happily learn to trade less and call it improvement.

---

## PART 7 — RISK RULES (`tools/guards.py`)

0DTE options are the most unforgiving instrument a retail trader touches. Value
goes to zero on a schedule. These are hard vetoes, checked on every call,
overriding any setup grade.

Implement each as a function returning `(passed: bool, reason: str)`:

1. **Time cutoff** — no new 0DTE entries after **15:00 ET**. Hard flat by
   **15:30 ET**. Theta in the last half hour is not a trade, it's a raffle.
2. **Opening lockout** — no entries in the first 15 minutes. The open is noise.
3. **Event lockout** — no entry within 15 minutes before or 10 minutes after a
   scheduled release (CPI, PPI, PCE, jobs, FOMC, Fed speakers).
4. **Daily loss limit** — after **−2R** on the day, the system stops calling
   trades and says so. This one is not overridable. Ask CJ to confirm the
   number during setup.
5. **Max trades per day** — default 3. Overtrading is the most common way a
   good method loses money.
6. **Cooldown** — no new call within 15 minutes of a loss. Revenge trading is
   the second most common way.
7. **Minimum stop distance** — reject any setup whose stop is tighter than
   **1.5× the average 5-minute bar range**. A stop inside bar noise is not a
   stop; it's a random exit, and it also makes the trade impossible to grade
   honestly.
8. **Liquidity check** — reject strikes with a wide spread relative to premium.
9. **Chop veto** — if the 9/21/50 EMAs sit within a configurable ATR fraction
   of each other, no trade in either direction.

When a guard vetoes, the response names the guard. CJ should always know
exactly what stopped it.

---

## PART 8 — THE TOOLS

Each is a plain Python module, importable and independently testable.

**`tools/market.py`**
`get_bars(ticker, interval, lookback)` · `get_indicators(df)` returning EMA
9/21/50/200, ATR, VWAP, volume ratio, bar-range sigma · `get_levels(ticker)`
returning prior day H/L/C, overnight H/L, opening range, session H/L ·
`get_option_chain(ticker)` — 0DTE strikes near the money, best effort from
yfinance, with a clear failure mode when unavailable · `is_market_open()`,
`minutes_until_close()`.

Cache every pull to `.cache/` with a timestamp so repeated calls in one session
don't re-fetch.

**`tools/vision.py`** — helpers for recording what was read from the image, the
confidence in each reading, and the reconciliation result against live data.
Structured output, not prose.

**`tools/session.py`** — create today's file, append an entry, compress when
long, extract carry-forward levels from yesterday exactly once.

**`tools/grade.py`** — as specified in 6a. Must be runnable standalone:
`python3 tools/grade.py --date 2026-08-22`.

**`tools/distill.py`** — as specified in 6b. Must print its reasoning, not just
its conclusions, so CJ can audit why a rule changed.

**`tools/guards.py`** — as specified in Part 7. Pure functions, no I/O, fully
unit-tested.

---

## PART 9 — AUTOMATION

**`.github/workflows/grade.yml`** — weekdays at 17:00 ET. Runs `grade.py` for
the day, commits `outcomes.csv` and an updated session file. Opens a GitHub
issue summarising the day: calls made, outcomes, running record.

**`.github/workflows/distill.yml`** — Sundays. Runs `distill.py`, commits any
`LESSONS.md` and `CHANGELOG.md` changes, and opens an issue explaining what
changed and on what evidence. If nothing met the promotion bar, it says so —
"no rule changes this week, here's what's still accumulating" is a valid and
useful report.

Both use the built-in `GITHUB_TOKEN`. No secrets required.

Note in the README that GitHub's free scheduler fires late and irregularly, and
that neither of these jobs is time-critical, so that's fine.

---

## PART 10 — TESTS AND ACCEPTANCE

Do not report this build complete until all of the following pass.

**Unit tests**
- Indicators match hand-computed values on a small fixture
- Every guard fires correctly at its boundary, on both sides
- A bar touching both stop and target grades as a **loss**
- Session files create, append, and compress correctly
- The distillation pass refuses to promote a rule at n=29 and promotes the same
  rule at n=31 with the same effect size

**Integration tests**
- A fabricated screenshot plus fixture data produces a well-formed TRADE
- Chop conditions produce NO TRADE, and the response names the chop veto
- An approaching level produces WAIT with a specific time
- Missing price data produces NO TRADE, never a fabricated level
- Being past 15:00 ET vetoes a textbook-perfect A setup

**Honesty tests — these matter most**
- No response ever states a level that didn't come from live data
- Every response distinguishes what was read from the image versus computed
  from data
- Grading never assumes the favourable fill on an ambiguous bar
- No rule enters `LESSONS.md` without a `CHANGELOG.md` entry naming its
  evidence
- No output implies a guaranteed or likely-profitable outcome

---

## PART 11 — BUILD ORDER

Build in this sequence. Get each stage working before starting the next.

1. Scaffold, `requirements.txt`, empty knowledge files
2. Read CJ's knowledge files; interview him for whatever's missing; write
   `_INDEX.md` and surface contradictions
3. `market.py` with tests — nothing works without correct data
4. `guards.py` with tests — safety before capability
5. `session.py` and the daily flow
6. `CLAUDE.md`: the full pipeline and response contract
7. End-to-end on a real screenshot from CJ; iterate on the response until he
   says it sounds like him
8. `grade.py` and the nightly workflow
9. `distill.py` and the weekly workflow
10. Full test suite, README, and an honest limitations section

At stage 7, **stop and get CJ's reaction before continuing.** The response is
the product; if the voice is wrong, everything after that is wasted work.

---

## APPENDIX — WHAT NOT TO DO

- Do not read exact prices off pixels and trade them. Reconcile against data.
- Do not produce a TRADE just because a screenshot arrived. Most screenshots
  should return NO TRADE or WAIT. A system that always finds a trade is
  useless — it's just an expensive way to agree with whatever CJ already
  wanted to do.
- Do not hedge. "Could go either way" is not a call. Commit or say no.
- Do not soften a NO TRADE to be encouraging.
- Do not let `LESSONS.md` grow into a swamp. 25 rules maximum.
- Do not promote a rule on a small sample because it looks good.
- Do not claim the system predicts the market. It applies rules and measures
  itself.
- Do not add a data source that needs a paid key.
- Do not write anything that would embarrass CJ if a client read it.

---

## A NOTE TO PUT IN THE README

State plainly: **no evidence has established that this method is profitable.**
The published research on intraday technical rules is discouraging — large
studies testing thousands of rules found none that survived correction for
data snooping, and short-horizon index moves tend to mean-revert rather than
continue. This system is built to apply a method consistently and to measure
itself honestly, so that the question can be answered with evidence instead of
feel. It is not built on a proven edge, and it should not be described as one.
