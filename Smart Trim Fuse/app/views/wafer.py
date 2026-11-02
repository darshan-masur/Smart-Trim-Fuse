import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import ui

from src import mcu as M
from src import pmic as P
from src import sensor as S
from src import soc as Q
from src.common import ai_iterations, to_code

st.title("Wafer lab")
ui.plain(
    "Each square is one chip (die), drawn where it sat on the silicon wafer. The colour shows what happened to it. "
    "Every wafer here was <b>held out</b>: the AI never saw it while learning. Hover over a square for its details."
)

RESULT = {"Exact first time": ui.GOOD, "One step off (+1 check)": ui.STEP, "Fallback: full search": ui.BAD}
PASS = {"Passes final test": ui.GOOD, "Fails final test": ui.BAD}
SKU = {"SoC-Pro": "sku-pro", "SoC-Std": "sku-std", "SoC-Lite": "sku-lite", "scrap": "sku-scrap", "unsold": "chart-muted"}
GRADES = {"Tight (±10 mg, ±0.5%)": (10.0, 0.5), "Medium (±12 mg, ±1%)": (12.0, 1.0), "Loose (±15 mg, ±1%)": (15.0, 1.0)}
VIEWS = {"MCU": ["AI trim result", "What-if: checks", "Drift fix", "Before trim"],
         "PMIC": ["AI rail result", "What-if: checks", "Hidden defects"],
         "Sensor": ["One-insertion result", "Package stress"], "SoC": ["Product plan", "What-if: speed test", "Working cores"]}
BUDGET = {"Exact first time": ui.GOOD, "Found with the extra checks": ui.STEP, "Fallback: full search": ui.BAD}
HYBRID = {"Sold on the prediction": ui.GOOD, "Speed-tested": ui.NA, "Sold too fast": ui.BAD}


def outcome(worst_err):
    return np.select([worst_err == 0, worst_err <= 1], ["Exact first time", "One step off (+1 check)"],
                     "Fallback: full search")


