import streamlit as st
import ui

ui.hero(
    "Smart Trim & Fuse · semiconductor test · MCU, PMIC, sensor, SoC",
    "Predict the trim, check it once.<br>Rule-check every fuse word.",
    "Every chip leaves the fab slightly off target, so the tester trims it and stores the settings in one-time fuses. "
    "This prototype predicts each trim code, verifies it with one measurement, falls back to the conventional search when the "
    "check fails, and rule-checks the fuse word first.",
    art=ui.wafer_art(),
)

h = ui.headline()
mt, ma = h["mcu_ms"]
dt, da = ui.mcuc_headline()
pt, pa = h["pmic_steps"]
st_, sa = h["sensor_s"]
rr, ro = h["soc_rev"]
ev = ui.evaluation()
skip = 100 - ev["soc_curve_test"][ev["soc_hybrid_MHz"] // 10]["hybrid_tested_%"]
c = st.columns(4)
with c[0]:
    ui.kpi("MCU", f"{mt / ma:.1f}×", "faster trimming", mt, ma, f"{mt:.1f} ms", f"{ma:.1f} ms",
           f"Time per chip, assuming a fixed time per measurement. MCU-C final-test pass {dt:.1%} → {da:.1%} "
           f"(early: 2 wafers).")
with c[1]:
    ui.kpi("PMIC", f"{pt / pa:.1f}×", "fewer tries", pt, pa, f"{pt:.1f}", f"{pa:.1f}",
           "Tries per chip: all 4 output rails predicted from one reference reading, then checked.")
with c[2]:
    ui.kpi("Sensor", "3 → 1", "oven passes", st_, sa, f"{st_:.1f} s", f"{sa:.1f} s",
           "Medium and Loose grades only; one pass assumed to take 1/3 of the time. Tight grade keeps 3 passes.")
with c[3]:
    ui.kpi("SoC", f"+{ro / rr - 1:.1%}", "weekly revenue", rr, ro, f"${rr / 1000:.0f}k", f"${ro / 1000:.0f}k",
           f"Same chips sold to match synthetic demand. {skip:.0f}% of chips skip the speed test.")

ui.step(1, "How it works", "Predict, verify once, fall back when the check fails, rule-check before any burn")
ui.workflow()

ui.step(2, "Take the tour")
l1, l2, l3, l4 = st.columns(4)
l1.page_link("views/wafer.py", label="Wafer lab: see every chip", icon=":material/blur_on:")
l2.page_link("views/demo.py", label="Live demo: one chip, step by step", icon=":material/memory:")
l3.page_link("views/results.py", label="Results and why", icon=":material/insights:")
l4.page_link("views/batch.py", label="Batch check: upload a file", icon=":material/upload_file:")
st.caption("9 synthetic datasets · models saved by the Colab notebooks · every result also checked wafer by wafer "
           "(notebook 06) · definitions in RESULTS_SOURCE_OF_TRUTH.md · a prototype, not a production tool "
           "(SAFETY_AND_LIMITATIONS.md).")
