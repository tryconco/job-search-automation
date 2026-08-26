<!-- DESK NOTE — added by the build, not part of CJ's original upload. -->

> **SCOPE RULING FOR THIS DESK.** CJ trades **long calls and long puts only, never spreads**
> (BUILD_PROMPT, Part 0). This file is the full unified knowledge base and it contains a great
> deal of spread material — broken wing butterflies, credit spreads, the Batman trade, the wheel.
>
> - **Operative here:** Section 2 (price action, candles, support/resistance, top-down, sizing,
>   the pre-trade checklist, entry and risk rules) and Section 4 (contract mechanics, bid/ask,
>   strike and expiry selection, candle patterns). These are the execution layer.
> - **Reference only:** Sections 1 and 3 (spread structures). Use them to answer a question CJ
>   asks. **Never** let them produce a call. If the engine ever emits a spread, it is broken.
> - The general principles in Section 1 that are structure-agnostic — expectancy, defined risk,
>   theta, delta, liquidity, "credit is not profit", "no revenge trading", position sizing —
>   **do** apply to long single-leg options and are carried into `01-decision-engine.md` and
>   `04-risk-rules.md`.

---

# Unified Options Trading Knowledge Base

*Single consolidated source for a custom GPT. Merges three uploads into one with no duplicated bulk.*

Organized in four sections:
1. GPT context and operating instructions (advanced framing)
2. Beginner and price action integration notes
3. Advanced options strategy source transcripts
4. Beginner options course full source transcript

**How the GPT should use this:** Lead with the systematic, defined-risk mindset in Sections 1 and 2, pull strategy mechanics from Section 3, and use Section 4 as the plain-spoken beginner foundation when a user needs the basics.

---

## Section 1. GPT Context and Operating Instructions

### Knowledge Base Context Expansion

This knowledge base is about options trading education, especially the difference between gambling with options and using options as structured, repeatable trading systems. Professional options traders do not simply guess direction — they choose strategies with defined risk, defined reward, clear entry logic, clear exit logic, and a tested statistical edge. A custom GPT using this material should emphasize probability, discipline, trade structure, back testing, position management, and the difference between owning an idea and merely hoping a trade works.

### Broken Wing Butterfly Strategy Summary

A broken wing butterfly is built from two short options surrounded by long options, where one wing is closer to the short strike than the other. A regular butterfly has balanced wings; a broken wing butterfly intentionally moves one long option closer to the shorts, which can turn a debit structure into a credit structure. It can be used directionally (bullish or bearish) or combined on both sides for a non-directional structure.

The key idea: a broken wing butterfly gives the trader **room to be slightly wrong**. If the market moves as expected, the options expire worthless and the trader keeps the credit. If the market moves mildly against the thesis, time decay may still let the trade close profitably. It can still lose if the market moves too far, too fast, or never behaves as expected — hence the emphasis on back testing, stops, targets, and disciplined management.

### Index Options Summary

Index options are cash-settled and tied to an index's value rather than shares of stock. A call benefits when the index closes above the call strike by enough to overcome cost; a put benefits when the index closes below the put strike by enough to overcome cost. This makes index options useful for expressing market views without individual stock assignment.

### Directional Options Summary

Directional use isn't about randomly buying calls or puts — it's about taking a market thesis and expressing it with more flexibility than simply buying or shorting stock. A bearish signal can use a call-side credit structure above the market; a bullish signal can use a put-side credit structure below the market. Indicators like RSI and moving averages are triggers/hypotheses to be tested against historical data, not guarantees.

### Batman / Field Goal Strategy Summary

Combines a call broken wing butterfly and a put broken wing butterfly into a non-directional trade that benefits if the market stays between two outer risk regions (resembling field-goal uprights or Batman ears on a risk graph). Useful when there's no strong directional opinion and the market is expected to stay in a range. Danger: a large move beyond the expected range causes losses.

### Small Account Options Summary

Focuses on defined-risk credit spreads (especially small index option spreads) for limited capital. Buying options with a small account often behaves like buying lottery tickets — options decay quickly and require the underlying to move far enough, fast enough. The alternative: a defined-risk selling structure (e.g., a narrow put credit spread) with a known maximum loss and capital requirement, tied to a simple rule set (e.g., enter after the index reclaims a moving average; exit if it closes back below it).

### Velocity of Capital Summary

Reusing trading capital efficiently instead of leaving it tied up after most profit has been captured. If a trade quickly earns a large portion of its possible profit, closing early and redeploying capital into a new, better-reflecting trade may increase total return by reducing reversal-risk exposure. This is not about overtrading — the replacement trade must have its own valid setup.

### Wheel Strategy Summary

The trader sells puts on a stock/ETF they genuinely want to own, at a price they'd be comfortable buying. If the stock stays above the strike, the put expires worthless and the premium is kept. If it falls below, the trader is assigned shares at the chosen price (still keeping the premium). After assignment, the trader sells covered calls; if the stock stays below the call strike, the premium is kept while retaining shares; if it rises above, shares are called away at a profit and the cycle restarts — hence "the wheel."

### Professional Edge Summary

Built around positive expectancy — like a casino, professional traders build a statistical edge that plays out over many repetitions. The goal isn't to win every trade, but to have average win rate × average win size exceed average loss rate × average loss size over many trades. No strategy is guaranteed; every trade has a winning and losing scenario. A trader can be right about direction and still lose money if the structure, expiration, strike, or timing is poor.

### Teaching Style Guidance for the Custom GPT

Explain strategies in plain English first, then connect to structure: what's bought, what's sold, where risk sits, where profit comes from, and what market behavior the trade wants. State whether the strategy is directional, non-directional, or income-oriented, and always explain why the trade can win *and* why it can lose. Credit received up front is not profit — it's cash flow, not risk-free money.

### Supplemental Strategy Operating Notes

Every option strategy = thesis + structure + risk + time + volatility + management.

- **Thesis**: the market opinion/signal.
- **Structure**: the specific spread/combination.
- **Risk**: amount that can be lost if the trade fails.
- **Time**: expiration window and theta effects.
- **Volatility**: the market pricing environment.
- **Management**: entry/exit/profit-taking/loss-acceptance rules.