def budget_view(d, errs, bits, chip_name):
    """What-if: how many extra one-step checks the tester may try before it falls back to the conventional search."""
    b = st.select_slider("Extra checks the tester may try before falling back to the conventional search", [0, 1, 2, 3], value=1,
                         key=f"wl_budget_{chip_name}")
    worst = np.max(list(errs.values()), axis=0)
    d = d.assign(Result=np.select([worst == 0, worst <= b], ["Exact first time", "Found with the extra checks"],
                                  "Fallback: full search"))
    tries = sum(np.where(e <= b, 1 + e, 1 + bits[t]) for t, e in errs.items())
    allw = pd.DataFrame(ui.evaluation()["budget"]).query("chip == @chip_name").set_index("budget").loc[b]
    single(ui.wafer_map(d, "Result", BUDGET, [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N")], 470),
           [("Tries per chip, this wafer", f"{tries.mean():.1f}", None),
            ("Fall back, this wafer", f"{(d.Result == 'Fallback: full search').mean():.0%}", None),
            ("All test wafers", f"{allw.tries_per_chip:.1f} tries · {allw['fallback_%']:.0f}% fall back", None)],
           f"Conventional flow: about {allw.today:.0f} tries per chip. The project uses 1 extra check. In the simulation, no code is "
           "accepted until a measurement confirms it, at every setting.",
           "Move the slider. <b>0</b>: only exact guesses are kept, so more chips fall back. <b>1</b> (the project's "
           "choice) rescues the chips one step off. <b>2-3</b> rescue a few more, with smaller gains each time. "
           "In the simulation this trades tester time only, because every accepted code is measured first.")


def single(chart, metrics, caption, notice):
    """Big map on the left, the few numbers that explain it on the right."""
    a, b = st.columns([2.4, 1], gap="medium")
    with a:
        ui.show_map(chart)
    with b:
        for label, value, delta in metrics:
            st.metric(label, value, delta, delta_color="normal" if delta else "off")
        st.caption(caption)
    ui.plain(notice, label="What to notice")


def pair(left_chart, right_chart, metrics, notice):
    """Before / after maps side by side in one chart, numbers underneath."""
    ui.show_pair(left_chart, right_chart)
    cols = st.columns(len(metrics))
    for c, (label, value, delta) in zip(cols, metrics, strict=True):
        c.metric(label, value, delta, delta_color="normal" if delta else "off")
    ui.plain(notice, label="What to notice")


toolbar = st.container(key="wl_toolbar")
c1, c2, c3 = toolbar.columns([1.3, 2.5, 1.1], vertical_alignment="bottom")
with c1:
    chip = st.segmented_control("Chip", list(VIEWS), default="MCU", key="wl_chip") or "MCU"
with c2:
    view = st.segmented_control("Show", VIEWS[chip], default=VIEWS[chip][0], key=f"wl_view_{chip}") or VIEWS[chip][0]

# ============================================================== MCU
if chip == "MCU" and view == "AI trim result":
    te = ui.mcu_test()
    with c3:
        w = st.selectbox("Wafer (MCU-A, held out)", sorted(te.wafer_id.unique()), key="wl_mcu_w")
    d = te[te.wafer_id == w].copy()
    errs = {t: np.abs(to_code(d[f"pred_{t}"], c["bits"]) - d[c["label"]]) for t, c in M.TRIMS.items()}
    d["Result"] = outcome(np.max(list(errs.values()), axis=0))
    for t, c in M.TRIMS.items():
        d[f"{t}_ai"] = to_code(d[f"pred_{t}"], c["bits"])
    today = sum(d[c["conv"]].mean() for c in M.TRIMS.values())
    ai = np.mean(sum(ai_iterations(errs[t], c["bits"]) for t, c in M.TRIMS.items()))
    single(ui.wafer_map(d, "Result", RESULT, [
               alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N"),
               alt.Tooltip("bg_trim_code_opt:Q", title="Bandgap best"), alt.Tooltip("bg_ai:Q", title="Bandgap AI"),
               alt.Tooltip("hsi_trim_code_opt:Q", title="Clock best"), alt.Tooltip("hsi_ai:Q", title="Clock AI"),
               alt.Tooltip("ldo_trim_code_opt:Q", title="LDO best"), alt.Tooltip("ldo_ai:Q", title="LDO AI")], 470),
           [("No search needed", f"{(d.Result != 'Fallback: full search').mean():.0%}", None),
            ("Tester steps per chip", f"{today:.0f} → {ai:.1f}", f"{ai - today:+.1f} steps")],
           "Teal ✓: all 3 codes exact. Gold •: one code one step off, fixed with one extra check. Copper ×: one "
           "circuit (usually the clock) failed its check and fell back to the conventional search.",
           "About <b>4 in 5 chips</b> finish without any search, and the average chip needs about 5 steps instead of "
           "20. In the simulation the copper chips cost tester time, not a wrong code: a code is accepted only after "
           "a measurement confirms it. Synthetic data.")

elif chip == "MCU" and view == "What-if: checks":
    te = ui.mcu_test()
    with c3:
        w = st.selectbox("Wafer (MCU-A, held out)", sorted(te.wafer_id.unique()), key="wl_mcu_w2")
    d = te[te.wafer_id == w].copy()
    budget_view(d, {t: np.abs(to_code(d[f"pred_{t}"], c["bits"]) - d[c["label"]]).values for t, c in M.TRIMS.items()},
                {t: c["bits"] for t, c in M.TRIMS.items()}, "MCU")

elif chip == "MCU" and view == "Drift fix":
    c2d, cw = ui.mcu_drift()
    with c3:
        st.text_input("Wafer (MCU-C, held out)", cw[1], disabled=True, key="wl_drift_w")
    d = c2d.assign(Today=np.where(np.abs(c2d.bg_final_V - 1.2) <= 5e-3, "Passes final test", "Fails final test"),
                   AI=np.where(np.abs(c2d.final_ai_V - 1.2) <= 5e-3, "Passes final test", "Fails final test"),
                   mv_today=(c2d.bg_final_V - 1.2) * 1000, mv_ai=(c2d.final_ai_V - 1.2) * 1000)
    rescued = int(((d.Today == "Fails final test") & (d.AI == "Passes final test")).sum())
    p_t, p_a = (d.Today == "Passes final test").mean(), (d.AI == "Passes final test").mean()
    tip = [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("mv_today:Q", title="Conventional flow: mV from 1.200 V", format="+.1f"),
           alt.Tooltip("mv_ai:Q", title="With AI: mV from 1.200 V", format="+.1f")]
    pair(ui.wafer_map(d, "Today", PASS, tip, 330, "Conventional flow: trim to 1.200 V"),
         ui.wafer_map(d, "AI", PASS, tip, 330, "With the drift-aware target"),
         [("Pass final test", f"{p_t:.1%} → {p_a:.1%}", f"{p_a - p_t:+.1%}"), ("Chips rescued", f"{rescued}", None),
          ("Fine-tuned with", "50 MCU-C chips", None)],
         "Packaging stress pushes the bandgap up after wafer sort (a little more toward the edge), so chips trimmed "
         "to exactly 1.200 V can end up out of spec: those are the copper × chips in the conventional flow. The AI predicts each chip's shift "
         "and trims it slightly low, so it lands on 1.200 V after packaging. It learned on the big MCU-A product and was tuned with only 50 MCU-C chips (transfer learning).")

elif chip == "MCU":
    mcu = ui.raw("mcu")
    with c3:
        w = st.selectbox("Wafer", sorted(mcu.wafer_id.unique()), key="wl_mcu_raw")
    d = mcu[mcu.wafer_id == w].assign(mv=lambda x: (x.bg_untrim_V - 1.2) * 1000)
    ch = ui.Map(lambda s, lg: alt.Chart(d).mark_rect(cornerRadius=3, stroke=ui.tok("bg"), strokeWidth=1.5).encode(
        x=alt.X("die_x:O", axis=None), y=alt.Y("die_y:O", axis=None, sort="descending"),
        color=alt.Color("mv:Q", scale=alt.Scale(scheme="blueorange", domainMid=0),
                        legend=alt.Legend(title="mV from 1.200 V", orient=lg)),
        tooltip=[alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("mv:Q", title="mV off target", format="+.1f"),
                 alt.Tooltip("bg_trim_code_opt:Q", title="Best trim code")]).properties(width=s, height=s), 470)
    single(ch, [("Product", d.derivative.iloc[0], None), ("Spread before trim", f"{d.mv.min():+.0f} to {d.mv.max():+.0f} mV", None)],
           "Orange = above 1.200 V, blue = below. Every chip needs its own trim code.",
           "The error forms <b>rings and slopes</b> across the wafer, not random noise. That's why the model is given "
           "each chip's position and the process measurements: they explain part of the pattern.")

# ============================================================== PMIC
elif chip == "PMIC":
    te, ot = ui.pmic_test(), ui.pmic_others()
    allp = pd.concat([te.assign(src="P1, held out"), ot.assign(src=ot.derivative.str.replace("PMIC-", "") + ", new derivative")])
    wl = allp.drop_duplicates("wafer_id")
    with c3:
        w = st.selectbox("Wafer", (wl.wafer_id + " (" + wl.src + ")").tolist(), key="wl_pmic_w").split(" (")[0]
    d = allp[allp.wafer_id == w].copy()
    if view == "What-if: checks":
        budget_view(d, {r: np.abs(to_code(d[f"pred_{r}"], 6) - d[f"{r}_trim_code_opt"]).values for r in P.RAILS},
                    {r: 6 for r in P.RAILS}, "Power chip")
    elif view == "AI rail result":
        d["Result"] = outcome(np.max([np.abs(to_code(d[f"pred_{r}"], 6) - d[f"{r}_trim_code_opt"]) for r in P.RAILS], axis=0))
        single(ui.wafer_map(d, "Result", RESULT, [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N")] +
                            [alt.Tooltip(f"{r}_trim_code_opt:Q", title=f"{r} best") for r in P.RAILS], 470),
               [("No search needed", f"{(d.Result != 'Fallback: full search').mean():.0%}", None),
                ("Rail measurements", "4 → 0 per chip", None)],
               "Only the reference voltage is measured; all 4 output rails are predicted. Teal ✓: all exact. Gold •: a "
               "rail one step off. Copper ×: a rail fell back to the normal trim.",
               "Wafers of the <b>P2 and C7 derivatives</b> look like P1, although the model only learned on P1. The rails "
               "follow the reference almost linearly, so a simple model carries over to new products.")
    else:
        flag = (d.efficiency_1A_pct < 88) | (d.load_reg_mV > 10)
        d["Result"] = np.select([flag & d.latent_defect, flag & ~d.latent_defect, ~flag & d.latent_defect],
                                ["Hidden defect caught", "False alarm", "Defect missed"], "Normal chip")
        single(ui.wafer_map(d, "Result", {"Normal chip": ui.GOOD, "Hidden defect caught": ui.BAD, "False alarm": ui.STEP,
                                          "Defect missed": ui.NA},
                            [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N"),
                             alt.Tooltip("efficiency_1A_pct:Q", title="Efficiency %", format=".1f"),
                             alt.Tooltip("load_reg_mV:Q", title="Load regulation mV", format=".1f")], 470),
               [("Hidden defects here", f"{int(d.latent_defect.sum())}", None),
                ("Caught by the rule", f"{int((flag & d.latent_defect).sum())}", None)],
               "A hidden defect passes the first test but fails later. Rule: efficiency below 88% or load regulation "
               "above 10 mV.",
               "On every PMIC wafer the simple datasheet rule catches <b>all</b> hidden defects with no false alarms. An "
               "AI anomaly detector caught fewer than half, so the rule stays.")

# ============================================================== Sensor
elif chip == "Sensor":
    _, te, ot, _ = ui.sensor_sets()
    sraw = ui.raw("sensor")
    der = sraw.drop_duplicates("wafer_id").set_index("wafer_id").derivative
    wl = sorted(set(te.wafer_id)) + sorted(set(ot.wafer_id))
    with c3:
        w = st.selectbox("Wafer", [f"{x} ({der[x]})" for x in wl], key="wl_sen_w").split(" (")[0]
    pos = sraw[sraw.wafer_id == w][["die_id", "die_x", "die_y", "characterized_3temp", "stress_gauge_mV", "radius_mm"]]
    if view == "One-insertion result":
        g = st.segmented_control("Product grade", list(GRADES), default="Medium (±12 mg, ±1%)", key="wl_grade") or \
            "Medium (±12 mg, ±1%)"
        ol, sl = GRADES[g]
        prod = pd.concat([te, ot[~ot.characterized_3temp]])
        p = prod[prod.wafer_id == w]
        e = S.errors(p, p.pred_tco.values, p.pred_tcs.values, p.pred_tco2.values)
        ok = np.ones(len(p), bool)
        for s in ("m40C", "85C"):
            ok &= (np.abs(e[f"off_{s}"]) <= ol) & (np.abs(e[f"sens_{s}"]) <= sl)
        die_ok = pd.Series(ok, index=p.index).groupby(p.die_id).all()
        d = pos.assign(Result=np.where(pos.characterized_3temp, "Sample: tested at 3 temperatures",
                                       np.where(pos.die_id.map(die_ok).fillna(False).astype(bool), "1 oven pass is enough",
                                                "Needs the 3-temperature test")))
        prodn = (d.Result != "Sample: tested at 3 temperatures").sum()
        single(ui.wafer_map(d, "Result", {"1 oven pass is enough": ui.GOOD, "Needs the 3-temperature test": ui.BAD,
                                          "Sample: tested at 3 temperatures": ui.NA},
                            [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N")], 470),
               [("Skip the hot and cold tests", f"{(d.Result == '1 oven pass is enough').sum() / max(prodn, 1):.0%}", None),
                ("Oven passes", "3 → 1", None)],
               "Each chip is tested at 25 °C only and the AI predicts how it behaves at −40 and 85 °C. Teal ✓: all 3 "
               "axes inside the grade's limits. Copper ×: needs the full test. Grey –: the 20% sample that still gets "
               "the full test.",
               "Switch the grade: at <b>Tight</b> many chips still need the full test, at <b>Medium</b> and <b>Loose</b> "
               "almost the whole wafer turns teal. So the one-insertion flow is used for the looser grades.")
    else:
        single(ui.wafer_heat(pos, "stress_gauge_mV", "Stress gauge (mV)",
                             [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("stress_gauge_mV:Q", format=".1f"),
                              alt.Tooltip("radius_mm:Q", title="From centre (mm)", format=".0f")], 470),
               [("Stress: edge vs centre", f"{pos[pos.radius_mm > 70].stress_gauge_mV.mean():.1f} vs "
                                          f"{pos[pos.radius_mm < 40].stress_gauge_mV.mean():.1f} mV", None)],
               "An on-chip gauge measures package stress. Stress shifts the offset, the temperature drift and the "
               "solder-reflow shift, so the model uses it.",
               "Stress grows toward the <b>edge</b> of the wafer, the same place where chips most often need the full "
               "temperature test.")

# ============================================================== SoC
elif view == "What-if: speed test":
    te, ftop = ui.soc_test()
    ev = ui.evaluation()
    with c3:
        w = st.selectbox("Wafer (held out)", sorted(te.wafer_id.unique()), key="wl_soc_w2")
    chosen = ev["soc_hybrid_MHz"]
    m = st.select_slider("Safety margin (MHz): a chip closer than this to a product boundary gets the 450 ms speed test",
                         list(range(0, 161, 10)), value=chosen, key="wl_soc_margin")
    sku = ui.raw("sku")
    sure, pe, unsure = Q.margin_split(te, sku, ftop, m / 1000)
    true_e = Q.eligibility(te, sku, Q.measured_ftop(te))
    esc = Q.unsafe(sure, pe, true_e) & ~unsure
    d = te.assign(Result=np.select([unsure, esc], ["Speed-tested", "Sold too fast"],
                                   "Sold on the prediction"), ai=sure, tested=Q.best_sku(true_e))
    d = d[d.wafer_id == w]
    single(ui.wafer_map(d, "Result", HYBRID, [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("Result:N"),
                                              alt.Tooltip("ai:N", title="AI product"),
                                              alt.Tooltip("tested:N", title="Speed-test product")], 470),
           [("Speed tests skipped, this wafer", f"{(d.Result != 'Speed-tested').mean():.0%}", None),
            ("Chips sold too fast, this wafer", f"{int((d.Result == 'Sold too fast').sum())}", None)],
           f"Teal ✓: far from any product boundary, sold on the prediction. Grey –: close to a boundary, so it gets "
           f"the normal speed test. Copper ×: sold as faster than it really is. Margin chosen on validation wafers: "
           f"{chosen} MHz.",
           "Move the slider down and copper chips appear: the risk of selling a chip too fast grows. Move it up and more "
           "chips get the speed test: safer, but less time saved. The margin was chosen on <b>validation</b> wafers "
           "(the smallest with zero escapes) and only then checked on these untouched wafers.")
    vc, tc = (pd.DataFrame(ev[k]).set_index("margin_MHz") for k in ("soc_curve_validation", "soc_curve_test"))
    ui.step(1, f"All wafers at {m} MHz: validation vs untouched test", "The margin was chosen on the left, checked on the right")
    cols = st.columns(2)
    for col, (name, cv) in zip(cols, [("Validation wafers (used to choose)", vc.loc[m]), ("Untouched test wafers", tc.loc[m])]):
        with col:
            ui.card(f"{100 - cv['hybrid_tested_%']:.0f}% skipped",
                    f"{int(cv.hybrid_escapes)} of {int(cv.chips)} chips sold too fast ({cv['hybrid_escape_%']:.2f}%) · "
                    f"revenue {cv['hybrid_revenue_%']:.1f}% of full testing", name)
    curve = pd.concat([vc.assign(Wafers="Validation"), tc.assign(Wafers="Untouched test")]).reset_index()
    line = alt.Chart(curve).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("margin_MHz:Q", title="Safety margin (MHz)"),
        y=alt.Y("hybrid_escape_%:Q", title="Chips sold too fast (%)"),
        color=alt.Color("Wafers:N", scale=ui.colors({"Validation": "probe", "Untouched test": "state-fallback"})),
        tooltip=["Wafers:N", "margin_MHz:Q", alt.Tooltip("hybrid_escape_%:Q", format=".2f"),
                 alt.Tooltip("hybrid_tested_%:Q", title="Speed-tested %", format=".1f")])
    rule = alt.Chart(pd.DataFrame({"m": [m]})).mark_rule(strokeDash=[4, 4], color=ui.tok("text-muted")).encode(x="m:Q")
    st.altair_chart(ui.chart_style((line + rule).properties(height=220)), width="stretch")
    st.caption("Where the two lines differ, the untouched wafers did worse than validation: that is why the margin is "
               "picked with zero escapes, not \"almost zero\".")

else:
    plan = ui.soc_plans()
    with c3:
        w = st.selectbox("Wafer", sorted(plan.wafer_id.unique()), key="wl_soc_w")
    d = plan[plan.wafer_id == w].copy()
    if view == "Product plan":
        moved = int(((d.today == "SoC-Std") & (d.optimised == "SoC-Lite")).sum())
        tip = [alt.Tooltip("die_id:N", title="Chip"), alt.Tooltip("today:N", title="Conventional rule"),
               alt.Tooltip("optimised:N", title="Optimised"), alt.Tooltip("n_good_cores:Q", title="Working cores")]
        pair(ui.wafer_map(d, "today", SKU, tip, 330, "Conventional rule"), ui.wafer_map(d, "optimised", SKU, tip, 330, "Optimised plan"),
             [("Std chips sold as Lite", f"{moved}", None),
              ("Lite chips on this wafer", f"{(d.today == 'SoC-Lite').sum()} → {(d.optimised == 'SoC-Lite').sum()}", None),
              ("All 20 wafers", "+34.7% revenue", None)],
             "In the conventional flow every chip becomes the best product it qualifies for, so far too many Std (orange) and too few Lite "
             "(green) are made. The optimiser sells the <b>slowest</b> Std-capable chips as Lite (2 more cores switched "
             "off) to match demand: the same chips earn $356,665 → $480,470 a week. Grey: chips beyond what was ordered.")
    else:
        single(ui.wafer_heat(d, "n_good_cores", "Working cores", [alt.Tooltip("die_id:N", title="Chip"),
                             alt.Tooltip("n_good_cores:Q", title="Working cores")], 460, scheme="greens"),
               [("All 8 cores working", f"{(d.n_good_cores == 8).mean():.0%}", None),
                ("Broken cores: edge vs centre", f"{8 - d[d.radius_mm > 100].n_good_cores.mean():.1f} vs "
                                                f"{8 - d[d.radius_mm < 50].n_good_cores.mean():.1f}", None)],
               "Each square's colour is the number of working cores (dark = all 8).",
               "Broken cores pile up at the <b>edge</b> of the wafer. Those chips can still be sold as Std or Lite by "
               "switching the broken cores off (harvesting).")
