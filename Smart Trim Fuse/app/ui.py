"""Shared look & feel (identical to the SoC Smart Binning app), cached data / model loaders and the cached
calculations every page uses."""

import base64
import json
import re
import sys
from pathlib import Path

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import theme  # noqa: E402

from src import mcu as M  # noqa: E402
from src import pmic as P  # noqa: E402
from src import sensor as S  # noqa: E402
from src import soc as Q  # noqa: E402
from src.common import code_metrics, wafer_split  # noqa: E402
from src.config import DATA, DATASETS, MODELS  # noqa: E402

SKU_DOMAIN = ["SoC-Pro", "SoC-Std", "SoC-Lite", "scrap"]

# Component styles, copied from the SoC Smart Binning app so both projects look the same.
STYLE = """
:root {
  --font-head: "Bricolage Grotesque", "Segoe UI", system-ui, sans-serif;
  --font-body: "DM Sans", "Segoe UI", system-ui, sans-serif;
  --radius: 16px;
  --grad: linear-gradient(100deg, var(--color-accent-grad-from), var(--color-accent-grad-to));
  --shadow-lg: 0 18px 36px -20px color-mix(in srgb, var(--color-text) 40%, transparent);
}

/* app surfaces and text */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
  background: var(--color-bg); color: var(--color-text);}
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {background: var(--color-bg-subtle);}
[data-testid="stSidebar"] {border-right: 1px solid var(--color-border);}
.block-container {padding-top: 2.4rem; max-width: 1180px;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {font-family: var(--font-head) !important; color: var(--color-text);
  letter-spacing: -0.025em;}
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"], .stApp label, .stApp p,
.stApp li, .stApp summary {color: var(--color-text);}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {color: var(--color-text-muted);}
.stApp a {color: var(--color-accent-text);}
[data-testid="stHeading"] h1 {font-size: 2.6rem; font-weight: 700 !important;}
[data-testid="stHeading"] h1::after {content: ""; display: block; width: 56px; height: 4px; margin-top: 12px;
  border-radius: 4px; background: var(--grad); animation: grow .8s ease both;}
@keyframes grow {from {width: 0;} to {width: 56px;}}

/* widgets */
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"] > div, .stApp [data-baseweb="base-input"],
.stApp input, .stApp textarea {background: var(--color-surface-raised); color: var(--color-text);
  border-color: var(--color-border);}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {
  background: var(--color-surface-raised) !important; color: var(--color-text) !important;}
.stApp [data-testid="stExpander"] details {background: var(--color-surface-raised);
  border: 1px solid var(--color-border); border-radius: 14px;}
.stApp [data-testid="stFileUploaderDropzone"] {background: var(--color-surface-raised);
  border: 1px dashed var(--color-border); color: var(--color-text);}
.stApp [data-testid="stMetricLabel"], .stApp [data-testid="stMetricLabel"] p {color: var(--color-text-muted);}
.stApp [data-testid="stMetricValue"] {color: var(--color-text); font-family: var(--font-head); letter-spacing: -0.02em;}
.stApp [data-baseweb="tab-list"] {gap: 8px;}
.stApp [data-baseweb="tab"], .stApp [data-baseweb="tab"] p {color: var(--color-text-muted);}
.stApp [data-baseweb="tab"][aria-selected="true"], .stApp [data-baseweb="tab"][aria-selected="true"] p {
  color: var(--color-accent-text);}
.stApp [data-baseweb="tab-highlight"] {background: var(--color-accent);}
.stApp [data-baseweb="tab-border"] {background: var(--color-border);}
.stApp [data-testid="stBaseButton-secondary"], .stApp [data-testid="stBaseButton-secondary"] p {
  background: var(--color-surface-raised); color: var(--color-text);}
.stApp [data-testid="stBaseButton-secondary"] {border: 1px solid var(--color-border); border-radius: 12px;}
.stApp [data-testid="stBaseButton-primary"], .stApp [data-testid="stBaseButton-primary"] p {
  background: var(--color-accent); color: var(--color-on-accent); border-color: var(--color-accent);}
.stApp [data-testid="stBaseButton-primary"] {border-radius: 12px;}
.stApp [data-testid^="stBaseButton"] {transition: transform .2s ease, box-shadow .2s ease;}
.stApp [data-testid="stBaseButton-secondary"]:hover, .stApp [data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-1px); box-shadow: var(--shadow-lg);}
/* segmented controls look like the pill switcher: a tinted track, the active option raised */
.stApp button[data-variant="segmented_control"] {
  background: var(--color-surface); color: var(--color-text-muted); border-color: var(--color-border);
  transition: background-color .2s ease, color .2s ease;}
.stApp button[data-variant="segmented_control"]:hover {color: var(--color-text);}
.stApp button[data-variant="segmented_control"][aria-checked="true"] {
  background: var(--color-surface-raised); color: var(--color-text); border-color: var(--color-accent);
  font-weight: 600;}
.stApp button[data-variant="segmented_control"] * {color: inherit;}
.stApp [data-testid="stPageLink"] a {background: var(--color-surface); border-radius: 14px;
  border: 1px solid transparent; transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;}
.stApp [data-testid="stPageLink"] a:hover {transform: translateY(-2px); box-shadow: var(--shadow-lg);
  border-color: var(--color-border);}
.stApp [data-testid="stPageLink"] a span, .stApp [data-testid="stPageLink"] a p {color: var(--color-text);}
.stApp [data-testid="stIconMaterial"] {color: inherit !important;}
.stApp [data-testid="stTopNavLink"], .stApp [data-testid="stTopNavLink"] p, .stApp [data-testid="stTopNavSection"],
.stApp [data-testid="stTopNavSection"] p, [data-testid="stTopNavDropdownLink"], [data-testid="stTopNavDropdownLink"] p {
  color: var(--color-text-muted);}
.stApp [data-testid="stTopNavLink"][aria-current="page"], .stApp [data-testid="stTopNavLink"][aria-current="page"] p {
  color: var(--color-text); background: var(--color-surface);}
.stApp [data-testid="stToolbar"] button, .stApp [data-testid="stToolbar"] button p,
[data-testid="stSidebarCollapseButton"] button, [data-testid="stExpandSidebarButton"] {color: var(--color-text);}
[data-testid="stTopNavPopover"], [data-baseweb="popover"] [data-testid="stTopNavPopover"] > div {
  background: var(--color-surface-raised);}
/* the theme switcher fits on one line in the sidebar */
[data-testid="stSidebar"] [data-testid="stButtonGroup"] > div {flex-wrap: nowrap;}
[data-testid="stSidebar"] button[data-variant="segmented_control"] {padding: 2px 6px; min-height: 32px;
  flex: 1 1 auto; min-width: 0;}
[data-testid="stSidebar"] button[data-variant="segmented_control"] * {font-size: .8rem; overflow: visible;
  text-overflow: clip; max-width: none;}

/* line icons (Material Symbols, bundled with Streamlit, so they work offline) */
.mi {font-family: "Material Symbols Rounded"; font-weight: normal; font-style: normal; font-size: 1.25em;
  line-height: 1; display: inline-block; vertical-align: -0.22em; letter-spacing: normal; text-transform: none;
  white-space: nowrap; direction: ltr; font-feature-settings: "liga"; font-variation-settings: "wght" 300;}

/* hero: centred, big two-tone headline */
.hero {text-align: center; padding: 48px 24px 36px; margin: 4px 0 8px 0; border-radius: 28px;
  background: radial-gradient(70% 80% at 50% 0%, var(--color-accent-soft) 0%, transparent 70%);}
.hero .logo {width: 76px; height: 76px; margin: 0 auto 20px; border-radius: 22px; background: var(--color-surface);
  display: flex; align-items: center; justify-content: center; color: var(--color-accent-text);}
.hero .logo .mi {font-size: 42px; vertical-align: 0;}
.hero .tag {display: inline-block; background: var(--color-surface); color: var(--color-text-muted);
  font-size: .82rem; font-weight: 500; padding: 6px 16px; border-radius: 999px;}
.stApp .hero h1 {font-family: var(--font-head); font-size: clamp(2.2rem, 4.6vw, 3.5rem); font-weight: 700;
  line-height: 1.06; letter-spacing: -0.035em; margin: 18px auto 18px; max-width: 900px; padding: 0;}
.hero h1 .grad {background: var(--grad); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;}
.stApp .hero p {color: var(--color-text-muted); font-size: 1.12rem; line-height: 1.65; max-width: 720px;
  margin: 0 auto;}

/* explanation boxes */
.plain {background: var(--color-accent-soft); border-left: 3px solid var(--color-accent); border-radius: 14px;
  padding: 14px 18px; margin: 6px 0 22px 0; color: var(--color-text); font-size: 1rem; line-height: 1.65;}
.plain b.lbl {display: block; font-family: var(--font-head); font-size: .74rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--color-accent-text); margin-bottom: 4px;}
.win {background: var(--color-success-soft); border-left: 3px solid var(--color-success); border-radius: 14px;
  padding: 14px 18px; line-height: 1.6; color: var(--color-text);}
.win .mi {color: var(--color-success);}

/* cards: soft tinted tiles, no hard borders, lift on hover */
.card {background: var(--color-surface); border: 1px solid transparent; border-radius: var(--radius);
  padding: 22px 24px; height: 100%; color: var(--color-text);
  transition: transform .25s ease, box-shadow .25s ease, background-color .25s ease, border-color .25s ease;}
.card:hover {transform: translateY(-3px); box-shadow: var(--shadow-lg); background: var(--color-surface-raised);
  border-color: var(--color-border);}
.card.center {text-align: center;}
.card .ic {color: var(--color-accent-text); font-size: 1.5rem; margin-bottom: 10px;}
.card .big {font-family: var(--font-head); font-size: 2.3rem; font-weight: 700; line-height: 1.1;
  letter-spacing: -0.03em;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;}
.card .lbl {color: var(--color-text-muted); font-size: .92rem; margin-top: 8px; line-height: 1.5;}
.card .ttl {font-family: var(--font-head); font-weight: 700; font-size: 1.12rem; margin-bottom: 6px;
  color: var(--color-text); letter-spacing: -0.01em;}
.card .txt {color: var(--color-text-muted); font-size: .94rem; line-height: 1.6;}

/* section headings */
.step {display: flex; gap: 14px; align-items: center; margin: 44px 0 14px 0;}
.step .num {background: var(--color-accent); color: var(--color-on-accent); width: 36px; height: 36px;
  border-radius: 11px; flex: none; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-head); font-weight: 700;}
.step .t {font-family: var(--font-head); font-size: 1.45rem; font-weight: 700; color: var(--color-text);
  letter-spacing: -0.02em;}
.step .s {color: var(--color-text-muted); font-size: .94rem; margin-top: 2px;}

.badge {display: inline-block; padding: 5px 14px; border-radius: 999px; color: var(--color-on-sku); font-weight: 600;
  font-size: .98rem;}
.cores {display: grid; grid-template-columns: repeat(4, 54px); gap: 8px; margin: 6px 0;}
.core {height: 54px; border-radius: 12px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; font-size: .72rem; font-weight: 600; transition: transform .2s ease;}
.core:hover {transform: scale(1.06);}
.core.good {background: var(--color-accent); color: var(--color-on-accent);}
.core.bad {background: var(--color-surface); color: var(--color-text-muted);
  border: 1px dashed var(--color-text-muted);}

/* flow on the home page */
.flow {display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap;}
.flow .box {flex: 1; min-width: 150px; background: var(--color-surface); border: 1px solid transparent;
  border-radius: var(--radius); padding: 20px; transition: transform .25s ease, box-shadow .25s ease;}
.flow .box:hover {transform: translateY(-3px); box-shadow: var(--shadow-lg); border-color: var(--color-border);}
.flow .box .ic {font-size: 1.7rem; color: var(--color-accent-text);}
.flow .box .h {font-family: var(--font-head); font-weight: 700; font-size: 1.05rem; margin: 8px 0 6px;
  color: var(--color-text);}
.flow .box .d {color: var(--color-text-muted); font-size: .9rem; line-height: 1.55;}
.flow .arrow {display: flex; align-items: center; color: var(--color-text-muted); font-size: 1.3rem;}
.check {font-size: 1rem; padding: 10px 0; border-bottom: 1px solid var(--color-border); color: var(--color-text);}
.check .ok {color: var(--color-success);} .check .warn {color: var(--color-warning);}
.muted {color: var(--color-text-muted); font-size: .9rem;}

/* dark themes: Streamlit draws data grids on a canvas in its light theme, so flip them to match */
:root:has(.theme-flag.scheme-dark) [data-testid="stDataFrame"] {filter: invert(1) hue-rotate(180deg);}

/* motion: lively but calm. Entrances use fill-mode "backwards" so hover effects still work afterwards. */
@keyframes fadeUp {from {opacity: 0; transform: translateY(14px);} to {opacity: 1; transform: none;}}
@keyframes rise {from {opacity: 0; transform: translateY(24px) scale(.98);} to {opacity: 1; transform: none;}}
@keyframes pop {0% {opacity: 0; transform: scale(.6);} 70% {transform: scale(1.08);}
  100% {opacity: 1; transform: none;}}
@keyframes drift1 {0%, 100% {transform: translate(0, 0) scale(1);} 50% {transform: translate(70px, 30px) scale(1.15);}}
@keyframes drift2 {0%, 100% {transform: translate(0, 0) scale(1.1);}
  50% {transform: translate(-80px, 24px) scale(.92);}}
@keyframes float {0%, 100% {transform: translateY(0);} 50% {transform: translateY(-7px);}}
@keyframes halo {0%, 100% {box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-accent) 28%, transparent);}
  60% {box-shadow: 0 0 0 14px color-mix(in srgb, var(--color-accent) 0%, transparent);}}
@keyframes shimmer {to {background-position: -200% center;}}
@keyframes nudge {0%, 100% {transform: translateX(0);} 50% {transform: translateX(5px);}}
@keyframes wiggle {0%, 100% {transform: none;} 30% {transform: rotate(-10deg) scale(1.15);}
  60% {transform: rotate(6deg) scale(1.15);}}

/* hero: drifting colour glows, a floating logo with a soft pulse, staggered text, a slow shimmer */
.hero {position: relative; overflow: hidden; isolation: isolate; animation: fadeUp .8s ease backwards;}
.hero::before, .hero::after {content: ""; position: absolute; z-index: -1; border-radius: 50%; filter: blur(50px);
  pointer-events: none;}
.hero::before {width: 360px; height: 360px; left: 10%; top: -140px; opacity: .9;
  background: var(--color-accent-soft); animation: drift1 14s ease-in-out infinite;}
.hero::after {width: 300px; height: 300px; right: 8%; top: -70px; opacity: .5;
  background: color-mix(in srgb, var(--color-accent) 30%, transparent); animation: drift2 18s ease-in-out infinite;}
.hero .logo {animation: float 5s ease-in-out infinite, halo 3.2s ease-out infinite;}
.hero .tag {animation: fadeUp .6s .15s ease backwards;}
.stApp .hero h1 {animation: rise .9s .25s cubic-bezier(.2, .7, .2, 1) backwards;}
.stApp .hero p {animation: fadeUp .7s .45s ease backwards;}
.hero h1 .grad, .card .big {background-image: linear-gradient(100deg, var(--color-accent-grad-from),
  var(--color-accent-grad-to) 50%, var(--color-accent-grad-from)); background-size: 200% auto;}
.hero h1 .grad {animation: shimmer 7s linear infinite;}
.card:hover .big {animation: shimmer 1.8s linear infinite;}

/* page titles, section numbers, cards, icons */
[data-testid="stHeading"] h1 {animation: rise .7s cubic-bezier(.2, .7, .2, 1) backwards;}
.step .num {animation: pop .55s cubic-bezier(.2, .8, .2, 1.2) backwards;}
.step .t, .step .s {animation: fadeUp .6s .1s ease backwards;}
.card, .flow .box, .plain, .win {animation: rise .7s cubic-bezier(.2, .7, .2, 1) backwards;}
[data-testid="stColumn"]:nth-child(2) .card {animation-delay: .08s;}
[data-testid="stColumn"]:nth-child(3) .card {animation-delay: .16s;}
[data-testid="stColumn"]:nth-child(4) .card {animation-delay: .24s;}
[data-testid="stColumn"]:nth-child(5) .card {animation-delay: .32s;}
.flow .box:nth-child(3) {animation-delay: .1s;} .flow .box:nth-child(5) {animation-delay: .2s;}
.flow .box:nth-child(7) {animation-delay: .3s;}
.card:hover, .flow .box:hover {border-color: color-mix(in srgb, var(--color-accent) 35%, transparent);}
.card:hover .ic .mi, .flow .box:hover .ic .mi {display: inline-block; animation: wiggle .6s ease;}
.flow .arrow .mi {animation: nudge 1.8s ease-in-out infinite;}
.badge {animation: pop .5s .2s cubic-bezier(.2, .8, .2, 1.2) backwards;}
.core {animation: pop .4s cubic-bezier(.2, .8, .2, 1.2) backwards;}
.core:nth-child(2) {animation-delay: .04s;} .core:nth-child(3) {animation-delay: .08s;}
.core:nth-child(4) {animation-delay: .12s;} .core:nth-child(5) {animation-delay: .16s;}
.core:nth-child(6) {animation-delay: .2s;} .core:nth-child(7) {animation-delay: .24s;}
.core:nth-child(8) {animation-delay: .28s;}

/* primary buttons: a light sweep on hover; page links slide their icon */
.stApp [data-testid="stBaseButton-primary"] {position: relative; overflow: hidden;}
.stApp [data-testid="stBaseButton-primary"]::after {content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(115deg, transparent 30%, rgba(255, 255, 255, .35) 50%, transparent 70%);
  transform: translateX(-120%); transition: transform .8s ease;}
.stApp [data-testid="stBaseButton-primary"]:hover::after {transform: translateX(120%);}
.stApp [data-testid="stPageLink"] a [data-testid="stIconMaterial"] {transition: transform .25s ease;}
.stApp [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"] {transform: translateX(3px) scale(1.1);}

/* reveal while scrolling, where the browser supports scroll-driven animation */
@supports (animation-timeline: view()) {
  .card, .flow .box, .plain, .win, .step, [data-testid="stVegaLiteChart"], [data-testid="stDataFrame"] {
    animation: rise linear backwards; animation-timeline: view(); animation-range: entry 0% cover 20%;}
}
@media (prefers-reduced-motion: reduce) {* {animation: none !important; transition: none !important;}}
"""

