"""Theme system: semantic colour tokens -> CSS custom properties, switched by a root-level class.

How it works
- Every colour has a *semantic* name (what it is for, not what it looks like): --color-bg, --color-text,
  --color-accent, --color-on-accent, ... Components only ever use these names.
- Each theme is one entry in THEMES. `css()` turns every entry into one CSS block:
      :root:has(.theme-flag.theme-<name>) { --color-...: ...; }
  The page carries an invisible flag element with the chosen theme's class, so switching themes is a
  class change on the root, resolved by CSS alone. The default theme is also written on plain :root,
  so the first paint is correct with no JavaScript at all.
- Adding a theme = add one dict to THEMES (same keys). Nothing else changes: CSS, charts and the
  theme switcher read THEMES, and tests/test_theme.py checks every theme for WCAG AA contrast.
"""

DEFAULT = "beige"

THEMES = {
    # warm sand, inspired by the beige component gallery
    "beige": {
        "label": "Beige", "scheme": "light",
        "bg": "#f6f1e9", "bg-subtle": "#efe8dc", "surface": "#e9e1d3", "surface-raised": "#fbf8f2",
        "border": "#ddd3c2", "text": "#2b2419", "text-muted": "#5f5444", "accent": "#5c4a32",
        "on-accent": "#ffffff", "accent-text": "#6e522c", "accent-soft": "#eee4d4",
        "accent-grad-from": "#9a6b2f", "accent-grad-to": "#5c4a32",
        "success": "#2f6b48", "success-soft": "#e3ecdf", "warning": "#8a5a00",
        "chart-grid": "#e4dccd", "chart-muted": "#8c8170",
        "sku-pro": "#2563c9", "sku-std": "#b84a1c", "sku-lite": "#167a55", "sku-scrap": "#776f63",
        "on-sku": "#ffffff",
        "probe": "#0b6a62", "probe-soft": "#dcebe5", "on-probe": "#ffffff",
        "state-good": "#0b6a62", "state-attn": "#9a6a0c", "state-fallback": "#b4501e", "state-neutral": "#857a69",
        "on-state": "#ffffff",
    },
    # paper and ink, inspired by diskbuddy.com
    "blue": {
        "label": "Blue", "scheme": "light",
        "bg": "#edebde", "bg-subtle": "#e6e3d3", "surface": "#f5f3e9", "surface-raised": "#fafaf4",
        "border": "#cfccd8", "text": "#1d2470", "text-muted": "#454b86", "accent": "#252e86",
        "on-accent": "#f5f3e9", "accent-text": "#252e86", "accent-soft": "#e1e0e3",
        "accent-grad-from": "#2563eb", "accent-grad-to": "#252e86",
        "success": "#2b6e40", "success-soft": "#e0e8d8", "warning": "#8a5200",
        "chart-grid": "#dcdad0", "chart-muted": "#7e7e96",
        "sku-pro": "#2563c9", "sku-std": "#b84a1c", "sku-lite": "#167a55", "sku-scrap": "#6f6c66",
        "on-sku": "#ffffff",
        "probe": "#0f766e", "probe-soft": "#d9e6dc", "on-probe": "#ffffff",
        "state-good": "#0f766e", "state-attn": "#94640a", "state-fallback": "#ad4b1b", "state-neutral": "#787586",
        "on-state": "#ffffff",
    },
    # bright and clean, orange accent, inspired by diskbuddy.com
    "light": {
        "label": "Light", "scheme": "light",
        "bg": "#fbfbfd", "bg-subtle": "#f5f5f7", "surface": "#f1f1f4", "surface-raised": "#ffffff",
        "border": "#e2e2e8", "text": "#1d1d1f", "text-muted": "#5f5f66", "accent": "#dd6b0c",
        "on-accent": "#1d1d1f", "accent-text": "#b2490a", "accent-soft": "#fdf0e4",
        "accent-grad-from": "#dd6b0c", "accent-grad-to": "#b2410c",
        "success": "#1f7a45", "success-soft": "#e6f4ea", "warning": "#8a5200",
        "chart-grid": "#ececf0", "chart-muted": "#8a8a92",
        "sku-pro": "#2563c9", "sku-std": "#b84a1c", "sku-lite": "#167a55", "sku-scrap": "#76767c",
        "on-sku": "#ffffff",
        "probe": "#0f766e", "probe-soft": "#e3f2ee", "on-probe": "#ffffff",
        "state-good": "#0f766e", "state-attn": "#9a6a0c", "state-fallback": "#b4501e", "state-neutral": "#808088",
        "on-state": "#ffffff",
    },
    # warm dark
    "dark": {
        "label": "Dark", "scheme": "dark",
        "bg": "#17150f", "bg-subtle": "#1e1b15", "surface": "#26221b", "surface-raised": "#2d2820",
        "border": "#3b352b", "text": "#f3eee5", "text-muted": "#bdb3a2", "accent": "#e2c08f",
        "on-accent": "#1b1710", "accent-text": "#e8c897", "accent-soft": "#2e271d",
        "accent-grad-from": "#f0d3a6", "accent-grad-to": "#d99b5a",
        "success": "#79d29f", "success-soft": "#1d2b22", "warning": "#f0b85a",
        "chart-grid": "#2f2a22", "chart-muted": "#8d8576",
        "sku-pro": "#6ea8f2", "sku-std": "#f08a5d", "sku-lite": "#45c994", "sku-scrap": "#a39e94",
        "on-sku": "#17150f",
        "probe": "#3cc0ad", "probe-soft": "#16302b", "on-probe": "#0f1412",
        "state-good": "#3cc0ad", "state-attn": "#e2b04a", "state-fallback": "#f08a5d", "state-neutral": "#8d8576",
        "on-state": "#17150f",
    },
}

