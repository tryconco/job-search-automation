# 01 DECISION ENGINE

How evidence becomes a verdict. Runs after the screenshot is read and reconciled, and after
`lessons/LESSONS.md` is loaded. Its output feeds `tools/guards.py`, which can veto anything.

Sources: `02-trycon-mas.md` (chart reading), `03-options-playbook.md` §2 and §4 (price action,
checklist, entry and risk rules), `06-mentor-engine.md` (the three layers), BUILD_PROMPT Part 3.

---

## Step A — Establish the stack

From `02-trycon-mas.md`. Recomputed from live bars; the screenshot only says where CJ is looking.

- **Above all five lines** (EMA 9/21/50/200, SMA 200) → strong uptrend, longs only.
- **Below all five** → strong downtrend, puts only.
- **Tangled inside the lines** → chop. Lower grade, and usually the chop veto.
- **Fast pair** (EMA 9 + EMA 21) is the dynamic intraday reference. This chart has no VWAP, so
  the fast pair stands in its place. Reclaim and hold above → long lean. Loss and fail below →
  short lean.
- **Anchor** (EMA 50) — above is intraday bullish, below is intraday bearish.
- **Heavy zone** (EMA 200 + SMA 200, which sit together) — the major line in the sand. Reclaim
  and hold above is strongly bullish. Rejection off it from below is strongly bearish. Distance
  from price to the zone measures how extended the move is, and the zone is usually either the
  target or the wall.
- **Crosses are confirmation, never a standalone trigger.** EMA 9 up through 21 and 50 is
  momentum turning up. Only counts next to a zone and a candle.

## Step B — Locate price against a real zone

From `03-options-playbook.md` §2. Zones, not exact prices.

Build the zone list from **computed levels only**: prior day H/L/C, overnight H/L, opening
range H/L, session H/L, and the MA values. Add anything CJ drew on the chart, labelled as his
mark. Bell icons on the price axis are existing alerts — treat those prices as levels he
already watches.

- A setup needs price **at or approaching a zone**. Mid-range entries are not setups.
- Third touch of a level is the strong one.
- Break and retest: broken resistance becomes support and the reverse.

## Step C — Require a closed-candle confirmation

From `02-trycon-mas.md` and `03-options-playbook.md` §2/§4. **React, do not predict.**

Accepted confirmations: pin bar at the zone, engulfing after a pullback, break of an inside-bar
range, a break-and-retest hold, a reclaim of the fast pair that closes and holds.

**A developing candle is not a signal.** If the countdown on the chart shows the signal candle
still printing, say so, and the verdict is WAIT until that candle closes. This rule is not
negotiable and it is the single most common reason a good-looking chart returns WAIT.

## Step D — Check room to the next level

The geometry gate. Walk the path from trigger to first target. If the heavy zone or any major
level sits between the trigger and T1, the reward is capped and the grade drops. A setup with
no room is not a trade no matter how clean the candle.

Minimum acceptable geometry: **T1 at least 1.5× the underlying stop distance.** Below that,
grade C.

## Step E — Grade it

The grade describes **setup quality only**. It says nothing about outcome.

**Grade A — all five must hold**
1. Price above all five MAs (long) or below all five (short) — clean stack, no tangle.
2. At a real zone, per Step B.
3. Closed-candle confirmation, per Step C.
4. Room to T1 ≥ 1.5R, per Step D.
5. Session window is prime (see Step F).

**Grade B** — the trade thesis is intact but exactly one of the five is missing or weak.
Typical B: perfect candle at a perfect zone, but the heavy zone caps the reward. That example is
from `06-mentor-engine.md` and it is the canonical B.

**Grade C** — two or more missing, or any of: EMAs tangled, no zone nearby, signal candle still
developing, no room, counter-trend against a clean stack. **C is always a skip.** Log it as an
honored skip.