# A few additions for this project (same tokens, same feel).
EXTRA = """
.fam {display: inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 600; font-size: .8rem;
  background: var(--color-accent); color: var(--color-on-accent); margin-right: 6px;}
.meth {display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600;
  background: var(--color-surface); color: var(--color-accent-text); border: 1px solid var(--color-border);}
.why {background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: 14px;
  padding: 14px 18px; margin: 6px 0 18px 0; line-height: 1.6; color: var(--color-text);
  animation: rise .7s cubic-bezier(.2, .7, .2, 1) backwards;}
.why b.lbl {display: block; font-family: var(--font-head); font-size: .74rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--color-accent-text); margin-bottom: 4px;}
.why .mi {color: var(--color-accent-text);}
/* Streamlit < 1.60 marks segmented-control buttons with data-testid instead of data-variant:
   same look as the SoC app on either version */
.stApp button[data-testid="stBaseButton-segmented_control"] {background: var(--color-surface);
  color: var(--color-text-muted); border-color: var(--color-border); transition: background-color .2s ease, color .2s ease;}
.stApp button[data-testid="stBaseButton-segmented_control"]:hover {color: var(--color-text);}
.stApp button[data-testid="stBaseButton-segmented_controlActive"] {background: var(--color-surface-raised);
  color: var(--color-text); border-color: var(--color-accent); font-weight: 600;}
.stApp button[data-testid^="stBaseButton-segmented_control"] * {color: inherit;}
[data-testid="stSidebar"] button[data-testid^="stBaseButton-segmented_control"] {padding: 2px 6px; min-height: 32px;
  flex: 1 1 auto; min-width: 0;}
[data-testid="stSidebar"] button[data-testid^="stBaseButton-segmented_control"] * {font-size: .8rem; overflow: visible;
  text-overflow: clip; max-width: none;}
"""

