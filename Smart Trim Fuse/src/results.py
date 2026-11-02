"""Results copied from the executed Colab notebooks (00-05, run on 31 Oct 2026).

These are the comparisons that needed training many models (all candidates, tuning, advanced checks), so the
website shows them as recorded instead of retraining. The final models' scores are recomputed live in the app
and match these numbers.
"""

# Notebook 01 - MCU, held-out MCU-A wafers. (model, exact %, within +/-1 %)
MCU_MODELS = {
    "Bandgap": [("Ridge", 77.67, 99.88), ("Random Forest", 80.70, 99.82), ("Formula (no ML)", 78.33, 99.64),
                ("XGBoost", 79.39, 99.53), ("LightGBM", 78.62, 99.05), ("HistGradientBoosting", 77.02, 98.87),
                ("MLP neural net", 59.68, 97.80)],
    "HSI oscillator": [("Random Forest", 59.38, 82.96), ("LightGBM", 48.93, 80.40),
                       ("HistGradientBoosting", 47.39, 80.05), ("XGBoost", 43.53, 77.67),
                       ("Formula (no ML)", 23.99, 69.36), ("MLP neural net", 24.05, 66.92), ("Ridge", 19.89, 55.40)],
    "LDO": [("Random Forest", 89.07, 100.0), ("LightGBM", 88.66, 100.0), ("HistGradientBoosting", 88.42, 100.0),
            ("XGBoost", 88.18, 100.0), ("Formula (no ML)", 86.11, 100.0), ("Ridge", 85.93, 100.0),
            ("MLP neural net", 81.12, 100.0)],
}
MCU_FINAL = {"Bandgap": "Random Forest + physics features", "HSI oscillator": "Random Forest + features, tuned",
             "LDO": "Random Forest + features, tuned"}

# Notebook 02 - PMIC rails from the reference only. (model, exact %, within +/-1 %)
PMIC_MODELS = {
    "buck1": [("Ridge", 46.29, 93.76), ("XGBoost", 43.85, 90.91), ("LightGBM", 43.35, 90.15),
              ("MLP neural net", 40.28, 89.74), ("Random Forest", 36.71, 83.05)],
    "buck2": [("Ridge", 48.15, 95.52), ("XGBoost", 44.39, 92.81), ("LightGBM", 43.22, 91.41),
              ("MLP neural net", 40.87, 90.46), ("Random Forest", 38.74, 86.94)],
    "ldo1": [("Ridge", 47.65, 94.98), ("MLP neural net", 43.67, 92.86), ("XGBoost", 48.15, 92.68),
             ("LightGBM", 46.34, 91.50), ("Random Forest", 42.63, 89.01)],
    "ldo2": [("Ridge", 45.12, 92.63), ("MLP neural net", 40.55, 89.78), ("XGBoost", 41.28, 89.20),
             ("LightGBM", 39.69, 87.93), ("Random Forest", 36.48, 84.58)],
}
PMIC_MULTI = {"buck1": (83.05, 80.56), "buck2": (86.93, 79.29), "ldo1": (89.01, 84.63), "ldo2": (84.58, 81.37)}
PMIC_THRESH = [("Reference (vref)", "Random Forest", 79.57, 59.99, "ML learns each die's DAC gain error"),
               ("OVP", "Formula", 99.91, 99.91, "already perfect with one measurement"),
               ("UVLO", "Formula", 99.91, 99.91, "already perfect with one measurement"),
               ("Current limit", "Formula", 99.86, 99.86, "already perfect with one measurement")]
PMIC_CS = [("No calibration", 28.94), ("2-point formula", 6.57), ("Ridge (2 points + process)", 3.30),
           ("LightGBM", 3.57), ("Random Forest", 3.71)]
PMIC_OTP = [("Rule checker", 100.0), ("Decision Tree (raw fields)", 98.5), ("Random Forest (raw fields)", 96.2)]
PMIC_DEFECT = [("Datasheet rule", 100.0, 100.0), ("Isolation Forest, top 0.5 %", 32.6, 25.0),
               ("Isolation Forest, top 1 %", 41.9, 16.2)]

