"""
Theme & animation layer for the SingleCellX Streamlit UI.

Everything in this module is pure HTML/CSS/SVG injected into Streamlit
via st.markdown(unsafe_allow_html=True). No extra Python packages
needed — keeps the dependency footprint identical to the upstream
project.
"""
from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------------------------
# Global stylesheet — gradients, glassmorphism, animations, custom widgets.
# ---------------------------------------------------------------------------
GLOBAL_CSS = """
<style>
/* ------------ Root palette ------------- */
:root {
  /* Warm light-brown publication palette */
  --sc-primary: #7c4a2a;    /* deep mocha */
  --sc-secondary: #a67c52;  /* warm tan */
  --sc-accent: #d97706;     /* golden amber */
  --sc-success: #386641;    /* olive green */
  --sc-warn: #b45309;       /* amber brown */
  --sc-danger: #991b1b;     /* deep maroon */
  --sc-bg-0: #fbf7f1;       /* ivory */
  --sc-bg-1: #fffaf0;       /* cream */
  --sc-text: #08131a;       /* very dark black-blue */
  --sc-muted: #5b4636;      /* muted brown */
  --sc-card: rgba(255, 250, 240, 0.94);
  --sc-border: rgba(8, 19, 26, 0.12);
}

/* ------------ App background ------------- */
.stApp {
  background:
    radial-gradient(circle at 18% 20%, rgba(124, 74, 34, 0.16), transparent 30%),
    radial-gradient(circle at 88% 88%, rgba(217, 119, 6, 0.16), transparent 36%),
    linear-gradient(135deg, #fbf7f1 0%, #f5ece0 38%, #f0e2d5 100%);
  color: var(--sc-text);
}

/* ------------ Headings ------------- */
h1, h2, h3, h4 { letter-spacing: -0.01em; }
h1 {
  background: linear-gradient(90deg, var(--sc-primary), var(--sc-accent), var(--sc-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
}

/* ------------ Sidebar ------------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(248, 250, 252, 0.96) 100%);
  border-right: 1px solid var(--sc-border);
}
section[data-testid="stSidebar"] * { color: var(--sc-text); }

/* ------------ Metric cards ------------- */
[data-testid="stMetric"] {
  background: var(--sc-card);
  backdrop-filter: blur(10px);
  border: 1px solid var(--sc-border);
  border-radius: 14px;
  padding: 14px 18px;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  animation: sc-fadeUp 0.45s ease both;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-3px);
  border-color: var(--sc-primary);
  box-shadow: 0 16px 40px rgba(124, 74, 34, 0.24);
}
[data-testid="stMetricValue"] {
  background: linear-gradient(90deg, var(--sc-primary), var(--sc-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
}

/* ------------ Buttons ------------- */
.stButton > button, .stDownloadButton > button {
  background: linear-gradient(90deg, var(--sc-primary), var(--sc-accent));
  color: #faf5ef !important;
  border: 1px solid rgba(8, 19, 26, 0.08);
  font-weight: 700;
  border-radius: 14px;
  padding: 0.75rem 1.3rem;
  box-shadow: 0 8px 30px rgba(124, 74, 34, 0.16);
  transition: transform 0.24s, box-shadow 0.24s, filter 0.24s;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px);
  filter: brightness(1.08);
  box-shadow: 0 18px 40px rgba(124, 74, 34, 0.22);
}
.stButton > button:active { transform: translateY(0); }

/* ------------ Tabs ------------- */
.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: transparent;
  border-bottom: 1px solid var(--sc-border);
}
.stTabs [data-baseweb="tab"] {
  background: rgba(255, 255, 255, 0.75);
  border-radius: 10px 10px 0 0;
  padding: 10px 18px;
  border: 1px solid rgba(8, 19, 26, 0.08);
  transition: all 0.2s;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(166, 124, 82, 0.16); }
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(124, 74, 42, 0.24), rgba(217, 119, 6, 0.15)) !important;
  border-color: rgba(124, 74, 42, 0.22) !important;
  color: #08131a !important;
}

/* ------------ Expanders / dataframes ------------- */
[data-testid="stExpander"] {
  background: var(--sc-card);
  border: 1px solid var(--sc-border);
  border-radius: 12px;
}

/* ------------ Alerts ------------- */
.stAlert { border-radius: 12px; border: 1px solid var(--sc-border); }

/* ------------ Animations ------------- */
@keyframes sc-fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes sc-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(124, 74, 34, 0.35); }
  50%      { box-shadow: 0 0 0 12px rgba(124, 74, 34, 0); }
}
@keyframes sc-spin {
  to { transform: rotate(360deg); }
}
@keyframes sc-float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}
@keyframes sc-shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
@keyframes sc-helix {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ------------ Custom components ------------- */
.sc-hero {
  padding: 34px 36px;
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 244, 230, 0.95), rgba(245, 233, 220, 0.95) 45%, rgba(250, 243, 235, 0.95));
  border: 1px solid rgba(124, 74, 34, 0.14);
  box-shadow: 0 24px 70px rgba(124, 74, 34, 0.08);
  backdrop-filter: blur(18px);
  display: flex; align-items: center; gap: 26px;
  animation: sc-fadeUp 0.6s ease both;
}
.sc-hero .sc-hero-icon { animation: sc-float 4s ease-in-out infinite; }
.sc-hero h1 { margin: 0; font-size: 2.2rem; }
.sc-hero p  { margin: 4px 0 0 0; color: var(--sc-muted); }

.sc-card {
  background: var(--sc-card);
  border: 1px solid var(--sc-border);
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 14px;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
  animation: sc-fadeUp 0.5s ease both;
}
.sc-card:hover {
  transform: translateY(-2px);
  border-color: var(--sc-primary);
  box-shadow: 0 14px 32px rgba(124, 74, 34, 0.16);
}
.sc-card h3 { margin-top: 0; }

.sc-pill {
  display: inline-block;
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  background: rgba(124, 74, 34, 0.12);
  color: var(--sc-primary);
  border: 1px solid rgba(124, 74, 34, 0.2);
}
.sc-pill.ok { background: rgba(16,185,129,0.18); color: var(--sc-success); border-color: rgba(16,185,129,0.3);}
.sc-pill.warn { background: rgba(245,158,11,0.18); color: var(--sc-warn); border-color: rgba(245,158,11,0.3);}
.sc-pill.err { background: rgba(239,68,68,0.18); color: var(--sc-danger); border-color: rgba(239,68,68,0.3);}

.sc-status-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--sc-success);
  margin-right: 6px;
  animation: sc-pulse 1.8s infinite;
}
.sc-status-dot.warn  { background: var(--sc-warn); }
.sc-status-dot.err   { background: var(--sc-danger); }
.sc-status-dot.idle  { background: var(--sc-muted); animation: none; }

.sc-step-row { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0 20px; }
.sc-step {
  flex: 1; min-width: 110px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--sc-card);
  border: 1px solid var(--sc-border);
  font-size: 0.85rem;
  text-align: center;
  transition: all 0.25s;
}
.sc-step.done {
  border-color: var(--sc-success);
  background: rgba(16, 185, 129, 0.10);
  color: var(--sc-success);
}
.sc-step.active {
  border-color: var(--sc-primary);
  background: rgba(217, 119, 6, 0.18);
  color: var(--sc-text);
  animation: sc-pulse 1.5s infinite;
}
.sc-step.pending { color: var(--sc-muted); }

.sc-progress-bar {
  height: 6px; border-radius: 4px; background: var(--sc-border);
  overflow: hidden; margin: 6px 0 14px;
}
.sc-progress-bar > div {
  height: 100%;
  background: linear-gradient(90deg, var(--sc-primary), var(--sc-secondary));
  border-radius: 4px;
  background-size: 200px 100%;
  animation: sc-shimmer 1.8s linear infinite;
  transition: width 0.4s ease;
}

.sc-footer {
  text-align: center; color: var(--sc-muted); font-size: 0.85rem;
  padding: 24px 0 12px;
}
</style>
"""


