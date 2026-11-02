"""Fuse-word checks: PASS only for a well-formed word on an identified die whose trim fields and TS_CAL1 were checked."""

import sys
import unittest

import pandas as pd

from common import APP_ROOT, B, raw
from src import mcu as M

GOOD = {"die_id": "MCU-006745", "derivative": "MCU-B", "fuse_map_hex": "0x0000023F10C1F61A"}


def verdicts(rows, schema=None):
    d, _ = B.clean(pd.DataFrame(rows), "MCU fuse words")
    out, _ = B.run_fuse(d, raw("schema") if schema is None else schema, raw("mcu"))
    return list(out.verdict), list(out.reason)


class Schema(unittest.TestCase):
    def test_project_schema_covers_all_64_bits_once(self):
        self.assertEqual(M.schema_problems(raw("schema")), [])

    def test_gap_overlap_and_missing_field_are_reported(self):
        s = raw("schema").copy()
        gap = s[s.field != "RESERVED"]
        self.assertTrue(any("belong to no field" in p for p in M.schema_problems(gap)))
        self.assertTrue(any("missing field" in p for p in M.schema_problems(gap)))
        overlap = s.copy()
        overlap.loc[overlap.field == "HSI_TRIM", "lsb"] = 5
        self.assertTrue(any("is in both" in p for p in M.schema_problems(overlap)))
        too_wide = s.copy()
        too_wide.loc[too_wide.field == "RESERVED", "nbits"] = 22
        self.assertTrue(any("outside" in p for p in M.schema_problems(too_wide)))

    def test_broken_schema_blocks_every_word(self):
        s = raw("schema")
        v, _ = verdicts([GOOD], schema=s[s.field != "RESERVED"])
        self.assertEqual(v, ["BLOCK"])


class WordFormat(unittest.TestCase):
    def test_only_0x_plus_16_hex_digits_is_accepted(self):
        for bad in ["0x23F10C1F61A", "0x00000023F10C1F61A", "0x0000023F10C1F6ZA", "0000023F10C1F61A", "-0x1", "",
                    "nan", "0x 0000023F10C1F61A"]:
            with self.subTest(word=bad), self.assertRaises(ValueError):
                M.parse_word(bad)
        self.assertEqual(M.parse_word(" 0x0000023f10c1f61a "), 0x0000023F10C1F61A)

    def test_malformed_words_are_blocked_not_truncated(self):
        v, r = verdicts([{**GOOD, "fuse_map_hex": "0x10000023F10C1F61A"}])  # 17 digits: old code dropped the top bit
        self.assertEqual(v, ["BLOCK"])
        self.assertIn("unreadable word", r[0])

    def test_unknown_product_is_blocked(self):
        self.assertEqual(verdicts([{**GOOD, "derivative": "MCU-Z"}])[0], ["BLOCK"])


class DieIdentity(unittest.TestCase):
    def test_good_word_on_known_die_passes(self):
        v, r = verdicts([GOOD])
        self.assertEqual(v, ["PASS"])
        self.assertIn("every field checked", r[0])

    def test_never_pass_without_checking_trim_fields(self):
        cases = {
            "unknown die": [{**GOOD, "die_id": "MCU-999999"}],
            "blank die": [{**GOOD, "die_id": None}],
            "badly formed die": [{**GOOD, "die_id": "die-12"}],
            "duplicate die": [GOOD, {**GOOD, "fuse_map_hex": "0x0000023F1016D0E3"}],
            "wrong derivative for die": [{**GOOD, "die_id": "MCU-006315", "derivative": "MCU-A",
                                          "fuse_map_hex": "0x000002FF505A2A64"}],
        }
        for name, rows in cases.items():
            with self.subTest(name):
                v, _ = verdicts(rows)
                self.assertNotIn("PASS", v)
                self.assertTrue(set(v) <= {"REVIEW", "BLOCK"})

    def test_no_die_id_column_means_review(self):
        v, _ = verdicts([{k: GOOD[k] for k in ("derivative", "fuse_map_hex")}])
        self.assertEqual(v, ["REVIEW"])

    def test_rule_failure_beats_review(self):
        w = M.parse_word(GOOD["fuse_map_hex"]) | (1 << 50)  # set a reserved bit
        v, _ = verdicts([{**GOOD, "die_id": "MCU-999999", "fuse_map_hex": f"0x{w:016X}"}])
        self.assertEqual(v, ["BLOCK"])

    def test_wrong_ts_cal1_is_blocked(self):
        w = M.parse_word(GOOD["fuse_map_hex"]) ^ (1 << 18)  # flip the lowest bit of TS_CAL1 (bits 29-18)
        v, r = verdicts([{**GOOD, "fuse_map_hex": f"0x{w:016X}"}])
        self.assertEqual(v, ["BLOCK"])
        self.assertIn("TS_CAL1", r[0])

    def test_every_field_has_a_rule(self):
        sys.path.insert(0, str(APP_ROOT / "app"))
        import ui
        mcu = raw("mcu")
        r = mcu[mcu.die_id == GOOD["die_id"]].iloc[0]
        checks = M.check_fuse(GOOD["fuse_map_hex"], GOOD["derivative"], raw("schema"), r[M.SORT_FIELDS].values)
        self.assertEqual(len(checks), 8)
        self.assertTrue(all(ok for _, ok, _ in checks))
        self.assertEqual(ui.fuse_unchecked(checks, raw("schema")), [])

    def test_corrupt_trim_field_is_blocked(self):
        w = M.parse_word(GOOD["fuse_map_hex"]) ^ 0b1
        self.assertEqual(verdicts([{**GOOD, "fuse_map_hex": f"0x{w:016X}"}])[0], ["BLOCK"])


class AuditDataset(unittest.TestCase):
    def test_all_injected_errors_caught_with_no_false_alarms(self):
        a = M.validate_all(raw("audit"), raw("mcu"), raw("schema"))
        self.assertEqual(int((a.flagged & a.has_error).sum()), int(a.has_error.sum()))
        self.assertEqual(int((a.flagged & ~a.has_error).sum()), 0)
        self.assertEqual(int(a.has_error.sum()), 406)


if __name__ == "__main__":
    unittest.main()