Key distinctions to always teach:
- Cash flow at entry ≠ profit (only known at close/expiration).
- Probability of profit ≠ quality of risk (a high win-rate trade can still be poor if losses are large relative to wins).
- A broken wing butterfly starts from the regular (equidistant) butterfly; pulling one wing closer creates the uneven, often credit-generating structure.
- Indicators (RSI, Bollinger Bands, moving averages) are triggers, not complete strategies — they must be tested with structure, exit, and stop rules.
- Index options settle in cash; stock options can lead to share assignment.
- Buying cheap options is often dangerous — a low dollar cost can still carry a high probability of expiring worthless.
- **Put credit spread**: sell a put at a higher strike, buy a put at a lower strike; wants underlying to stay above the short put.
- **Call credit spread**: sell a call at a lower strike, buy a call at a higher strike; wants underlying to stay below the short call.
- The long option in a credit spread defines/limits maximum loss.
- Velocity of capital = weighing remaining reward vs. remaining risk on a trade that's already captured most of its profit.
- The wheel requires willingness to own the underlying; assignment is not failure, it's the entry.
- Covered calls cap upside above the strike in exchange for income.
- Every strategy has a market regime where it performs poorly (credit spreads in sharp directional moves, debit spreads when moves don't happen fast enough, non-directional trades during breakouts, the wheel during sustained declines).
- Theta helps sellers when price stays in a favorable range but does not override a sharp adverse move.
- Expiration should match the thesis' expected timeframe.
- Delta = directional sensitivity and an approximate probability of expiring in the money.
- Premium is compensation for risk — there is no free premium.
- To close a spread: reverse the opening transactions (buy back what was sold, sell what was bought).
- Max loss in a defined-risk spread ≈ distance between strikes minus credit received (or debit paid), though planned stops may exit earlier.
- Back testing is required, not optional — treat every strategy as a hypothesis.
- Adjustments aren't automatically superior to simple stops; complexity isn't edge by itself.
- Annualized returns are a math lens, not a promise.
- Losing trades are part of any edge-based system; the goal is controlling loss size, not avoiding losses.
- No revenge trading — every trade must meet the same rules regardless of recent wins/losses.
- Position sizing is essential; a strategy can have edge and still be dangerous if oversized.
- The same directional view can be expressed many ways (shares, calls, puts, credit/debit spreads, broken wing butterfly) — match structure to thesis.
- Liquidity and bid/ask spreads matter, especially for multi-leg trades.
- Educational examples illustrate mechanics; they are not trade recommendations.

### Glossary (Custom GPT Reference)

- **Call**: right to buy at strike (buyer); obligation to sell if assigned (seller).
- **Put**: right to sell at strike (buyer); obligation to buy if assigned (seller).
- **Credit trade**: cash received at open; profit only if closed/expires favorably.
- **Debit trade**: cash paid at open; needs value increase to profit.
- **Spread**: combination of bought/sold options shaping risk.
- **Credit spread**: options-selling structure with defined risk.
- **Debit spread**: directional structure with defined risk.
- **Butterfly**: short body + long wings.
- **Broken wing butterfly**: uneven butterfly, one wing closer than the other.
- **Batman trade**: call-side + put-side broken wing butterflies combined, for range-bound theses.
- **The wheel**: sell puts to enter stock at a desired price → sell covered calls after assignment → repeat.
- **Theta**: time decay effect; usually helps sellers, hurts buyers.
- **Delta**: directional sensitivity / rough probability of expiring in the money.
- **Assignment**: option seller must fulfill the obligation (buy/sell shares; cash-settled for index options).
- **Expiration**: contract endpoint — worthless, cash-settled, or assigned.
- **Positive expectancy**: favorable mathematical profile over many trades (not every trade).
- **Back testing**: reviewing historical strategy performance under defined rules.
- **Stop/Target**: planned exits for losing/winning trades, set before entry.
- **Hypothesis**: an unproven trading idea requiring testing.
- **Regime**: market environment type (trend, range, high/low volatility, panic, drift).

### Custom GPT Answering Principles

- When explaining a strategy: purpose → construction → desired outcome → causes of loss → management idea.
- When comparing strategies: compare by thesis, capital requirement, probability, max reward/risk, assignment exposure, time/volatility sensitivity, and management ease — never simply call one "better."
- When asked whether to enter a trade: require a thesis, an exit rule, and a sizing plan.
- When asked about a losing trade: check thesis validity, whether the stop has been hit, and whether adjustment would genuinely improve expectancy.
- When asked about rolling: it's closing one trade and opening another — judge it as a fresh trade with its own expectancy.
- Use risk language carefully: never "risk free" or "guaranteed" — prefer "defined risk," "limited risk," "favorable expectancy," "controlled loss."

### Additional Scenario Notes

- Trending market → directional debit/credit spreads may fit better than income structures (check if the move is already priced in).
- Range-bound market → premium collection can work if the range thesis is supported and risk beyond the range is defined.
- Elevated volatility → richer credits, but larger possible moves; rich premium ≠ automatic edge.
- Low volatility → selling pays less, leaves less error room; can precede expansion.
- Early signal → structures with time/room (e.g., broken wing butterfly) may fit better than a short-fuse option purchase.
- Immediate/tested signal → a debit spread with clear target/stop may fit better.
- Small account → defined risk, narrow spreads, small size, and strict exits matter even more.

### Final Knowledge Base Framing

Options should be traded as structured instruments, not lottery tickets. Every strategy should answer: What am I trying to express? What has to happen for this to work? What proves this trade wrong? How much can I lose? How will I take profit? Why does this setup have edge? What happens if the market does something inconvenient? The GPT should favor repeatable rules over predictions, defined exits over hope, and probability over excitement.

---

## Section 2. Beginner and Price Action Integration Notes

The beginner course material is the **practical execution layer** supporting the advanced strategy material: the trader must know what an option contract is, how the option chain works, how to select a strike, how to enter/exit using bid/ask, how to read price action, mark support/resistance, and manage risk without becoming emotional.

### Core Beginner Concepts

- **Calls** = bets on price moving up; **Puts** = bets on price moving down.
- **Strike price** = the level attached to the contract.
- **Option chain** = where you choose expiration, strike, and call/put side.
- **Bid** = price used when selling; **Ask** = price used when buying. A wide bid-ask spread reduces entry/exit efficiency.
- **Day trading** = open/close same day; **Swing trading** = held beyond the same day; **LEAPs** = longer-dated options giving a thesis more time.

### Candlestick / Price Action Layer

- A candlestick visually summarizes open, high, low, close for a chosen period.
- **Green candle**: close > open (buying pressure). **Red candle**: close < open (selling pressure).
- **Pin bar**: strong reversal signal where the candle's body/close is near one extreme after testing the other (bullish pin bar at support; bearish pin bar at resistance) — most powerful single-candle pattern.
- **Engulfing pattern**: a new candle's body fully overtakes the prior candle's body after a pullback (bullish engulfing after downtrend; bearish engulfing after uptrend). Especially high-probability near the 200-day moving average or other support/resistance.
- **Harami / inside bar**: today's candle is smaller and inside yesterday's range — a volatility compression signal, not a reversal signal by itself. The trade is the breakout above/below the inside bar's range, not the bar itself.
- **Doji**: open and close are virtually equal — a standoff between bulls and bears.

### Support, Resistance, Supply & Demand

- **Support** = floor where price bounces; **Resistance** = ceiling where price rejects.
- **Supply zone** = area where sellers previously overwhelmed buyers; **Demand zone** = area where buyers previously overwhelmed sellers.
- Zones, not exact prices — mark with multiple touches, prior highs/lows, premarket highs/lows, previous day's high/low, intraday highs/lows, and trend lines.
- **Break and retest**: resistance that's broken can become new support (and vice versa).
- Rule of thumb: third touches of support/resistance are considered strong.

### Top-Down Analysis

Start from higher timeframes (weekly → daily → 4-hour → 1-hour → 15-minute → 5-minute) to find structure before dropping to lower timeframes for entries. A clean 5-minute signal against a major daily resistance is a weaker setup than one aligned with the larger trend and level.

### Psychology & Risk Management Layer

- Consistency comes from repeatable position sizing, setups, and rules — like "zeroing a rifle": keep the sight picture (risk) consistent and adjust the process, not the risk itself.
- **Sizing in**: know your intended full size before entry; scale in as the setup confirms (e.g., partial size at breakout, add at the midpoint of the candle, full size only if the level holds).
- Every trade explanation should include size logic, stop logic, target logic, and invalidation criteria.
- Indicators are references, not reasons by themselves. No pattern has a perfect win rate. The goal is edge and risk control, not certainty.

### Pre-Trade Checklist

1. Identify support/resistance zones (not exact points).
2. Determine proximity to support (buy) or resistance (sell).
3. Check multiple timeframes for conflicting signals.
4. Define risk-to-reward before entry.
5. Define exact entry, target, and stop before the trade.
6. Check for major economic events (CPI, FOMC, unemployment claims, GDP, Fed speeches).
7. Confirm healthy volume/liquidity.
8. Ask: does this meet all criteria, or am I being impulsive?

### Entry & Risk Rules

- Wait for confirmation (bounce, reclaim, pin bar, engulfing candle, break-and-retest, moving-average reclaim) — don't predict, react.
- Never enter solely because RSI is oversold or MACD is curling.
- Size to a level where both green and red days are emotionally tolerable; size down immediately if in a rut.
- Every trade must have a stop before entry; a day trade should never quietly become a swing trade to avoid taking a loss.
- Avoid margin without already knowing how to manage risk.

### Connecting Beginner Material to Advanced Strategies

- Bullish view → calls, put credit spreads, call debit spreads, bullish broken wing butterflies, or the wheel.
- Bearish view → puts, call credit spreads, put debit spreads, or bearish broken wing butterflies.
- Neutral view → non-directional structures like the Batman / field goal trade.

The GPT should teach like a coach: explain the setup in plain English, identify market condition, map zones, describe the option structure, define risk/target, describe invalidation, and specify what to wait for — never hype, never imply certainty, never turn every chart into a forced entry.

---

## Section 3. Advanced Options Strategy Source Transcripts (Seth Freudberg / SMB Capital)

### Chapter 1–3: What Is a Broken Wing Butterfly? / How Index Options Work / When Option Buyers Win and Lose

Options can be traded either as a repeated systematic edge (law of large numbers) or to express a directional viewpoint with more flexibility than simply buying/shorting an underlying. Most large options traders trade **index options** — cash bets that pay off based on where the index closes relative to a strike, since an index itself can't be bought or sold. A call pays off if the index closes above the call strike by enough to exceed cost; a put pays off if it closes below the put strike by enough. Option buyers win when the move exceeds cost; they lose if the move doesn't happen, or happens but not far enough to cover the option's cost.

**Example**: With the S&P 500 closing at 6,745 (illustrative), a 6,500 call that finished 245 points in the money pays $24,500 (100/point), while a 6,500 put and a 6,900 call would expire worthless, and a 6,900 put would pay $15,500.

### Chapter 4–5: Regular Butterfly vs. Broken Wing Butterfly

A **regular (equidistant) butterfly** sells two options at a center strike and buys one long option an equal distance above and below — typically a **debit spread** (you pay to enter, since the two long premiums exceed the short premium collected).

A **broken wing butterfly** moves one long wing closer to the shorts than the other, making that wing cheaper. Pulling the wing in enough can flip the structure from a debit to a **credit** (you receive cash to open). Example: a put broken wing butterfly brought in $20,000 from selling puts, paid $14,000 for the closer long put and $5,300 for the farther long put — netting a credit instead of a debit.

### Chapter 6–7: Why Traders Use Broken Wing Butterflies / RSI as a Directional Trigger

The credit-oriented broken wing butterfly gives the trader **room to be a little wrong**. If a directional signal (e.g., RSI hitting 70 = overbought, suggesting a bearish move) is early or the market only reacts mildly, the structure can still profit because of time decay, even if price doesn't move immediately as expected. Delta doubles as an approximate probability of expiring in the money (e.g., a 20-delta option ≈ 20% chance of finishing in the money, ~80% chance of expiring worthless — favorable for the option seller).

### Chapter 8–9: Bearish and Bullish Broken Wing Butterfly Examples

**Bearish example** (RSI overbought at 70): sold a 20-delta call structure ~100+ points above market, collecting $4,340 credit. Despite an initial rally, the market eventually sold off and closed below all strikes — full credit captured as profit.

**Bullish example** (RSI oversold at 30): entered a ~19.83-delta put structure with unequal wing distances (75 points vs. 200 points), collecting a $1,725 credit requiring $60,000 in capital. The market initially bounced against the thesis, then continued falling — but because time had passed, the near-the-money put lost value from decay even while going in-the-money, allowing the trade to be closed for a $7,200 profit (roughly 12% return in 31 days, ~140% annualized) — more than the initial credit. This illustrates that being "a little wrong" can sometimes produce *more* profit than being immediately right, because time decay assists the position.

### Chapter 10–11: How Time Decay Helps / Why Being "A Little Wrong" Can Still Work

Time decay can offset an adverse move, particularly on options with slower-reacting signals, but only within limits — a fast, large move against the structure early in the trade (before decay has time to work) can still cause a loss. This is why back testing is essential before trading a specific indicator/structure combination.

### Chapter 12–14: The Batman / Field Goal Strategy

A non-directional combination of a call-side and put-side broken wing butterfly, resembling football uprights (or Batman ears) on a risk graph. Used when there is no directional conviction (e.g., RSI near 50). Example: a 63-day trade with strikes at 10-delta (high probability), 10 points above and 20 points below market on each side, collecting $850 (calls) + $550 (puts) = $1,400 credit on $8,600 required capital. The market moved but stayed within the "uprights," and both sides expired worthless — capturing the full $1,400 credit.

Broken wing butterflies (and the Batman trade) can be directional or non-directional, but **all can lose** if price moves far/fast enough. Every strategy requires back testing, a stop, and a profit target, run across many historical instances of the trigger condition.

### Chapter 15: Q&A Highlights

- **Edge sources**: some edges exist inherently in market pricing; others come from combining a directional indicator with the right option structure — usually both matter.
- **Adjusting vs. set-it-and-forget-it**: neither is universally superior; both can be powerful depending on the strategy and its back-tested behavior.
- **Managing larger-than-expected moves**: the options market adjusts strike pricing to reflect current volatility (a 10-delta strike sits farther away when volatility is high). Adjustment options for a troubled Batman trade include rolling the threatened side up/out or introducing wholly different management logic — many possible adjustments exist.
- **Broken wing butterfly vs. plain credit spread**: the advantage is tolerance for a thesis that takes time to develop, since the structure won't get stopped out as quickly.
- **Risk of gamma squeezes/wide wing spreads**: can worsen realized losses versus theoretical max loss — a real cost that shows up in back testing and must be accepted if the overall strategy remains profitable.
- **How the market "eats your lunch"**: sharp immediate adverse moves, mild-but-sufficient adverse moves, or the thesis simply never playing out. Every options trade has a losing scenario; not taking your stop is one of the fastest ways to blow up an otherwise valid strategy.

### Small Account / XSP Options Strategy (Under $100 Per Trade)

Buying options with a small account behaves like buying lottery tickets — a possible big win, but a more likely loss because of rapid time decay. The alternative taught is a **systematic put credit spread on XSP** (an index priced at ~10% of the S&P 500, making it accessible to small accounts).

**Rule set example**: Enter an at-the-money put credit spread (sell the strike just below the current index price, buy the strike one increment lower) whenever the index closes back above its 20-day moving average after being below it. Exit if the index closes back below the 20-day moving average.

**Illustrative trades**: 
- April 24 entry: sold the 548 put, bought the 547 put, net credit $38, capital required ~$62.
- August 4 entry: sold 632/631 puts, credit $33, capital ~$67 — expired worthless for full profit as the index rallied.
- September entry: sold 646/645 puts, credit $37, capital ~$63 — index gapped down below the moving average, triggering an exit at a $23 loss (smaller than the wins).

Across all signal occurrences from April through the test period, most trades won and the few losses were each smaller than the individual wins, netting a $187 profit — about a 62% return on a conservative $300 starting capital base (sized to survive a losing streak, even though any single trade required far less). The broader lesson: even ultra-small accounts can trade systematically with defined risk, letting discipline and structure — not the amount of capital — determine long-term success.

---

## Section 4. Beginner Options Course (Full Source Transcript, Cleaned)

### Course 1 – Option Trading Basics

- **Buying an option**: you always buy at the **ask** price, and pricing on the platform is often shown with the decimal shifted two places for the true dollar cost (a quote of "3.70" = $370 per contract before commission).
- **Selling an option**: you always sell at the **bid** price. To close a position, sell at the bid (if long) or buy back at the ask (if short).
- **Spread** = difference between bid and ask; a tighter spread means more efficient entries/exits.
- **Order types**: limit orders let you specify the price you're willing to pay/accept; market orders fill immediately at the best available price (fine for fast-moving candles, but be mindful of wide spreads).
- **Choosing expiration**: match the expiration to your trading style — a same-day/five-minute-chart trade uses a near-term expiration; a multi-month directional swing thesis uses an expiration two to three months out.
- **Day trading** = entering and exiting within the same day. **Swing trading** = holding beyond one day.
- **Risk sizing example**: if your personal loss threshold is $1,000, size your position so a defined stop (e.g., 50% loss) equals no more than that dollar amount — meaning you'd deploy roughly $2,000 of capital knowing a 50% stop caps your loss near $1,000.
- Always check the **option contract label** (ticker, strike, call/put, expiration date, and price) before entering, e.g., "STZ 135 call, expires 12/19, filled at $4.79."

### Course 2 – Candlestick Mastery

- **Bullish** (bulls) = buyers/rising prices; **Bearish** (bears) = sellers/falling prices.
- Every candlestick represents price action for one unit of the chosen timeframe (one day on a daily chart, five minutes on a 5-minute chart, etc.).
- **Green candle**: close > open. **Red candle**: close < open. The **body** = the range between open and close; **wicks/shadows** = the range beyond the body (the high/low that wasn't held into the close).
- **Big green/red candles** signal strong buying/selling pressure and are typically accompanied by high volume.
- **Doji**: open and close are virtually equal — a standoff between bulls and bears.
- **Pin bar** (the most powerful single-candle pattern): price is pushed sharply one way, then reversed to close near the opposite extreme before the candle closes — represents a fast rejection and potential reversal. Bullish pin bars are strongest at support; bearish pin bars are strongest at resistance. Entry: ~15 cents above the high (bullish) or ~15 cents below the low (bearish); stop is placed at the opposite end of that candle.
- **Engulfing pattern**: a candle's body fully covers the prior candle's body after a pullback — bullish engulfing after a downtrend, bearish engulfing after an uptrend. Especially high-probability at the 200-day moving average or a support/resistance level. Entry: ~15 cents beyond the high (bullish) or low (bearish) of the engulfing candle.
- **Harami / inside bar** ("pregnant" in Japanese): today's candle body is fully contained within yesterday's — signals compression/indecision, not a standalone reversal. Entry is a break above or below the high/low of the inside-bar range (including wicks); the opposite extreme becomes the stop.

### Course 3 – Trends, Support & Resistance, Supply & Demand

- **Support** = floor, where price has bounced (buyers overwhelming sellers); **Resistance** = ceiling, where price has rejected (sellers overwhelming buyers).
- Mark zones using trend lines, horizontal lines/rays, and multiple touches; the rule of thumb is that a third touch of a level is a strong signal.
- **Break and retest**: once resistance is broken, it frequently becomes new support on a pullback (and vice versa for broken support).
- **Channels**: parallel support/resistance lines forming a range; breakouts from a channel often retrace to retest the broken boundary before continuing.
- **Top-down analysis**: start from the weekly/daily chart for major structure, then step down to 4-hour, 1-hour, 15-minute, and 5-minute charts to find levels and entries invisible on higher timeframes — always keep premarket highs/lows, previous-day highs/lows, and intraday levels in view.

### Course 5 – Charting on TradingView & Top-Down Analysis

Practical charting workflow: use trend lines, horizontal rays, and the "info line" tool to mark levels across timeframes, moving from weekly down to 5-minute charts to progressively reveal more granular support/resistance, breakout, and retest zones. Always account for after-hours and premarket price action as additional reference levels.

### Position Sizing Technique — "Sizing In"

Rather than entering full size immediately, scale in as a setup confirms: e.g., with an intended full size of $1,000, enter about one-third ($300) at the breakout, add to about two-thirds ($600) if price holds around the midpoint of the breakout candle, and reach full size only if the level continues to hold (with the stop placed at the low of that candle). This reduces emotional pressure and avoids oversized entries at poor prices.

### Trading Rules Reference (from rules.json)

**Core Principles**
- Indicators are a reference, never the sole reason to take a trade.
- Patterns tend to repeat, but they don't always have to.
- The market does what it wants — respect it, don't fight it.
- Every open position is a position exposed to risk.
- There is no 100% success rate; the goal is a proper edge, not perfection.

**Pre-Trade Checklist**
1. Identify support/resistance zones, not exact price points.
2. Determine if the stock is closer to support (potential buy) or resistance (potential sell).
3. Check multiple timeframes — is it overbought on the daily even if bullish on the 1-minute?
4. Formulate a risk-to-reward ratio before entering.
5. Define exact entry, target, and stop-loss price.
6. Check for upcoming economic reports (CPI, FOMC, unemployment).
7. Verify the stock has healthy volume.
8. Ask: "Does this meet all my trade criteria, or am I being impulsive?"

**Entry Rules**
- Wait for confirmation of support/reversal before buying — don't predict, react.
- Buy at or near support zones based on prior pattern behavior.
- If shorting, enter at or near resistance zones with confirmation of rejection.
- Never buy solely because RSI says oversold or MACD shows a reversal.
- Look for an EMA crossover or price reclaiming an EMA as confirmation.

**Risk Management**
- Trade a size where both green and red days are emotionally tolerable.
- If in a rut, size down immediately.
- Every trade must have a defined stop loss before entry.
- Never let a day trade turn into a swing trade because you refuse to cut losses.
- Do not use margin if you don't already know how to manage risk.

**Key Economic Events to Watch**
- **CPI** (monthly) — measures inflation.
- **FOMC Rate Decision** (monthly) — the most significant monthly event.
- **Unemployment / Initial Claims** (weekly, Thursdays, ~1 hour before market open).
- **GDP** (quarterly).
- Never enter a swing trade right before a major economic report; expect volatility around Fed Chair speeches.

**Annual Risk Cadence**
Start the year trading smaller size to build a cushion. If the year opens red, avoid "playing catch-up" with larger size. After a consistent green stretch (commonly cited as ~90 days), size can be increased. This mirrors marksmanship training: don't adjust your "sight picture" (risk management) trade-to-trade — adjust the *process* (entries, trigger discipline, patience) instead.

---

*Note: This Markdown file consolidates and organizes the full content extracted from the source PDF (`knowledge-base-3.0.pdf`), covering all four sections as structured in the original document.*