# Redesign (Nov 2026): a semiconductor-test identity on top of the warm palette. "probe" teal is the accent for
# wafer states, charts, controls and status; every status also has a text symbol.
REDESIGN = """
/* content starts below the top navigation bar (it used to hide the first line of every page) */
.block-container {padding-top: 4.6rem; padding-bottom: 3rem;}

/* presentation mode: no development controls in the top bar */
[data-testid="stAppDeployButton"], [data-testid="stStatusWidget"] {display: none !important;}

/* full-strength secondary text: Streamlit dims captions to 60%, and the scroll-driven reveal left headings
   half-transparent until scrolled further. Entrances now play once, then everything stays at full opacity. */
.stApp [data-testid="stCaptionContainer"] {opacity: 1;}
@supports (animation-timeline: view()) {
  .card, .flow .box, .plain, .win, .step, [data-testid="stVegaLiteChart"], [data-testid="stDataFrame"] {
    animation: rise .6s cubic-bezier(.2, .7, .2, 1) backwards; animation-timeline: auto;}
}
.wf-down span {font-size: .78rem;}
.ico {width: 1.2em; height: 1.2em; display: inline-block; vertical-align: -0.24em; flex: none;}

/* synthetic-data notice */
.simnote {display: flex; gap: 10px; align-items: flex-start; background: var(--color-probe-soft);
  border: 1px solid color-mix(in srgb, var(--color-probe) 35%, transparent); color: var(--color-text);
  border-radius: 12px; padding: 9px 14px; font-size: .9rem; line-height: 1.45; margin: 0 0 6px 0;}
.simnote .ico {color: var(--color-probe); margin-top: 1px;}

/* controls and status use the probe accent */
.stApp button[data-variant="segmented_control"][aria-checked="true"],
.stApp button[data-testid="stBaseButton-segmented_controlActive"] {border-color: var(--color-probe);
  box-shadow: inset 0 -2px 0 var(--color-probe);}
.stApp [data-baseweb="tab-highlight"] {background: var(--color-probe);}
.step .num {background: var(--color-probe); color: var(--color-on-probe);}
.win {background: var(--color-probe-soft); border-left-color: var(--color-probe);}
.win .ico {color: var(--color-probe);}
.why .ico, .card .ic .ico {color: var(--color-probe);}
.card .ic {font-size: 1.6rem;}
.step {margin: 30px 0 12px 0;}

/* hero: compact, story left, wafer illustration right */
.hero2 {display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; align-items: center; padding: 18px 26px;
  margin: 2px 0 12px; border-radius: 24px; border: 1px solid var(--color-border);
  background: radial-gradient(60% 90% at 85% 40%, var(--color-probe-soft) 0%, transparent 70%),
              radial-gradient(60% 80% at 10% 0%, var(--color-accent-soft) 0%, transparent 70%), var(--color-bg);
  animation: fadeUp .6s ease backwards;}
.hero2 .tag {display: inline-block; background: var(--color-surface); color: var(--color-text-muted);
  font-size: .8rem; font-weight: 600; padding: 5px 13px; border-radius: 999px; letter-spacing: .01em;}
.stApp .hero2 h1 {font-family: var(--font-head); font-size: clamp(1.75rem, 3vw, 2.4rem); font-weight: 700;
  line-height: 1.08; letter-spacing: -0.03em; margin: 12px 0 10px; padding: 0;}
.hero2 h1 .grad {background: var(--grad); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;}
.stApp .hero2 p {color: var(--color-text-muted); font-size: 1.02rem; line-height: 1.6; margin: 0;}
.hero2 .hart {display: flex; justify-content: center;}
.wafer-art {width: 100%; max-width: 380px; height: auto; display: block;}

/* headline metrics */
.kpi {background: var(--color-surface); border-radius: var(--radius); padding: 16px 18px; height: 100%;
  border: 1px solid transparent; transition: border-color .2s ease, transform .2s ease;
  animation: rise .6s cubic-bezier(.2, .7, .2, 1) backwards;}
.kpi:hover {border-color: color-mix(in srgb, var(--color-probe) 40%, transparent); transform: translateY(-2px);}
.khead {display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 4px 8px;
  margin-bottom: 8px;}
.kchip {font-family: var(--font-head); font-weight: 700; font-size: .82rem; color: var(--color-probe);
  letter-spacing: .06em; text-transform: uppercase;}
.simtag {font-size: .68rem; font-weight: 600; color: var(--color-text-muted); border: 1px dashed var(--color-text-muted);
  border-radius: 999px; padding: 1px 8px; white-space: nowrap;}
.kval {font-family: var(--font-head); font-size: 2.05rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.05;
  color: var(--color-text);}
.kunit {font-family: var(--font-body); font-size: .9rem; font-weight: 500; color: var(--color-text-muted);
  margin-left: 6px; letter-spacing: 0;}
.kbars {display: grid; grid-template-columns: 1fr auto; gap: 2px 8px; align-items: center; margin: 12px 0 8px;
  font-size: .78rem; color: var(--color-text-muted);}
.kbars .klbl {grid-column: 1 / -1; margin-top: 4px;}
.kbars .trk {height: 8px; border-radius: 99px; background: var(--color-bg-subtle); overflow: hidden;}
.kbars .fill {display: block; height: 100%; border-radius: 99px;}
.kbars .fill.today {background: var(--color-state-neutral);} .kbars .fill.proto {background: var(--color-probe);}
.kbars .knum {color: var(--color-text); font-variant-numeric: tabular-nums; text-align: right;}
.knote {font-size: .82rem; line-height: 1.45; color: var(--color-text-muted);}

/* workflow diagram */
.wf {display: grid; gap: 10px 8px; align-items: stretch;
  grid-template-columns: 1fr 36px 1fr 36px 1fr 46px 1.25fr;
  grid-template-areas: "m a1 p a2 v a3 f" ". . . . d . ." ". . b b b b ." "foot foot foot foot foot foot foot";}
.wf-node {background: var(--color-surface); border-radius: 14px; padding: 13px 14px; border: 1px solid transparent;}
.wf-node .wf-ic {color: var(--color-probe); font-size: 1.35rem; line-height: 1;}
.wf-t {font-family: var(--font-head); font-weight: 700; font-size: .98rem; margin: 6px 0 4px; color: var(--color-text);}
.wf-d {font-size: .84rem; line-height: 1.5; color: var(--color-text-muted);}
.wf-node.fb {background: color-mix(in srgb, var(--color-state-fallback) 9%, var(--color-surface));
  border: 1px dashed var(--color-state-fallback);}
.wf-node.fb .wf-ic {color: var(--color-state-fallback);}
.wf-arrow {display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--color-probe);
  font-size: 1.2rem; gap: 2px;}
.wf-arrow span {font-size: .7rem; font-weight: 600;}
.wf-down {display: flex; flex-direction: column; align-items: center; color: var(--color-state-fallback); gap: 2px;
  font-size: .74rem; font-weight: 600; text-align: center;}
.wf-down .ico {transform: rotate(90deg); font-size: 1.2rem;}
.wf-foot {grid-area: foot; font-size: .84rem; color: var(--color-text-muted); margin-top: 2px;}
.pill {display: inline-block; font-size: .72rem; font-weight: 700; padding: 1px 8px; border-radius: 999px;
  margin: 3px 2px 0 0; white-space: nowrap; color: var(--color-on-state);}
.pill.good {background: var(--color-state-good);} .pill.attn {background: var(--color-state-attn);}
.pill.bad {background: var(--color-state-fallback);} .pill.na {background: var(--color-state-neutral);}

/* fuse-word diagram */
.fuseword {background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: 14px;
  padding: 12px 14px; margin: 8px 0 14px;}
.fw-scroll {overflow-x: auto;} .fw-scroll .fw-img {min-width: 620px; width: 100%; height: auto; display: block;}
.fw-meta {font-size: .8rem; color: var(--color-text-muted); margin: 4px 0 8px;}
.fw-tab {width: 100%; border-collapse: collapse; font-size: .84rem;}
.fw-tab th, .fw-tab td {text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--color-border);
  color: var(--color-text);}
.fw-tab th {color: var(--color-text-muted); font-weight: 600;}

/* the one-measurement check: one card per circuit, fallback unmistakable */
.chks {display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; margin: 4px 0 10px;}
.chk {border-radius: 14px; padding: 12px 14px; background: var(--color-surface); border: 2px solid transparent;
  border-left-width: 6px;}
.chk.good {border-color: var(--color-state-good);} .chk.attn {border-color: var(--color-state-attn);}
.chk.bad {border-color: var(--color-state-fallback); border-style: dashed solid dashed solid;
  background: color-mix(in srgb, var(--color-state-fallback) 10%, var(--color-surface));}
.chk-n {font-size: .78rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase;
  letter-spacing: .06em;}
.chk-h {font-family: var(--font-head); font-weight: 700; font-size: 1.02rem; margin: 3px 0 4px;}
.chk-h {color: var(--color-text);}
.chk-h .g {display: inline-flex; width: 1.3em; height: 1.3em; border-radius: 50%; align-items: center;
  justify-content: center; color: var(--color-on-state); font-size: .85em; margin-right: 4px; vertical-align: .05em;}
.chk.good .g {background: var(--color-state-good);} .chk.attn .g {background: var(--color-state-attn);}
.chk.bad .g {background: var(--color-state-fallback);}
.chk-b {font-size: .86rem; line-height: 1.5; color: var(--color-text);}
.chk-b s {text-decoration-color: var(--color-state-fallback); text-decoration-thickness: 2px;}
.fb-banner {display: flex; gap: 10px; align-items: flex-start; border: 2px solid var(--color-state-fallback);
  background: color-mix(in srgb, var(--color-state-fallback) 12%, var(--color-bg)); color: var(--color-text);
  border-radius: 14px; padding: 12px 14px; margin: 4px 0 10px; line-height: 1.5;}
.fb-banner .ico {width: 1.5em; height: 1.5em; margin-top: 1px;}

/* Wafer lab toolbar */
.st-key-wl_toolbar {background: var(--color-surface); border-radius: 16px; padding: 10px 14px 4px;
  border: 1px solid var(--color-border); margin-bottom: 8px;}
.st-key-wl_toolbar button[data-variant="segmented_control"],
.st-key-wl_toolbar button[data-testid^="stBaseButton-segmented_control"] {padding: 2px 10px; min-height: 34px;}
.st-key-wl_toolbar button[data-variant="segmented_control"] *,
.st-key-wl_toolbar button[data-testid^="stBaseButton-segmented_control"] * {font-size: .85rem;}

/* wafer maps: the wide version on desktop, the narrow one on phones */
.st-key-map_narrow, .st-key-pair_narrow {display: none;}
[data-testid="stVegaLiteChart"] {max-width: 100%; overflow-x: auto;}

/* small screens */
@media (max-width: 760px) {
  .st-key-map_wide, .st-key-pair_wide {display: none;}
  .st-key-map_narrow, .st-key-pair_narrow {display: block;}
  .st-key-wl_toolbar {padding: 8px 10px 2px;}
  .block-container {padding-top: 4.2rem; padding-left: 1rem; padding-right: 1rem;}
  .hero2 {grid-template-columns: 1fr; gap: 6px; padding: 14px 16px;}
  .hero2 .hart {order: -1;} .wafer-art {max-width: 190px;}
  .stApp .hero2 h1 {font-size: 1.6rem; margin: 8px 0 6px;} .stApp .hero2 p {font-size: .95rem; line-height: 1.5;}
  .wf {grid-template-columns: 1fr; grid-template-areas: "m" "a1" "p" "a2" "v" "d" "b" "a3" "f" "foot";}
  .wf-arrow .ico, .wf-down .ico {transform: rotate(90deg);}
  .wf-arrow {flex-direction: row;}
  .kval {font-size: 1.8rem;}
}
"""


