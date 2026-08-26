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
| 4 | Daily loss limit | After **−2R** on the day, the desk stops calling trades. **Not overridable.** | `daily_loss_limit_r` |
| 5 | Max trades per day | Default **3**. | `max_trades_per_day` |
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
   from becoming a bad month.
5. **Max trades per day.** Overtrading is the most common way a good method loses money.
6. **Cooldown.** Revenge trading is the second most common way. `03-options-playbook.md` states
   it flatly: *no revenge trading — every trade must meet the same rules regardless of recent
   wins or losses.*
7. **Minimum stop distance.** A stop inside bar noise is not a stop, it is a random exit. It
   also makes the trade impossible to grade honestly, which corrupts the learning loop.
8. **Liquidity.** A wide spread is a guaranteed loss taken at entry. Requires a chain
   screenshot — a price chart cannot show a spread (`02-trycon-mas.md`).
9. **Chop veto.** Tangled MAs are the single clearest "sit out" signal on this chart.

## Sizing

From `03-options-playbook.md` §2 and §4.

- Risk is defined in **R**, where 1R = `risk_per_trade_usd` in `config.json`.
- Size so that both green and red days are emotionally tolerable. **If in a rut, size down
  immediately.**
- Contract count = floor(risk budget ÷ per-contract risk), minimum 1, and if 1 contract exceeds
  the budget the response says so rather than rounding CJ into a bigger position.
- Grade B trades size at `b_grade_size_fraction` of full size.
- **Sizing in** is available on A setups: roughly one third at the trigger, two thirds if price
  holds the midpoint of the trigger candle, full size only if the level continues to hold.

> **CONFIRM WITH CJ.** `risk_per_trade_usd` is currently **$100**, a placeholder. BUILD_PROMPT
> Part 7 says to ask him for the daily loss number during setup. Both `risk_per_trade_usd` and
> `daily_loss_limit_r` should be his numbers, not defaults.

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
