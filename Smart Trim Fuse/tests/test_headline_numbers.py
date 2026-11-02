"""Every headline number in RESULTS_SOURCE_OF_TRUTH.csv is recomputed here from the saved models and
evaluation_06.json. If a notebook is re-run and a number moves, this check fails until the table is updated."""

import csv
import logging
import sys
import unittest

import numpy as np
import pandas as pd

from common import APP_ROOT

sys.path.insert(0, str(APP_ROOT / "app"))
logging.disable(logging.CRITICAL)  # Streamlit's "no script run context" messages
import ui

from src import mcu as M
from src import pmic as P
from src.common import to_code, wafer_split

TABLE = APP_ROOT.parent / "RESULTS_SOURCE_OF_TRUTH.csv"


def recomputed():
    h, ev = ui._headline.__wrapped__(None), ui.evaluation()
    p = ui.pmic_test()
    pmic_ok = np.all([np.abs(to_code(p[f"pred_{r}"], 6) - p[f"{r}_trim_code_opt"]) <= 1 for r in P.RAILS], axis=0)
    drift = pd.DataFrame(ev["lowo_drift"])
    t80 = next(r for r in ev["soc_curve_test"] if r["margin_MHz"] == ev["soc_hybrid_MHz"])
    lm = pd.DataFrame(ev["lowo_mcu"])
    (mt, ma), (pt, pa), (rr, ro) = h["mcu_ms"], h["pmic_steps"], h["soc_rev"]
    hits, total, false = h["fuse"]
    return {
        "MCU_TIME": f"{mt / ma:.1f}x",
        "MCU_NOSEARCH": f"{_mcu_no_search():.1%}",
        "MCU_TRIES": f"{lm.tries_today.median():.1f} -> {lm.tries_ai.median():.1f}",
        "MCUC_DRIFT": f"{drift['fine_tuned_median_%'].mean():.1f}%",
        "PMIC_TRIES": f"{pt / pa:.1f}x",
        "PMIC_NOSEARCH": f"{pmic_ok.mean():.1%}",
        "SENSOR_TIME": f"{h['sensor_s'][1]:.1f} s",
        "SENSOR_PASS": next(r["reported (one split)"] for r in ev["summary"] if r["result"].endswith("(Medium)")),
        "SOC_REVENUE": f"{(ro / rr - 1):.1%}",
        "SOC_SKIP": f"{100 - t80['hybrid_tested_%']:.1f}%",
        "FUSE_CHECK": f"{hits}/{total}" if false == 0 else f"{hits}/{total} with {false} false alarms",
        "REPAIR": f"+{h['repair_saved']}",
        "SOC_VMIN": f"{_vmin_test_errors().abs().mean():.2f} mV",
    }


def _vmin_test_errors():
    """Measured minus predicted worst-core Vmin on the held-out SoC wafers (notebook 07)."""
    vb = ui.model("vmin")
    _, te = wafer_split(ui.raw("soc"))
    return te[[f"core{i}_vmin_2GHz_mV" for i in range(8)]].max(axis=1) - vb["model"].predict(te[vb["features"]])


def _mcu_no_search():
    te = ui.mcu_test()
    return np.all([np.abs(to_code(te[f"pred_{t}"], c["bits"]) - te[c["label"]]) <= 1 for t, c in M.TRIMS.items()],
                  axis=0).mean()


class Headlines(unittest.TestCase):
    def test_table_matches_recomputed_numbers(self):
        with open(TABLE, encoding="utf-8") as f:
            table = {r["id"]: r["value"] for r in csv.DictReader(f)}
        got = recomputed()
        for k, v in got.items():
            with self.subTest(k):
                self.assertEqual(table[k], v)

    def test_vmin_margin_covers_every_held_out_chip(self):
        vb = ui.model("vmin")
        err = _vmin_test_errors()
        self.assertEqual(int((err > vb["margin_mV"]).sum()), vb["metrics"]["test_under_at_margin"])
        self.assertEqual(vb["metrics"]["test_under_at_margin"], 0)
        self.assertEqual(sorted(wafer_split(ui.raw("soc"))[1].wafer_id.unique()), vb["test_wafers"])

    def test_soc_margin_has_no_over_graded_chips(self):
        ev = ui.evaluation()
        t80 = next(r for r in ev["soc_curve_test"] if r["margin_MHz"] == ev["soc_hybrid_MHz"])
        self.assertEqual(t80["hybrid_escapes"], 0)
        self.assertEqual(ev["soc_hybrid_MHz"], 80)

    def test_otp_table_value(self):
        with open(TABLE, encoding="utf-8") as f:
            self.assertEqual(next(r["value"] for r in csv.DictReader(f) if r["id"] == "OTP_CHECK"), "100%")


if __name__ == "__main__":
    unittest.main()
