# KNOWLEDGE INDEX

What each file governs, which decisions it touches, and — most importantly — **where two files
contradict each other**. Per BUILD_PROMPT Part 2, contradictions are surfaced, not silently
resolved. Where the build had to pick something to be able to run, the pick is stated, the
reason is given, and the switch to flip is named.

Read this file before changing any knowledge file.

---

## The files

| File | Origin | Governs | Touches |
|---|---|---|---|
| `00-persona.md` | **Derived** from `06` Voice + BUILD_PROMPT Part 2 | Voice, the three layers, forbidden claims | Every response |
| `01-decision-engine.md` | **Derived** from `02`, `03` §2/§4, `06` | Grades, conviction rubric, verdict selection | Step 6 of the pipeline |
| `02-trycon-mas.md` | **CJ, verbatim** | How to read the TradingView chart and the five MAs | Steps 1, 2, 6 |
| `03-options-playbook.md` | **CJ, verbatim** + scope preamble | Price action, checklist, contract mechanics | Steps 1, 6, 7 |
| `04-risk-rules.md` | **Derived** from BUILD_PROMPT Part 7 + `03` risk rules | The nine guards, sizing, exits | `tools/guards.py` |
| `05-mistake-log.md` | **Derived**, deliberately near-empty | Repeated failures and the rules they earned | Weekly review |
| `06-mentor-engine.md` | **CJ, verbatim** | The teaching half of the response | Every response |
| `07-journal-protocol.md` | **CJ, verbatim** + scope preamble | Result vocabulary, review questions | `grade.py`, review |
| `_source/BUILD_PROMPT.md` | **CJ, verbatim** | The build specification itself | Everything |

"Derived" means the build wrote it from CJ's material. Every derived claim should be traceable
to a source file. If you find one that is not, it is a bug — flag it.

---

## CONTRADICTIONS — CJ must rule on these

### 1. Central time vs Eastern time  ·  `02` vs BUILD_PROMPT  ·  **cosmetic, resolved**

- `02-trycon-mas.md`: *"Judge the session in Central, never convert to Eastern."*
- BUILD_PROMPT Parts 3–7: every time is ET (15:00 ET cutoff, 15:30 flat, "WAIT until 10:45 ET").

**Build's resolution.** The engine computes in **ET** — the options market, the economic
calendar, and the guards all run on it, and translating them invites an off-by-an-hour bug that
would silently break guard 1. Every time CJ *reads* is printed **Central first, ET second**:
`10:45 CT / 11:45 ET`. Nothing is lost and his stated preference governs the display.

**Risk if wrong:** none material. Cosmetic only.

---

### 2. Screenshot authority vs live data authority  ·  `02` vs BUILD_PROMPT  ·  **substantive, resolved by splitting**

- `02-trycon-mas.md`: *"The screenshot is the freshest price available to this desk. Public web
  quotes run about fifteen minutes behind. Never let a web quote overrule what the chart shows."*
- BUILD_PROMPT Step 2: *"Never trade off pixel-read numbers… If the screenshot and the data
  disagree, say so in the response and trust the data."*

These look opposed. They are not, once you separate **price now** from **levels**.

**Build's resolution — the split:**

| Question | Authority | Why |
|---|---|---|
| What price is it right now? | **The screenshot** | yfinance intraday is delayed; CJ's chart is live |
| Where is the 21 EMA? ATR? Prior day high? Opening range? VWAP? | **Live bars, always** | Pixel-read values are not levels. This is a hard honesty rule. |
| Is the screenshot stale? | **Live bars** | Reconcile against *closed* bars only |

So: **no level ever comes from a pixel.** The screenshot places CJ on a map the data drew.

**The reconciliation rule.** Compare the screenshot's price against the live bar covering the
screenshot's own timestamp — not against the newest bar. If they disagree by more than a tick or
two on a *closed* bar, the screenshot is stale: say so and ask for a fresh one. If the screenshot
is simply *newer* than the last available bar, that is data lag, not staleness — note it, use the
screenshot price for the trigger, and keep using data for every level.

**If yfinance returns nothing** — weekend, outage, bad ticker — the verdict is **NO TRADE — no
data**. Never fabricate a level. This one has no override.

---

### 3. VWAP  ·  `02` vs BUILD_PROMPT  ·  **substantive, resolved**

- `02-trycon-mas.md`: *"This chart has no VWAP, so the fast pair is the dynamic intraday
  reference in its place."*
- BUILD_PROMPT: VWAP appears in the level set and in two of the three sample responses
  ("Above session VWAP (765.90) since 10:15").

**Build's resolution.** VWAP **is** computed — it is legitimate data and it costs nothing. But:

1. The **fast pair (EMA 9/21) stays the primary dynamic reference** in the decision engine, per
   CJ's file. VWAP is secondary confirmation only, and cannot by itself make or break a grade.
2. Any mention of VWAP is labelled **computed, not on your chart**, per the three-layer rule.
   The mentor read may never point at VWAP as visible evidence, because it is not visible.