> **OPEN QUESTION FOR CJ — is a B tradeable?** `06-mentor-engine.md` closing lines treat only A
> as actionable ("Everything else, B, C, premarket, closed → No setup, no trade"). BUILD_PROMPT
> Part 4 shows a TRADE at Grade B. These conflict and it materially changes trade frequency.
> Current setting, in `config.json`: `b_grade_tradeable: true`, at
> `b_grade_size_fraction: 0.5` and only when conviction ≥ 60. Flip that flag to `false` for
> A-only. Do not change it silently — it belongs to CJ.

## Step F — Session timing

Judged in **Central**, per `02-trycon-mas.md`. ET shown alongside because the guards and the
options market run on ET.

| Central | Eastern | Window |
|---|---|---|
| before 08:30 | before 09:30 | Premarket. No calls. Lighter shaded background on the chart. |
| 08:30–08:45 | 09:30–09:45 | Opening lockout. The open is noise. |
| 08:45–10:30 | 09:45–11:30 | **Prime.** Best structure of the day. |
| 10:30–12:30 | 11:30–13:30 | Midday. Grade drops one letter unless the stack is clean and the zone is major. |
| 12:30–14:00 | 13:30–15:00 | Afternoon. Tradeable, but theta is accelerating on 0DTE. |
| after 14:00 | after 15:00 | No new entries. Hard veto. |
| 14:30 | 15:30 | Hard flat regardless of position. |

## Step G — Size it by grade

**There is no conviction score.** CJ dropped it on 2026-08-26. `06-mentor-engine.md` forbids a
confidence percentage, and a number out of 100 printed next to a trade reads as a likelihood no
matter how it is labelled. The grade carries the quality judgement; the WHY and AGAINST lines
carry the reasons, each one checkable.

The grade decides the size. CJ's rule, in his words: *"most of the time it will be $100, but
depending on the trade — say the trade is really good — you can get a little more… $350."*

| Grade | Risk | In R | Why |
|---|---|---|---|
| **A** | $350 | 3.5R | All five legs clean. Uncommon — the prime-window requirement alone limits it. |
| **B** | $100 | 1.0R | The common case, and the default. |
| **C** | — | — | Skip. |

**1R is always $100**, whatever the position size. The R unit has to stay fixed or the daily
loss limit, the ledger and every promoted lesson stop being comparable to each other. So a
max-size A risks **3.5R, not 1R** — which is why one losing A very nearly ends the day against
the −4R limit. That is deliberate.

> **Standing concern, on the record.** A 3.5× size range means one A-grade loss erases three and
> a half B-grade wins. On a method with no established edge, size variance amplifies swings
> faster than it amplifies returns. CJ asked for the range and it is built as asked; it is one
> line in `config.json` (`grade_risk_multiplier`) to compress.

Sizing in is available on an A: roughly a third at the trigger, two thirds if price holds the
midpoint of the trigger candle, full size only if the level keeps holding.

## Step H — Write both sides

Every call lists **WHY** and **AGAINST**. If the opposing case does not change the decision,
leave it out and stay compact (`06-mentor-engine.md`). If it does change it, it belongs in the
grade, and say so in that line.

## Step I — Hand to the guards

`tools/guards.py` runs last and can veto an A setup at full conviction. When a guard vetoes,
**the response names the guard.** CJ should always know exactly what stopped it.

## Step J — Pick the verdict

- **TRADE** — clears the engine and every guard.
- **NO TRADE** — does not clear, and will not soon. Say precisely what is missing.
- **WAIT UNTIL `<time>`** — does not clear *yet*, but there is a specific nameable reason it
  might. Must state the exact time to send the next chart, what to look for, what makes it a
  yes, and what kills it.

`WAIT` is the verdict CJ most needs and the one a lazy system never gives. Use it whenever there
is a real reason to check back — an approaching level, a developing candle, an event about to
clear, a range about to resolve. **Never use it as a hedge to avoid committing.**

Most screenshots should return NO TRADE or WAIT. A system that always finds a trade is just an
expensive way to agree with whatever CJ already wanted to do.
