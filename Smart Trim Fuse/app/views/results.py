import altair as alt
import pandas as pd
import streamlit as st
import ui

from src import results as R
from src.config import DATASETS

h = ui.headline()
ev = ui.evaluation()
mt, ma = h["mcu_ms"]
ht, ha = h["hsi_w1"]
dt, da = ui.mcuc_headline()
pt, pa = h["pmic_steps"]
st_, sa = h["sensor_s"]
rr, ro = h["soc_rev"]
fc, fe, ff = h["fuse"]

lm, lp, ls, lq, ld = (pd.DataFrame(ev[k]) for k in ("lowo_mcu", "lowo_pmic", "lowo_sensor", "lowo_soc", "lowo_drift"))
p1, pnew = lp[lp["product"] == "PMIC-P1"], lp[lp["product"] != "PMIC-P1"]
s2 = ls[ls["product"] == "ACC-2G"]
HYB = ev["soc_hybrid_MHz"]
hyb = pd.DataFrame(ev["soc_curve_test"]).set_index("margin_MHz").loc[HYB]
vb = ui.model("vmin")  # notebook 07
vm = vb["metrics"]

st.title("Results and why")
ui.plain("One card per result: <b>before → after</b>, how it works, why that method was chosen, and how much it varies "
         "from wafer to wafer. All 9 datasets are used; each card names the ones behind it.")


def result(title, data, big, how, why, spread):
    st.html(f'<div class="card"><div class="ttl">{title}</div><div class="muted" style="margin-bottom:6px">{data}</div>'
            f'<div class="big">{big}</div><div class="muted" style="margin:2px 0 8px">{ui.icon("bar_chart")} {spread}</div>'
            f'<div class="lbl"><b>How:</b> {how}</div>'
            f'<div class="txt" style="margin-top:8px"><b>Why this method:</b> {why}</div></div>')


def span(s, fmt):
    return f"{fmt(s.min())} to {fmt(s.max())}"


cards = [
    ("MCU trimming", "mcu_trim_fuse", f"{mt:.1f} → {ma:.1f} ms",
     "a Random Forest predicts the bandgap, clock and regulator codes; the tester checks each once.",
     f"it beat 5 other models. It matters most for the clock: right or one step off for {ha:.0%} of chips, "
     f"vs {ht:.0%} with a formula.",
     f"Each of {len(lm)} wafers held out in turn: {span(lm.speedup_x, lambda v: f'{v:.1f}×')} faster"),
    ("MCU-C final test", "mcu_trim_fuse", f"{dt:.1%} → {da:.1%}",
     "predict how much packaging shifts each chip, and trim it slightly low so it lands on target.",
     "transfer learning: the model learned on the big MCU-A product and was tuned with just 50 MCU-C chips.",
     f"Only 2 wafers, so an early result: {span(pd.concat([ld['fine_tuned_min_%'], ld['fine_tuned_max_%']]), lambda v: f'{v:.1f}%')} "
     "pass, tuning on either wafer with 20 different 50-chip samples"),
    ("Fuse maps", "mcu_fuse_schema + mcu_fuse_map_audit", f"{fc} / {fe} blocked",
     f"rules built from the fuse schema check every field before burning; {ff} false alarms.",
     "the spec defines the right answer, and a fuse can't be undone, so exact rules beat a model.",
     "Rules give the same answer on every wafer: no spread to report"),
    ("PMIC trimming", "pmic_trim_otp + pmic_otp_config_requests", f"{pt:.0f} → {pa:.0f} steps",
     "Ridge predicts all 4 output voltages from one reference reading. Customer settings are checked by "
     "datasheet rules (100% correct).",
     "the rails follow the reference almost linearly, so a simple linear model wins and works on new derivatives.",
     f"{len(p1)} P1 wafers: {span(p1.fewer_tries_x, lambda v: f'{v:.1f}×')} fewer tries · {len(pnew)} wafers of "
     f"P2/C7 it never saw: {span(pnew.fewer_tries_x, lambda v: f'{v:.1f}×')}"),
    ("Sensor calibration", "sensor_calibration", f"{st_:.1f} → {sa:.1f} s",
     "test at 25 °C only and predict the hot and cold behaviour (Ridge). Most chips pass at medium and loose grades.",
     "near-linear physics and a small training set. Tight grades still use 3 temperatures: honest limit.",
     f"Medium grade on {len(s2)} wafers: {span(s2['Medium_%'], lambda v: f'{v:.0f}%')} pass with one oven pass"),
    ("SoC product plan + speed test", "soc_binning_harvesting + soc_sku_demand + memory_repair_bitmaps",
     f"+${(ro - rr):,.0f} / week",
     f"an integer program decides which product each chip becomes, to match demand. Only chips within {HYB} MHz of a "
     f"product boundary get the speed test: {100 - hyb['hybrid_tested_%']:.0f}% skip it, {int(hyb.hybrid_escapes)} of "
     f"{int(hyb.chips):,} sold too fast (95% upper bound ≈ {300 / hyb.chips:.2f}%).",
     "the product mix has an exact best answer, so an optimiser. The margin was chosen on validation wafers, then "
     "checked on untouched ones.",
     f"Plan on each of {len(lq)} wafers: {span(lq['uplift_%'], lambda v: f'+{v:.0f}%')} revenue"),
    ("SoC minimum voltage (Vmin)", "soc_binning_harvesting", f"{vm['baseline_mae_mV']:.0f} → {vm['mae_mV']:.1f} mV error",
     f"a Ridge model predicts each chip's worst-core Vmin at 2 GHz from the same monitors as the speed model, before "
     f"any voltage search. A {vb['margin_mV']} mV margin chosen on validation wafers covered every untouched chip "
     f"({vm['test_under_at_margin']} of {vm['test_chips']:,} under-predicted; 95% upper bound "
     f"{vm['upper95_pct']:.2f}%).",
     "Vmin moves almost linearly with the process monitors, so a straight-line model beat Random Forest and gradient "
     "boosting. The error before the arrow is one fleet-wide value for every chip.",
     f"Each of 20 wafers held out in turn: {vm['lowo_mae_min_mV']:.1f} to {vm['lowo_mae_max_mV']:.1f} mV"),
]
for row in range(0, len(cards), 2):
    a, b = st.columns(2)
    for col, c in zip((a, b), cards[row:row + 2]):
        with col:
            result(*c)

