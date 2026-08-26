# 05 MISTAKE LOG

Repeated failures, and the rule each one earned. A mistake enters this file only when it has
**actually happened on this desk** and is visible in `ledger/outcomes.csv` or the journal.

## How an entry gets here

1. `tools/grade.py` marks a resolved call, including a `rule_break` flag when the entry
   happened outside the plan.
2. Review (weekly, or `tools/distill.py`) counts rule breaks by type and by session window.
3. A pattern that repeats gets **proposed** in a response.
4. It lands in this file only after CJ confirms it. This mirrors the journal protocol in
   `07-journal-protocol.md`: Claude proposes the line, CJ accepts it.

Never write an entry here from a single bad trade. One loss is not a mistake, it is a loss.

## Observed on this desk

*Empty. Nothing has been graded yet. Do not populate this section from assumption — it is the
section that must be earned.*

| Date | Mistake | Times seen | Rule it earned | Evidence |
|---|---|---|---|---|

## Carried from CJ's own rules — not yet observed here

These are rules CJ wrote in `03-options-playbook.md`. They are stated as things a trader does
wrong, so they are worth watching for, but **none of them has been observed on this desk yet**
and none may be cited as CJ's personal pattern until it shows up in the ledger.

| Watch for | Source rule |
|---|---|
| Revenge trading after a loss | "No revenge trading — every trade must meet the same rules regardless of recent wins/losses." Guard 6 enforces it. |
| Letting a day trade become a swing trade | "Never let a day trade turn into a swing trade because you refuse to cut losses." On 0DTE, guard 1 enforces it. |
| Sizing up while in a rut | "If in a rut, size down immediately." |
| Entering on an indicator alone | "Never buy solely because RSI says oversold or MACD shows a reversal." |
| Entering on a developing candle | `02-trycon-mas.md`: a candle still counting down can flip its shape before the close. |
| Predicting instead of reacting | "Wait for confirmation — don't predict, react." |
| Impulse entries | Checklist item 8: "Does this meet all my trade criteria, or am I being impulsive?" |

## The review questions

From `07-journal-protocol.md`. Run against the month, not against one bad day.

- How many entries broke a rule, and which rule keeps showing up.
- How many A grades were actually taken, and how many were passed on.
- Which session window produced the most rule breaks.
- Did losses cluster right after other losses. That is the cooldown gate earning its place.
- Rules followed against total trades taken, as a plain count.
