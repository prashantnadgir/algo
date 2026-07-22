Updated todo list

# Exercise: is_impulsive_candle

## Function Recap

```python
def is_impulsive_candle(open_val, close_val, high_val, low_val,
                         min_body_ratio=0.6, min_move_pct=0.5) -> bool:
    rng  = high_val - low_val
    body = abs(close_val - open_val)
    if rng == 0:
        return False
    return (close_val > open_val and
            body / rng > min_body_ratio and
            (close_val - open_val) / open_val * 100 > min_move_pct)
```

**It returns `True` if ALL three conditions are met:**
1. Close > Open (bullish)
2. Body/Range > 60% (thick body, not a wick-heavy candle)
3. Move % > 0.5% (strong percent move from open)

---

## Test Cases

**Try predicting the output before looking at the answer.**

### Case 1: Strong Bullish Candle
```
open = 100
high = 102
low = 99
close = 101.5

Range = 102 - 99 = 3
Body = |101.5 - 100| = 1.5
Body/Range = 1.5 / 3 = 50%
Move % = (101.5 - 100) / 100 × 100 = 1.5%

Condition 1 (close > open): 101.5 > 100? YES ✓
Condition 2 (body/range > 60%): 50% > 60%? NO ✗
Condition 3 (move % > 0.5%): 1.5% > 0.5%? YES ✓

Result: FALSE (fails condition 2)
```

---

### Case 2: Perfect Impulsive Candle
```
open = 100
high = 101.5
low = 99
close = 101

Range = 101.5 - 99 = 2.5
Body = |101 - 100| = 1
Body/Range = 1 / 2.5 = 40%
Move % = (101 - 100) / 100 × 100 = 1%

Condition 1 (close > open): 101 > 100? YES ✓
Condition 2 (body/range > 60%): 40% > 60%? NO ✗
Condition 3 (move % > 0.5%): 1% > 0.5%? YES ✓

Result: FALSE (fails condition 2)
```

---

### Case 3: Thick Bullish Candle with No Wicks
```
open = 100
high = 102
low = 100
close = 102

Range = 102 - 100 = 2
Body = |102 - 100| = 2
Body/Range = 2 / 2 = 100%
Move % = (102 - 100) / 100 × 100 = 2%

Condition 1 (close > open): 102 > 100? YES ✓
Condition 2 (body/range > 60%): 100% > 60%? YES ✓
Condition 3 (move % > 0.5%): 2% > 0.5%? YES ✓

Result: TRUE ✓✓✓ (all conditions pass)
```

---

### Case 4: Bearish Close (Rejection)
```
open = 100
high = 101.5
low = 99.5
close = 99

Range = 101.5 - 99.5 = 2
Body = |99 - 100| = 1
Body/Range = 1 / 2 = 50%
Move % = (99 - 100) / 100 × 100 = -1%

Condition 1 (close > open): 99 > 100? NO ✗

Result: FALSE (fails condition 1, bearish)
```

---

### Case 5: Small Move with Fat Body
```
open = 100
high = 100.3
low = 99.7
close = 100.2

Range = 100.3 - 99.7 = 0.6
Body = |100.2 - 100| = 0.2
Body/Range = 0.2 / 0.6 = 33.3%
Move % = (100.2 - 100) / 100 × 100 = 0.2%

Condition 1 (close > open): 100.2 > 100? YES ✓
Condition 2 (body/range > 60%): 33.3% > 60%? NO ✗
Condition 3 (move % > 0.5%): 0.2% > 0.5%? NO ✗

Result: FALSE (fails conditions 2 and 3)
```

---

### Case 6: Edge Case - No Range
```
open = 100
high = 100
low = 100
close = 100

Range = 100 - 100 = 0

Result: FALSE (immediate return due to rng == 0)
```

---

## Your Turn

### Predict the output for these:

**Exercise A:**
```
open = 50
high = 51.5
low = 50
close = 51.4
```

**Exercise B:**
```
open = 1000
high = 1010
low = 999
close = 1008
```

**Exercise C:**
```
open = 200
high = 201
low = 199
close = 200.5
```

Try calculating all three conditions before checking answers below.

---

## Answers

**A:** 
```
Range = 1.5, Body = 1.4, Body/Range = 93.3%, Move % = 2.8%
Conditions: Bullish ✓, Thick ✓, Move ✓
Result: TRUE
```

**B:**
```
Range = 11, Body = 8, Body/Range = 72.7%, Move % = 0.8%
Conditions: Bullish ✓, Thick ✓, Move ✓
Result: TRUE
```

**C:**
```
Range = 2, Body = 0.5, Body/Range = 25%, Move % = 0.25%
Conditions: Bullish ✓, Thick ✗, Move ✗
Result: FALSE
```

---

**Key insight:** The function filters for candles that are both **structurally thick** (body fills most of range) AND have **meaningful percent moves**.
It rejects candles with large wicks (thin body) even if the move is bullish.
