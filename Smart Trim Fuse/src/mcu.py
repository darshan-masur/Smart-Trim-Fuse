"""MCU: trim-code features (notebook 01), drift-aware bandgap target (notebook 01, Part 8)
and the rule-based fuse-map validator (schema + audit datasets, notebook 00)."""

import re

import numpy as np
import pandas as pd

TRIMS = {  # physics of each trim DAC (same as notebook 01)
    "bg": dict(name="Bandgap", unit="V", label="bg_trim_code_opt", untrim="bg_untrim_V", bits=6, mid=32,
               target=1.200, lsb=0.002, mult=False, conv="bg_conv_iterations", ms=1.2),
    "hsi": dict(name="HSI oscillator", unit="MHz", label="hsi_trim_code_opt", untrim="hsi_untrim_MHz", bits=7,
                mid=64, target=16.0, lsb=0.002, mult=True, conv="hsi_conv_iterations", ms=2.0),
    "ldo": dict(name="LDO regulator", unit="V", label="ldo_trim_code_opt", untrim="ldo_untrim_V", bits=5, mid=16,
                target=1.10, lsb=0.005, mult=False, conv="ldo_conv_iterations", ms=1.0),
}


def formula_code(df, t):
    """Physics only: assumes every die's trim DAC is perfect."""
    c = TRIMS[t]
    u = df[c["untrim"]].values
    return c["mid"] + (c["target"] / u - 1) / c["lsb"] if c["mult"] else c["mid"] - (u - c["target"]) / c["lsb"]


def add_features(df):
    d = df.copy()
    for t, c in TRIMS.items():
        d[f"{t}_ideal_code"] = formula_code(d, t)
        d[f"{t}_err_from_target"] = d[c["untrim"]] - c["target"]
    return d


def predict_codes(df, bundle):
    """Raw (unrounded) model predictions for the three trims."""
    d = add_features(df)
    return pd.DataFrame({t: bundle[t]["model"].predict(d[bundle[t]["features"]]) for t in TRIMS}, index=df.index)


# ---------------------------------------------------------------- drift-aware target
def add_drift_features(df, max_radius):
    d = df.copy()
    d["bg_shift_mV"] = (d.bg_final_V - d.bg_trimmed_sort_V) * 1000
    d["r2"] = (d.radius_mm / max_radius) ** 2
    return d


def predict_shift(df, bundle, is_c=1):
    b = bundle["bg_drift"]
    return b["model"].predict(df[b["features"][:-1]].assign(is_c=is_c))


def with_offset_target(df, shift_mV):
    """Trim to 1.200 V - predicted shift, in real 2 mV steps. Returns (final V, sort V)."""
    steps = np.round((1.2 - shift_mV / 1000 - df.bg_trimmed_sort_V) / 0.002)
    sort_v = df.bg_trimmed_sort_V + steps * 0.002
    return df.bg_final_V + (sort_v - df.bg_trimmed_sort_V), sort_v


# ---------------------------------------------------------------- fuse-map validator
def expected_values(schema):
    """Schema text -> numbers: {derivative: {field: value or None (per-die)}}."""
    def num(v):
        v = str(v)
        return None if v == "per-die" else int(v, 16) if v.startswith("0x") else int(v)
    return {d: {r.field: num(r[d]) for _, r in schema.iterrows()} for d in ["MCU-A", "MCU-B", "MCU-C"]}


WORD_BITS = 64
WORD_RE = re.compile(r"0[xX][0-9A-Fa-f]{16}")  # exactly 64 bits: "0x" + 16 hex digits
REQUIRED_FIELDS = {"BG_TRIM", "HSI_TRIM", "LDO_TRIM", "TS_CAL1", "FLASH_SIZE", "PERIPH_EN", "TEMP_GRADE",
                   "DEBUG_LOCK", "RDP", "RESERVED"}


def _layout(schema):
    return [(r.field, int(r.lsb), int(r.nbits)) for r in schema.itertuples(index=False)]


