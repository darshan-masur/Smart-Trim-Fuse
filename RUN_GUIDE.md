# Run guide: from a clean machine to every result

Prototype on **synthetic data only** (see [`SAFETY_AND_LIMITATIONS.md`](SAFETY_AND_LIMITATIONS.md)).

## 0. What you need

| Item | Version checked | Notes |
|---|---|---|
| Python | **3.13.1**, 64-bit | Checked on Windows 11. Other 3.13.x versions should work. |
| Packages | `Smart Trim Fuse/requirements.txt` | 48 packages, all pinned, dependencies included. **scikit-learn must be 1.9.0**: the saved models were made with it. |
| Notebooks (optional) | `Smart Trim Fuse/requirements-notebooks.txt` | Adds matplotlib, seaborn, xgboost, lightgbm and Jupyter. |
| Disk | about 1 GB | Mostly the virtual environment. |

**Windows path length:** create the virtual environment in a short folder path. On 1 Nov 2026 a clean install
failed inside a very long temp path, because scikit-learn has deeply nested files and Windows limits paths to 260
characters by default. The fix is a shorter folder, or enabling Windows long paths.

## 1. Clean install (one time, needs internet)

```bash
cd "Smart Trim Fuse"   # from the repository root
```

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

```bash
.venv/Scripts/python -m pip check
```

On macOS / Linux, use `.venv/bin/python` instead of `.venv/Scripts/python`. Tested on a fresh
environment: all 48 pinned packages installed, `pip check` found no conflicts, all tests passed, and all 5 app pages
loaded with no errors.

## 2. Run the checks (about 10 s)

```bash
.venv/Scripts/python -m unittest discover -s tests -v
```

39 checks in 7 files:

| File | What it checks |
|---|---|
| `tests/test_fuse_rules.py` | The schema covers all 64 bits exactly once. Malformed words (too short or long, not hex, no `0x`) are blocked, never truncated. **PASS only** with a unique die_id found in the sort records and checked trim and TS_CAL1 fields (8 rules, every field covered); otherwise REVIEW or BLOCK. A wrong TS_CAL1 is blocked. 406 / 406 audit errors are caught with 0 false alarms. |
| `tests/test_otp_rules.py` | Each OTP rule; the first broken rule wins; an unreadable address is never "valid"; the dataset and Demo labels match. |
| `tests/test_batch_files.py` | File recognition (including an MCU file missing one column). Missing, text and impossible values are never predicted. The messy file's counts add up. **Every Demo file matches `Demo/expected_results.csv`.** |
| `tests/test_wafer_split.py` | No wafer in both training and test; about 25% of wafers held out; reproducible with seed 42; Demo files never use training wafers. |
| `tests/test_headline_numbers.py` | Every value in `RESULTS_SOURCE_OF_TRUTH.csv` is recomputed from the saved models and `evaluation_06.json`. |
| `tests/test_project_files.py` | The data and model copies listed in `PROJECT_MAP.md` stay identical to the canonical files. |
| `tests/test_theme.py` | All 4 colour themes pass WCAG AA contrast; icons are drawings that never print a word. |

## 3. Start the website

```bash
.venv/Scripts/python -m streamlit run app/streamlit_app.py
```

Open http://localhost:8501. Run it from the `Smart Trim Fuse` folder so `.streamlit/config.toml` is picked up.
From the repository root, `streamlit run "Smart Trim Fuse/app/streamlit_app.py"` works too (the root has its own copy
of the config, as Streamlit Community Cloud needs).

**What "offline" means:**

- Installing packages needs internet once.
- After that, the app needs no internet. All data, models and computations are local, and it calls no external API.
- The two fonts (DM Sans, Bricolage Grotesque) load from Google Fonts. Without internet the browser uses a fallback
  font, and everything else works the same. The icons are bundled with Streamlit.
- Streamlit usage statistics are switched off (`gatherUsageStats = false`).
- The first start computes the headline numbers from the models (a few seconds) and caches them on disk.

## 4. Check the Batch page by hand (optional)

Open **Batch check**, choose **Use a Demo file**, and compare each file with `Demo/README.md` or
`Demo/expected_results.csv`. The same comparison runs automatically in `tests/test_batch_files.py`.

## 5. Re-run the notebooks (optional, start to finish)

The notebooks are in `Colab Notebook/`. Run them **in this order**, each with *Run all*:

| Order | Notebook | Writes |
|---|---|---|
| 1 | `00_Data_Overview_Cleaning_EDA.ipynb` | `cleaned/*.csv` (for exploration only; the models use the raw CSVs) |
| 2 | `01_MCU_Trim_Fuse.ipynb` | `trim_models.joblib` |
| 3 | `02_PMIC_Trim_OTP.ipynb` | `pmic_models.joblib` |
| 4 | `03_Sensor_Calibration.ipynb` | `sensor_models.joblib` |
| 5 | `04_SoC_Binning_Repair.ipynb` | `soc_models.joblib` |
| 6 | `05_Advanced_Methods_Check.ipynb` | nothing (comparison only) |
| 7 | `06_Evaluation_and_Deployment.ipynb` | `evaluation_06.json` |
| 8 | `07_SoC_Vmin_Prediction.ipynb` | `vmin_models.joblib` |

- **Locally:** install `requirements-notebooks.txt` into the same environment, then open the folder in Jupyter or
  VS Code. The 9 CSVs are already next to the notebooks.
- **In Colab:** upload the notebook. When asked, upload the dataset CSVs (and for 05/06, the `.joblib` files made by
  01–04). Notebook 06 installs scikit-learn 1.9.0 if needed. Restart the session when it says so.
- All splits use `random_state = 42`, so a re-run reproduces the same wafers and the same numbers. Tree models use
  their own seeds too. A different scikit-learn version may change the last digit.

**After a re-run:** copy the 5 `.joblib` files and `evaluation_06.json` into `Smart Trim Fuse/models/`, then
re-run step 2. `test_headline_numbers.py` tells you if any headline moved. If one did, update
`RESULTS_SOURCE_OF_TRUTH.csv` / `.md` first, then the deck, report and dashboard.

## 6. Regenerate the synthetic data (optional)

The data generator came with the dataset:
`AI Trim & Fuse/Dataset/trimfuse_synthetic_dataset/trimfuse_synth/generate_synthetic_data.py` (see its README).
A different `--seed` gives a different draw, and every number in this project would change. Only the default seed
is checked.

## 7. Build the submission zip (optional)

From the repository root:

```bash
python make_submission.py
```

This writes `Smart_Trim_Fuse_submission.zip` with the canonical files only (see
[`PROJECT_MAP.md`](PROJECT_MAP.md)). Virtual environments, caches, bytecode, editor settings, backups and
regenerable outputs are left out.
