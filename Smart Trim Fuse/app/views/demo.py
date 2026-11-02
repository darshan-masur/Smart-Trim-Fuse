import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import ui

from src import mcu as M
from src import pmic as P
from src import soc as Q
from src.common import ai_iterations, to_code

st.title("Live demo")
ui.plain("Follow one chip from a wafer the AI <b>never saw</b>, in four steps: what the tester measures → what the AI "
         "predicts → the one check (and the fallback if it's wrong) → what it saves. <b>Typical chip</b> shows the "
         "usual case, <b>Tricky chip</b> one where the AI is off and the safety net takes over.")

RES = {1: "Exact first time", 2: "One step off: 1 extra check"}


def pick(pool, key, typical, tricky):
    """Chip picker with three shortcuts. typical / tricky are subsets of pool."""
    if key not in st.session_state:
        st.session_state[key] = typical.iloc[0]
    a, b, c, d = st.columns([2.2, 1, 1, 1], vertical_alignment="bottom")
    with a:
        st.selectbox("Chip", pool.tolist(), key=key)
    for col, label, icon, src in [(b, "Typical chip", ":material/thumb_up:", typical),
                                  (c, "Tricky chip", ":material/report:", tricky),
                                  (d, "Random chip", ":material/casino:", pool)]:
        with col:
            st.button(label, icon=icon, width="stretch", key=f"{key}_{label}",
                      on_click=lambda s=src: st.session_state.update({key: s.sample(1).iloc[0]}))
    return st.session_state[key]


def two_cards(today_big, today_txt, ai_big, ai_txt):
    a, b = st.columns(2)
    with a:
        ui.card(today_big, today_txt, "Conventional flow")
    with b:
        ui.card(ai_big, ai_txt, "With the AI")


def range_note(row, chip):
    """Out-of-range check from notebook 06: is every input inside what the model learned from?"""
    rng = ui.evaluation()["ranges"][chip]
    out = [c for c, (lo, hi) in rng.items() if c in row and not lo <= row[c] <= hi]
    if out:
        st.warning(f"Unusual chip: {', '.join(out)} outside the training range, so it skips the AI and goes "
                   "through the conventional flow.", icon=":material/rule:")
    else:
        st.caption(":material/verified: Every reading is inside the range the AI learned from, so its prediction is used.")


chip = st.segmented_control("Chip family", ["MCU", "PMIC", "Sensor", "SoC"], default="MCU", key="dm_chip") or "MCU"

