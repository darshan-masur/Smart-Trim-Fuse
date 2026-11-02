"""SoC: rebuilt SKU rules, speed-model features, the demand-aware ILP optimiser (notebook 04)
and the greedy / exact memory-repair algorithms."""

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

ORDER = ["SoC-Pro", "SoC-Std", "SoC-Lite"]
KS = (8, 6, 4)
FCOLS = [f"core{i}_fmax_GHz" for i in range(8)]


def prepare(soc):
    d = soc.copy()
    d["n_good_cores"] = d[FCOLS].notna().sum(axis=1)
    d["leak_hot_A"] = d.iddq_25C_mA * 22 / 1000  # leakage at hot, design rule from the spec
    fs = -np.sort(-d[FCOLS].fillna(-1).values, axis=1)  # fastest core first, defective = -1
    for k in KS:
        d[f"f_top{k}"] = np.where(fs[:, k - 1] > 0, fs[:, k - 1], np.nan)
    d["ro_x_cpm"] = d.ro_freq_MHz / d.cpm_path_delay_ps
    d["log_iddq"] = np.log(d.iddq_25C_mA)
    return d


def measured_ftop(d):
    return {k: d[f"f_top{k}"].values for k in KS}


def predicted_ftop(d, bundle):
    return {k: np.where(d[f"f_top{k}"].notna(), bundle["speed_models"][k].predict(d[bundle["features"]]), np.nan)
            for k in KS}


def eligibility(d, skus, ftop, guard_ghz=0.0):
    """Per SKU: eligible?, AVS bin, power (W). The product spec's rules, rebuilt as code."""
    s_ = skus.set_index("sku")
    out = {}
    for s in ORDER:
        k, f, tdp = int(s_.loc[s, "cores"]), s_.loc[s, "fmax_GHz"], s_.loc[s, "tdp_W"]
        fslow = ftop[k] - guard_ghz
        with np.errstate(invalid="ignore", divide="ignore"):
            v_need = 0.85 * (f / fslow) ** 0.8
            b = np.ceil((np.maximum(v_need, 0.76) - 0.75) / 0.0125 - 1e-9)
            vb = 0.75 + b * 0.0125
            p = k * 0.62 * (vb / 0.85) ** 2 * f + d.leak_hot_A.values * vb
            ok = d.l2_repairable.values & np.isfinite(fslow) & (v_need <= 0.90) & (p <= tdp)
        out[s], out[s + "_bin"], out[s + "_W"] = ok, np.where(ok, b, -1), np.where(ok, p, np.nan)
    return pd.DataFrame(out, index=d.index)


def best_sku(elig):
    """The conventional rule: the best product the die qualifies for."""
    return np.select([elig[s].values for s in ORDER], ORDER, default="scrap")


def margin_split(d, skus, ftop, margin_ghz):
    """Speed-test only the dies the AI is unsure about (notebook 06, Part 4.2). Each die's product is worked out with its
    predicted speed minus and plus the margin: if both agree, the die is sold on the prediction (with the pessimistic,
    safer voltage bin); if not, it is close to a product boundary and gets the normal speed test.
    Returns (product from the prediction, its eligibility table, unsure mask)."""
    pe = eligibility(d, skus, ftop, margin_ghz)
    sure = best_sku(pe)
    return sure, pe, sure != best_sku(eligibility(d, skus, ftop, -margin_ghz))


def unsafe(assigned, pred_elig, true_elig):
    """Assignment the die can't really meet: wrong SKU, or a voltage bin lower than it needs."""
    assigned = np.asarray(assigned)
    bad = np.zeros(len(assigned), bool)
    for s in ORDER:
        m = assigned == s
        bad[m] = ~true_elig[s].values[m] | (pred_elig[s + "_bin"].values[m] < true_elig[s + "_bin"].values[m])
    return bad


def scaled_demand(skus, n_dies, n_total):
    return (skus.set_index("sku").weekly_demand_units * n_dies / n_total).round().astype(int)


def rule_revenue(sku_list, skus, demand):
    price = skus.set_index("sku").price_usd
    made = pd.Series(sku_list).value_counts().reindex(ORDER).fillna(0).astype(int)
    sold = np.minimum(made, demand[ORDER])
    return float((sold * price[ORDER]).sum()), made, sold