tabs = st.tabs([":material/scatter_plot: Across wafers", ":material/compare_arrows: Baseline vs method",
                ":material/badge: Model cards", ":material/psychology: Why simple models won",
                ":material/shield: Safety rules"])

# ---------------------------------------------------------------- across wafers
with tabs[0]:
    ui.plain("Each dot is one wafer, held out while the model learned from all the others. The dashed line is the "
             "number from the single test split used everywhere else. Close together means the result is stable.",
             label="How to read")
    charts = [("MCU: no search %", lm["no_search_%"], 83.0), ("PMIC: × fewer tries", p1.fewer_tries_x, 3.9),
              ("Sensor: pass %", s2["Medium_%"], 96.0), ("SoC: revenue +%", lq["uplift_%"], 34.7)]
    cols = st.columns(4)
    for col, (title, s, rep) in zip(cols, charts):
        d = pd.DataFrame({"v": s.values, "j": [(i % 5 - 2) * 0.12 for i in range(len(s))]})
        dots = alt.Chart(d).mark_circle(size=70, color=ui.tok("probe"), opacity=0.85).encode(
            x=alt.X("j:Q", axis=None, scale=alt.Scale(domain=[-0.6, 0.6])),
            y=alt.Y("v:Q", title=None, scale=alt.Scale(zero=False, padding=12)), tooltip=[alt.Tooltip("v:Q", format=".1f")])
        ref = alt.Chart(pd.DataFrame({"r": [rep]})).mark_rule(strokeDash=[5, 4], color=ui.tok("state-attn")).encode(y="r:Q")
        with col:
            st.altair_chart(ui.chart_style((dots + ref).properties(height=200, title=title)), width="stretch")
            st.caption(f"{len(s)} wafers · worst {s.min():.1f}, best {s.max():.1f}")
    st.caption("New chip versions have only 2-3 wafers each (MCU-C, PMIC-C7, ACC-16G), so their results are shown as "
               "early results, not ranges.")

# ---------------------------------------------------------------- baselines
with tabs[1]:
    ui.plain("Every method is compared with the conventional flow: the existing test flow, the physics formula or the current "
             "rule. A method is kept only where it improves the result that matters.", label="How to read")
    b = pd.DataFrame(ev["baselines"]).rename(columns=str.capitalize).map(ui.wording)
    st.dataframe(b, hide_index=True, width="stretch")

