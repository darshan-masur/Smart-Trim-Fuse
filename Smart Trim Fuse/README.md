# Smart Trim & Fuse: Streamlit app

> **Prototype on synthetic data.** Every number is a simulation result, not a real-world saving, yield or safety
> claim. It is not a production tool and must not be used to program real fuses. See `../SAFETY_AND_LIMITATIONS.md`.
> Full setup and checks: `../RUN_GUIDE.md`. Number definitions: `../RESULTS_SOURCE_OF_TRUTH.md`.

**Smart Trim & Fuse** is the interactive website for all 9 datasets of the project. It has the same look as the SoC Smart Binning app (same
theme file, same styles, the same 4 colour themes).

## Run it

Python 3.13.1, packages pinned in `requirements.txt` (clean-install steps in `../RUN_GUIDE.md`).

```bash
cd "Smart Trim Fuse"   # from the repository root
python -m streamlit run app/streamlit_app.py
```

Checks (about 10 s): `python -m unittest discover -s tests -v`.

Then open http://localhost:8501. After installation the app needs no internet: data, models and computations are
local. Only the two web fonts come from Google Fonts; without internet a fallback font is used. Run it from this folder so `.streamlit/config.toml` (the
beige theme and fonts) is picked up.

## Pages

| Page | Datasets | What you can do |
|---|---|---|
| Overview | all 9 | The idea in 3 steps and one headline number per chip family, in plain words |
| Wafer lab | MCU, PMIC, sensor, SoC + SKU demand | Every die at its wafer position: AI trim result, MCU-C drift before/after, hidden defects, one-insertion pass/fail by grade, SoC product plan today vs optimised, working cores. Two **what-if** views with sliders: how many extra checks before falling back (MCU, PMIC), and the SoC safety margin (which chips skip the speed test), with validation vs untouched-wafer results |
| Live demo | MCU (+ fuse schema), PMIC, sensor, SoC | One die in 4 steps: what the tester measures → what the AI predicts → the check and fallback → what it saves. **Typical chip** / **Tricky chip** / **Random chip** buttons, plus the out-of-range check |
| Results | all 9 | One card per result (before → after, how, why, and the range across wafers), then tabs: across wafers, baseline vs method, model cards, why simple models won, safety rules |
| Batch check | upload or `../Demo` files | Recognise a CSV, clean it, run the right model or rule on every row, self-score, download results. Rows with missing or impossible data are *not predicted; conventional review required* (the page runs no tester flow). Fuse words: **PASS** only with an identified die and checked trim and TS_CAL1 fields, otherwise **REVIEW** or **BLOCK** |

The earlier, more detailed pages from before the redesign are kept locally only (not in the repository).

## Folders

```
app/            streamlit_app.py (navigation), theme.py (copied from the SoC app), ui.py (styles + cached loaders),
                views/ (one file per page)
tests/          focused checks: fuse and OTP rules, file recognition, missing values, wafer split, Demo files,
                headline numbers vs ../RESULTS_SOURCE_OF_TRUTH.csv, identical data / model copies
src/            config.py, common.py, mcu.py, pmic.py, sensor.py, soc.py (features, rules, optimiser, repair), batch.py,
                results.py (model comparisons recorded from notebooks 01-05)
data/           the 9 CSVs + DATA_DICTIONARY.md
models/         trim_models, pmic_models, sensor_models, soc_models (.joblib), saved by the Colab notebooks,
                and evaluation_06.json (notebook 06: wafer-by-wafer ranges, validated SoC margin, model cards)
.streamlit/     config.toml (theme, copied from the SoC app)
```

## Where the numbers come from

- **Models:** the exact `.joblib` files saved by notebooks 01-04. Nothing is retrained in the app. If you re-run a
  notebook, copy its new `.joblib` file into `models/`. Notebook 06 writes `evaluation_06.json`: copy it into
  `models/` too.
- **Live results:** every chip page recomputes its final model's results on the same held-out wafers as the
  notebooks (same split, seed 42). They match the notebooks.
- **Comparisons:** results that needed many models to be trained (all candidates, tuning, advanced checks) are recorded
  in `src/results.py` from the executed notebooks.

All data is synthetic. This is a prototype: see `../SAFETY_AND_LIMITATIONS.md` for what real use would need.
