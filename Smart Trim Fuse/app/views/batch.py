import pandas as pd
import streamlit as st
import ui

from src import batch as B
from src.config import ROOT

DEMO = ROOT.parent / "Demo"

st.title("Batch check")
ui.plain(
    "Upload a whole CSV of dies (or requests, or fuse words) and the page runs the right model or rule on every row, "
    "the same way the tester would. It <b>recognises the file by its columns</b>, cleans it, tells you exactly what it "
    "fixed, and never guesses: a row with a missing or impossible measurement is not predicted and is marked "
    "for conventional review. "
    "If the file also contains the true answers (as the Demo files do), the page scores itself."
)

src = st.segmented_control("Data source", ["Use a Demo file", "Upload my own CSV"], default="Use a Demo file",
                           key="b_src") or "Use a Demo file"
df, name = None, None
if src == "Use a Demo file":
    files = sorted(p.name for p in DEMO.glob("*.csv") if p.name != "expected_results.csv") if DEMO.exists() else []
    if not files:
        st.info("No Demo folder found next to the app. Upload a CSV instead.", icon=":material/folder_off:")
    else:
        name = st.selectbox("Demo file", files, key="b_demo")
        df = pd.read_csv(DEMO / name)
else:
    up = st.file_uploader("CSV file", type=["csv"], key="b_up")
    if up is not None:
        name = up.name
        try:
            df = pd.read_csv(up)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
            st.error("The file could not be read as a CSV. Save it as comma-separated text (.csv) and try again.")
            st.stop()
if df is None:
    with st.expander("Which files are recognised?"):
        st.dataframe(pd.DataFrame([(k, len(v), ", ".join(v[:6]) + " …") for k, v in B.REQUIRED.items()],
                                  columns=["File type", "Required columns", "First columns"]), hide_index=True, width="stretch")
    st.stop()

# --- step 1: recognise -----------------------------------------------------------------------------
ui.step(1, "What is this file?", f"{name} · {len(df):,} rows · {df.shape[1]} columns")
kind, missing, score = B.detect(df)
if score < 0.6:
    st.error(f"Not recognised as test data: it has only {score:.0%} of the columns of the closest file type "
             f"({kind}). Nothing was run.", icon=":material/help:")
    st.dataframe(pd.DataFrame([(k, ", ".join(v)) for k, v in B.REQUIRED.items()], columns=["File type", "Required columns"]),
                 hide_index=True, width="stretch")
    st.stop()
if missing:
    st.error(f"Looks like **{kind}**, but {len(missing)} required column(s) are missing: "
             + ", ".join(f"`{c}`" for c in missing[:10]) + ". Add them and upload again.", icon=":material/table_rows:")
    st.stop()
st.success(f"Recognised as **{kind}**", icon=":material/check_circle:")

# --- step 2: clean -----------------------------------------------------------------------------------
d, log = B.clean(df, kind)
ui.step(2, "Cleaning report", "Every fix, so you know exactly what the models saw")
st.dataframe(pd.DataFrame(log, columns=["Check", "Rows affected", "What was done"]), hide_index=True, width="stretch")
k1, k2, k3, k4 = st.columns(4)
with k1:
    ui.card(f"{len(df):,}", "rows in the file")
with k2:
    ui.card(f"{len(df) - len(d):,}", "removed (duplicates and re-tests)")
with k3:
    ui.card(f"{int(d._usable.sum()):,}", "rows predicted")
with k4:
    ui.card(f"{int((~d._usable).sum()):,}", "not predicted; conventional review required")

# --- step 3: run -------------------------------------------------------------------------------------
ui.step(3, "Results", "Same models and rules as the chip pages")
if kind.startswith("MCU dies"):
    out, summ = B.run_mcu(d, ui.model("trim"), ui.defect_screen())
elif kind.startswith("PMIC"):
    out, summ = B.run_pmic(d, ui.model("pmic"))
elif kind.startswith("Sensor"):
    out, summ = B.run_sensor(d, ui.model("sensor"), ui.defect_screen())
elif kind.startswith("SoC"):
    out, summ = B.run_soc(d, ui.model("soc"), ui.raw("sku"))
elif kind.startswith("Customer"):
    out, summ = B.run_otp(d)
else:
    out, summ = B.run_fuse(d, ui.raw("schema"), ui.raw("mcu"))
if summ:
    st.markdown("**Self-check against the answers in the file**")
    st.dataframe(pd.DataFrame(summ, columns=["Check", "Result"]), hide_index=True, width="stretch")
else:
    st.caption("The file has no answer columns, so there is nothing to score against: these are pure predictions.")
if "defect" in out.columns and (out.defect != "").any():
    bad = out[out.defect != ""]
    st.warning(f"**{len(bad)} defective {'die' if len(bad) == 1 else 'dies'} caught** before any AI result was used: "
               + ("each one is scrapped or sold with fewer cores, decided by the structural test."
                  if kind.startswith("SoC") else "each one goes to the conventional flow and failure analysis."),
               icon=":material/report:")
    st.dataframe(bad[[c for c in ("die_id", "derivative", "product_AI", "defect", "action") if c in bad.columns]],
                 hide_index=True, width="stretch")
    st.markdown("**Every row**")
st.dataframe(out, hide_index=True, width="stretch", height=min(460, 38 + 35 * len(out)))
st.download_button("Download results (CSV)", out.to_csv(index=False), f"results_{name}", icon=":material/download:",
                   type="primary")
ui.why(
    "A tester must never act on a guess. So the page fixes only what is safe to fix (duplicates, re-tests, "
    "True/False typed as text) and blanks anything impossible (a negative voltage, text in a number column). It "
    "then <b>refuses to predict</b> any row with a blank required value and marks it for conventional review "
    "(this page runs no tester flow itself). Fuse words are <b>PASS</b> only when the die is identified and its trim "
    "fields are checked; otherwise <b>REVIEW</b> or <b>BLOCK</b>. The Demo folder's <b>expected_results.csv</b> "
    "lists what each demo file should show. Synthetic data; prototype only.",
    label="Why the page refuses to guess",
)