def current():
    """Name of the active theme (session state, else the default)."""
    return st.session_state.get("theme") or theme.DEFAULT


def tok(name):
    """A semantic colour of the active theme, for places CSS can't reach (chart marks)."""
    return theme.THEMES[current()][name]


def _keep_theme():
    if st.session_state.theme is None:  # clicking the active option again would clear it
        st.session_state.theme = theme.DEFAULT
    st.query_params["theme"] = st.session_state.theme


def setup():
    """Theme switcher + styles. The flag element's class selects the theme in pure CSS."""
    if "theme" not in st.session_state:
        q = st.query_params.get("theme")
        st.session_state.theme = q if q in theme.THEMES else theme.DEFAULT
    with st.sidebar:
        st.segmented_control(":material/palette: Theme", list(theme.THEMES), key="theme", on_change=_keep_theme,
                             format_func=lambda k: theme.THEMES[k]["label"], width="stretch")
        name = current()
        st.html(f'<div class="theme-flag theme-{name} scheme-{theme.THEMES[name]["scheme"]}" hidden></div>')
    st.html(f"<style>{theme.css()}\n{STYLE}\n{EXTRA}\n{REDESIGN}</style>")


# ---------------------------------------------------------------------------
# components (same as the SoC app, plus the "why this method" box)
# ---------------------------------------------------------------------------
# Inline SVG line icons. They are drawn, not typed, so an icon can never show up as a word (the icon font used
# before showed "tune" whenever it had not loaded yet). Old Material names map onto the same few drawings.
_SVG = {
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    "block": '<circle cx="12" cy="12" r="9"/><path d="M5.8 5.8l12.4 12.4"/>',
    "verify": '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "fallback": '<path d="M4 9h11a5 5 0 0 1 0 10H9"/><path d="M8 5L4 9l4 4"/>',
    "speed": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4.5-5.5"/>',
    "idea": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
    "probe": '<path d="M3 3l10 10"/><path d="M6 3h-3v3"/><rect x="12" y="13" width="8" height="8" rx="1.5"/>',
    "predict": '<path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z"/><path d="M18 16l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
    "fuse": '<rect x="2.5" y="8.5" width="19" height="7" rx="3.5"/><path d="M6 12h3l1.5-2 3 4 1.5-2h3"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "chart": '<path d="M5 20V11M12 20V4M19 20v-6"/>',
    "chip": '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    "flask": '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/><path d="M7.5 15h9"/>',
    "review": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
}
_ALIAS = {"check_circle": "check", "verified": "verify", "psychology": "idea", "bar_chart": "chart", "undo": "fallback",
          "memory": "chip", "tune": "chip", "sensors": "probe", "science": "flask", "rule": "review"}


