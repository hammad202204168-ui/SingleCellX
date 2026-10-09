"""Settings module — cache stats, parameter export, pipeline reset."""
from __future__ import annotations

import json

import streamlit as st

from app.services.cache import get_cache
from streamlit_modules import state
from streamlit_modules import theme


def render() -> None:
    st.subheader("⚙️ Settings & Cache")

    # Apply any saved color overrides immediately so the page reflects them
    saved = state.get("colors")
    if saved:
        try:
            theme.inject_color_overrides(saved)
        except Exception:
            pass

    # Cache
    st.markdown("### Result cache")
    cache = get_cache()
    stats = cache.stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hits", stats["hits"])
    c2.metric("Misses", stats["misses"])
    c3.metric("Hit rate", f"{stats['hit_rate_pct']:.1f}%")
    c4.metric("Cached items", stats["cached_items"])
    if st.button("🗑️ Clear cache"):
        cache.clear()
        st.success("Cache cleared.")

    st.divider()
    st.markdown("### Pipeline parameters (persisted in session)")
    params = state.get("params")
    st.json(params)

    pc1, pc2 = st.columns(2)
    with pc1:
        st.download_button("⬇️ Download parameters JSON",
                           data=json.dumps(params, indent=2),
                           file_name="params.json",
                           mime="application/json",
                           use_container_width=True)
    with pc2:
        uploaded = st.file_uploader("Load parameters JSON", type=["json"],
                                    key="params_upload",
                                    label_visibility="collapsed")
        if uploaded is not None and st.button("Apply uploaded params",
                                              use_container_width=True):
            try:
                new = json.loads(uploaded.getvalue().decode())
                params.update({k: v for k, v in new.items() if k in params})
                st.success("Parameters loaded.")
            except Exception as exc:
                st.error(f"Failed to load: {exc}")

    st.divider()
    st.markdown("### Reset pipeline")
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("🔁 Reset results (keep data)", use_container_width=True):
            state.reset_pipeline(keep_data=True)
            st.success("Pipeline reset.")
    with rc2:
        if st.button("🧹 Reset everything", type="secondary",
                     use_container_width=True):
            state.reset_pipeline(keep_data=False)
            st.success("Full reset done.")

    # ------------------------------------------------------------------
    # Appearance: color pickers and presets
    # ------------------------------------------------------------------
    st.divider()
    st.markdown("### Appearance — Colors & Theme")
    # Populate defaults from current saved state or sensible vibrant defaults
    saved = state.get("colors") or {}
    defaults = {
        "sc-primary": saved.get("sc-primary", "#7c4a2a"),
        "sc-secondary": saved.get("sc-secondary", "#a67c52"),
        "sc-accent": saved.get("sc-accent", "#d97706"),
        "sc-success": saved.get("sc-success", "#386641"),
        "sc-warn": saved.get("sc-warn", "#b45309"),
        "sc-danger": saved.get("sc-danger", "#991b1b"),
        "sc-bg-0": saved.get("sc-bg-0", "#fbf7f1"),
        "sc-bg-1": saved.get("sc-bg-1", "#fffaf0"),
        "sc-text": saved.get("sc-text", "#08131a"),
        "sc-muted": saved.get("sc-muted", "#5b4636"),
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        primary = st.color_picker("Primary", defaults["sc-primary"])
        secondary = st.color_picker("Secondary", defaults["sc-secondary"])
        accent = st.color_picker("Accent", defaults["sc-accent"])
    with c2:
        success = st.color_picker("Success", defaults["sc-success"])
        warn = st.color_picker("Warning", defaults["sc-warn"])
        danger = st.color_picker("Danger", defaults["sc-danger"])
    with c3:
        bg0 = st.color_picker("Background (deep)", defaults["sc-bg-0"])
        bg1 = st.color_picker("Card background", defaults["sc-bg-1"])
        text = st.color_picker("Text color", defaults["sc-text"])

    if st.button("Apply colors", use_container_width=True):
        new = {
            "sc-primary": primary,
            "sc-secondary": secondary,
            "sc-accent": accent,
            "sc-success": success,
            "sc-warn": warn,
            "sc-danger": danger,
            "sc-bg-0": bg0,
            "sc-bg-1": bg1,
            "sc-text": text,
        }
        state.set_("colors", new)
        try:
            theme.inject_color_overrides(new)
            st.success("Colors applied — UI updated.")
        except Exception as exc:
            st.error(f"Failed to apply colors: {exc}")

    if st.button("Wow brown preset", use_container_width=True):
        preset = {
            "sc-primary": "#7c4a2a",
            "sc-secondary": "#a67c52",
            "sc-accent": "#d97706",
            "sc-success": "#386641",
            "sc-warn": "#b45309",
            "sc-danger": "#991b1b",
            "sc-bg-0": "#fbf7f1",
            "sc-bg-1": "#fffaf0",
            "sc-text": "#08131a",
        }
        state.set_("colors", preset)
        try:
            theme.inject_color_overrides(preset)
            st.success("Brown publication preset applied.")
        except Exception as exc:
            st.error(f"Failed to apply preset: {exc}")
