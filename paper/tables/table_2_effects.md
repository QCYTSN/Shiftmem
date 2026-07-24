# Primary and descriptive effects

| group | difference | nominal 95% CI | n | test | p | status |
|---|---|---|---|---|---|---|
| Overall | 45.44 | [-2.72, 93.60] | 70 | wilcoxon_signed_rank_normal | 0.203 | prespecified primary, dependence-limited |
| Test-ID | -2.67 | [-60.17, 54.82] | 30 | paired_t_test | 0.925 | prespecified descriptive |
| Test-OOD | 81.53 | [9.50, 153.56] | 40 | wilcoxon_signed_rank_normal | 0.093 | prespecified descriptive |
| DeepSeek | 107.73 | [23.09, 192.37] | 35 | wilcoxon_signed_rank_normal | 0.023 | unadjusted descriptive |
| MiniMax | -16.85 | [-53.91, 20.22] | 35 | paired_t_test | 0.379 | unadjusted descriptive |
| ID: demand-jump | -67.38 | [-153.83, 19.07] | 10 | paired_t_test | 0.112 | descriptive subgroup |
| ID: gradual-demand | 50.62 | [-77.60, 178.84] | 10 | paired_t_test | 0.395 | descriptive subgroup |
| ID: supply-delay | 8.74 | [-96.67, 114.15] | 10 | paired_t_test | 0.855 | descriptive subgroup |
| OOD: early-combined | 151.24 | [-107.60, 410.08] | 10 | paired_t_test | 0.219 | descriptive subgroup |
| OOD: false-alarm | 55.26 | [-116.55, 227.07] | 10 | wilcoxon_signed_rank_exact | 0.742 | descriptive subgroup |
| OOD: periodic | -12.94 | [-49.87, 23.99] | 10 | wilcoxon_signed_rank_exact | 0.641 | descriptive subgroup |
| OOD: poisson-jump | 132.56 | [22.08, 243.04] | 10 | paired_t_test | 0.024 | descriptive subgroup |
