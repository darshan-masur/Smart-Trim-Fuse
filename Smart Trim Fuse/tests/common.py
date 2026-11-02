"""Shared loaders for the checks. Reads the same files as the app, without Streamlit."""

import sys
import warnings
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
warnings.filterwarnings("ignore")

from src import batch as B
from src import screen as X
from src.config import DATA, DATASETS, MODELS

DEMO = APP_ROOT.parent / "Demo"


@lru_cache
def raw(name):
    return pd.read_csv(DATA / DATASETS[name][0])


@lru_cache
def model(name):
    return joblib.load(MODELS / f"{name}_models.joblib")


@lru_cache
def screen():
    return X.fit(raw("mcu"), raw("sensor"))


def run_file(df):
    """Exactly what the Batch check page does: (kind, missing, score, cleaned, log, results, summary)."""
    kind, missing, score = B.detect(df)
    if score < 0.6 or missing:
        return kind, missing, score, None, None, None, None
    d, log = B.clean(df, kind)
    if kind.startswith("MCU dies"):
        out, summ = B.run_mcu(d, model("trim"), screen())
    elif kind.startswith("PMIC"):
        out, summ = B.run_pmic(d, model("pmic"))
    elif kind.startswith("Sensor"):
        out, summ = B.run_sensor(d, model("sensor"), screen())
    elif kind.startswith("SoC"):
        out, summ = B.run_soc(d, model("soc"), raw("sku"))
    elif kind.startswith("Customer"):
        out, summ = B.run_otp(d)
    else:
        out, summ = B.run_fuse(d, raw("schema"), raw("mcu"))
    return kind, missing, score, d, log, out, summ
