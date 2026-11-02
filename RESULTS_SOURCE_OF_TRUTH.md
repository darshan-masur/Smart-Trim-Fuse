# Results: single source of truth

**Every number here comes from a simulation on synthetic data.** No real chips, testers, fabs or customers were
involved. The numbers show how the methods behave on data built to resemble real data. They are not real savings,
yield or quality results.

The machine-readable version is [`RESULTS_SOURCE_OF_TRUTH.csv`](RESULTS_SOURCE_OF_TRUTH.csv). It holds one row per
headline, with its dataset, rows evaluated, split, seed, model, metric definition, assumptions, wafer range and the
code that computes it. `Smart Trim Fuse/tests/test_headline_numbers.py` recomputes every value from the saved models
and fails if one no longer matches. The app, slides, report, dashboard and interview material quote **only** these
numbers (the Power BI dashboard and the interview material are kept locally, not in this repository).

## Result types

| Type | Meaning |
|---|---|
| **Measured on held-out synthetic data** | The model never saw these wafers. Counted directly from the data. |
| **Modelled (simulation + assumed timing)** | A count (tries, oven passes) turned into time with an assumed time per step. The assumption is in the table. |
| **Optimiser on synthetic inputs** | No model is trained. The gain depends on synthetic prices, demand or bitmaps. |
| **Rule check on synthetic labels / injected errors** | Shows the rules are implemented as specified. Not proof that they cover every real-world error. |

## Headlines

| ID | Headline | Type | Evaluated on | Range across wafers |
|---|---|---|---|---|
| MCU_TIME | MCU trimming 28.7 → 7.4 ms per chip (**3.9×**) | Modelled | 1,684 MCU-A dies, 4 held-out wafers | 2.9× to 4.7× (15 wafers) |
| MCU_NOSEARCH | **83%** of MCU chips need no search (formula alone: 70%) | Measured | same | 67% to 91% |
| MCU_TRIES | MCU tries per chip **19.8 → 4.8** | Measured (try model) | 15 wafers, one held out at a time | median |
| MCUC_DRIFT | MCU-C final-test pass **90.7% → 99.4%** | Measured, **early: 2 wafers only** | 421 dies per wafer, each wafer tested once | 99.0% to 99.8% |
| PMIC_TRIES | Power chip **44.7 → 11.5** tries (**3.9×**) | Measured (try model) | 2,212 PMIC-P1 dies, 4 held-out wafers | 3.6× to 4.0×; P2/C7 3.5× to 3.9× |
| PMIC_NOSEARCH | **79%** of power chips need no search | Measured | same | 71% to 83% |
| SENSOR_TIME | Sensor 7.2 → **2.6 s** per chip, Medium / Loose grades only | Modelled | ACC-2G production dies, 4 held-out wafers | - |
| SENSOR_PASS | **96%** of Medium-grade chips within limits after 1 oven pass | Measured | same | 95% to 97% (Tight: 66% to 71%) |
| SOC_REVENUE | SoC **+34.7%** revenue a week ($356,665 → $480,470) | Optimiser | all 6,160 dies, synthetic prices / demand | +33% to +58% per wafer |
| SOC_SKIP | **85%** of SoC chips skip the speed test, 0 of 1,540 over-graded | Measured | 5 held-out wafers; margin chosen on validation wafers | 95% upper bound on over-grading ≈ 0.19% |
| FUSE_CHECK | **406 / 406** injected fuse-map errors caught, 0 false alarms | Rule check | all 1,500 audit words | - |
| OTP_CHECK | **400 / 400** customer requests judged as labelled | Rule check | all 400 requests | - |
| REPAIR | Exact repair saves **17** more arrays than greedy (1,860 vs 1,843) | Optimiser | 3,000 bitmaps | - |
| SOC_VMIN | SoC worst-core Vmin predicted with **4.2 mV** typical error (median baseline 27 mV); a **25 mV** margin left 0 of 1,540 chips under-predicted | Measured | 5 held-out wafers; margin chosen on validation wafers | 3.8–4.5 mV; 95% upper bound on under-prediction ≈ 0.19% |

**Split used everywhere:** `GroupShuffleSplit` by `wafer_id`. 25% of the base version's wafers are held out, with
`random_state = 42` (`src/common.py wafer_split`). No wafer is ever on both sides. The base versions are MCU-A,
PMIC-P1, ACC-2G and the one SoC die. Other versions (MCU-B/C, PMIC-P2/C7, ACC-8G/16G) are never used for training.
`tests/test_wafer_split.py` checks this.

## Why `baseline_results.txt` shows different numbers

`AI Trim & Fuse/Dataset/.../baseline_results.txt` came **with the dataset**. The dataset author wrote it to show that
each use case can be learned. It uses simpler models, other metrics and its own sampling, so it is a reference
point, not a result of this project.

| Topic | baseline_results.txt | This project | Reason |
|---|---|---|---|
| MCU trims | bandgap exact 75.8%, HSI 47.3%, LDO 89.4% (per trim) | 83% of dies need no search (all 3 trims within 1 code) | Different metric; physics features and tuning (notebook 01) |
| MCU-C drift | 90.9% → 99.4% | 90.7% → 99.4% (99.0–99.8%) | Different sampling; the same conclusion |
| PMIC rails | within 1 code: 83–91% per rail | 79% of dies have all 4 rails within 1 code | Per rail vs all rails at once |
| Sensor | TCO R² 0.84, TCS R² 0.94 | 96% of Medium-grade dies within limits | Model fit vs pass rate |
| SoC | rule-based product mix only | +34.7% revenue from the optimiser | The baseline does not compute revenue |
| Fuse maps | 406 / 406, 0 false alarms | 406 / 406, 0 false alarms | Same |
| Memory repair | greedy 61.4%, exact 62.0%, 17 saved | 1,843 vs 1,860 of 3,000, 17 saved | Same |

## Assumptions that change the size of the numbers

- **Time per measurement** (MCU: bandgap 1.2 ms, HSI 2.0 ms, LDO 1.0 ms) and **one oven pass = 1/3 of the
  3-temperature test** (sensor) are assumptions, not measurements. Real tester overheads would shrink the speed-ups.
- **Try model:** 1 try if the predicted code is exact, 2 if it is 1 code off, otherwise a full binary search.
- **Sensor escapes:** about 4% of Medium-grade chips would be outside the limit after one oven pass. Only the 5%
  monitoring sample would catch some of them.
- **SoC revenue** depends entirely on 3 synthetic rows of prices and demand.
- **Rule checks** (fuse, OTP) are scored against labels made by the same generator rules. They prove the
  implementation, not the completeness of the rules.
