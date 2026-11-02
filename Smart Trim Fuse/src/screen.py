"""Defect screens for the Batch check: catch physically defective dies (the dataset's latent defects) before any AI
result is used for them. A flagged die gets no AI code: it goes to the conventional flow and failure analysis.

- MCU: the untrimmed bandgap is compared with what the die's process monitors and position predict for a healthy
  die. More than 25 mV away = suspect (healthy dies stay within about 14 mV, defects are 49 mV or more away).
- Sensor: the MEMS resonance is compared with what the process predicts. More than 5% low = suspect (healthy dies
  stay above -3.7%, defects are below -7%).
- PMIC: the datasheet rule (efficiency at 1 A below 88% or load regulation above 10 mV).
- SoC: structural test results (L2 cache not repairable = scrap; defective cores lower the product).

The two process models are robust linear fits on the base product's training wafers only (same split as the
notebooks), so the batch files' wafers are never used to fit them."""

import numpy as np
from sklearn.linear_model import HuberRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.common import wafer_split
from src.config import PCM, POS

BG_LIMIT_V = 0.025
RES_LIMIT = -0.05
EFF_MIN_PCT, LOAD_REG_MAX_MV = 88, 10


def _fit(df, y):
    return make_pipeline(StandardScaler(), HuberRegressor(max_iter=1000)).fit(df[PCM + POS], y)


def fit(mcu, sensor):
    """Expected-healthy models for the MCU bandgap and the sensor resonance."""
    m, _ = wafer_split(mcu[mcu.derivative == "MCU-A"])
    s, _ = wafer_split(sensor[sensor.derivative == "ACC-2G"])
    return {"bg": _fit(m, m.bg_untrim_V), "res": _fit(s, np.log(s.mems_resonance_kHz))}


def mcu(d, scr):
    """Reason per row ('' = healthy)."""
    off = d.bg_untrim_V - scr["bg"].predict(d[PCM + POS])
    return np.where(off.abs() > BG_LIMIT_V, [f"untrimmed bandgap {v * 1000:+.0f} mV from a healthy die (limit "
                                             f"±{BG_LIMIT_V * 1000:.0f} mV)" for v in off], "")


def sensor(d, scr):
    dev = np.exp(np.log(d.mems_resonance_kHz) - scr["res"].predict(d[PCM + POS])) - 1
    return np.where(dev < RES_LIMIT, [f"MEMS resonance {v:+.1%} vs a healthy die (limit {RES_LIMIT:.0%})" for v in dev],
                    "")


def pmic(d):
    if not {"efficiency_1A_pct", "load_reg_mV"} <= set(d.columns):
        return np.full(len(d), "")
    why = []
    for e, lr in zip(d.efficiency_1A_pct, d.load_reg_mV, strict=True):
        bad = ([f"efficiency {e:.1f}% (min {EFF_MIN_PCT}%)"] if e < EFF_MIN_PCT else []) + \
              ([f"load regulation {lr:.1f} mV (max {LOAD_REG_MAX_MV} mV)"] if lr > LOAD_REG_MAX_MV else [])
        why.append("; ".join(bad))
    return np.array(why)


def summary(flag, d):
    """Rows for the self-check table: flagged count, and caught / false alarms when the file has the true answer."""
    flag = np.asarray(flag, bool)
    rows = [("Dies flagged as defective", f"{flag.sum()} of {len(flag)}")]
    if "latent_defect" in d.columns:
        known = d.latent_defect.astype(str).str.lower().isin(["true", "1"]).values
        rows += [("Known defects caught", f"{(flag & known).sum()} of {known.sum()}"),
                 ("Healthy dies flagged (false alarms)", f"{(flag & ~known).sum()}")]
    return rows