COLOR_KEYS = [k for k in THEMES[DEFAULT] if k not in ("label", "scheme")]

# foreground/background pairs that must pass WCAG AA: (fg, bg, minimum ratio)
# 4.5:1 for body text, 3:1 for large text (hero gradient) and for chart marks / UI parts (WCAG 1.4.11)
PAIRS = (
    [("text", b, 4.5) for b in ("bg", "bg-subtle", "surface", "surface-raised", "accent-soft", "success-soft")]
    + [("text-muted", b, 4.5) for b in ("bg", "bg-subtle", "surface", "surface-raised", "accent-soft")]
    + [("accent-text", b, 4.5) for b in ("bg", "surface", "surface-raised", "accent-soft")]
    + [("on-accent", "accent", 4.5), ("success", "success-soft", 4.5), ("success", "bg", 4.5),
       ("warning", "bg", 4.5)]
    + [("on-sku", s, 4.5) for s in ("sku-pro", "sku-std", "sku-lite", "sku-scrap")]
    + [(s, "bg", 3.0) for s in ("sku-pro", "sku-std", "sku-lite", "sku-scrap", "chart-muted", "accent")]
    + [("accent-grad-from", "bg", 3.0), ("accent-grad-to", "bg", 3.0)]
    # the semiconductor accent and the status colours used by wafer maps, charts, controls and status labels
    + [("on-probe", "probe", 4.5), ("text", "probe-soft", 4.5), ("probe", "bg", 4.5), ("probe", "surface", 4.5)]
    + [(s, b, 3.0) for s in ("state-good", "state-attn", "state-fallback", "state-neutral") for b in ("bg", "surface")]
    + [("on-state", s, 3.0) for s in ("state-good", "state-attn", "state-fallback", "state-neutral")]
)


def _lum(hex_color):
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def audit():
    """[(theme, fg, bg, ratio, needed)] for every pair that fails AA (empty = all pass)."""
    return [(name, f, b, round(contrast(t[f], t[b]), 2), need)
            for name, t in THEMES.items() for f, b, need in PAIRS if contrast(t[f], t[b]) < need]


def _block(t):
    return " ".join(f"--color-{k}: {t[k]};" for k in COLOR_KEYS) + f" color-scheme: {t['scheme']};"


def css():
    """CSS custom properties for every theme; the default also lives on plain :root (first paint)."""
    rules = [f":root {{ {_block(THEMES[DEFAULT])} }}"]
    rules += [f":root:has(.theme-flag.theme-{name}) {{ {_block(t)} }}" for name, t in THEMES.items()]
    return "\n".join(rules)