# ---------------------------------------------------------------- model cards
with tabs[2]:
    st.caption("One card per model: what it predicts, what it needs, what it beats, where it was tested and when it "
               "steps aside. All data is synthetic.")
    mc = ev["model_cards"]
    for i in range(0, len(mc), 2):
        cols = st.columns(2)
        for col, m in zip(cols, mc[i:i + 2]):
            rows = "".join(f'<div class="lbl" style="margin-top:4px"><b>{k.capitalize()}:</b> {ui.wording(m[k]).replace("->", "→")}</div>'
                           for k in ("predicts", "needs", "beats", "result", "tested on", "falls back when"))
            with col:
                st.html(f'<div class="card"><div class="ttl">{m["model"]}</div>{rows}'
                        f'<div class="muted" style="margin-top:8px">Data: synthetic</div></div>')
    with st.expander("Results by product version and wafer zone (chips needing no search, %)"):
        z = pd.DataFrame(ev["by_zone"]).pivot_table(index=["model", "product"], columns="zone", values="no_search_%",
                                                    sort=False).round(1).reset_index()
        st.dataframe(z, hide_index=True, width="stretch")
        st.caption("Edge = outer 30% of the wafer radius. The new versions (MCU-B, MCU-C, P2, C7) were never used for "
                   "training the trim models.")

# ---------------------------------------------------------------- simple models
with tabs[3]:
    a, b = st.columns([1.3, 1])
    with a:
        d = pd.DataFrame(R.MCU_MODELS["HSI oscillator"], columns=["Model", "Exact", "Right or one step off (%)"])
        d["Winner"] = d.Model == "Random Forest"
        st.altair_chart(ui.chart_style((
            alt.Chart(d).mark_bar(cornerRadiusEnd=4, height=18).encode(
                y=alt.Y("Model:N", sort=None, title=None), x=alt.X("Right or one step off (%):Q", scale=alt.Scale(domain=[0, 100])),
                color=alt.condition(alt.datum.Winner, alt.value(ui.tok("probe")), alt.value(ui.tok("chart-muted"))))
            + alt.Chart(d).mark_text(align="left", dx=4, color=ui.tok("text")).encode(
                y=alt.Y("Model:N", sort=None), x="Right or one step off (%):Q", text=alt.Text("Right or one step off (%):Q", format=".0f"))
        ).properties(height=220, title="Hardest trim (MCU clock): every model on unseen wafers")), width="stretch")
    with b:
        verdicts = [("Transfer learning (drift)", True), ("Random Forest / Ridge", True), ("Deep learning (MLP)", False),
                    ("Graph / spatial models (GNN, kriging)", False), ("Confidence routing", False), ("GAN", False),
                    ("RNN / LSTM", False), ("Reinforcement learning", False)]
        st.html("".join(f'<div class="check"><span class="mi {"ok" if ok else "warn"}">{"check_circle" if ok else "cancel"}</span> '
                        f'{m}</div>' for m, ok in verdicts))
        st.caption("Deep learning never won; leftover errors are random from chip to chip, so graph and spatial models "
                   "had nothing to learn.")

# ---------------------------------------------------------------- safety
with tabs[4]:
    s = st.columns(4)
    for col, (ic, t, x) in zip(s, [
            ("verified", "Verify first", "In the simulation, every prediction is checked once before a fuse would be "
                                         "blown."),
            ("undo", "Fall back", "A failed check, or a reading outside the training range, sends the chip to the "
                                  "conventional flow: in the simulation this costs time, not quality."),
            ("lock", "Rules for security", "Debug locks and protection bits are checked by fixed rules. A fuse word "
                                           "passes only when the die is identified and its trim fields are checked."),
            ("speed", "Test when unsure", f"SoC chips within {HYB} MHz of a product boundary still get the speed test: "
                                          f"{int(hyb.hybrid_escapes)} of {int(hyb.chips):,} sold too fast on untouched "
                                          f"wafers (not proof of zero risk).")], strict=True):
        with col:
            ui.text_card(t, x, ic)

with st.expander("The 9 datasets and where each one is used"):
    st.dataframe(pd.DataFrame([(v[0], v[1], len(ui.raw(k)), v[3]) for k, v in DATASETS.items()],
                              columns=["Dataset", "Chip", "Rows", "Method"]), hide_index=True, width="stretch",
                 column_config={"Rows": st.column_config.NumberColumn(format="%d")})