**Open:** if CJ adds VWAP to his TradingView layout, promote it and update `02`.

---

### 4. Conviction score vs "no confidence percentage"  ·  `06` vs BUILD_PROMPT  ·  **substantive, resolved**

- `06-mentor-engine.md`: *"No confidence percentage. Do not say a setup is seventy percent
  likely."*
- BUILD_PROMPT Part 4: the sample TRADE header reads `conviction 68`.

**Build's resolution.** Keep the number, strip the probability reading. Conviction is a
**rubric tally out of 100** with its six components printed (`01-decision-engine.md` Step G), so
it is auditable arithmetic, not a forecast. It is never phrased as a likelihood, and the header
prints `conviction 68/100 (rubric)` so the word cannot be mistaken for a percentage chance.

**Risk if wrong:** if CJ reads it as a probability anyway, the rule in `06` has been violated in
effect even though the letter is satisfied. Say the word if you want it removed entirely.

---

### 5. Is a Grade B tradeable?  ·  `06` vs BUILD_PROMPT  ·  **SUBSTANTIVE, UNRESOLVED — needs CJ**

- `06-mentor-engine.md` closing lines: *"Actionable A"* … *"Everything else, B, C, premarket,
  closed → No setup, no trade. Patience is the position."* That reads as **A-only**.
- BUILD_PROMPT Part 4: the canonical TRADE example is **Grade B**, conviction 68.

**This is the one contradiction that materially changes how often the desk trades**, so the
build did not bury a choice inside prose. It is a flag:

```json
"grading": { "b_grade_tradeable": true, "b_grade_size_fraction": 0.5, "b_grade_min_conviction": 60 }
```

Current setting trades B at **half size** with conviction ≥ 60. Set `b_grade_tradeable` to
`false` for strict A-only. **CJ should decide this, not the build.**

---

### 6. Four moving averages vs five  ·  `02` vs BUILD_PROMPT  ·  **minor, resolved**

BUILD_PROMPT says EMA 9/21/50/200. The actual Trycon MAs indicator prints **five** lines —
EMA 9, 21, 50, 200 **and SMA 200** — and `02` treats the EMA 200 / SMA 200 pair as one "heavy
zone". All five are computed. The heavy zone is read as a zone, not two lines.

---

### 7. Long options only vs a spread-heavy knowledge base  ·  `03` vs BUILD_PROMPT  ·  **resolved by scoping**

BUILD_PROMPT Part 0: *"long calls and puts only, never spreads."* But `03-options-playbook.md`
is largely about broken wing butterflies, credit spreads, the Batman trade, and the wheel.

**Build's resolution**, stated as a preamble inside `03` itself: Sections 2 and 4 are the
operative execution layer; Sections 1 and 3 are **reference only** and may answer a question but
may never produce a call. Structure-agnostic principles from Section 1 — expectancy, defined
risk, theta, delta, liquidity, no revenge trading, sizing — do carry over to long single-leg
options.

**If this desk ever emits a spread, it is broken.** There is a test for it.

---

### 8. Manual journal loop vs automatic ledger  ·  `07` vs BUILD_PROMPT  ·  **resolved by CJ's own file**

`07-journal-protocol.md` describes a copy-paste loop and says so explicitly: *"In the Claude
Code version this file wrote itself. In a Project it cannot."* This **is** the Claude Code
version, so `ledger/calls.csv` and `ledger/outcomes.csv` supersede the paste loop.

What is **kept** from `07`, because the build prompt has no equivalent and it is better:

- The **Result vocabulary**, including `taken, broke rules` — the flag BUILD_PROMPT omits and
  the most diagnostic value in the set. Carried into `outcomes.csv` as `rule_break`.
- **Honored skips get logged on purpose.** Agrees with BUILD_PROMPT Part 3 Step 8.
- The five **review questions**, carried into `05-mistake-log.md`.
- **Claude proposes, CJ confirms** for anything entering the mistake log.

---

## OPEN QUESTIONS — nothing in any file answers these

| # | Question | Current placeholder | Where |
|---|---|---|---|
| 1 | Is a Grade B tradeable? | yes, half size, conviction ≥ 60 | `config.json` → `grading` |
| 2 | Dollar risk per trade (1R) | **$100 placeholder** | `config.json` → `risk_per_trade_usd` |
| 3 | Daily loss limit | −2R (BUILD_PROMPT default; Part 7 says to confirm) | `config.json` → `daily_loss_limit_r` |
| 4 | Max trades per day | 3 (BUILD_PROMPT default) | `config.json` → `max_trades_per_day` |
| 5 | Strike selection on 0DTE — how far OTM? | nearest strike ≥ T1, ATM fallback | `tools/market.py` |
| 6 | Does he trade QQQ the same as SPY, or is SPY primary? | treated identically | `config.json` → `tickers` |

Every placeholder is a **guess by the build**, not a preference of CJ's. They are all one line to
change.
