

| Function | Primary DSA / Pattern | Time | Space | Sliding Window |
|----------|----------------------|------|-------|----------------|
| `find_pivot_lows` | Fixed-size sliding window minimum check | O(N×2n) | O(N) | Yes |
| `get_last_pivot_low` | Filter + last element retrieval | O(N×2n) | O(N) | Indirect |
| `is_impulsive_candle` | Constant-time rule evaluation | O(1) | O(1) | No |
| `check_bos` | Threshold crossing detection | O(N) | O(N) | No |
| `find_pivot_highs` | Fixed-size sliding window maximum check | O(N×2n) | O(N) | Yes |
| `detect_liquidity_sweep` | Pivot + suffix scan minimum | O(N×2n + N) | O(N) | Indirect |
| `find_bullish_fvg` | Single pass gap pattern detection | O(N) | O(K) | No |
| `check_fvg_retest` | Linear interval membership scan | O(K) | O(1) | No |
| `analyse_bos_fvg_setup` | Sequential pipeline with early exits | O(N×2n) dominant | O(N) | Indirect |
| `analyse_stock` | Full orchestration per symbol | O(N×2n) + network | O(N) | Indirect |

**Legend:** N = number of candles/bars, n = window size (half-width for pivot detection), K = number of FVG zones

