"""Smart Trim & Fuse - interactive UI for all 9 datasets of the AI-Optimized Trim & Fuse project.

Run (from the 'Smart Trim Fuse' folder):  streamlit run app/streamlit_app.py
Everything runs offline. The models are the ones saved by the Colab notebooks (01-04).
"""

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP.parent))

import importlib  # noqa: E402

import streamlit as st  # noqa: E402
import theme  # noqa: E402
import ui  # noqa: E402

from src import batch, common, config, mcu, pmic, results, screen, sensor, soc  # noqa: E402

# A running server keeps imported helper modules in memory (src/ too, as Streamlit only re-runs app/). Reload them
# each run, dependencies first, so edits and redeploys are picked up.
for m in (config, common, mcu, pmic, sensor, soc, screen, batch, results, theme, ui):
    importlib.reload(m)

st.set_page_config(page_title="Smart Trim & Fuse", page_icon=":material/tune:", layout="wide")
ui.setup()
ui.glossary()
ui.sim_note()

V = APP / "views"
pages = [
    st.Page(V / "overview.py", title="Overview", icon=":material/home:", url_path="overview", default=True),
    st.Page(V / "wafer.py", title="Wafer lab", icon=":material/blur_on:", url_path="wafer"),
    st.Page(V / "demo.py", title="Live demo", icon=":material/memory:", url_path="demo"),
    st.Page(V / "results.py", title="Results", icon=":material/insights:", url_path="results"),
    st.Page(V / "batch.py", title="Batch check", icon=":material/upload_file:", url_path="batch"),
]
st.navigation(pages, position="top").run()