def _resolve(svg):
    """Theme colours written as var(--color-x) become the active theme's hex values (an SVG drawn as an image can't
    read the page's CSS variables; the page re-renders when the theme changes, so it stays in sync)."""
    return re.sub(r"var\(--color-([a-z-]+)\)", lambda m: tok(m.group(1)), svg)


def svg_img(svg, cls="", alt=""):
    """st.html strips inline <svg>, so drawings are embedded as images (data URI)."""
    svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    data = base64.b64encode(_resolve(svg).encode("utf8")).decode()
    role = f'alt="{alt}"' if alt else 'alt="" aria-hidden="true"'
    return f'<img class="{cls}" {role} src="data:image/svg+xml;base64,{data}"/>'


def icon(name, color="probe"):
    """A small line icon in a theme colour; unknown names draw nothing (never a word)."""
    path = _SVG.get(_ALIAS.get(name, name))
    if not path:
        return ""
    return svg_img(f'<svg viewBox="0 0 24 24" fill="none" stroke="var(--color-{color})" stroke-width="1.8" '
                   f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>', "ico")


_WORDING = [("today's binary search", "the conventional binary search"), ("today's search", "the conventional search"),
            ("today's method", "the conventional flow")]


def wording(text):
    """Display wording for stored notebook text: 'today's …' is shown as the conventional flow."""
    if not isinstance(text, str):
        return text
    for old, new in _WORDING:
        text = text.replace(old, new)
    return text


def sim_note(text=None):
    """The synthetic-data notice, shown at the top of every page."""
    text = text or ("Prototype on synthetic data: every number is a simulation result, not a real-world saving, "
                    "yield or safety claim. This site does not run a tester or program fuses.")
    st.html(f'<div class="simnote" role="note">{icon("flask")}<span>{text}</span></div>')


def hero(tag, title, text, art=""):
    """Compact two-column hero: the story on the left, a wafer illustration on the right (stacks on phones).
    Text after <br> in the title is drawn in the accent gradient."""
    first, _, second = title.partition("<br>")
    head = first + (f'<br><span class="grad">{second}</span>' if second else "")
    st.html(f'<div class="hero2"><div class="htxt"><span class="tag">{tag}</span><h1>{head}</h1><p>{text}</p></div>'
            f'<div class="hart">{art}</div></div>')


@st.cache_data(persist="disk", show_spinner=False)
def _art_dies(_stamp):
    """Real result of every die on one held-out MCU-A wafer, for the hero illustration (cached on disk)."""
    te = mcu_test()
    w = sorted(te.wafer_id.unique())[0]
    d = te[te.wafer_id == w]
    worst = np.max([np.abs(np.clip(np.round(d[f"pred_{t}"]), 0, 2 ** c["bits"] - 1) - d[c["label"]])
                    for t, c in M.TRIMS.items()], axis=0)
    state = np.select([worst == 0, worst <= 1], ["good", "attn"], "fallback")
    return w, list(zip(d.die_x.astype(int), d.die_y.astype(int), state, strict=True))


def wafer_art():
    """Hero illustration: a held-out wafer (real die results), a probe card touching one die, the trim signal
    converging on target, and the 64-bit fuse word that is rule-checked before any burn."""
    w, dies = _art_dies(tuple(round(p.stat().st_mtime) for p in sorted(MODELS.glob("*.joblib"))))
    xs, ys = [x for x, _, _ in dies], [y for _, y, _ in dies]
    nx, ny = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    cx, cy, r = 140, 152, 114
    cell = 2 * r * 0.86 / max(nx, ny)
    x0, y0 = cx - cell * nx / 2, cy - cell * ny / 2
    rects, good = [], []
    for x, y, s in dies:
        px, py = x0 + (x - min(xs)) * cell, y0 + (max(ys) - y) * cell
        rects.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{cell - 1.2:.1f}" height="{cell - 1.2:.1f}" rx="1.2" '
                     f'fill="var(--color-state-{s})"/>')
        if s == "good":
            good.append((px, py))
    # the probe touches a good die a little up and right of the centre
    probe_die = min(good, key=lambda p: (p[0] - cx - 30) ** 2 + (p[1] - cy + 25) ** 2) if good else (cx, cy)
    tx, ty = probe_die[0] + cell / 2, probe_die[1] + cell / 2
    bits = "1011001011100110"
    fuse = "".join(f'<rect x="{206 + i * 9.5:.1f}" y="264" width="8.3" height="13" rx="1.5" '
                   f'fill="var(--color-{"probe" if b == "1" else "surface"})" stroke="var(--color-border)"/>'
                   for i, b in enumerate(bits))
    svg = f'''<svg viewBox="0 0 360 300" font-family="Segoe UI, DM Sans, sans-serif">
 <circle cx="{cx}" cy="{cy}" r="{r}" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="2"/>
 <path d="M{cx - 9} {cy + r - 1} h18" stroke="var(--color-bg)" stroke-width="5"/>
 {"".join(rects)}
 <g stroke="var(--color-text-muted)" stroke-width="1.6" fill="none" stroke-linecap="round">
  <path d="M{tx + 58} 18 L{tx + 4} {ty - 2}"/><path d="M{tx + 76} 24 L{tx + 6} {ty}"/></g>
 <rect x="{tx + 52}" y="6" width="44" height="18" rx="4" fill="var(--color-text-muted)"/>
 <circle cx="{tx}" cy="{ty}" r="{cell * 1.1:.1f}" fill="none" stroke="var(--color-probe)" stroke-width="2.4"/>
 <g transform="translate(250 64)">
  <rect width="104" height="70" rx="10" fill="var(--color-surface-raised)" stroke="var(--color-border)"/>
  <text x="10" y="17" font-size="9.5" fill="var(--color-text-muted)">trim signal</text>
  <path d="M10 56 h12 v-26 h12 v18 h12 v-9 h12 v5 h12 v-2 h12 h10" fill="none" stroke="var(--color-probe)"
   stroke-width="2"/>
  <path d="M10 42 H96" stroke="var(--color-state-attn)" stroke-dasharray="3 3"/>
  <text x="66" y="38" font-size="8.5" fill="var(--color-text-muted)">target</text></g>
 <text x="206" y="258" font-size="9.5" fill="var(--color-text-muted)">fuse word · rule-checked first</text>
 {fuse}
 <text x="10" y="292" font-size="8.5" fill="var(--color-text-muted)">Wafer {w} (synthetic, held out)</text>
</svg>'''
    return svg_img(svg, "wafer-art", f"Illustration: held-out synthetic wafer {w}, each die coloured by its real AI trim "
                   "result (teal exact, gold one step off, copper fallback), a probe needle on one die, the trim signal "
                   "settling on target, and the fuse word that is rule-checked before any burn")


def kpi(chip, value, unit, before, after, before_lbl, after_lbl, note):
    """A headline number with its unit, a before / after bar pair and the synthetic-simulation tag."""
    top = max(before, after) or 1
    bar = lambda v, cls: f'<span class="trk"><span class="fill {cls}" style="width:{max(v / top * 100, 3):.0f}%"></span></span>'
    st.html(f'''<div class="kpi">
 <div class="khead"><span class="kchip">{chip}</span><span class="simtag">Synthetic simulation</span></div>
 <div class="kval">{value}<span class="kunit">{unit}</span></div>
 <div class="kbars">
  <span class="klbl">Conventional flow</span>{bar(before, "today")}<span class="knum">{before_lbl}</span>
  <span class="klbl">Prototype</span>{bar(after, "proto")}<span class="knum">{after_lbl}</span></div>
 <div class="knote">{note}</div></div>''')


