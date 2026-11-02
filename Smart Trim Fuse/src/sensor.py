"""Sensor: one row per die-axis (notebook 03), predicted temperature coefficients and the spec check."""

import numpy as np
import pandas as pd

from src.common import wafer_split
from src.config import PCM, POS

DIE = ["die_id", "lot_id", "wafer_id", "derivative", "package", "full_scale_g", "latent_defect",
       "characterized_3temp", "stress_gauge_mV", "asic_vref_mV", "mems_resonance_kHz", "mems_q_factor",
       "conv_test_time_s"] + PCM + POS
PER_AXIS = {"st_response_{a}_mg": "st_response_mg", "offset_{a}_25C_mg": "offset_25C_mg",
            "sens_{a}_25C_rel": "sens_25C_rel", "offset_{a}_m40C_mg": "offset_m40C_mg",
            "offset_{a}_85C_mg": "offset_85C_mg", "sens_{a}_m40C_rel": "sens_m40C_rel",
            "sens_{a}_85C_rel": "sens_85C_rel", "tco_{a}_true_mg_per_C": "tco", "tco2_{a}_true_mg_per_C2": "tco2",
            "tcs_{a}_true_ppm_per_C": "tcs", "post_reflow_offset_shift_{a}_mg": "reflow_shift_mg"}
COEFS = ["tco", "tcs", "tco2"]


def to_long(sensor):
    parts = []
    for i, a in enumerate("xyz"):
        p = sensor[DIE].copy()
        p["axis"] = i
        for src, dst in PER_AXIS.items():
            p[dst] = sensor[src.format(a=a)]
        parts.append(p)
    d = pd.concat(parts, ignore_index=True)
    g = d.groupby("die_id")
    d["offset_25C_mean3"] = g.offset_25C_mg.transform("mean")
    d["sens_25C_mean3"] = g.sens_25C_rel.transform("mean")
    d["is_lga12"] = (d.package == "LGA12").astype(int)
    return d


def split(sensor, long):
    """Notebook 03 split: train = characterized ACC-2G dies of training wafers; test = production dies of held-out
    wafers. Returns (train, test, others) in the long layout."""
    base = sensor[sensor.derivative == "ACC-2G"].reset_index(drop=True)
    _, te = wafer_split(base)
    test_w = set(te.wafer_id)
    b = long[long.derivative == "ACC-2G"]
    train = b[~b.wafer_id.isin(test_w) & b.characterized_3temp].reset_index(drop=True)
    test = b[b.wafer_id.isin(test_w) & ~b.characterized_3temp].reset_index(drop=True)
    return train, test, long[long.derivative != "ACC-2G"].reset_index(drop=True)


def predict(d, bundle):
    return {c: bundle["coefficients"][c].predict(d[bundle["features"]]) for c in COEFS}


def errors(d, tco, tcs, tco2):
    """Offset error (mg) and sensitivity error (%) at -40 and 85 °C after calibrating with these coefficients."""
    out = {}
    for t, s in [(-40, "m40C"), (85, "85C")]:
        dt = t - 25
        out[f"off_{s}"] = (d[f"offset_{s}_mg"] - (d.offset_25C_mg + tco * dt + tco2 * dt ** 2)).values
        out[f"sens_{s}"] = ((d[f"sens_{s}_rel"] / (d.sens_25C_rel * (1 + tcs * 1e-6 * dt)) - 1) * 100).values
    return out


def pass_rate(d, tco, tcs, tco2, off_lim, sens_lim):
    e = errors(d, tco, tcs, tco2)
    ok = np.ones(len(d), bool)
    for s in ("m40C", "85C"):
        ok &= (np.abs(e[f"off_{s}"]) <= off_lim) & (np.abs(e[f"sens_{s}"]) <= sens_lim)
    return ok.mean()