# Notebook 03 - sensor, spec +/-10 mg / +/-0.5 %. (method, R2 TCO, R2 TCS, spec pass %)
SENSOR_MODELS = [("Ridge + 3-axis features, tuned (final)", 0.811, 0.856, 69.33), ("Ridge", 0.800, 0.852, 67.69),
                 ("LightGBM", 0.820, 0.831, 64.90), ("XGBoost", 0.811, 0.828, 64.60),
                 ("Random Forest", 0.771, 0.829, 63.32), ("MLP neural net", 0.728, 0.844, 62.33),
                 ("Fleet average (classic 1 insertion)", None, None, 9.65),
                 ("No temperature compensation", None, None, 1.55)]
SENSOR_DEFECT = [("Rule: resonance > 6 % below wafer median", 97.1, 89.5), ("Isolation Forest, top 0.5 %", 0.0, 0.0),
                 ("Isolation Forest, top 1 %", 2.9, 0.9)]
SENSOR_TRANSFER = [("ACC-8G", 68.05, 68.65), ("ACC-16G", 69.26, 69.41)]

# Notebook 04 - SoC speed (average over the 3 targets). (model, R2, MAE MHz)
SOC_MODELS = [("Ridge + physics features (final)", 0.990, 20.6), ("Ridge", 0.990, 20.7), ("XGBoost", 0.984, 26.1),
              ("LightGBM", 0.983, 26.6), ("Random Forest", 0.981, 28.1), ("MLP neural net", 0.969, 36.2)]
SOC_REPAIR_ML = (97.5, 22)  # ML accuracy %, arrays wrongly called repairable

# Notebook 05 - advanced methods. (method, task, evidence, verdict)
ADVANCED = [
    ("Spatial error check", "all 5 tasks", "neighbour correlation of model errors +0.00 to +0.09; wafer explains "
     "0-1.3 % of the error", "Errors are random: nothing left for spatial models"),
    ("Kriging correction (10 % measured dies)", "all 5 tasks", "MAE worse by +12 % to +34 %", "Hurts"),
    ("GNN-style neighbour features", "all 5 tasks", "MAE changed by less than 2 %", "No real effect"),
    ("Confidence routing (quantile regression)", "MCU HSI", "best setting on validation = never route",
     "No gain"),
    ("Quantile (per-die) guard band", "SoC binning", "no setting safe: 5.9-11.4 % unsafe dies on test",
     "Unsafe: keep the fixed 80 MHz band"),
    ("Error model for hybrid flow", "Sensor", "picked risky dies no better than random (+0.2 points)",
     "No gain"),
    ("Drift-aware target (transfer learning)", "MCU-C", "final-test pass 90.7 % -> 99.4 % (99.0-99.8 % across 2 wafers)", "Helps (kept)"),
    ("Fine-tuning with 50 MCU-C dies", "MCU-C", "shift error 1.62 -> 0.90 mV", "Helps (kept)"),
]
RULED_OUT = [
    ("GAN", "Generates fake data", "It can only copy patterns already in the data, and fuse decisions can't rest on "
     "fake dies (traceability). The small derivatives already work without it."),
    ("RNN / LSTM", "Learns from sequences", "Each die is one independent row: there is no time order to learn."),
    ("Reinforcement learning", "Learns decisions by trial", "Predict-then-verify already needs 1-2 steps, and the "
     "SKU decision has an exact integer-programming solution. RL needs a live tester to explore."),
    ("Full GNN / CNN wafer maps", "Learns spatial patterns", "Notebook 05 showed the remaining errors have no "
     "spatial pattern to learn."),
    ("Bigger neural networks", "Complex non-linear patterns", "The tuned MLP never won: the data is small, tabular "
     "and close to linear physics."),
]
