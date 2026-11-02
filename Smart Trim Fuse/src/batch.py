"""Batch check: recognise an uploaded CSV, clean it, run the right model / rule on every row.

Six kinds of file are recognised by their columns (the same columns as the project's datasets). Rows that can't be
predicted safely (a missing or impossible measurement) are never guessed: they are marked "not predicted;
conventional review required". This page runs no tester flow itself.

Fuse words get one of three verdicts: PASS only when the word is well formed, the die_id is unique in the file and
found in the sort records (same derivative), and every rule passes, including the per-die trim and TS_CAL1 fields;
BLOCK when any rule fails or the word is unreadable; REVIEW when the rules that could be run pass but the die's
identity, trim codes or TS_CAL1 reading could not be confirmed.
"""

import re

import numpy as np
import pandas as pd

from src import mcu as M
from src import pmic as P
from src import sensor as S
from src import soc as Q
from src.common import to_code
from src.config import PCM, POS

REQUIRED = {
    "MCU dies (trim prediction)": ["bg_untrim_V", "hsi_untrim_MHz", "ldo_untrim_V", "bg_trimmed_sort_V"] + PCM + POS,
    "PMIC dies (rail prediction)": ["vref_untrim_V", "vref_trimmed_sort_V", "cs_meas_0p5A_A", "cs_meas_2p0A_A"] + PCM + POS,
    "Sensor dies (25 °C calibration)": [f"{c}_{a}_{s}" for a in "xyz" for c, s in
                                        [("offset", "25C_mg"), ("sens", "25C_rel")]] +
                                       [f"st_response_{a}_mg" for a in "xyz"] +
                                       ["stress_gauge_mV", "asic_vref_mV", "mems_resonance_kHz", "mems_q_factor",
                                        "package"] + PCM + POS,
    "SoC dies (speed and product)": ["ro_freq_MHz", "cpm_path_delay_ps", "iddq_25C_mA", "l2_repairable"] +
                                    [f"core{i}_defect" for i in range(8)] + PCM + POS,
    "Customer OTP requests": ["buck1_V", "buck2_V", "ldo1_V", "ldo2_V", "sequence", "i2c_addr", "other_addresses_on_bus"],
    "MCU fuse words": ["derivative", "fuse_map_hex"],
}
MAY_BE_BLANK = {"other_addresses_on_bus"}  # an empty bus is a valid answer
NOT_PREDICTED = "not predicted; conventional review required (missing or impossible data)"
DIE_ID_RE = re.compile(r"MCU-\d{6}")
ID_COL = {"Customer OTP requests": "request_id", "MCU fuse words": "die_id"}
POSITIVE = ["bg_untrim_V", "hsi_untrim_MHz", "ldo_untrim_V", "bg_trimmed_sort_V", "vref_untrim_V", "vref_trimmed_sort_V",
            "ro_freq_MHz", "cpm_path_delay_ps", "iddq_25C_mA", "mems_resonance_kHz", "pcm_rs_ohm_sq", "pcm_tox_A",
            "pcm_mobility_rel", "buck1_V", "buck2_V", "ldo1_V", "ldo2_V"]
TEXT = {"package", "sequence", "i2c_addr", "other_addresses_on_bus", "derivative", "fuse_map_hex", "die_id", "lot_id",
        "wafer_id", "request_id", "customer", "label", "error_type", "sku_rule_based"}


def detect(df):
    """Best-matching kind, plus the required columns it is missing (empty list = usable).

    Among kinds with at least 60 % of their columns, the one matching the most columns wins: an MCU die file also
    has `derivative` and `fuse_map_hex`, so a die file missing one column must not turn into a fuse-word file."""
    cols = set(df.columns)
    hits = {k: len(cols & set(v)) for k, v in REQUIRED.items()}
    scores = {k: hits[k] / len(v) for k, v in REQUIRED.items()}
    kind = max(scores, key=lambda k: (scores[k] >= 0.6, hits[k] if scores[k] >= 0.6 else 0, scores[k]))
    return kind, [c for c in REQUIRED[kind] if c not in cols], scores[kind]


def rows_kept_note(log):
    return "; ".join(f"{step}: {n}" for step, n, _ in log if n)


def _to_bool(s):
    m = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
    return s.map(lambda v: m.get(str(v).strip().lower(), np.nan) if not isinstance(v, (bool, np.bool_)) else bool(v))


