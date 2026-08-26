# 04 RISK RULES

Hard vetoes. Checked on every call. They override any setup grade and any conviction score.
Implemented as pure functions in `tools/guards.py`, unit-tested at both sides of every boundary.

0DTE options are the most unforgiving instrument a retail trader touches. Value goes to zero on
a schedule. These rules exist because the method cannot save a position that theta has already
taken.

## The nine guards

| # | Guard | Rule | Config key |
|---|---|---|---|
| 1 | Time cutoff | No new 0DTE entry after **15:00 ET / 14:00 CT**. Hard flat by **15:30 ET / 14:30 CT**. | `no_entry_after_et`, `hard_flat_et` |
| 2 | Opening lockout | No entry in the first **15 minutes** of the regular session. | `opening_lockout_minutes` |
| 3 | Event lockout | No entry within **15 min before** or **10 min after** a scheduled release. | `event_lockout_*_minutes` |
| 4 | Daily loss limit | After **−4R (−$400)** on the day, the desk stops calling trades. **Not overridable.** | `daily_loss_limit_r` |
| 5 | Max trades per day | **5**. | `max_trades_per_day` |
| 6 | Cooldown | No new call within **15 minutes** of a loss. | `cooldown_minutes_after_loss` |
| 7 | Minimum stop distance | Reject any stop tighter than **1.5× the average 5-minute bar range**. | `min_stop_bar_range_multiple` |
| 8 | Liquidity | Reject a strike whose bid/ask spread exceeds **10% of premium**. | `max_spread_pct_of_premium` |
| 9 | Chop veto | If EMA 9/21/50 sit within **0.25 × ATR** of each other, no trade either direction. | `chop_veto_atr_fraction` |

### Why each one is there

1. **Time cutoff.** Theta in the last half hour is not a trade, it is a raffle.
2. **Opening lockout.** The open is noise. The opening range needs to print before it means
   anything.
3. **Event lockout.** Event proximity is a first-class input, not a footnote. A perfect chart
   8 minutes before CPI is a NO TRADE, and the response must say that is why. Watch list from
   `03-options-playbook.md`: CPI, PPI, PCE, FOMC, jobs and initial claims, GDP, Fed speakers,
   Treasury auctions.
4. **Daily loss limit.** The one rule with no override path. It is the rule that keeps a bad day
   from becoming a bad month. **−4R** is derived, not guessed: with sizes running 1.0R to 3.5R
   and five trades allowed, one max-size A loss (−3.5R) leaves 0.5R and effectively ends the
   day — which is what a max-size loss should do — while four base-size losses are what it
   takes otherwise, so a slow bad day still leaves room for the trades CJ wants.
5. **Max trades per day.** Overtrading is the most common way a good method loses money. CJ set
   this at **5**: *"typically I want to trade as much as possible in one day… like five options
   a day, but stay profitable."* Five is the ceiling, not a target.
6. **Cooldown.** Revenge trading is the second most common way. `03-options-playbook.md` states
   it flatly: *no revenge trading — every trade must meet the same rules regardless of recent
   wins or losses.*
7. **Minimum stop distance.** A stop inside bar noise is not a stop, it is a random exit. It
   also makes the trade impossible to grade honestly, which corrupts the learning loop.
8. **Liquidity.** A wide spread is a guaranteed loss taken at entry. Requires a chain
   screenshot — a price chart cannot show a spread (`02-trycon-mas.md`).
9. **Chop veto.** Tangled MAs are the single clearest "sit out" signal on this chart.

## Sizing

Confirmed by CJ, 2026-08-26.

| Grade | Risk | In R |
|---|---|---|
| **A** — all five legs clean | **$350** | 3.5R |
| **B** — one leg missing | **$100** | 1.0R |
| **C** | skip | — |

- **1R = $100 always**, whatever the position size. The R unit stays fixed or the daily loss
  limit, the ledger and every lesson stop being comparable. A max-size A therefore risks 3.5R.
- Contract count = floor(budget ÷ per-contract risk). If one contract exceeds the budget, the
  response says so rather than rounding CJ into a bigger position.
- **Without a chain there is no premium.** A price chart cannot show a bid or ask
  (`02-trycon-mas.md`), so the desk says *size it off your chain* instead of inventing a number
  that looks precise.
- Size so that both green and red days are emotionally tolerable. **If in a rut, size down
  immediately** (`03-options-playbook.md`).
- **Sizing in** on an A: about a third at the trigger, two thirds if price holds the midpoint of
  the trigger candle, full size only if the level keeps holding.

> **Standing concern, on the record.** A 3.5× size range means one A-grade loss erases three and
> a half B-grade wins. On a method with no established edge, size variance amplifies swings
> faster than it amplifies returns. CJ asked for the range and it is built as asked. One line in
> `config.json` (`grade_risk_multiplier`) compresses it.

## Exit discipline

- Hard flat by **15:30 ET / 14:30 CT** regardless of position.
- **Never let a day trade become a swing trade** to avoid taking a loss
  (`03-options-playbook.md`). On 0DTE this is not a preference, it is arithmetic — the contract
  expires today.
- Dead trade rule: if the underlying has not moved toward the target in ~20 minutes, close it.
  Dead trade, live theta.
- The stop is on the **underlying**. The contract exit price is derived from it and is an
  estimate, always labelled as one.

## What the guards cannot do

They cannot make CJ take the exit. Every guard here is advisory in the only sense that matters:
this desk produces a call, and he places every order by hand.
