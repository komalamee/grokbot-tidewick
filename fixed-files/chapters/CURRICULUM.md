# Curriculum map: v1 (16 chapters)

Season 1 Beginner (chapters 1–10) and Season 2 Intermediate (11–16). One options idea per chapter, at most two objectives. Story is not here. Titles are working titles. Every number below is checked by `tests/test_curriculum.py`; model prices come from `engine/case_maths.py` with the inputs stated, and are not market quotes. Cases are fictional pounds. Each chapter's case stands alone unless it says otherwise.

Status key: **worked** = full chapter file with checked numbers and placeholder story · **mapped** = concept, objectives and a checked case sketch only.

## Season 1: Beginner

| # | Working title | The one idea | Objectives | Case sketch (checked) | Optional panel | Status |
|---|---|---|---|---|---|---|
| 1 | A right and a promise | An option is a right bought for a fee; the seller takes on a promise | Right v promise; the fee is paid up front and kept by the seller | Sell a put: 10 crates at £10, fee £8. Ends £12 → +£8. At £7 → −£22. Breakeven £9.20. Worst −£92 | Put, premium, strike, expiry, exercise/assignment | worked |
| 2 | Money set aside | A cash-secured put sets aside the full price you've promised; the fee isn't the result yet | Cash set aside v cash free to use; premium is not profit | £480 cash. A: £12 agreed, fee £9, set aside £120, free £369. B: £11, £5, £110, £375. Ends £13 → +£9 / +£5. At £10 → −£11 / −£5 | Cash-secured put, breakeven, moneyness | worked |
| 3 | When the price falls | Assignment: you buy at the agreed price even when the market is lower; quantity and agreed price set the downside | Assignment; size of the downside | £480 cash, sell put 10 at £10 for £8, ends £7: cash £388, crates worth £70, wealth £458, result −£22. Twice the quantity: −£44. Crates worth £0: −£92 | Assignment, ITM/OTM at expiry | mapped |
| 4 | Time and the end date | Expiry ends the right; more time means a bigger fee and a longer commitment, not a free extra | Expiry; time and fee | Model put, price £10, agreed £10, 40% volatility, no interest: 30 days £0.46/crate (£4.57 for 10), 90 days £0.79 (£7.91). Three times as long is not three times the fee | Time value, theta | mapped |
| 5 | Owning the goods | After assignment you own the goods and their risk; the fee lowers your cost but doesn't promise recovery | Ownership risk; effective cost | Bought 10 at £10 (£100) after a £8 fee: effective cost £92. Now worth £70: paper loss £22. No rebound is promised | Cost basis | mapped |
| 6 | Buying a call | A bought call is a right to buy; you can be right about direction and still lose the fee | Long call; breakeven | Buy call, 10 units, agreed £10, fee £1/unit (£10). Ends £9 → −£10; £10.50 → −£5; £13 → +£20. Breakeven £11 | Call option, delta (not an exact probability: e.g. 30-day model delta 0.52 v model chance of ending above £10 0.48) | mapped |
| 7 | A fee for your goods | A covered call earns a fee on goods you own but gives up rises above the agreed price | Covered call; upside given up | Own 10 at £10, sell call at £12 for £1/unit. Ends £15 → +£30 (owning alone +£50, so £20 given up). Ends £5 → −£40 (fee softens, doesn't remove, the £50 fall). Most you can make £30 | Covered call, called away | mapped |
| 8 | Leaving before the end | You can close early by buying back a promise or selling a right; quotes and costs decide the result | Buy to close / sell to close; costs and the bid/ask gap | Sold for £8, buy back at £11 + £1 cost → −£4. Bought for £10, sell at £7 − £1 cost → −£4 | Bid/ask spread, closing trades | mapped |
| 9 | Paper loss, real loss | A loss on goods you still hold is unrealised; selling makes it realised, but your wealth doesn't drop twice | Realised v unrealised | Cash £388 + crates marked at £70 = £458 before selling; sell at £70 → cash £458. Same wealth, the loss is now realised | Realised/unrealised, mark to market | mapped |
| 10 | Judging a decision | Judge a decision by what you knew when you made it, not by one result | Process v outcome; compare your reason with what happened | Same promise as ch1, two endings: £12 → +£8, £7 → −£22. Same decision, same information. Season 1 finale: the player's saved reasons come back | (none: reflection chapter) | mapped |

## Season 2: Intermediate

| # | Working title | The one idea | Objectives | Case sketch (checked) | Optional panel | Status |
|---|---|---|---|---|---|---|
| 11 | Paying for uncertainty | An option's price = what it's worth if used now + time value; implied volatility is the expected size of moves, not their direction | Intrinsic v time value; implied volatility | Model call, price £12, agreed £10, 90 days, no interest: worth £2 used now. At 30% volatility £2.09; 40% £2.21; 50% £2.36. Only the time value changes | Implied volatility, vega (90-day at-the-money call, 30% → 31%: about +£0.02 a unit) | mapped |
| 12 | One pot of cash | Every promise shares one pot of cash; size scales the risk, not just the fees | Position size; shared capital | £300 cash. Promise 1: 10 at £10 for £8. Promise 2: 10 at £15 for £12. Both: cash £320, set aside £250, free £70. Only 1: free £208. Only 2: free £162 | Position sizing | mapped |
| 13 | Hidden in common | Different goods can fall together if they share one cause; a winning record can hide it | Concentration; stress test | Three promises on goods that all depend on one buyer. Numbers to be authored with the story (stress table) | Correlation | mapped (case to write) |
| 14 | Many small wins | Lots of small wins can hide one big loss; weigh the fee against the size of the loss | Small wins v tail loss; weighted outcomes | Clearly made-up teaching odds: +£5 nine times, −£80 once → 9 × £5 − £80 = −£35. Per try at those odds: 0.9 × £5 − 0.1 × £80 = −£3.50 | Expected value (labelled as made-up odds, not real frequencies) | mapped |
| 15 | The shock | One shared shock can hit several promises at once; having enough money isn't the same as having cash to use | Shared shock; solvency v usable cash | Two cash-secured puts: 10 at £10 for £8 (ends £6) → −£32; 10 at £15 for £12 (ends £9) → −£48. Total −£80 | Liquidity | mapped |
| 16 | Counting what's left | Rebuild from an honest list of what you have and owe, keeping a cash buffer rather than chasing a target | Balance sheet; rebuild with a buffer | Cash £20 + goods £60 − debt £30 = £50. A paid job earns £25 → £75, cash £45; the debt is still £30 until paid. Season 2 finale | Balance sheet | mapped |

## Boundaries (v1)

- No uncovered (naked) calls, no margin, no spreads, no Greeks as required maths. Those belong to the Advanced season.
- Panels name real terms after the player has met the idea. They are optional and never block the story.
- Delta is never presented as an exact probability. Selling options is never framed as always coming out ahead. No promise that prices recover.
- Clues never depend on the result of a case.