def clean(df, kind):
    """Returns (clean table, list of (step, rows affected, what was done))."""
    d, log = df.copy(), []
    n = int(d.duplicated().sum())
    d = d.drop_duplicates()
    log.append(("Exact duplicate rows", n, "removed"))
    idc = ID_COL.get(kind, "die_id")
    if idc in d.columns and kind != "MCU fuse words":
        n = int(d[idc].duplicated(keep="last").sum())
        d = d.drop_duplicates(idc, keep="last")
        log.append((f"Repeated {idc} (re-tested)", n, "kept the latest row"))
    bools = [c for c in d.columns if c.endswith(("_defect", "_pass", "_repairable", "latent_defect", "has_error",
                                                 "characterized_3temp"))]
    n_txt = 0
    for c in bools:
        if d[c].dtype == object:
            n_txt += int(d[c].notna().sum())
            d[c] = _to_bool(d[c])
    log.append(("True/False typed as text", n_txt, "converted to booleans"))
    bad_num = 0
    for c in REQUIRED[kind]:
        if c in d.columns and c not in TEXT and not c.endswith(("_defect", "_repairable")):
            before = d[c].isna().sum()
            d[c] = pd.to_numeric(d[c], errors="coerce")
            bad_num += int(d[c].isna().sum() - before)
    log.append(("Text in a number column", bad_num, "set to blank"))
    imp = 0
    for c in POSITIVE:
        if c in d.columns:
            m = d[c] <= 0
            imp += int(m.sum())
            d.loc[m, c] = np.nan
    if "radius_mm" in d.columns:
        m = d.radius_mm < 0
        imp += int(m.sum())
        d.loc[m, "radius_mm"] = np.nan
    log.append(("Impossible values (zero or negative)", imp, "set to blank"))
    need = [c for c in REQUIRED[kind] if c in d.columns and c not in MAY_BE_BLANK]
    miss = d[need].isna().any(axis=1)
    log.append(("Rows with a blank required value", int(miss.sum()),
                "not predicted; conventional review required (never guessed)"))
    d["_usable"] = ~miss
    return d.reset_index(drop=True), log


# ---------------------------------------------------------------- runners: each returns (results, summary rows)
def _code_summary(name, truth, pred_code, bits):
    err = np.abs(pred_code - truth)
    return [(f"{name}: exact", f"{(err == 0).mean():.1%}"), (f"{name}: within ±1 code", f"{(err <= 1).mean():.1%}")]


def run_mcu(d, bundle):
    ok = d[d._usable]
    out = d[[c for c in ("die_id", "wafer_id", "derivative") if c in d.columns]].copy()
    summary = []
    if len(ok):
        pr = M.predict_codes(ok, bundle)
        for t, c in M.TRIMS.items():
            out.loc[ok.index, f"{t}_code_AI"] = to_code(pr[t], c["bits"])
            if c["label"] in d.columns:
                summary += _code_summary(c["name"], ok[c["label"]].values, to_code(pr[t], c["bits"]), c["bits"])
    out["action"] = np.where(d._usable, "AI codes proposed; verify once on the tester", NOT_PREDICTED)
    return out, summary


def run_pmic(d, bundle):
    ok = d[d._usable]
    out = d[[c for c in ("die_id", "wafer_id", "derivative") if c in d.columns]].copy()
    summary = []
    if len(ok):
        pr = P.predict_rails(ok, bundle)
        f = P.add_features(ok)
        for r in P.RAILS:
            out.loc[ok.index, f"{r}_code_AI"] = to_code(pr[r], 6)
            if f"{r}_trim_code_opt" in d.columns:
                summary += _code_summary(r, ok[f"{r}_trim_code_opt"].values, to_code(pr[r], 6), 6)
        for c, short in zip(P.CS_TARGETS, ["cs_gain_err_pct", "cs_offset_mA", "cs_inl_pct"], strict=True):
            out.loc[ok.index, f"{short}_AI"] = bundle["current_sense"][c].predict(f[bundle["cs_features"]]).round(3)
    if {"efficiency_1A_pct", "load_reg_mV"} <= set(d.columns):
        out["defect_flag"] = (d.efficiency_1A_pct < 88) | (d.load_reg_mV > 10)
    out["action"] = np.where(d._usable, "AI rail codes proposed; verify once on the tester", NOT_PREDICTED)
    return out, summary


