"""Export module — CSV / JSON / HTML report bundles."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from app.services.export import (
    export_markers_csv, export_embeddings_csv, export_pca_variance_csv,
    export_qc_summary_csv, export_cell_assignments_csv,
)
from streamlit_modules import state


def _build_html_report(results: dict) -> bytes:
    """Self-contained HTML report with embedded CSS."""
    qc = results.get("qc") or {}
    clusters = results.get("clusters") or {}
    pca = results.get("pca") or {}
    markers = results.get("markers") or {}
    ann = results.get("annotation")

    marker_rows = []
    for cname, ms in markers.items():
        for m in ms[:5]:
            marker_rows.append(
                f"<tr><td>{cname}</td><td>{m.get('gene','')}</td>"
                f"<td>{m.get('log_fc','')}</td><td>{m.get('p_value','')}</td></tr>"
            )

    ann_html = ""
    if ann is not None and len(ann):
        ann_rows = "".join(
            f"<tr><td>{r['cluster']}</td><td>{r['cell_type']}</td>"
            f"<td>{r['confidence']}</td><td>{r['n_cells']}</td></tr>"
            for _, r in ann.iterrows()
        )
        ann_html = f"""
        <h2>Cell-type annotation</h2>
        <table><thead><tr><th>Cluster</th><th>Type</th><th>Conf.</th><th>Cells</th></tr></thead>
        <tbody>{ann_rows}</tbody></table>
        """

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SingleCellX report</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #f8fafc; color: #0f172a;
          padding: 32px; max-width: 920px; margin: auto; }}
  h1 {{ background: linear-gradient(90deg, #7c3aed, #f472b6);
        -webkit-background-clip: text; color: transparent; }}
  h2 {{ color: #0ea5e9; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 8px; border: 1px solid #cbd5e1; text-align: left; }}
  th {{ background: rgba(14,165,233,0.12); }}
  .meta {{ color: #475569; font-size: 0.9rem; }}
  .card {{ background: rgba(248,250,252,0.95); padding: 16px; border-radius: 12px;
           border: 1px solid #cbd5e1; margin: 12px 0; }}
</style></head>
<body>
  <h1>🧬 SingleCellX analysis report</h1>
  <p class="meta">Generated {datetime.utcnow().isoformat()}Z</p>

  <h2>Quality control</h2>
  <div class="card"><pre>{json.dumps({k:v for k,v in qc.items() if not k.startswith('_')}, indent=2)}</pre></div>

  <h2>Clustering</h2>
  <div class="card">
    Clusters: <b>{clusters.get('n_clusters','—')}</b><br>
    Silhouette: <b>{clusters.get('silhouette','—')}</b><br>
    Inertia: <b>{clusters.get('inertia','—')}</b>
  </div>

  <h2>PCA</h2>
  <div class="card">Components: {pca.get('n_components','—')}</div>

  {ann_html}

  <h2>Top markers (5 / cluster)</h2>
  <table><thead><tr><th>Cluster</th><th>Gene</th><th>log2 FC</th><th>p</th></tr></thead>
  <tbody>{''.join(marker_rows)}</tbody></table>

  <p class="meta">SingleCellX v3.0 — modular Streamlit pipeline.</p>
</body></html>"""
    return html.encode()


