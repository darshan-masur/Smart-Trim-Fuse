"""Customer OTP request rules (PMIC datasheet limits, I2C address, power-up sequence)."""

import unittest

import pandas as pd

from common import DEMO, B, raw
from src import pmic as P

OK = dict(buck1=0.8, buck2=1.1, ldo1=1.8, ldo2=3.3, sequence="buck1>buck2>ldo1>ldo2", i2c_addr="0x60", bus=["0x3B"])


def label(**kw):
    a = {**OK, **kw}
    return P.check_request(a["buck1"], a["buck2"], a["ldo1"], a["ldo2"], a["sequence"], a["i2c_addr"], a["bus"])[0]


class Rules(unittest.TestCase):
    def test_each_rule(self):
        self.assertEqual(label(), "valid")
        self.assertEqual(label(buck1=2.0), "out_of_range")
        self.assertEqual(label(i2c_addr="0x05"), "address_reserved")
        self.assertEqual(label(i2c_addr="0x7A"), "address_reserved")
        self.assertEqual(label(bus=["0x60"]), "address_collision")
        self.assertEqual(label(bus=[]), "valid")
        self.assertEqual(label(sequence="buck1>buck2>ldo1"), "invalid_sequence")
        self.assertEqual(label(sequence="buck1>buck1>ldo1>ldo2"), "invalid_sequence")
        self.assertEqual(label(sequence="ldo2>buck1>buck2>ldo1"), "sequence_conflict")

    def test_first_broken_rule_wins_when_two_fail(self):
        self.assertEqual(label(buck1=2.0, i2c_addr="0x05"), "out_of_range")

    def test_unreadable_address_is_not_valid(self):
        d, _ = B.clean(pd.DataFrame([{"buck1_V": 0.8, "buck2_V": 1.1, "ldo1_V": 1.8, "ldo2_V": 3.3,
                                      "sequence": OK["sequence"], "i2c_addr": "0xZZ", "other_addresses_on_bus": ""}]),
                       "Customer OTP requests")
        out, _ = B.run_otp(d)
        self.assertEqual(out.verdict.iloc[0], "unreadable")

    def test_dataset_and_demo_labels_match(self):
        r = raw("otp_req")
        got = [P.check_request(x.buck1_V, x.buck2_V, x.ldo1_V, x.ldo2_V, str(x.sequence), str(x.i2c_addr),
                               [a for a in str(x.other_addresses_on_bus).split(";") if a.strip() and a != "nan"])[0]
               for x in r.itertuples()]
        self.assertEqual(got, list(r.label))
        demo = pd.read_csv(DEMO / "06_otp_customer_requests_12.csv")
        d, _ = B.clean(demo, "Customer OTP requests")
        out, _ = B.run_otp(d)
        self.assertEqual(list(out.verdict), list(demo.expected_label))


if __name__ == "__main__":
    unittest.main()