def run_sensor(d, bundle):
    ok = d[d._usable].copy()
    out = d[[c for c in ("die_id", "wafer_id", "derivative") if c in d.columns]].copy()
    summary = []
    if len(ok):
        for c in ["lot_id", "wafer_id", "derivative", "full_scale_g", "latent_defect", "characterized_3temp",
                  "conv_test_time_s"]:
            if c not in ok.columns:
                ok[c] = np.nan
        for a in "xyz":  # S.to_long needs the hot/cold columns; absent in production files
            for c in ["offset_{a}_m40C_mg", "offset_{a}_85C_mg", "sens_{a}_m40C_rel", "sens_{a}_85C_rel",
                      "tco_{a}_true_mg_per_C", "tco2_{a}_true_mg_per_C2", "tcs_{a}_true_ppm_per_C",
                      "post_reflow_offset_shift_{a}_mg"]:
                if c.format(a=a) not in ok.columns:
                    ok[c.format(a=a)] = np.nan
        long = S.to_long(ok.reset_index().rename(columns={"index": "_row"}).assign(die_id=lambda x: x._row.astype(str)))
        p = S.predict(long, bundle)
        for i, a in enumerate("xyz"):
            m = long.axis == i
            rows = long.loc[m, "die_id"].astype(int).values
            for c in S.COEFS:
                out.loc[rows, f"{c}_{a}_AI"] = np.round(p[c][m.values], 5)
            if f"tco_{a}_true_mg_per_C" in d.columns and d[f"tco_{a}_true_mg_per_C"].notna().any():
                t = d.loc[rows, f"tco_{a}_true_mg_per_C"].values
                summary.append((f"TCO {a}: mean error (mg/°C)", f"{np.nanmean(np.abs(t - p['tco'][m.values])):.3f}"))
        dev = d.mems_resonance_kHz / d.mems_resonance_kHz.median() - 1
        out["defect_flag"] = dev < -0.06
    out["action"] = np.where(d._usable, "AI calibration codes proposed (1 insertion)", NOT_PREDICTED)
    return out, summary


def run_soc(d, bundle, skus):
    d = d.copy()
    for c in ["l2_repairable"] + [f"core{i}_defect" for i in range(8)]:
        d[c] = d[c].astype("boolean").fillna(False).astype(bool) if d[c].dtype == object else d[c].astype(bool)
    ok = Q.prepare(d[d._usable].assign(**{f"core{i}_fmax_GHz": np.where(d.loc[d._usable, f"core{i}_defect"], np.nan, 1.0)
                                          for i in range(8)}))
    # the real per-core speeds aren't known before the speed test: only which cores work (structural test)
    out = d[[c for c in ("die_id", "wafer_id") if c in d.columns]].copy()
    summary = []
    if len(ok):
        ok.index = d.index[d._usable]
        ftop = {k: np.where(ok[f"f_top{k}"].notna(), bundle["speed_models"][k].predict(ok[bundle["features"]]), np.nan)
                for k in Q.KS}
        for k in Q.KS:
            out.loc[ok.index, f"speed_{k}cores_GHz_AI"] = np.round(ftop[k], 3)
        guard = bundle["guard_band_MHz"] / 1000
        e = Q.eligibility(ok, skus, ftop, guard)
        out.loc[ok.index, "product_AI"] = Q.best_sku(e)
        if "sku_rule_based" in d.columns:
            same = (out.loc[ok.index, "product_AI"] == d.loc[ok.index, "sku_rule_based"]).mean()
            rank = {"scrap": 0, "SoC-Lite": 1, "SoC-Std": 2, "SoC-Pro": 3}
            hi = (out.loc[ok.index, "product_AI"].map(rank) > d.loc[ok.index, "sku_rule_based"].map(rank)).mean()
            summary += [("Same product as the full speed test", f"{same:.1%}"),
                        ("Product higher than the speed test (over-graded)", f"{hi:.1%}")]
    out["action"] = np.where(d._usable, f"product proposed from prediction ({bundle['guard_band_MHz']} MHz guard band)",
                             NOT_PREDICTED)
    return out, summary