def workflow():
    """Measure → Predict → Verify → Rule-check, with the fallback path when the check fails."""
    node = lambda n, ic, t, d, cls="": (f'<div class="wf-node {cls}" style="grid-area:{n}"><div class="wf-ic">'
                                        f'{icon(ic, "state-fallback" if cls == "fb" else "probe")}</div>'
                                        f'<div class="wf-t">{t}</div><div class="wf-d">{d}</div></div>')
    arrow = lambda n, txt="": f'<div class="wf-arrow" style="grid-area:{n}"><span>{txt}</span>{icon("arrow")}</div>'
    st.html(f'''<div class="wf">
 {node("m", "probe", "1 · Measure", "Readings the tester already takes: untrimmed values, process data, die position.")}
 {arrow("a1")}
 {node("p", "predict", "2 · Predict", "A model trained on earlier wafers proposes each trim code. No search loop.")}
 {arrow("a2")}
 {node("v", "verify", "3 · Verify once", "Set the code, measure once. In range and on target?")}
 {arrow("a3", "pass")}
 {node("f", "fuse", "4 · Rule-check the fuse word", "64-bit layout, product settings, trim fields. "
       '<span class="pill good">✓ PASS</span> <span class="pill attn">• REVIEW</span> <span class="pill bad">× BLOCK</span>')}
 <div class="wf-down" style="grid-area:d">{icon("arrow", "state-fallback")}<span>fails, or an input is out of range</span></div>
 {node("b", "fallback", "Fallback: conventional full search", "The chip gets the conventional binary search, then the same "
       "check, then step 4. Costs tester time; in the simulation, no wrong code is accepted.", "fb")}
 <div class="wf-foot">On a real tester, a fuse would be burned only after <b>PASS</b>. This prototype only simulates the
  flow on synthetic data: it does not drive a tester or program fuses.</div>
</div>''')


def check_panel(items, noun="circuit"):
    """The one-measurement check, one card per circuit: ✓ accepted, • accepted after one extra step, or
    × prediction rejected → the conventional search. A banner says so whenever fallback is triggered.
    items: [(name, AI code, best code from the full search, DAC bits)]."""
    cards, failed = [], []
    for name, ai, best, bits in items:
        off = abs(ai - best)
        if off == 0:
            cls, head, body = "good", '<span class="g">✓</span> Accepted', f"AI code <b>{ai}</b> measured on target. 1 measurement."
        elif off == 1:
            cls, head, body = "attn", '<span class="g">•</span> Accepted after 1 extra step', (
                f"AI code <b>{ai}</b> was 1 code off; one step to <b>{best}</b> confirmed it. 2 measurements.")
        else:
            failed.append(name)
            cls, head, body = "bad", '<span class="g">×</span> Prediction rejected', (
                f"AI code <s>{ai}</s> measured {off} codes off target, so it is not used. <b>Fallback:</b> the "
                f"conventional binary search found <b>{best}</b>. {1 + bits} measurements.")
        cards.append(f'<div class="chk {cls}"><div class="chk-n">{name}</div><div class="chk-h">{head}</div>'
                     f'<div class="chk-b">{body}</div></div>')
    banner = ""
    if failed:
        banner = (f'<div class="fb-banner">{icon("fallback", "state-fallback")}<div><b>Fallback triggered.</b> The AI '
                  f'prediction for {", ".join(failed)} failed its check and was <b>rejected</b>; that {noun} was '
                  f"trimmed by the conventional search instead. The other {noun}s keep their checked AI codes. "
                  f"(Simulation on synthetic data.)</div></div>")
    st.html(f'{banner}<div class="chks">{"".join(cards)}</div>')


FUSE_SHORT = {"BG_TRIM": "BG", "HSI_TRIM": "HSI", "LDO_TRIM": "LDO", "TS_CAL1": "TS_CAL1", "FLASH_SIZE": "FL",
              "PERIPH_EN": "PERIPH", "TEMP_GRADE": "T", "DEBUG_LOCK": "D", "RDP": "R", "RESERVED": "RESERVED"}
_RULE_FIELDS = {"Flash size": ["FLASH_SIZE"], "Peripheral mask": ["PERIPH_EN"], "Temperature grade": ["TEMP_GRADE"],
                "Debug port": ["DEBUG_LOCK"], "Read-out protection": ["RDP"], "Reserved bits": ["RESERVED"],
                "Trim fields": ["BG_TRIM", "HSI_TRIM", "LDO_TRIM"], "TS_CAL1": ["TS_CAL1"]}


def _field_status(checks):
    """{field: True/False} for every fuse field a rule covered; fields with no rule are absent."""
    status = {}
    for rule, ok, _ in checks:
        for key, fields in _RULE_FIELDS.items():
            if rule.startswith(key):
                for f in fields:
                    status[f] = status.get(f, True) and ok
    return status


def fuse_unchecked(checks, schema):
    """Fuse fields that no rule covered, in schema order (empty = every field checked)."""
    status = _field_status(checks)
    return [f for f, _, _ in M._layout(schema) if f not in status]


def fuse_word(hex_word, schema, checks):
    """The 64-bit fuse word as a bit strip (MSB left), split into its schema fields; each field marked
    ✓ passed / × failed / – not checked, in colour and in text."""
    word = M.parse_word(hex_word)
    status = _field_status(checks)
    cw = 15.0
    cells, labels, rows = [], [], []
    for f, lsb, nb in sorted(M._layout(schema), key=lambda t: -t[1]):
        left = (63 - (lsb + nb - 1)) * cw
        st_ = status.get(f)
        fill = "probe-soft" if st_ is True else "state-fallback" if st_ is False else "surface"
        txt = "on-state" if st_ is False else "text"
        mark = "✓" if st_ is True else "×" if st_ is False else "–"
        for i in range(nb):
            b = (word >> (lsb + nb - 1 - i)) & 1
            x = left + i * cw
            cells.append(f'<rect x="{x:.1f}" y="22" width="{cw - 1:.1f}" height="22" rx="2" fill="var(--color-{fill})"/>'
                         f'<text x="{x + cw / 2 - .5:.1f}" y="37" font-size="10" text-anchor="middle" '
                         f'fill="var(--color-{txt})">{b}</text>')
        cells.append(f'<rect x="{left - .5:.1f}" y="21" width="{nb * cw:.1f}" height="24" rx="3" fill="none" '
                     f'stroke="var(--color-text-muted)" stroke-width="1"/>')
        labels.append(f'<text x="{left + nb * cw / 2:.1f}" y="15" font-size="9.5" text-anchor="middle" '
                      f'fill="var(--color-text-muted)">{FUSE_SHORT.get(f, f)}</text>')
        value = (word >> lsb) & ((1 << nb) - 1)
        cls = "good" if st_ is True else "bad" if st_ is False else "na"
        rows.append(f'<tr><td><code>{f}</code></td><td>{lsb + nb - 1}–{lsb}</td><td>{value}</td>'
                    f'<td><span class="pill {cls}">{mark} {"passed" if st_ else "failed" if st_ is False else "not checked"}</span></td></tr>')
    st.html(f'''<div class="fuseword">
 <div class="fw-scroll">{svg_img(f'<svg viewBox="-2 0 964 50" font-family="Segoe UI, DM Sans, sans-serif">'
                                   f'{"".join(labels)}{"".join(cells)}</svg>', "fw-img",
                                   f"64-bit fuse word {hex_word} split into its fields; the table below lists each rule")}</div>
 <div class="fw-meta"><code>{hex_word}</code> · bit 63 on the left, bit 0 on the right</div>
 <table class="fw-tab"><tr><th>Field</th><th>Bits</th><th>Value</th><th>Rule</th></tr>{"".join(rows)}</table></div>''')


def plain(text, label="In plain words"):
    st.html(f'<div class="plain"><b class="lbl">{label}</b>{text}</div>')


def why(text, label="Why this method"):
    st.html(f'<div class="why"><b class="lbl">{icon("psychology")} {label}</b>{text}</div>')


def win(text, mark="check_circle"):
    st.html(f'<div class="win">{icon(mark)} {text}</div>')


def step(num, title, sub=""):
    st.html(f'<div class="step"><div class="num">{num}</div><div><div class="t">{title}</div>'
            f'<div class="s">{sub}</div></div></div>')


def card(big, label, title=None):
    t = f'<div class="ttl">{title}</div>' if title else ""
    st.html(f'<div class="card">{t}<div class="big">{big}</div><div class="lbl">{label}</div></div>')


def text_card(title, text, mark=""):
    ic = f'<div class="ic">{icon(mark)}</div>' if mark else ""
    st.html(f'<div class="card center">{ic}<div class="ttl">{title}</div><div class="txt">{text}</div></div>')


def sku_key(sku):
    return "sku-" + sku.replace("SoC-", "").lower()


def badge(sku):
    return f'<span class="badge" style="background:var(--color-{sku_key(sku)})">{sku}</span>'


def fam(text):
    return f'<span class="fam">{text}</span>'


def meth(text):
    return f'<span class="meth">{text}</span>'


def chart_style(ch):
    muted = tok("text-muted")
    return (
        ch.configure(background="transparent", font="DM Sans")
        .configure_axis(gridColor=tok("chart-grid"), domainColor=tok("border"), tickColor=tok("border"),
                        labelColor=muted, titleColor=muted, labelFontSize=12, titleFontSize=12)
        .configure_view(strokeWidth=0)
        .configure_legend(labelColor=muted, titleColor=muted, labelFontSize=12, titleFontSize=12, orient="bottom",
                          labelLimit=320)
        .configure_title(color=tok("text"))
    )


