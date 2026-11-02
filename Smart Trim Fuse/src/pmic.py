"""PMIC: rail and threshold trims (notebook 02), current-sense calibration and the customer OTP rule checker."""

import numpy as np
import pandas as pd

RAILS = ["buck1", "buck2", "ldo1", "ldo2"]
LIMITS = {"buck1": (0.4, 1.8), "buck2": (0.4, 1.8), "ldo1": (0.8, 3.3), "ldo2": (1.2, 3.6)}  # datasheet limits (V)

CFG = {
    "vref": dict(label="vref_trim_code_opt", untrim="vref_untrim_V", bits=6, mid=32, lsb=0.00075, mult=False,
                 target=0.600, trimmed="vref_trimmed_sort_V", spec=0.0025, conv=6.33),
    "ovp": dict(label="ovp_trim_code_opt", untrim="ovp_untrim_V", bits=4, mid=8, lsb=0.005, mult=True,
                target=3.63, trimmed="ovp_trimmed_V", spec=None, conv=4),
    "uvlo": dict(label="uvlo_trim_code_opt", untrim="uvlo_untrim_V", bits=4, mid=8, lsb=0.005, mult=True,
                 target=2.70, trimmed="uvlo_trimmed_V", spec=None, conv=4),
    "ilim": dict(label="ilim_trim_code_opt", untrim="ilim_untrim_A", bits=5, mid=16, lsb=0.01, mult=True,
                 target=3.0, trimmed="ilim_trimmed_A", spec=None, conv=5),
}
for _r in RAILS:
    CFG[_r] = dict(label=f"{_r}_trim_code_opt", untrim=f"{_r}_untrim_V", bits=6, mid=32, lsb=0.002, mult=True,
                   target=f"{_r}_target_V", trimmed=f"{_r}_trimmed_sort_V", spec=0.005, conv=6.33)


def target(c, df):
    return df[c["target"]].values if isinstance(c["target"], str) else c["target"]


def formula_code(df, t):
    c = CFG[t]
    u = df[c["untrim"]].values
    return c["mid"] + (target(c, df) / u - 1) / c["lsb"] if c["mult"] else c["mid"] - (u - c["target"]) / c["lsb"]


def add_features(df):
    """Physics features used by the saved models (notebook 02, Parts 4, 6 and 10)."""
    d = df.copy()
    d["ref_ideal_code"] = 32 + (0.600 / d.vref_trimmed_sort_V - 1) / 0.002
    d["vref_err_mV"] = (d.vref_untrim_V - 0.600) * 1000
    s = (d.cs_meas_2p0A_A - d.cs_meas_0p5A_A) / 1.5
    d["cs_gain_2pt"] = (s - 1) * 100
    d["cs_off_2pt"] = (d.cs_meas_0p5A_A - 0.5 * s) * 1000
    return d


def predict_rails(df, bundle):
    d = add_features(df)
    return pd.DataFrame({r: bundle["rails"][r]["model"].predict(d[bundle["rails"][r]["features"]]) for r in RAILS},
                        index=df.index)


# ---------------------------------------------------------------- current sense
CS_TARGETS = ["cs_gain_err_true_pct", "cs_offset_true_mA", "cs_inl_true_pct"]
SWEEP = np.linspace(0, 3, 31)


def sensor_error(ge, off, inl):
    """Current error (A) over a 0-3 A sweep, one row per die."""
    ge, off, inl = (np.atleast_1d(np.asarray(x, float)) for x in (ge, off, inl))
    i = SWEEP[None, :]
    return i * ge[:, None] / 100 + off[:, None] / 1000 + inl[:, None] / 100 * i * (i - 3) / 1.5


# ---------------------------------------------------------------- OTP request checker
def check_request(buck1, buck2, ldo1, ldo2, sequence, i2c_addr, bus):
    """Datasheet rules in priority order. Returns (label, [(rule, passed, detail), ...])."""
    volts = {"buck1": buck1, "buck2": buck2, "ldo1": ldo1, "ldo2": ldo2}
    seq = [s.strip() for s in sequence.split(">") if s.strip()]
    addr = int(i2c_addr, 16) if isinstance(i2c_addr, str) else int(i2c_addr)
    bus_ints = [int(a, 16) for a in bus] if bus and isinstance(bus[0], str) else list(bus or [])
    bad_v = [f"{k} {v:.3f} V (allowed {LIMITS[k][0]}-{LIMITS[k][1]} V)" for k, v in volts.items()
             if not LIMITS[k][0] <= v <= LIMITS[k][1]]
    rules = [
        ("out_of_range", "Every rail voltage is inside its datasheet limits", not bad_v,
         "; ".join(bad_v) or "all 4 rails inside limits"),
        ("address_reserved", "I²C address is not reserved (0x00-0x07, 0x78-0x7F)", 0x08 <= addr <= 0x77,
         f"address 0x{addr:02X}"),
        ("address_collision", "I²C address is free on the customer's bus", addr not in bus_ints,
         f"bus has {', '.join(f'0x{a:02X}' for a in bus_ints) or 'no other devices'}"),
        ("invalid_sequence", "Sequence powers each of the 4 rails exactly once", sorted(seq) == sorted(RAILS),
         " > ".join(seq)),
        ("sequence_conflict", "The 3.3 V I/O rail (ldo2) is not powered first", not seq or seq[0] != "ldo2",
         f"first rail: {seq[0] if seq else '-'}"),
    ]
    label = next((code for code, _, ok, _ in rules if not ok), "valid")
    return label, [(name, ok, detail) for _, name, ok, detail in rules]
