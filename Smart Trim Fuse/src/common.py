"""Helpers shared by every chip: the wafer split and the trim-code metrics used on the test floor."""

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from src.config import SEED


def wafer_split(df):
    """Same split as the notebooks: 25 % of wafers held out, no wafer on both sides."""
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED).split(df, groups=df.wafer_id))
    return df.iloc[tr].reset_index(drop=True), df.iloc[te].reset_index(drop=True)


def to_code(pred, bits):
    """A trim code is a whole number inside the DAC range."""
    return np.clip(np.round(pred), 0, 2 ** bits - 1).astype(int)


def ai_iterations(err, bits):
    """Predict -> verify: 1 measurement if exact, 2 if one step off, else fall back to the full search."""
    err = np.abs(err)
    return np.where(err == 0, 1, np.where(err <= 1, 2, 1 + bits))


def code_metrics(y, pred_raw, bits, conv_iters):
    code = to_code(pred_raw, bits)
    err = np.abs(code - np.asarray(y))
    ai = ai_iterations(err, bits).mean()
    return {"exact": (err == 0).mean(), "within1": (err <= 1).mean(), "ai_iters": ai,
            "conv_iters": float(conv_iters), "saved": 1 - ai / conv_iters, "mae": np.abs(np.asarray(y) - pred_raw).mean()}
