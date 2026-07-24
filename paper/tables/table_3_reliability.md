# Reliability and context burden

| split | model | method | cells | attempts | failed/invalid attempts | failed/invalid rate | reviews | fallbacks | fallback rate | input tokens | output tokens | recovered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Test-ID | DeepSeek | ShiftMem | 20 | 681 | 3 | 0.4% | 678 | 0 | 0.0% | 4476701 | 68232 | 8/15 |
| Test-ID | DeepSeek | Lexical baseline | 20 | 625 | 39 | 6.2% | 600 | 14 | 2.3% | 3711109 | 60558 | 7/15 |
| Test-ID | MiniMax | ShiftMem | 20 | 966 | 506 | 52.4% | 677 | 217 | 32.1% | 2819601 | 412821 | 13/15 |
| Test-ID | MiniMax | Lexical baseline | 20 | 867 | 462 | 53.3% | 600 | 195 | 32.5% | 2440632 | 359232 | 10/15 |
| Test-OOD | DeepSeek | ShiftMem | 20 | 761 | 96 | 12.6% | 709 | 44 | 6.2% | 4421885 | 63979 | 4/20 |
| Test-OOD | DeepSeek | Lexical baseline | 20 | 667 | 129 | 19.3% | 600 | 62 | 10.3% | 3449941 | 55912 | 6/20 |
| Test-OOD | MiniMax | ShiftMem | 20 | 876 | 237 | 27.1% | 712 | 73 | 10.3% | 4048546 | 579335 | 7/20 |
| Test-OOD | MiniMax | Lexical baseline | 20 | 746 | 208 | 27.9% | 600 | 62 | 10.3% | 3348830 | 484359 | 6/20 |