def schema_problems(schema):
    """Empty list if the schema covers every bit of the 64-bit word exactly once and has every field the rules use."""
    problems, owner = [], [None] * WORD_BITS
    for f, lsb, nb in _layout(schema):
        if nb < 1 or lsb < 0 or lsb + nb > WORD_BITS:
            problems.append(f"{f}: bits {lsb}-{lsb + nb - 1} fall outside the {WORD_BITS}-bit word")
            continue
        for b in range(lsb, lsb + nb):
            if owner[b] is not None:
                problems.append(f"bit {b} is in both {owner[b]} and {f}")
            owner[b] = f
    gaps = [b for b, o in enumerate(owner) if o is None]
    if gaps:
        problems.append(f"{len(gaps)} bit(s) belong to no field (first: bit {gaps[0]})")
    missing = REQUIRED_FIELDS - set(schema.field)
    if missing:
        problems.append("missing field(s): " + ", ".join(sorted(missing)))
    return problems


def parse_word(hex_word):
    """The word as an int, or ValueError if it is not exactly '0x' + 16 hex digits (no silent truncation)."""
    s = str(hex_word).strip()
    if not WORD_RE.fullmatch(s):
        raise ValueError(f"not a {WORD_BITS}-bit hex word ('0x' + 16 hex digits): {s!r}")
    return int(s, 16)


def decode(hex_word, schema, layout=None):
    w = parse_word(hex_word)
    return {f: (w >> lsb) & ((1 << nb) - 1) for f, lsb, nb in (layout or _layout(schema))}


# the per-die fuse fields and the sort-record columns they must equal
SORT_FIELDS = ["bg_trim_code_opt", "hsi_trim_code_opt", "ldo_trim_code_opt", "ts_cal1_30C_counts"]


def check_fuse(hex_word, derivative, schema, trims=None, _parsed=None):
    """Every rule as (rule, passed, detail). `trims` = the die's sort values in SORT_FIELDS order (bg, hsi, ldo trim
    codes, then the TS_CAL1 reading at 30 C), if known; the 4th value is optional."""
    layout, expected = _parsed or (_layout(schema), expected_values(schema))
    f, e = decode(hex_word, schema, layout), expected[derivative]
    rules = [
        ("Flash size matches the product", f["FLASH_SIZE"] == e["FLASH_SIZE"],
         f"fused {f['FLASH_SIZE']}, expected {e['FLASH_SIZE']}"),
        ("Peripheral mask matches the product", f["PERIPH_EN"] == e["PERIPH_EN"],
         f"fused 0x{f['PERIPH_EN']:02X}, expected 0x{e['PERIPH_EN']:02X}"),
        ("Temperature grade matches", f["TEMP_GRADE"] == e["TEMP_GRADE"],
         f"fused {f['TEMP_GRADE']}, expected {e['TEMP_GRADE']}"),
        ("Debug port is locked (security)", f["DEBUG_LOCK"] == 1, f"fused {f['DEBUG_LOCK']}, must be 1"),
        ("Read-out protection as required", f["RDP"] == e["RDP"], f"fused {f['RDP']}, expected {e['RDP']}"),
        ("Reserved bits are all 0", f["RESERVED"] == 0, f"value {f['RESERVED']}"),
    ]
    if trims is not None:
        fused = (f["BG_TRIM"], f["HSI_TRIM"], f["LDO_TRIM"])
        sort = tuple(int(x) for x in trims[:3])
        rules.append(("Trim fields equal the sort trim codes", fused == sort, f"fused {fused}, sort result {sort}"))
        if len(trims) > 3:
            rules.append(("TS_CAL1 equals the sort temperature-sensor reading", f["TS_CAL1"] == int(trims[3]),
                          f"fused {f['TS_CAL1']}, sort reading {int(trims[3])}"))
    return rules


def validate_all(audit, mcu, schema):
    """Run the validator on every audit word; returns the audit table with a 'flagged' column and the first broken rule."""
    trims = mcu.set_index("die_id")[SORT_FIELDS]
    codes = dict(zip(trims.index, trims.values))
    parsed = (_layout(schema), expected_values(schema))  # parse the schema once, not per word
    flagged, why = [], []
    for r in audit.itertuples(index=False):
        res = check_fuse(r.fuse_map_hex, r.derivative, schema, codes[r.die_id], parsed)
        bad = [name for name, ok, _ in res if not ok]
        flagged.append(bool(bad))
        why.append(bad[0] if bad else "all rules pass")
    return audit.assign(flagged=flagged, first_broken_rule=why)