# ============================================================== MCU
if chip == "MCU":
    te = ui.mcu_test()
    worst = np.max([np.abs(to_code(te[f"pred_{t}"], c["bits"]) - te[c["label"]]) for t, c in M.TRIMS.items()], axis=0)
    r = te[te.die_id == pick(te.die_id, "dm_mcu", te.die_id[worst == 0], te.die_id[worst > 1])].iloc[0]

    ui.step(1, "What the tester measures", "Readings it already takes, before any trimming")
    cols = st.columns(4)
    for col, (t, c) in zip(cols, M.TRIMS.items()):
        col.metric(f"{c['name']} before trim", f"{r[c['untrim']]:.4f} {c['unit']}",
                   f"target {c['target']} {c['unit']}", delta_color="off", delta_arrow="off")
    cols[3].metric("Where on the wafer", f"{r.radius_mm:.0f} mm", "from the centre", delta_color="off", delta_arrow="off")
    range_note(r, "MCU")

    ui.step(2, "What the AI predicts", "One trim code per circuit, straight away: no search loop")
    rows, steps, ms = [], 0, 0.0
    for t, c in M.TRIMS.items():
        best, ai = int(r[c["label"]]), int(to_code(r[f"pred_{t}"], c["bits"]))
        n = int(ai_iterations(ai - best, c["bits"]))
        steps, ms = steps + n, ms + n * c["ms"]
        rows.append({"Circuit": c["name"], "AI code": ai, "Best code (from the full search)": best,
                     "The check": RES.get(n, "Off by more: fall back to the conventional search")})
    cols = st.columns(3)
    for col, row in zip(cols, rows):
        col.metric(row["Circuit"], f"code {row['AI code']}")

    ui.step(3, "The check, and the fallback", "Set the code, measure once. Only a circuit that fails gets the conventional search")
    ui.check_panel([(c["name"], int(to_code(r[f"pred_{t}"], c["bits"])), int(r[c["label"]]), c["bits"])
                    for t, c in M.TRIMS.items()], "circuit")
    with st.expander("The same check as a table"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    checks = M.check_fuse(r.fuse_map_hex, r.derivative, ui.raw("schema"), r[M.SORT_FIELDS].values)
    ok = sum(c[1] for c in checks)
    unchecked = ui.fuse_unchecked(checks, ui.raw("schema"))
    coverage = "every field checked" if not unchecked else f"{', '.join(unchecked)} not checked"
    verdict = ("so the prototype's rules would allow it" if ok == len(checks) else "so the word is blocked")
    ui.win(f"<b>Fuse word check: {'✓ PASS' if ok == len(checks) else '× BLOCK'}</b> · {ok} of {len(checks)} rules "
           f"passed · {coverage}, {verdict} (simulation only: real fuse programming needs the controls in "
           "SAFETY_AND_LIMITATIONS.md).", "verified" if ok == len(checks) else "block")
    ui.fuse_word(r.fuse_map_hex, ui.raw("schema"), checks)

    ui.step(4, "What it saves", "For this chip")
    today_steps = int(sum(r[c["conv"]] for c in M.TRIMS.values()))
    two_cards(f"{today_steps} steps", f"binary search on 3 circuits · {r.conv_trim_time_ms:.1f} ms",
              f"{steps} steps", f"predict, then check · {ms:.1f} ms")
    if steps > 6:
        st.caption("A tricky chip: a circuit failed its check, so its AI code was rejected and the tester ran the "
                   "conventional search for it. In the simulation that costs a few milliseconds, not a wrong code. About 1 chip in "
                   "6 is like this.")

# ============================================================== PMIC
elif chip == "PMIC":
    pool = pd.concat([ui.pmic_test(), ui.pmic_others()], ignore_index=True)
    worst = np.max([np.abs(to_code(pool[f"pred_{x}"], 6) - pool[f"{x}_trim_code_opt"]) for x in P.RAILS], axis=0)
    r = pool[pool.die_id == pick(pool.die_id, "dm_pmic", pool.die_id[worst == 0], pool.die_id[worst > 1])].iloc[0]

    ui.step(1, "What the tester measures", f"{r.derivative}: only the reference voltage, not the 4 outputs")
    a, b, c = st.columns(3)
    a.metric("Reference before trim", f"{r.vref_untrim_V:.4f} V", "target 0.600 V", delta_color="off", delta_arrow="off")
    b.metric("Reference after its trim", f"{r.vref_trimmed_sort_V:.4f} V")
    c.metric("Where on the wafer", f"{r.radius_mm:.0f} mm", "from the centre", delta_color="off", delta_arrow="off")
    range_note(r, "Power chip")

    ui.step(2, "What the AI predicts", "All 4 output rails from that one reading")
    rows, rail_steps = [], 0
    for x in P.RAILS:
        best, ai = int(r[f"{x}_trim_code_opt"]), int(to_code(r[f"pred_{x}"], 6))
        n = int(ai_iterations(ai - best, 6))
        rail_steps += n
        rows.append({"Output rail": x, "Target": f"{r[f'{x}_target_V']:.2f} V", "AI code": ai,
                     "Best code (from the full search)": best,
                     "The check": RES.get(n, "Off by more: fall back to the conventional search")})
    cols = st.columns(4)
    for col, row in zip(cols, rows):
        col.metric(row["Output rail"], f"code {row['AI code']}", row["Target"], delta_color="off", delta_arrow="off")

    ui.step(3, "The check, and the fallback", "Each rail is set and measured once")
    ui.check_panel([(x, int(to_code(r[f"pred_{x}"], 6)), int(r[f"{x}_trim_code_opt"]), 6) for x in P.RAILS], "rail")
    with st.expander("The same check as a table"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    ui.step(4, "What it saves", "For this chip")
    two_cards(f"{int(r.conv_trim_iterations)} steps", "reference + 4 rails + 3 thresholds, each by binary search",
              f"{rail_steps} rail steps", "measure the reference only, predict all 4 rails, check once")

# ============================================================== Sensor
elif chip == "Sensor":
    _, te, _, _ = ui.sensor_sets()
    worst = np.maximum(np.abs(te.offset_m40C_mg - (te.offset_25C_mg + te.pred_tco * -65 + te.pred_tco2 * 65 ** 2)),
                       np.abs(te.offset_85C_mg - (te.offset_25C_mg + te.pred_tco * 60 + te.pred_tco2 * 60 ** 2)))
    die_worst = worst.groupby(te.die_id).max()
    ids = pd.Series(die_worst.index)
    die = pick(ids, "dm_sen", ids[(die_worst <= 6).values], ids[(die_worst > 12).values])
    d = te[te.die_id == die]
    ax_i = int(d.axis.iloc[int(np.argmax(worst[d.index].values))])  # show the chip's worst axis
    r = d[d.axis == ax_i].iloc[0]

    ui.step(1, "What the tester measures", "One pass at room temperature (25 °C)")
    a, b, c = st.columns(3)
    a.metric(f"Offset, {'xyz'[ax_i]} axis", f"{r.offset_25C_mg:.1f} mg")
    b.metric("Sensitivity", f"{r.sens_25C_rel:.4f}")
    c.metric("Package stress gauge", f"{r.stress_gauge_mV:.1f} mV")
    range_note(r, "Sensor")

    ui.step(2, "What the AI predicts", "How the offset moves when the chip gets cold (−40 °C) and hot (85 °C)")
    t_ = np.linspace(-40, 85, 26)
    dt = t_ - 25
    line = pd.DataFrame({"°C": t_, "mg": r.offset_25C_mg + r.pred_tco * dt + r.pred_tco2 * dt ** 2})
    pts = pd.DataFrame({"°C": [-40, 25, 85], "mg": [r.offset_m40C_mg, r.offset_25C_mg, r.offset_85C_mg]})
    ch = (alt.Chart(line).mark_line(strokeWidth=3, color=ui.tok("probe")).encode(
              x=alt.X("°C:Q", title="Temperature (°C)"), y=alt.Y("mg:Q", title="Zero-g offset (mg)"))
          + alt.Chart(pts).mark_point(size=140, filled=True, color=ui.tok("state-fallback")).encode(
              x="°C:Q", y="mg:Q", tooltip=[alt.Tooltip("°C:Q"), alt.Tooltip("mg:Q", format=".1f")]))
    st.altair_chart(ui.chart_style(ch.properties(height=220)), width="stretch")
    st.caption("Teal line: the AI's prediction from 25 °C. Copper dots: what the full 3-temperature test really measured "
               "(shown here only for comparison).")

    ui.step(3, "The check against the product grade", "Medium grade: within ±12 mg at every temperature")
    err = float(die_worst[die])
    if err <= 12:
        ui.win(f"<b>Within ±12 mg</b> (worst axis {err:.1f} mg off): one oven pass is enough for this chip.")
    else:
        st.warning(f"Worst axis is {err:.1f} mg off, outside ±12 mg: this chip falls back to the full 3-temperature test.",
                   icon=":material/thermostat:")

    ui.step(4, "What it saves", "For this chip")
    s = ui.headline()["sensor_s"]
    two_cards("3 oven passes", f"−40, 25 and 85 °C · about {s[0]:.1f} s",
              "1 oven pass" if err <= 12 else "3 oven passes",
              "25 °C only; hot and cold predicted" if err <= 12 else "this chip keeps the full test")

# ============================================================== SoC
else:
    te, ftop = ui.soc_test()
    ev = ui.evaluation()
    margin = ev["soc_hybrid_MHz"]
    sku = ui.raw("sku")
    sure, pe, unsure = Q.margin_split(te, sku, ftop, margin / 1000)
    true_sku = Q.best_sku(Q.eligibility(te, sku, Q.measured_ftop(te)))
    die = pick(te.die_id, "dm_soc", te.die_id[~unsure], te.die_id[unsure])
    i = te.index[te.die_id == die][0]
    one = te.loc[[i]]
    plan = ui.soc_plans().set_index("die_id")

    ui.step(1, "What the tester measures", "Quick on-chip monitors: no 450 ms speed test yet")
    defects = [bool(one[f"core{k}_defect"].iloc[0]) for k in range(8)]
    tiles = "".join(f'<div class="core {"bad" if b else "good"}">{"✕" if b else "✓"}<span>core {k}</span></div>'
                    for k, b in enumerate(defects))
    a, b = st.columns([1, 2.2])
    with a:
        st.html(f'<div class="cores">{tiles}</div>')
        st.caption(f"{8 - sum(defects)} of 8 cores work.")
    with b:
        x, y, z = st.columns(3)
        x.metric("Ring oscillator", f"{one.ro_freq_MHz.iloc[0]:.0f} MHz")
        y.metric("Critical path delay", f"{one.cpm_path_delay_ps.iloc[0]:.0f} ps")
        z.metric("Leakage at 25 °C", f"{one.iddq_25C_mA.iloc[0]:.0f} mA")
        range_note(one.iloc[0], "SoC")

    ui.step(2, "What the AI predicts", f"Each product's speed, then the product with the speed ±{margin} MHz")
    opt_sku = Q.best_sku(Q.eligibility(one, sku, {k: ftop[k][[i]] for k in Q.KS}, -margin / 1000))[0]
    c1, c2 = st.columns(2)
    with c1:
        st.html(f'<div class="card"><div class="ttl">If the chip is {margin} MHz slower</div>{ui.badge(sure[te.index.get_loc(i)])}</div>')
    with c2:
        st.html(f'<div class="card"><div class="ttl">If the chip is {margin} MHz faster</div>{ui.badge(opt_sku)}</div>')
    vb = ui.model("vmin")  # notebook 07: worst-core Vmin from the same monitors
    v_pred = float(vb["model"].predict(one[vb["features"]])[0])
    v_meas = float(one[[f"core{c}_vmin_2GHz_mV" for c in range(8)]].max(axis=1).iloc[0])
    v1, v2, v3 = st.columns(3)
    v1.metric("Predicted Vmin", f"{v_pred:.0f} mV", help="Worst-core minimum voltage at 2 GHz, from the monitors")
    v2.metric(f"+ {vb['margin_mV']} mV margin", f"{v_pred + vb['margin_mV']:.0f} mV",
              help="Safety margin chosen on validation wafers")
    v3.metric("Measured Vmin", f"{v_meas:.0f} mV", f"{v_meas - v_pred:+.1f} mV vs prediction", delta_color="off",
              help="The real value, shown here only to compare")
    st.caption("Vmin = the worst core's minimum voltage at 2 GHz, predicted from the monitors with no voltage search. "
               "The margin was chosen on validation wafers so that no chip gets less voltage than it needs; in this "
               "dataset the voltage bin itself is set from speed. Synthetic data.")

    ui.step(3, "The decision, and the fallback", "Same product both ways: sell on the prediction. Different: speed test")
    k = te.index.get_loc(i)
    if unsure[k]:
        st.warning(f"Close to a product boundary, so this chip gets the normal 450 ms speed test. The test says "
                   f"{true_sku[k]}.", icon=":material/speed:")
    else:
        ok = sure[k] == true_sku[k] or true_sku[k] == "scrap"
        ui.win(f"<b>Far from any boundary:</b> sold as {sure[k]} with no speed test. The speed test (run here only to "
               f"check) says {true_sku[k]}{': the same' if ok else ''}.")

    ui.step(4, "What it saves, and what it is sold as", "For this chip")
    opt = plan.loc[die, "optimised"]
    opt_badge = ui.badge(opt) if opt != "unsold" else \
        '<span class="badge" style="background:var(--color-chart-muted)">Not needed this week</span>'
    c1, c2 = st.columns(2)
    with c1:
        ui.card("0 ms saved" if unsure[k] else "450 ms saved", "speed test run" if unsure[k] else "speed test skipped",
                "Test time")
    with c2:
        st.html(f'<div class="card"><div class="ttl">The product plan</div>{opt_badge}<div class="lbl" '
                f'style="margin-top:10px">what this chip is sold as, to match what customers order</div></div>')
    cur = pd.DataFrame(ev["soc_curve_test"]).set_index("margin_MHz").loc[margin]
    st.caption(f"On all untouched test wafers: {100 - cur['hybrid_tested_%']:.0f}% of chips skip the speed test, with "
               f"{int(cur['hybrid_escapes'])} of {int(cur['chips']):,} sold too fast (synthetic data; not proof of zero "
               "risk). The money comes from the product plan.")
