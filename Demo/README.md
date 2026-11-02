# Demo: batch test files for Smart Trim & Fuse

Use these files to check by hand that the website works. Each one tests something different. The same table is checked automatically by `Smart Trim Fuse/tests/test_batch_files.py` (see `RUN_GUIDE.md`).

**All files are synthetic.** They show how the prototype behaves on simulated data; they say nothing about real chips.

## How to use

1. Start the website: run `python -m streamlit run app/streamlit_app.py` in the `Smart Trim Fuse` folder (or open the live link in the main README).
2. Open the **Batch check** page.
3. Choose **Use a Demo file** and pick a file, or choose **Upload my own CSV** and upload one of these files.
4. Compare what you see with the table below (the same table is in `expected_results.csv`).

## The files

| File | What it tests |
|---|---|
| `01_mcu_unseen_wafer_40_dies.csv` | 40 MCU dies from wafers the model never saw. Predicts the bandgap, HSI and LDO trim codes and scores itself against the true codes. |
| `02_mcu_messy_export.csv` | A messy export: 3 duplicate rows, 2 re-tested dies, a negative and a zero voltage, 2 missing values, "n/a" typed into a number column, TRUE/FALSE as text, and an extra column. The page must clean it and refuse to predict the 5 broken rows. |
| `03_pmic_new_derivatives_30_dies.csv` | 30 PMIC dies of the P2 and C7 derivatives, which the model was **not** trained on. Predicts all 4 rail codes from the reference only. |
| `04_sensor_production_25_dies.csv` | 25 production accelerometers (25 °C data only). Predicts the temperature coefficients for all 3 axes. |
| `05_soc_unseen_wafers_40_dies.csv` | 40 SoC dies from unseen wafers. Predicts core speed and the product (with the 80 MHz guard band). Must show 0 % unsafe. |
| `06_otp_customer_requests_12.csv` | 12 new customer requests written by hand, covering every rule: valid, out of range, reserved address, address collision, invalid sequence, sequence conflict, and one with two problems at once. |
| `07_fuse_words_20.csv` | 20 MCU fuse words: 12 with an injected error (2 of every error type) and 8 good ones. Every error must be blocked, with no false alarms. |
| `09_fuse_edge_cases_15.csv` | 15 fuse words that test the verdicts: **PASS** only for a well-formed word on a die found in the sort records (unique, same product) with its trim fields and TS_CAL1 reading checked; **REVIEW** for an unknown, blank, badly formed, duplicated or mismatched die_id; **BLOCK** for a word that is too short, too long, not hex, missing `0x`, for an unknown product, or with a wrong trim field. |
| `08_wrong_file_sales_report.csv` | Not test data at all (a sales table). The page must say it is not recognised and run nothing. |
| `10_mcu_defective_dies_20.csv` | 20 MCU dies, **6 of them really defective** (the dataset's latent defects): their untrimmed bandgap is 49-80 mV away from what a healthy die with the same process would read. All 6 must be flagged and get no AI code; the 14 healthy dies must not be flagged. |
| `11_pmic_hidden_defects_20.csv` | 20 power chips, **6 with hidden defects**: low efficiency at 1 A or poor load regulation (datasheet limits 88% and 10 mV). |
| `12_sensor_defective_mems_20.csv` | 20 accelerometers, **6 with a defective MEMS structure**: the resonance is 7-14% lower than the process predicts (limit -5%). |
| `13_soc_defective_chips_20.csv` | 20 SoC dies, **7 with structural defects**: an L2 cache that can't be repaired or too many bad cores (scrap), or 2-3 bad cores (sold as a smaller product). |

## What you should see

| File | Recognised as | Rows in file / removed / checked / not predicted | Cleaning the page reports | Result summary |
|---|---|---|---|---|
| `01_mcu_unseen_wafer_40_dies.csv` | MCU dies (trim prediction) | 40 / 0 / 40 / 0 | nothing to clean | Dies flagged as defective = 0 of 40; Known defects caught = 0 of 0; Healthy dies flagged (false alarms) = 0; Bandgap: exact = 80.0%; Bandgap: within ±1 code = 100.0%; HSI oscillator: exact = 72.5%; HSI oscillator: within ±1 code = 87.5%; LDO regulator: exact = 92.5%; LDO regulator: within ±1 code = 100.0% |
| `02_mcu_messy_export.csv` | MCU dies (trim prediction) | 30 / 5 / 20 / 5 | Exact duplicate rows: 3; Repeated die_id (re-tested): 2; Impossible values (zero or negative): 2; Rows with a blank required value: 5 | Dies flagged as defective = 0 of 25; Known defects caught = 0 of 0; Healthy dies flagged (false alarms) = 0; Bandgap: exact = 80.0%; Bandgap: within ±1 code = 100.0%; HSI oscillator: exact = 40.0%; HSI oscillator: within ±1 code = 70.0%; LDO regulator: exact = 90.0%; LDO regulator: within ±1 code = 100.0% |
| `03_pmic_new_derivatives_30_dies.csv` | PMIC dies (rail prediction) | 30 / 0 / 30 / 0 | nothing to clean | Dies flagged as defective = 0 of 30; Known defects caught = 0 of 0; Healthy dies flagged (false alarms) = 0; buck1: exact = 50.0%; buck1: within ±1 code = 96.7%; buck2: exact = 26.7%; buck2: within ±1 code = 93.3%; ldo1: exact = 50.0%; ldo1: within ±1 code = 93.3%; ldo2: exact = 60.0%; ldo2: within ±1 code = 96.7% |
| `04_sensor_production_25_dies.csv` | Sensor dies (25 °C calibration) | 25 / 0 / 25 / 0 | nothing to clean | Dies flagged as defective = 0 of 25; Known defects caught = 0 of 0; Healthy dies flagged (false alarms) = 0; TCO x: mean error (mg/°C) = 0.045; TCO y: mean error (mg/°C) = 0.058; TCO z: mean error (mg/°C) = 0.052 |
| `05_soc_unseen_wafers_40_dies.csv` | SoC dies (speed and product) | 40 / 0 / 40 / 0 | nothing to clean | Dies with a structural defect = 16 of 40; Sold with fewer cores (harvested) = 16; Scrapped = 0; Same product as the full speed test = 92.5%; Product higher than the speed test (over-graded) = 0.0% |
| `06_otp_customer_requests_12.csv` | Customer OTP requests | 12 / 0 / 12 / 0 | nothing to clean | Valid requests = 3 of 12; Matches the expected label = 100% |
| `07_fuse_words_20.csv` | MCU fuse words | 20 / 0 / 20 / 0 | nothing to clean | Words blocked = 12 of 20; Words needing review = 0 of 20; Injected errors caught = 12 of 12; False alarms = 0 |
| `08_wrong_file_sales_report.csv` | not recognised | - | The page explains which columns are expected; nothing is run. |  |
| `09_fuse_edge_cases_15.csv` | MCU fuse words | 15 / 0 / 15 / 0 | nothing to clean | Words blocked = 6 of 15; Words needing review = 6 of 15; Matches the expected verdict = 100% |
| `10_mcu_defective_dies_20.csv` | MCU dies (trim prediction) | 20 / 0 / 20 / 0 | nothing to clean | Dies flagged as defective = 6 of 20; Known defects caught = 6 of 6; Healthy dies flagged (false alarms) = 0; Bandgap: exact = 57.1%; Bandgap: within ±1 code = 100.0%; HSI oscillator: exact = 28.6%; HSI oscillator: within ±1 code = 78.6%; LDO regulator: exact = 100.0%; LDO regulator: within ±1 code = 100.0% |
| `11_pmic_hidden_defects_20.csv` | PMIC dies (rail prediction) | 20 / 0 / 20 / 0 | nothing to clean | Dies flagged as defective = 6 of 20; Known defects caught = 6 of 6; Healthy dies flagged (false alarms) = 0; buck1: exact = 35.7%; buck1: within ±1 code = 92.9%; buck2: exact = 28.6%; buck2: within ±1 code = 92.9%; ldo1: exact = 50.0%; ldo1: within ±1 code = 92.9%; ldo2: exact = 35.7%; ldo2: within ±1 code = 78.6% |
| `12_sensor_defective_mems_20.csv` | Sensor dies (25 °C calibration) | 20 / 0 / 20 / 0 | nothing to clean | Dies flagged as defective = 6 of 20; Known defects caught = 6 of 6; Healthy dies flagged (false alarms) = 0; TCO x: mean error (mg/°C) = 0.035; TCO y: mean error (mg/°C) = 0.039; TCO z: mean error (mg/°C) = 0.042 |
| `13_soc_defective_chips_20.csv` | SoC dies (speed and product) | 20 / 0 / 20 / 0 | nothing to clean | Dies with a structural defect = 7 of 20; Sold with fewer cores (harvested) = 5; Scrapped = 2; Same product as the full speed test = 90.0%; Product higher than the speed test (over-graded) = 0.0% |

## The defective dies (files 10-13)

The rows are copied unchanged from the project datasets, from wafers the models never trained on. The dataset marks
each true defect (`latent_defect`); the page does not use that column to decide, only to score itself.

| File | Defective dies | What is wrong | What the page does |
|---|---|---|---|
| `10_mcu_defective_dies_20.csv` | MCU-000219, MCU-000322, MCU-003855 (MCU-A), MCU-006893 (MCU-B), MCU-007731, MCU-007772 (MCU-C) | Bandgap 49-80 mV off; all 6 fail final test in the dataset | No AI trim code; conventional flow + failure analysis |
| `11_pmic_hidden_defects_20.csv` | PMIC-000312, PMIC-000543, PMIC-005231 (P1), PMIC-008597, PMIC-008886 (P2), PMIC-010286 (C7) | Efficiency below 88% and / or load regulation above 10 mV; all 6 fail final test | No AI rail codes; conventional flow + failure analysis |
| `12_sensor_defective_mems_20.csv` | SNS-000508, SNS-000516, SNS-005081 (2G), SNS-008523, SNS-008649 (8G), SNS-010387 (16G) | MEMS resonance 7-14% low | No AI calibration; conventional flow + failure analysis |
| `13_soc_defective_chips_20.csv` | SOC-000042 (L2 not repairable), SOC-004888 (4 bad cores, no product it can meet) → scrap; SOC-000014, -026, -028 (3 bad cores) → SoC-Lite; SOC-000001, -005 (2 bad cores) → SoC-Std | Structural test failures | Scrapped or sold with fewer cores, the same product as the conventional flow |

How the MCU and sensor screens work: a robust linear model, fitted on the base product's training wafers only,
predicts what a **healthy** die with the same process monitors and position should read. A die far from that is
flagged (MCU bandgap more than 25 mV away, sensor resonance more than 5% low). On every wafer the models never trained
on, this catches all the defects (MCU 14 of 14, sensor 15 of 15, PMIC 16 of 16) with no healthy die flagged; healthy
dies stay within 14 mV and -3.7%. Synthetic data: on real chips the limits would be set from real failure analysis.

Fuse-word verdicts: **PASS** = every rule checked and passed (every field of the word is covered by a rule); **BLOCK** = a rule failed or the word is unreadable; **REVIEW** = the rules that could run pass, but the die or its trim codes could not be confirmed (never burned automatically). "Not predicted" rows are marked *conventional review required*: the page itself runs no tester flow.

All data is synthetic. The files were made from the project's datasets, using only wafers, derivatives or requests the models were not trained on.