def _strip_private(d):
    """Drop session-only `_xxx` keys for JSON export."""
    if isinstance(d, dict):
        return {k: _strip_private(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [_strip_private(x) for x in d]
    if isinstance(d, np.ndarray):
        return d.tolist()
    return d


def render() -> None:
    st.subheader("📤 Export & Reports")

    qc = state.get("qc")
    clusters = state.get("clusters")
    if qc is None and clusters is None:
        st.warning("Nothing to export yet — run the pipeline first.")
        return

    # Bundle results
    bundle = {
        "qc": qc, "pca": state.get("pca"), "umap": state.get("umap"),
        "tsne": state.get("tsne"), "clusters": clusters,
        "markers": state.get("markers"), "annotation": state.get("annotation"),
        "cycle_phases": (state.get("cycle_phases").tolist()
                         if state.get("cycle_phases") is not None else None),
        "trajectory": state.get("trajectory"),
        "params": state.get("params"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    clean = _strip_private(bundle)
    if isinstance(clean.get("annotation"), pd.DataFrame):
        clean["annotation"] = clean["annotation"].to_dict(orient="records")

    st.markdown("### Quick downloads")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if state.get("markers"):
            buf = io.StringIO()
            export_markers_csv(state.get("markers"), buf)
            st.download_button("📋 Markers CSV", data=buf.getvalue(),
                               file_name="markers.csv", mime="text/csv",
                               use_container_width=True)

    with c2:
        st.download_button("💾 Full JSON",
                           data=json.dumps(clean, indent=2, default=str),
                           file_name="singlecellx_results.json",
                           mime="application/json",
                           use_container_width=True)

    with c3:
        st.download_button("📄 HTML report",
                           data=_build_html_report(bundle),
                           file_name="singlecellx_report.html",
                           mime="text/html",
                           use_container_width=True)

    with c4:
        if qc:
            buf = io.StringIO()
            export_qc_summary_csv({k: v for k, v in qc.items()
                                   if not k.startswith("_")}, buf)
            st.download_button("📊 QC summary CSV",
                               data=buf.getvalue(),
                               file_name="qc_summary.csv", mime="text/csv",
                               use_container_width=True)

    st.divider()
    st.markdown("### Coordinates & assignments")

    c1, c2, c3 = st.columns(3)
    umap = state.get("umap")
    if umap is not None and clusters is not None:
        with c1:
            buf = io.StringIO()
            cell_ids = list(qc["_counts"].index)
            export_embeddings_csv("UMAP", umap["coords"], cell_ids,
                                  clusters["labels"], buf)
            st.download_button("UMAP embeddings",
                               data=buf.getvalue(),
                               file_name="umap_embeddings.csv",
                               mime="text/csv", use_container_width=True)

    pca = state.get("pca")
    if pca is not None:
        with c2:
            buf = io.StringIO()
            export_pca_variance_csv(pca["variance_ratio"],
                                    pca["cumulative_variance"], buf)
            st.download_button("PCA variance",
                               data=buf.getvalue(),
                               file_name="pca_variance.csv", mime="text/csv",
                               use_container_width=True)

    if clusters is not None:
        with c3:
            buf = io.StringIO()
            cell_ids = list(qc["_counts"].index)
            export_cell_assignments_csv(cell_ids, clusters["labels"], buf)
            st.download_button("Cluster assignments",
                               data=buf.getvalue(),
                               file_name="cluster_assignments.csv",
                               mime="text/csv", use_container_width=True)

    st.divider()
    st.markdown("### AnnData (.h5ad) export")
    st.caption(
        "Bundles counts, metadata, embeddings and parameters into a single "
        "AnnData file — the standard format used by scanpy and scvi-tools."
    )
    if qc is not None and st.button("🧪 Export AnnData (.h5ad)",
                                    use_container_width=True):
        try:
            import tempfile, os
            from app.services.anndata_io import assemble_anndata_from_results
            adata = assemble_anndata_from_results(
                qc=qc, pca=state.get("pca"),
                umap=state.get("umap"), tsne=state.get("tsne"),
                clusters=clusters,
                annotation=state.get("annotation"),
                cycle_phases=state.get("cycle_phases"),
                trajectory=state.get("trajectory"),
                params=state.get("params"),
            )
            with tempfile.NamedTemporaryFile(suffix=".h5ad",
                                             delete=False) as tmp:
                adata.write_h5ad(tmp.name)
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                payload = f.read()
            os.unlink(tmp_path)
            st.download_button("⬇️ Download .h5ad",
                               data=payload,
                               file_name="singlecellx_results.h5ad",
                               mime="application/octet-stream",
                               use_container_width=True)
        except Exception as exc:
            st.error(f"Failed to build AnnData: {exc}")

    st.divider()
    st.markdown("### Bundle everything")
    if st.button("📦 Build complete ZIP bundle", use_container_width=True):
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("results.json",
                        json.dumps(clean, indent=2, default=str))
            zf.writestr("report.html",
                        _build_html_report(bundle).decode())
            if state.get("markers"):
                buf = io.StringIO()
                export_markers_csv(state.get("markers"), buf)
                zf.writestr("markers.csv", buf.getvalue())
            if qc:
                buf = io.StringIO()
                export_qc_summary_csv({k: v for k, v in qc.items()
                                       if not k.startswith("_")}, buf)
                zf.writestr("qc_summary.csv", buf.getvalue())
            if clusters:
                buf = io.StringIO()
                cell_ids = list(qc["_counts"].index)
                export_cell_assignments_csv(cell_ids, clusters["labels"], buf)
                zf.writestr("cluster_assignments.csv", buf.getvalue())
        st.download_button("⬇️ Download bundle",
                           data=z.getvalue(),
                           file_name="singlecellx_bundle.zip",
                           mime="application/zip",
                           use_container_width=True)