def run_otp(d):
    rows = []
    for r in d.to_dict("records"):
        if not r.get("_usable", True):
            rows.append(("incomplete", "missing a required value"))
            continue
        bus = [a.strip() for a in str(r["other_addresses_on_bus"]).split(";") if a.strip() and a.strip() != "nan"]
        try:
            label, checks = P.check_request(r["buck1_V"], r["buck2_V"], r["ldo1_V"], r["ldo2_V"], str(r["sequence"]),
                                            str(r["i2c_addr"]).strip(), bus)
            rows.append((label, next((f"{n}: {det}" for n, ok, det in checks if not ok), "all rules pass")))
        except ValueError:
            rows.append(("unreadable", "address is not a hex number"))
    out = d[[c for c in ("request_id", "customer") if c in d.columns]].copy()
    out["verdict"], out["reason"] = zip(*rows) if rows else ([], [])
    summary = [("Valid requests", f"{(out.verdict == 'valid').sum()} of {len(out)}")]
    expected = "expected_label" if "expected_label" in d.columns else ("label" if "label" in d.columns else None)
    if expected:
        summary.append(("Matches the expected label", f"{(out.verdict.values == d[expected].values).mean():.0%}"))
    return out, summary


def _die_identity(r, ids, sort):
    """(sort values, problem). The die's trim codes and TS_CAL1 reading, only when the die_id is well formed, unique in
    the file and in the sort records."""
    die = str(r.get("die_id", "")).strip()
    if not die or die == "nan":
        return None, "no die_id"
    if not DIE_ID_RE.fullmatch(die):
        return None, f"die_id {die!r} is not a valid MCU die id"
    if ids[die] > 1:
        return None, f"die_id {die} appears {ids[die]} times in this file"
    if die not in sort.index:
        return None, f"die_id {die} not found in the sort records"
    if sort.at[die, "derivative"] != str(r["derivative"]).strip():
        return None, f"sort records say {sort.at[die, 'derivative']}, word says {str(r['derivative']).strip()}"
    return sort.loc[die, M.SORT_FIELDS].values, None


def run_fuse(d, schema, mcu):
    """PASS / BLOCK / REVIEW per word (see the module docstring). A broken schema blocks every word."""
    out = d[[c for c in ("die_id", "derivative", "fuse_map_hex") if c in d.columns]].copy()
    problems = M.schema_problems(schema)
    if problems:
        out["verdict"], out["reason"] = "BLOCK", "fuse schema is invalid: " + "; ".join(problems)
        return out, [("Words blocked", f"{len(out)} of {len(out)}")]
    sort = mcu.drop_duplicates("die_id").set_index("die_id")
    ids = d["die_id"].astype(str).str.strip().value_counts() if "die_id" in d.columns else {}
    verdict, why = [], []
    for r in d.to_dict("records"):
        try:
            t, id_problem = _die_identity(r, ids, sort)
            res = M.check_fuse(r["fuse_map_hex"], str(r["derivative"]).strip(), schema, t)
        except ValueError as e:
            verdict.append("BLOCK")
            why.append(f"unreadable word: {e}")
            continue
        except KeyError:
            verdict.append("BLOCK")
            why.append(f"unknown product {str(r.get('derivative')).strip()!r}")
            continue
        bad = [n for n, ok, _ in res if not ok]
        if bad:
            verdict.append("BLOCK")
            why.append(bad[0])
        elif id_problem:
            verdict.append("REVIEW")
            why.append(f"product rules pass, trim and TS_CAL1 fields not checked: {id_problem}")
        else:
            verdict.append("PASS")
            why.append("all rules pass, every field checked")
    out["verdict"], out["reason"] = verdict, why
    summary = [("Words blocked", f"{(out.verdict == 'BLOCK').sum()} of {len(out)}"),
               ("Words needing review", f"{(out.verdict == 'REVIEW').sum()} of {len(out)}")]
    if "expected_verdict" in d.columns:
        summary.append(("Matches the expected verdict", f"{(out.verdict.values == d.expected_verdict.values).mean():.0%}"))
    if "has_error" in d.columns:
        he = d.has_error.astype(bool).values
        bl = (out.verdict == "BLOCK").values
        summary += [("Injected errors caught", f"{(bl & he).sum()} of {he.sum()}"), ("False alarms", f"{(bl & ~he).sum()}")]
    return out, summary
