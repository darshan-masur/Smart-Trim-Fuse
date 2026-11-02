# Technical notes

How Smart Trim & Fuse works: the data, the approach for each chip family, how the results were validated, and what
the application does. All data is synthetic (see the main [README](../README.md)); every number is defined in
[RESULTS_SOURCE_OF_TRUTH.md](../RESULTS_SOURCE_OF_TRUTH.md).

## 1. Scope

**AI-Optimized Trim & Fuse for Derivative Chips.** Analog circuits are trimmed on the tester by a trial-and-error
search, and the results are stored in one-time fuses. The project replaces most of that search with a prediction that
is verified by a single measurement, keeps the conventional search as a fallback, and checks every fuse word with fixed
rules before it would be programmed. It covers four chip families: microcontroller (MCU), power-management IC (PMIC),
accelerometer and SoC.

## 2. Dataset

The synthetic dataset provided with the task: 9 CSV files, about 41,000 rows, four chip types, each with a large base
product and one or two small new versions. It ships with a data dictionary and its generator script.

| File | Rows | Use |
|---|---|---|
| `mcu_trim_fuse.csv` | 8,420 | MCU trims, MCU-C drift, fuse fields |
| `mcu_fuse_schema.csv` | 10 | 64-bit fuse-word layout |
| `mcu_fuse_map_audit.csv` | 1,500 | Fuse words, 406 with injected errors |
| `pmic_trim_otp.csv` | 11,060 | Power-chip trims, current sense, hidden defects |
| `pmic_otp_config_requests.csv` | 400 | Customer OTP settings |
| `sensor_calibration.csv` | 11,060 | Accelerometer calibration at −40 / 25 / 85 °C |
| `soc_binning_harvesting.csv` | 6,160 | SoC core speed, defects, products |
| `soc_sku_demand.csv` | 3 | Prices and weekly demand |
| `memory_repair_bitmaps.csv` | 3,000 | Cache fail maps for repair |

## 3. Approach by notebook

1. **00 Data overview, cleaning, EDA:** all 9 files profiled, cleaned and charted; consistency checks across files;
   first version of the fuse-word rules.
2. **01 MCU:** wafer-grouped split (25% of wafers held out, seed 42); physics-formula baseline; Ridge, Random Forest,
   XGBoost, LightGBM, HistGradientBoosting and an MLP compared; tuned with wafer-grouped cross-validation. Final model:
   Random Forest ×3 (bandgap, clock, LDO). Drift-aware bandgap target for MCU-C: a shift model learned on MCU-A and
   fine-tuned with 50 MCU-C chips.
3. **02 PMIC:** four output rails predicted from one reference reading (Ridge); threshold trims by formula;
   current-sense calibration; customer OTP settings checked by datasheet rules (100%, vs 96–98.5% for ML); hidden
   defects caught by a datasheet rule (43 / 43; Isolation Forest caught about a third).
4. **03 Sensor:** hot and cold behaviour predicted from a single 25 °C test (Ridge ×3); pass rate by product grade
   (Tight 69%, Medium 96%, Loose 98%), so the Tight grade keeps the full three-temperature test.
5. **04 SoC:** core speed predicted from on-chip monitors; predicting the product of every chip was rejected because
   the required safety margin lost revenue; an integer program matches products to demand (+34.7% in simulation);
   exact memory repair (+17 arrays over greedy).
6. **05 Advanced methods:** spatial / GNN-style features, quantile routing, GAN augmentation, RNN and reinforcement
   learning evaluated; none improved on the simple models.
7. **06 Evaluation and deployment:** each wafer held out in turn (ranges rather than one number); SoC safety margin
   chosen on validation wafers (80 MHz, zero escapes) and confirmed on untouched wafers; speed test kept only for chips
   near a product boundary (85% skip); fallback rates; a monitoring alarm tested with a simulated tester fault;
   out-of-range detection; model cards.
8. **07 SoC Vmin:** worst-core minimum voltage at 2 GHz predicted from the same monitors as the speed model (Ridge,
   4.2 mV typical error vs 27 mV for one fleet-wide value); a 25 mV safety margin chosen on validation wafers left 0 of
   1,540 untouched chips under-predicted; each wafer held out in turn gives 3.8–4.5 mV. In this dataset the AVS bin is
   set from speed, so the model adds a voltage estimate without changing the bin logic. Chips that skip the speed
   test take their AVS bin from the slower edge of the prediction: 0 of 1,306 get less voltage than they need (34% exact
   bin, 66% higher, mean +12.7 mV).
9. **08 MCU temperature sensor:** only MCU-C is measured at 110 °C, so the hot calibration point (TS_CAL2) of MCU-A
   and MCU-B is predicted from the 30 °C reading, the process monitors and die position (Ridge, trained on MCU-C).
   Typical temperature error 0.82 °C vs 3.0 °C for one fixed slope, 95% within ±2 °C, 0.78–0.87 °C per wafer. The
   gain comes from carrying the process dependence across versions; 89% of MCU-A/B chips lie outside MCU-C's process
   range, so a real flow would confirm it on a measured sample first.

## 4. Validation and controls

- **Wafer-grouped evaluation.** No wafer appears in both training and test; the base product is used for training and
  the smaller versions are never trained on. Every model result is also reported as a range across wafers.
- **Baselines.** Each model is compared with the physics formula or the conventional method, and is kept only where
  it improves the result that matters.
- **Predict, verify, fall back.** A predicted code is accepted only after a measurement confirms it; otherwise, or when
  an input is outside the training range, the chip goes through the conventional search.
- **Fuse-word rules.** A word must be exactly 64 bits, and the schema must cover every bit once. **PASS** requires a
  die identified in the sort records (unique, same product) and all 8 rules passing: product settings, security locks,
  reserved bits, trim fields and the TS_CAL1 reading. Otherwise the word is **REVIEW** or **BLOCK**.
- **Single source of truth.** Every headline number is defined with its dataset, split, seed, model and assumptions,
  and is recomputed from the saved models by an automated test.
- **Automated checks.** 40 tests: fuse and OTP rules, file recognition and cleaning, the wafer split, every Demo file,
  the headline numbers, identical data copies and colour contrast.
- **Reproducibility.** Python 3.13.1 with 48 pinned packages; a clean install has been tested.

## 5. Application

A Streamlit app that loads the saved models (nothing is retrained in the app):

- **Overview:** the workflow, including the fallback path, and the headline results.
- **Wafer lab:** every die of a held-out wafer, with what-if sliders for the number of checks and the SoC margin.
- **Live demo:** one chip in four steps; on a tricky chip the rejected prediction and the conventional search are
  shown, followed by the 64-bit fuse-word check.
- **Results:** wafer-by-wafer ranges, baselines, model cards and the methods that did not help.
- **Batch check:** upload a CSV; it is recognised by its columns, cleaned, and checked row by row. Rows with missing or
  impossible data are not predicted and are marked for conventional review.

Status is always shown with a symbol as well as a colour (✓ good, • attention, × fallback, – neutral), and every page
carries the synthetic-data notice.

## 6. Limitations and next steps

- The data is synthetic, so the size of every gain must be confirmed on real wafers, first in shadow mode beside the
  conventional flow.
- The MCU-C result rests on two wafers, and the SoC revenue gain on three synthetic rows of prices and demand.
- This is a prototype: no ISO 26262 or other compliance is claimed, and it must not be used to program real fuses
  (see [SAFETY_AND_LIMITATIONS.md](../SAFETY_AND_LIMITATIONS.md)).
