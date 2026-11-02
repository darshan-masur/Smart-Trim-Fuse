"""Batch check: file recognition, missing / impossible values, and the Demo files against expected_results.csv."""

import unittest

import numpy as np
import pandas as pd

from common import DEMO, B, raw, run_file

EXPECTED = pd.read_csv(DEMO / "expected_results.csv").set_index("File")


class Recognition(unittest.TestCase):
    def test_each_dataset_is_recognised_as_its_own_kind(self):
        for name, kind in [("mcu", "MCU dies"), ("pmic", "PMIC"), ("sensor", "Sensor"), ("soc", "SoC"),
                           ("otp_req", "Customer"), ("audit", "MCU fuse words")]:
            with self.subTest(name):
                k, missing, score = B.detect(raw(name).head(50))
                self.assertTrue(k.startswith(kind))
                self.assertEqual(missing, [])
                self.assertEqual(score, 1.0)

    def test_unrelated_file_is_not_recognised(self):
        self.assertLess(B.detect(pd.read_csv(DEMO / "08_wrong_file_sales_report.csv"))[2], 0.6)

    def test_missing_required_column_is_reported(self):
        k, missing, _ = B.detect(raw("mcu").head(5).drop(columns=["bg_untrim_V"]))
        self.assertTrue(k.startswith("MCU dies"))
        self.assertEqual(missing, ["bg_untrim_V"])


class MissingValues(unittest.TestCase):
    def test_blank_text_and_impossible_values_are_never_predicted(self):
        df = raw("mcu").head(6).copy()
        df["bg_untrim_V"] = df["bg_untrim_V"].astype(object)
        df.loc[1, "bg_untrim_V"] = np.nan
        df.loc[2, "bg_untrim_V"] = "n/a"
        df.loc[3, "bg_untrim_V"] = -1.2
        df.loc[4, "hsi_untrim_MHz"] = 0
        kind, _, _, d, log, out, _ = run_file(df)
        self.assertEqual(list(d._usable), [True, False, False, False, False, True])
        self.assertTrue(out.loc[~d._usable, "action"].eq(B.NOT_PREDICTED).all())
        self.assertTrue(out.loc[~d._usable, "bg_code_AI"].isna().all())
        self.assertIn("conventional review required", dict((s, w) for s, _, w in log)["Rows with a blank required value"])

    def test_messy_demo_counts_add_up(self):
        df = pd.read_csv(DEMO / "02_mcu_messy_export.csv")
        _, _, _, d, _, _, _ = run_file(df)
        self.assertEqual(len(df) - len(d) + int(d._usable.sum()) + int((~d._usable).sum()), len(df))


class DemoFiles(unittest.TestCase):
    def test_every_demo_file_matches_expected_results(self):
        files = sorted(p.name for p in DEMO.glob("*.csv") if p.name != "expected_results.csv")
        self.assertEqual(sorted(EXPECTED.index), files)
        for f in files:
            with self.subTest(f):
                df = pd.read_csv(DEMO / f)
                kind, missing, score, d, log, out, summ = run_file(df)
                e = EXPECTED.loc[f]
                if e["Recognised as"] == "not recognised":
                    self.assertLess(score, 0.6)
                    continue
                self.assertEqual(kind, e["Recognised as"])
                self.assertEqual([len(df), len(df) - len(d), int(d._usable.sum()), int((~d._usable).sum())],
                                 [e["Rows in file"], e["Removed"], e["Predicted"], e["Not predicted"]])
                self.assertEqual(B.rows_kept_note(log) or "nothing to clean", e["Cleaning the page reports"])
                self.assertEqual("; ".join(f"{a} = {b}" for a, b in summ), e["Result summary"])


if __name__ == "__main__":
    unittest.main()
