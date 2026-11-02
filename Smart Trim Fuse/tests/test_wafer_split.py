"""The train / test split is by wafer: no wafer on both sides, and the same wafers every run (seed 42).

As in the notebooks, each model is trained on its base version only (MCU-A, PMIC-P1, ACC-2G, the one SoC die);
the other versions are never in training."""

import unittest

import pandas as pd

from common import DEMO, raw
from src.common import wafer_split

BASE = {"mcu": "MCU-A", "pmic": "PMIC-P1", "sensor": "ACC-2G", "soc": None}


def base(name):
    df = raw(name)
    return df if BASE[name] is None else df[df.derivative == BASE[name]].reset_index(drop=True)


class WaferSplit(unittest.TestCase):
    def test_no_wafer_in_both_train_and_test(self):
        for name in BASE:
            with self.subTest(name):
                tr, te = wafer_split(base(name))
                self.assertEqual(set(tr.wafer_id) & set(te.wafer_id), set())
                self.assertEqual(len(tr) + len(te), len(base(name)))

    def test_about_a_quarter_of_wafers_held_out(self):
        for name in BASE:
            with self.subTest(name):
                share = wafer_split(base(name))[1].wafer_id.nunique() / base(name).wafer_id.nunique()
                self.assertGreater(share, 0.15)
                self.assertLess(share, 0.35)

    def test_split_is_reproducible(self):
        for name in BASE:
            with self.subTest(name):
                self.assertEqual(sorted(set(wafer_split(base(name))[1].wafer_id)),
                                 sorted(set(wafer_split(base(name))[1].wafer_id)))

    def test_demo_files_never_use_training_wafers(self):
        for demo, name in [("01_mcu_unseen_wafer_40_dies.csv", "mcu"), ("03_pmic_new_derivatives_30_dies.csv", "pmic"),
                           ("04_sensor_production_25_dies.csv", "sensor"), ("05_soc_unseen_wafers_40_dies.csv", "soc")]:
            with self.subTest(demo):
                train = set(wafer_split(base(name))[0].wafer_id)
                self.assertEqual(set(pd.read_csv(DEMO / demo).wafer_id) & train, set())


if __name__ == "__main__":
    unittest.main()
