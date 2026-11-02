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

## What you should see

| File | Recognised as | Rows in file / removed / checked / not predicted | Cleaning the page reports | Result summary |
|---|---|---|---|---|
| `01_mcu_unseen_wafer_40_dies.csv` | MCU dies (trim prediction) | 40 / 0 / 40 / 0 | nothing to clean | Bandgap: exact = 80.0%; Bandgap: within ±1 code = 100.0%; HSI oscillator: exact = 72.5%; HSI oscillator: within ±1 code = 87.5%; LDO regulator: exact = 92.5%; LDO regulator: within ±1 code = 100.0% |
| `02_mcu_messy_export.csv` | MCU dies (trim prediction) | 30 / 5 / 20 / 5 | Exact duplicate rows: 3; Repeated die_id (re-tested): 2; Impossible values (zero or negative): 2; Rows with a blank required value: 5 | Bandgap: exact = 80.0%; Bandgap: within ±1 code = 100.0%; HSI oscillator: exact = 40.0%; HSI oscillator: within ±1 code = 70.0%; LDO regulator: exact = 90.0%; LDO regulator: within ±1 code = 100.0% |
| `03_pmic_new_derivatives_30_dies.csv` | PMIC dies (rail prediction) | 30 / 0 / 30 / 0 | nothing to clean | buck1: exact = 50.0%; buck1: within ±1 code = 96.7%; buck2: exact = 26.7%; buck2: within ±1 code = 93.3%; ldo1: exact = 50.0%; ldo1: within ±1 code = 93.3%; ldo2: exact = 60.0%; ldo2: within ±1 code = 96.7% |
| `04_sensor_production_25_dies.csv` | Sensor dies (25 °C calibration) | 25 / 0 / 25 / 0 | nothing to clean | TCO x: mean error (mg/°C) = 0.045; TCO y: mean error (mg/°C) = 0.058; TCO z: mean error (mg/°C) = 0.052 |
| `05_soc_unseen_wafers_40_dies.csv` | SoC dies (speed and product) | 40 / 0 / 40 / 0 | nothing to clean | Same product as the full speed test = 92.5%; Product higher than the speed test (over-graded) = 0.0% |
| `06_otp_customer_requests_12.csv` | Customer OTP requests | 12 / 0 / 12 / 0 | nothing to clean | Valid requests = 3 of 12; Matches the expected label = 100% |
| `07_fuse_words_20.csv` | MCU fuse words | 20 / 0 / 20 / 0 | nothing to clean | Words blocked = 12 of 20; Words needing review = 0 of 20; Injected errors caught = 12 of 12; False alarms = 0 |
| `08_wrong_file_sales_report.csv` | not recognised | - | The page explains which columns are expected; nothing is run. |  |
| `09_fuse_edge_cases_15.csv` | MCU fuse words | 15 / 0 / 15 / 0 | nothing to clean | Words blocked = 6 of 15; Words needing review = 6 of 15; Matches the expected verdict = 100% |

Fuse-word verdicts: **PASS** = every rule checked and passed (every field of the word is covered by a rule); **BLOCK** = a rule failed or the word is unreadable; **REVIEW** = the rules that could run pass, but the die or its trim codes could not be confirmed (never burned automatically). "Not predicted" rows are marked *conventional review required*: the page itself runs no tester flow.

All data is synthetic. The files were made from the project's datasets, using only wafers, derivatives or requests the models were not trained on.