def sku_scale():
    return alt.Scale(domain=SKU_DOMAIN, range=[tok(sku_key(s)) for s in SKU_DOMAIN])


def colors(mapping):
    """Pin each category to a theme colour ({label: token}); Altair would otherwise sort labels alphabetically."""
    return alt.Scale(domain=list(mapping), range=[tok(v) for v in mapping.values()])


def palette(n=4):
    """Theme colours for categorical series."""
    return [tok(k) for k in ("sku-pro", "sku-std", "sku-lite", "chart-muted", "accent")][:n]


def glossary():
    with st.sidebar, st.expander(":material/menu_book: Glossary: chip-test words in plain language"):
        for term, mean in [
            ("Wafer / die", "A silicon disc holding hundreds of identical chips (dies)."),
            ("Derivative", "A variant of a base chip: same silicon, different specs, package or settings."),
            ("Trim", "A small digital code that corrects an analog circuit (voltage, clock) to its target."),
            ("Trim code / LSB", "The code value; one LSB is the smallest step it can move the output."),
            ("Binary search trim", "The conventional flow: measure, adjust, re-measure, about 6-8 times per trim."),
            ("Predict-then-verify", "AI predicts the code, the tester checks it once and searches only if wrong."),
            ("Fuse / OTP", "One-time programmable memory. Once blown it can never be changed."),
            ("Fuse map", "The bit layout of the fuse word: trims, memory size, security locks."),
            ("Wafer sort / final test", "First test on the wafer; last test after the chip is packaged."),
            ("Drift", "How much a value moves between wafer sort and final test, due to packaging stress."),
            ("Bandgap / HSI / LDO", "Voltage reference / 16 MHz on-chip clock / voltage regulator."),
            ("PMIC rail", "One output voltage of a power-management chip (buck or LDO)."),
            ("TCO / TCS", "How much a sensor's offset / sensitivity changes per °C."),
            ("Insertion", "One pass through the tester at one temperature."),
            ("SKU", "What a chip is sold as: SoC-Pro, Std or Lite."),
            ("Guard band", "A safety margin subtracted from a prediction so no chip is over-graded."),
            ("PCM", "Process test structures that measure transistor properties."),
        ]:
            st.markdown(f"**{term}** - {mean}")


# ---------------------------------------------------------------------------
# data and models (cached once per server)
# ---------------------------------------------------------------------------
@st.cache_data
def raw(name):
    return pd.read_csv(DATA / DATASETS[name][0])


@st.cache_resource
def model(name):
    return joblib.load(MODELS / f"{name}_models.joblib")


@st.cache_data
def evaluation():
    """Notebook 06 results: ranges across wafers, the validated SoC margin, fallback rates, model cards."""
    return json.loads((MODELS / "evaluation_06.json").read_text(encoding="utf8"))


def mcuc_headline():
    """MCU-C final-test pass (conventional flow, with the drift fix): mean of both wafer directions (RESULTS_SOURCE_OF_TRUTH
    MCUC_DRIFT). The Wafer lab still shows the single held-out wafer."""
    d = pd.DataFrame(evaluation()["lowo_drift"])
    return d["today_%"].mean() / 100, d["fine_tuned_median_%"].mean() / 100


SYNTHETIC_NOTE = ("Prototype on synthetic data: every number is a simulation result, not a real-world saving, yield "
                  "or safety claim.")


@st.cache_data
def dictionary():
    """DATA_DICTIONARY.md -> {file name: table of column, role, description, example}."""
    text = (DATA / "DATA_DICTIONARY.md").read_text(encoding="utf8")
    out = {}
    for block in re.split(r"\n## ", text)[1:]:
        name = block.split("\n", 1)[0].strip()
        rows = [ln for ln in block.splitlines() if ln.startswith("| `")]
        out[name] = pd.DataFrame(
            [[c.strip().strip("`") for c in ln.strip("|").split("|")] for ln in rows],
            columns=["Column", "Role", "Description", "Example"])
    return out


# ---------------------------------------------------------------- MCU
@st.cache_data
def mcu_test():
    """Held-out MCU-A wafers with the saved models' raw predictions (same split as notebook 01)."""
    a = raw("mcu")[raw("mcu").derivative == "MCU-A"].reset_index(drop=True)
    _, te = wafer_split(a)
    pr = M.predict_codes(te, model("trim"))
    for t in M.TRIMS:
        te[f"pred_{t}"] = pr[t].values
        te[f"formula_{t}"] = M.formula_code(te, t)
    return te


@st.cache_data
def mcu_metrics():
    te, rows = mcu_test(), {}
    for t, c in M.TRIMS.items():
        conv = te[c["conv"]].mean()
        rows[t] = {"ai": code_metrics(te[c["label"]], te[f"pred_{t}"], c["bits"], conv),
                   "formula": code_metrics(te[c["label"]], te[f"formula_{t}"], c["bits"], conv)}
    return rows


@st.cache_data
def mcu_drift():
    d = M.add_drift_features(raw("mcu"), raw("mcu").radius_mm.max())
    cw = sorted(d[d.derivative == "MCU-C"].wafer_id.unique())
    c2 = d[d.wafer_id == cw[1]].reset_index(drop=True)
    c2["pred_shift_mV"] = M.predict_shift(c2, model("trim"))
    c2["final_ai_V"], c2["sort_ai_V"] = M.with_offset_target(c2, c2.pred_shift_mV)
    return c2, cw


@st.cache_data
def fuse_validation():
    return M.validate_all(raw("audit"), raw("mcu"), raw("schema"))


# ---------------------------------------------------------------- PMIC
@st.cache_data
def pmic_test():
    p1 = raw("pmic")[raw("pmic").derivative == "PMIC-P1"].reset_index(drop=True)
    _, te = wafer_split(p1)
    te = P.add_features(te)
    pr = P.predict_rails(te, model("pmic"))
    for r in P.RAILS:
        te[f"pred_{r}"] = pr[r].values
        te[f"formula_{r}"] = P.formula_code(te, r)
    b = model("pmic")
    te["pred_vref"] = b["thresholds"]["vref"]["model"].predict(te[b["thresholds"]["vref"]["features"]])
    for t in ["vref", "ovp", "uvlo", "ilim"]:
        te[f"formula_{t}"] = P.formula_code(te, t)
    for c in P.CS_TARGETS:
        te[f"pred_{c}"] = b["current_sense"][c].predict(te[b["cs_features"]])
    return te


@st.cache_data
def pmic_others():
    o = P.add_features(raw("pmic")[raw("pmic").derivative != "PMIC-P1"].reset_index(drop=True))
    pr = P.predict_rails(o, model("pmic"))
    for r in P.RAILS:
        o[f"pred_{r}"] = pr[r].values
    return o


# ---------------------------------------------------------------- Sensor
@st.cache_data
def sensor_sets():
    long = S.to_long(raw("sensor"))
    tr, te, ot = S.split(raw("sensor"), long)
    b = model("sensor")
    for d in (te, ot):
        p = S.predict(d, b)
        for c in S.COEFS:
            d[f"pred_{c}"] = p[c]
        d["pred_reflow"] = b["reflow"].predict(d[b["reflow_features"]])
    fleet = {c: tr[c].mean() for c in S.COEFS}
    return tr, te, ot, fleet


# ---------------------------------------------------------------- SoC
@st.cache_data
def soc_data():
    return Q.prepare(raw("soc"))


@st.cache_data
def soc_true_elig():
    d = soc_data()
    return Q.eligibility(d, raw("sku"), Q.measured_ftop(d))


@st.cache_data
def soc_test():
    _, te = wafer_split(soc_data())
    return te, Q.predicted_ftop(te, model("soc"))


@st.cache_data
def soc_guard_table(guards):
    te, ftop = soc_test()
    sku = raw("sku")
    true_e = Q.eligibility(te, sku, Q.measured_ftop(te))
    price = sku.set_index("sku").price_usd
    rank = {"scrap": 0, "SoC-Lite": 1, "SoC-Std": 2, "SoC-Pro": 3}
    true_rank = pd.Series(Q.best_sku(true_e)).map(rank).values
    rows = []
    for g in guards:
        pe = Q.eligibility(te, sku, ftop, g / 1000)
        ps = Q.best_sku(pe)
        pr = pd.Series(ps).map(rank).values
        rows.append({"guard_MHz": g, "unsafe": Q.unsafe(ps, pe, true_e).mean(), "under_bin": (pr < true_rank).mean(),
                     "match": (ps == Q.best_sku(true_e)).mean(),
                     "revenue_per_die": pd.Series(ps).map(price).fillna(0).mean()})
    full = pd.Series(Q.best_sku(true_e)).map(price).fillna(0).mean()
    return pd.DataFrame(rows), full