def optimise(elig, skus, demand):
    """Integer linear program: maximise revenue, units per SKU <= demand, each die used once, only eligible SKUs."""
    price = skus.set_index("sku").price_usd.to_dict()
    pattern = elig[ORDER].apply(lambda r: tuple(s for s in ORDER if r[s]), axis=1)
    groups = pattern.value_counts()
    var = [(g, s) for g in groups.index for s in g]
    if not var:
        return pd.Series(dtype=int), pattern, 0.0
    # tiny tie-break: at equal revenue, keep a die in its own best product (the group's first entry)
    c = -np.array([price[s] + (1e-3 if s == g[0] else 0.0) for g, s in var], float)
    a_sku = np.array([[1 if s == t else 0 for _, s in var] for t in ORDER])
    a_grp = np.array([[1 if g == h else 0 for g, _ in var] for h in groups.index])
    sol = milp(c, constraints=[LinearConstraint(a_sku, 0, demand[ORDER].values),
                               LinearConstraint(a_grp, 0, groups.values)],
               integrality=np.ones(len(var)), bounds=Bounds(0, np.inf))
    alloc = pd.Series(sol.x.round().astype(int), index=pd.MultiIndex.from_tuples(var, names=["group", "sku"]))
    revenue = float(sum(n * price[s] for (_, s), n in alloc.items()))
    return alloc, pattern, revenue


def assign_dies(alloc, pattern):
    """Hand the optimiser's group counts out to individual dies."""
    out = pd.Series("unsold", index=pattern.index)
    for (g, s), n in alloc.items():
        free = pattern.index[(pattern == g).values & (out == "unsold").values][:n]
        out.loc[free] = s
    return out


# ---------------------------------------------------------------- memory repair (4 spare rows + 4 spare columns)
def parse(cells):
    return set() if pd.isna(cells) else {tuple(map(int, c.split(":"))) for c in cells.split(";")}


def greedy_repair(fails, sr=4, sc=4):
    """Replace the line with the most fails, again and again. Returns (ok, rows, cols)."""
    fails, rows, cols = set(fails), [], []
    while fails and (sr or sc):  # same tie-breaking as notebook 04 (matches the dataset's labels 100 %)
        rc, cc = pd.Series([r for r, _ in fails]).value_counts(), pd.Series([c for _, c in fails]).value_counts()
        br = (rc.index[0], rc.iloc[0]) if sr else (None, -1)
        bc = (cc.index[0], cc.iloc[0]) if sc else (None, -1)
        if br[1] >= bc[1]:
            fails = {f for f in fails if f[0] != br[0]}
            rows.append(br[0])
            sr -= 1
        else:
            fails = {f for f in fails if f[1] != bc[0]}
            cols.append(bc[0])
            sc -= 1
    return not fails, rows, cols


def exact_repair(fails, sr=4, sc=4):
    """Must-repair lines first, then branch and bound. Finds a repair whenever one exists. Returns (ok, rows, cols)."""
    if not fails:
        return True, [], []
    rows, cols = {}, {}
    for r, c in fails:
        rows.setdefault(r, set()).add(c)
        cols.setdefault(c, set()).add(r)
    for r, cs in rows.items():  # a row with more fails than spare columns must take a spare row
        if len(cs) > sc:
            if not sr:
                return False, [], []
            ok, a, b = exact_repair({f for f in fails if f[0] != r}, sr - 1, sc)
            return ok, [r] + a, b
    for c, rs in cols.items():
        if len(rs) > sr:
            if not sc:
                return False, [], []
            ok, a, b = exact_repair({f for f in fails if f[1] != c}, sr, sc - 1)
            return ok, a, [c] + b
    if len(fails) > 2 * sr * sc:  # bound: too many fails left for the spares
        return False, [], []
    r, c = min(fails)  # branch: this cell needs its row or its column
    if sr:
        ok, a, b = exact_repair({f for f in fails if f[0] != r}, sr - 1, sc)
        if ok:
            return True, [r] + a, b
    if sc:
        ok, a, b = exact_repair({f for f in fails if f[1] != c}, sr, sc - 1)
        if ok:
            return True, a, [c] + b
    return False, [], []
