<!-- DESK NOTE — added by the build, not part of CJ's original upload. -->

> **THIS IS THE CLAUDE CODE VERSION.** CJ's file opens by saying so itself: *"In the Claude Code
> version this file wrote itself. In a Project it cannot."* It can here. `ledger/calls.csv` and
> `ledger/outcomes.csv` are written automatically, so the copy-paste loop below is **superseded**
> — CJ does not paste lines any more.
>
> What is **kept and binding** from this file:
> - The **Result vocabulary**, including `taken, broke rules`. That flag is not in BUILD_PROMPT
>   and it is the most diagnostic field in the set — it is carried into `outcomes.csv` as
>   `rule_break`.
> - **Honored skips get logged on purpose.** The skips are the discipline.
> - The five **review questions** — carried into `05-mistake-log.md`.
> - **Claude proposes, CJ confirms** for anything entering the mistake log.
> - *"Claude never invents an outcome. Unknown stays unknown until Josh says otherwise."*
>
> See `_INDEX.md` contradiction 8.

---

# 09 JOURNAL

The record of this desk. In the Claude Code version this file wrote itself. In a Project it cannot. Claude proposes the line, Josh pastes it in and re uploads this file. That is the whole loop, and it is the one piece of the system that depends on him, not on the model.

## How it works

1. Every fresh chart response ends with a copy ready journal line in a code block.
2. Josh pastes that line under the current month below.
3. When an outcome is known, he updates the Result field on that line.
4. He re uploads this file to the Project knowledge, at whatever rhythm he keeps. End of day is clean. End of week is the minimum for review to mean anything.
5. On REVIEW, Claude reads only what is in this file. If it is not in here, it did not happen as far as the desk is concerned.

Claude never claims to have saved anything. Claude never invents an outcome. Unknown stays unknown until Josh says otherwise.

## Line format

`YYYY-MM-DD HH:MM CT | TICKER | GRADE | direction | trigger / target / invalidation | reason | Result: unknown`

For C and NO TRADE, drop the levels and keep the reason.

`YYYY-MM-DD HH:MM CT | TICKER | C | skip | reason | Result: honored`

Honored skips get logged on purpose. The skips are the discipline, and a month of clean skips is a better record than a month of forced entries.

## Result values

* unknown. No outcome reported yet.
* taken, win. Entered on the trigger, closed green.
* taken, loss. Entered on the trigger, hit the invalidation.
* taken, broke rules. Entered outside the plan, either result. This one is the important flag.
* passed. Setup graded A or B, not taken.
* honored. Skip respected.

## Review questions

Run these against the month, not against one bad day.

* How many entries broke a rule, and which rule keeps showing up.
* How many A grades were actually taken, and how many were passed on.
* Which session window produced the most rule breaks.
* Did losses cluster right after other losses. That is the cool down gate earning its place.
* Rules followed against total trades taken, as a plain count.

Any repeated failure becomes a proposed entry for 05 MISTAKE LOG. Claude proposes it in the response. It lands in the file only after Josh confirms and pastes it.

## 2026-08

Paste entries below this line, newest at the bottom.