@st.cache_data
def repair_results():
    r = raw("repair").copy()
    fails = r.fail_cells.apply(Q.parse)
    r["exact_ok"] = fails.apply(lambda f: Q.exact_repair(f)[0])
    return r

# ---------------------------------------------------------------- wafer maps
# One status palette everywhere: good / attention / fallback / neutral. Each state also has a symbol, drawn on the
# die and in the legend, so the maps never rely on colour alone.
GOOD, STEP, BAD, NA = "state-good", "state-attn", "state-fallback", "state-neutral"
GLYPH = {GOOD: "✓", STEP: "•", BAD: "×", NA: "–"}


def _square(d, size):
    """Width and height that make every die a square (wafers have more columns than rows, or the reverse)."""
    nx, ny = max(d.die_x.nunique(), 1), max(d.die_y.nunique(), 1)
    cell = size / max(nx, ny)
    return cell * nx, cell * ny, cell


def _legend_expr(mapping):
    labels = {k: f"{GLYPH[v]}  " for k, v in mapping.items() if v in GLYPH}
    return f"({json.dumps(labels)})[datum.label] + datum.label" if labels else "datum.label"


class Map:
    """A wafer map that can be drawn at any size: wide (legend beside it) on desktop, narrow (legend below) on
    phones. Both are rendered and CSS shows the one that fits, so hover still works (no CSS scaling)."""

    def __init__(self, fn, size):
        self.fn, self.size = fn, size

    def build(self, size=None, legend="right"):
        return self.fn(size or self.size, legend)


NARROW = 300  # map size on phones


def wafer_map(d, field, mapping, tooltip, size=400, title=None):
    return Map(lambda s, lg: _wafer_map(d, field, mapping, tooltip, s, title, lg), size)


def wafer_heat(d, field, label, tooltip, size=400, scheme="goldorange"):
    return Map(lambda s, lg: _wafer_heat(d, field, label, tooltip, s, scheme, lg), size)


def _wafer_map(d, field, mapping, tooltip, size, title, legend):
    """One square per die at its real wafer position, coloured by a category ({label: theme token}), with the
    state's symbol on every die that is not 'good' and in the legend."""
    w, h, cell = _square(d, size)
    enc = {"x": alt.X("die_x:O", axis=None), "y": alt.Y("die_y:O", axis=None, sort="descending")}
    rect = alt.Chart(d).mark_rect(cornerRadius=max(1.5, cell * .18), stroke=tok("bg"), strokeWidth=1.2).encode(
        **enc, tooltip=tooltip,
        color=alt.Color(f"{field}:N", scale=colors(mapping),
                        legend=alt.Legend(title=None, orient=legend, labelExpr=_legend_expr(mapping), symbolType="square",
                                          symbolSize=160, labelLimit=400, columns=1)))
    glyphs = {k: GLYPH[v] for k, v in mapping.items() if v in GLYPH and v != GOOD}
    marks = d.assign(_g=d[field].map(glyphs)).dropna(subset=["_g"]) if glyphs else d.iloc[:0]
    layer = rect
    if len(marks) and cell >= 8:
        layer = rect + alt.Chart(marks).mark_text(fontSize=max(7, cell * .62), fontWeight="bold",
                                                  color=tok("on-state")).encode(**enc, text="_g:N", tooltip=tooltip)
    return layer.properties(width=w, height=h, title=title or "")


def _wafer_heat(d, field, label, tooltip, size, scheme, legend):
    w, h, cell = _square(d, size)
    ch = alt.Chart(d).mark_rect(cornerRadius=max(1.5, cell * .18), stroke=tok("bg"), strokeWidth=1.2).encode(
        x=alt.X("die_x:O", axis=None), y=alt.Y("die_y:O", axis=None, sort="descending"),
        color=alt.Color(f"{field}:Q", scale=alt.Scale(scheme=scheme), legend=alt.Legend(title=label, orient=legend)),
        tooltip=tooltip)
    return ch.properties(width=w, height=h)


PAD = alt.AutoSizeParams(type="pad")  # the map keeps its size; the legend beside it adds width instead of squeezing it


def _show(ch):
    st.altair_chart(chart_style(ch.properties(autosize=PAD)).configure_title(color=tok("text"), fontSize=14,
                                                                             anchor="start"), width="content")


def show_map(m):
    """One map: wide on desktop, narrow on phones."""
    with st.container(key="map_wide"):
        _show(m.build())
    with st.container(key="map_narrow"):
        _show(m.build(NARROW, "bottom"))


def show_pair(left, right):
    """Two maps with one shared legend: side by side on desktop, stacked on phones."""
    with st.container(key="pair_wide"):
        _show(alt.hconcat(left.build(), right.build(), spacing=30).resolve_scale(color="shared"))
    with st.container(key="pair_narrow"):
        _show(alt.vconcat(left.build(NARROW, "bottom"), right.build(NARROW, "bottom"), spacing=16)
              .resolve_scale(color="shared"))


@st.cache_data
def soc_plans():
    """Per-die product: the conventional rule and the optimised plan (dataset demand and prices)."""
    d, e, sku = soc_data(), soc_true_elig(), raw("sku")
    alloc, pattern, _ = Q.optimise(e, sku, sku.set_index("sku").weekly_demand_units)
    out = d[["die_id", "wafer_id", "die_x", "die_y", "radius_mm", "n_good_cores", "f_top8", "f_top6", "f_top4"]].copy()
    out["today"] = Q.best_sku(e)
    # hand the plan to individual dies: inside each group the fastest dies keep the higher product,
    # so the slowest Std-capable dies are the ones sold as Lite (physically sensible; revenue is the same)
    k_of = {"SoC-Pro": 8, "SoC-Std": 6, "SoC-Lite": 4}
    opt = pd.Series("unsold", index=d.index)
    for g in pattern.unique():
        idx = pattern.index[pattern == g]
        order = d.loc[idx, f"f_top{k_of[g[0]]}"].sort_values(ascending=False).index if g else idx
        start = 0
        for sku in g:
            n = int(alloc.get((g, sku), 0))
            opt.loc[order[start:start + n]] = sku
            start += n
    out["optimised"] = opt.values
    return out


def headline():
    """The few numbers the website leads with. Saved to disk and keyed to the model files, so a restart is instant
    and a re-copied model recomputes them."""
    return _headline(tuple(round(p.stat().st_mtime) for p in sorted(MODELS.glob("*.joblib"))))


@st.cache_data(persist="disk", show_spinner="Computing the results from the saved models...")
def _headline(_models_stamp):
    """All recomputed from the saved models."""
    mm = mcu_metrics()
    ms = {"bg": 1.2, "hsi": 2.0, "ldo": 1.0}
    c2, _ = mcu_drift()
    te = pmic_test()
    rails = sum(code_metrics(te[f"{r}_trim_code_opt"], te[f"pred_{r}"], 6, 6.33)["ai_iters"] for r in P.RAILS)
    vref = code_metrics(te.vref_trim_code_opt, te.pred_vref, 6, 6.33)["ai_iters"]
    thr = sum(code_metrics(te[P.CFG[t]["label"]], te[f"formula_{t}"], P.CFG[t]["bits"], 1)["ai_iters"] for t in ("ovp", "uvlo", "ilim"))
    sen_s = raw("sensor").conv_test_time_s.mean()
    sku = raw("sku")
    e = soc_true_elig()
    dem = sku.set_index("sku").weekly_demand_units
    rev_rule, _, _ = Q.rule_revenue(Q.best_sku(e), sku, dem)
    _, _, rev_opt = Q.optimise(e, sku, dem)
    val = fuse_validation()
    rep = repair_results()
    pmic_iters = raw("pmic").conv_trim_iterations.mean()
    return {
        "mcu_ms": (sum(mm[t]["ai"]["conv_iters"] * ms[t] for t in ms), sum(mm[t]["ai"]["ai_iters"] * ms[t] for t in ms)),
        "hsi_w1": (mm["hsi"]["formula"]["within1"], mm["hsi"]["ai"]["within1"]),
        "drift": ((abs(c2.bg_final_V - 1.2) <= 5e-3).mean(), (abs(c2.final_ai_V - 1.2) <= 5e-3).mean()),
        "pmic_steps": (pmic_iters, rails + vref + thr),
        "sensor_s": (sen_s, 0.95 * sen_s / 3 + 0.05 * sen_s),
        "soc_rev": (rev_rule, rev_opt),
        "fuse": (int((val.flagged & val.has_error).sum()), int(val.has_error.sum()), int((val.flagged & ~val.has_error).sum())),
        "repair_saved": int((rep.exact_ok & ~rep.greedy_repairable).sum()),
    }