# ---------------------------------------------------------------------------
# Reusable HTML components.
# ---------------------------------------------------------------------------
def _dna_svg(size: int = 56) -> str:
    """Inline rotating-DNA SVG. Pure SVG + CSS, no external assets."""
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 100 100" style="animation: sc-helix 8s linear infinite;">
      <defs>
        <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stop-color="#6366f1"/>
          <stop offset="50%" stop-color="#ec4899"/>
          <stop offset="100%" stop-color="#06b6d4"/>
        </linearGradient>
      </defs>
      <g stroke="url(#g1)" stroke-width="3" fill="none" stroke-linecap="round">
        <path d="M30,10 Q70,30 30,50 Q70,70 30,90"/>
        <path d="M70,10 Q30,30 70,50 Q30,70 70,90"/>
        <line x1="34" y1="20" x2="66" y2="20"/>
        <line x1="40" y1="35" x2="60" y2="35"/>
        <line x1="34" y1="50" x2="66" y2="50"/>
        <line x1="40" y1="65" x2="60" y2="65"/>
        <line x1="34" y1="80" x2="66" y2="80"/>
      </g>
    </svg>
    """


def inject_global_css() -> None:
    """Inject the global stylesheet exactly once per session."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def inject_color_overrides(colors: dict[str, str]) -> None:
  """Inject runtime color variable overrides.

  `colors` should be a mapping of CSS variable names (without leading
  `--`) to hex/color strings, e.g. {'sc-primary': '#ff00aa'}.
  """
  if not colors:
    return
  vars_css = "\n".join(f"  --{k}: {v};" for k, v in colors.items())
  css = f"<style>:root {{\n{vars_css}\n}}</style>"
  st.markdown(css, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str) -> None:
    """Big animated hero banner with rotating DNA icon."""
    st.markdown(
        f"""
        <div class="sc-hero">
            <div class="sc-hero-icon">{_dna_svg(72)}</div>
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_steps(steps: list[str], current: int | None) -> None:
    """Animated stepper: 'done' / 'active' / 'pending' states."""
    chips = []
    for i, name in enumerate(steps):
        if current is None:
            cls = "pending"
        elif i < current:
            cls = "done"
        elif i == current:
            cls = "active"
        else:
            cls = "pending"
        marker = "✓" if cls == "done" else ("●" if cls == "active" else "○")
        chips.append(f'<div class="sc-step {cls}">{marker} {name}</div>')
    st.markdown(f'<div class="sc-step-row">{"".join(chips)}</div>',
                unsafe_allow_html=True)


def render_status(label: str, kind: str = "ok") -> None:
    """Small inline status with pulsing dot. kind: ok|warn|err|idle"""
    st.markdown(
        f'<span class="sc-status-dot {kind if kind != "ok" else ""}"></span>'
        f'<span style="font-size:0.9rem;">{label}</span>',
        unsafe_allow_html=True,
    )


def render_card(title: str, body_html: str, pill: str | None = None) -> None:
    pill_html = f'<span class="sc-pill">{pill}</span>' if pill else ""
    st.markdown(
        f'<div class="sc-card"><h3>{title} {pill_html}</h3>{body_html}</div>',
        unsafe_allow_html=True,
    )


def render_footer(version: str = "3.0") -> None:
    st.markdown(
        f"""
        <div class="sc-footer">
          🧬 <b>SingleCellX</b> v{version} · modular scRNA-seq pipeline ·
          built with Streamlit, scikit-learn, scipy, UMAP & Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )
