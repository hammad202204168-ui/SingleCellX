/* ============================================================
   Chart helpers (Plotly)
   ------------------------------------------------------------
   Shared dark theme + cluster palette. Five chart functions:
   - renderScatter2D (UMAP/t-SNE/PCA embeddings, colored by cluster)
   - renderClusterBar  (cluster size distribution)
   - renderVariance    (PCA cumulative variance)
   - renderVolcano     (marker gene significance)
   - renderExprViolin  (expression distribution per cluster)
   ============================================================ */

const CLUSTER_COLORS = [
  '#c8ff3a', '#4cf2ff', '#ff6079', '#ffb74c', '#b46aff',
  '#6fe7a3', '#ff8ec7', '#7fd5ff', '#ffd95c', '#d3ff9e',
];

const DARK_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family: 'Inter Tight, system-ui, sans-serif', color: '#97a3b8', size: 12 },
  margin: { l: 60, r: 30, t: 30, b: 50 },
  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)', linecolor: 'rgba(255,255,255,0.15)', tickfont: { color: '#5d6a82' } },
  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zerolinecolor: 'rgba(255,255,255,0.1)', linecolor: 'rgba(255,255,255,0.15)', tickfont: { color: '#5d6a82' } },
  legend: { font: { color: '#e7ecf3', size: 11 }, bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(255,255,255,0.1)', borderwidth: 1 },
  hoverlabel: { bgcolor: '#111728', bordercolor: '#c8ff3a', font: { color: '#e7ecf3', family: 'JetBrains Mono, monospace' } },
};

const CONFIG = { displayModeBar: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'], responsive: true };

/* ---------- 2D embedding scatter ---------- */
function renderScatter2D(containerId, coords, labels, title, xLabel = 'X', yLabel = 'Y') {
  const traces = {};
  for (let i = 0; i < coords.length; i++) {
    const c = labels[i];
    if (!traces[c]) {
      traces[c] = {
        x: [], y: [],
        mode: 'markers',
        type: 'scattergl',
        name: `Cluster ${c}`,
        marker: {
          size: 6,
          color: CLUSTER_COLORS[c % CLUSTER_COLORS.length],
          opacity: 0.8,
          line: { width: 0.5, color: 'rgba(255,255,255,0.2)' },
        },
        hovertemplate: `<b>Cell #%{pointNumber}</b><br>${xLabel}: %{x:.2f}<br>${yLabel}: %{y:.2f}<extra>Cluster ${c}</extra>`,
      };
    }
    traces[c].x.push(coords[i][0]);
    traces[c].y.push(coords[i][1]);
  }

  const layout = {
    ...DARK_LAYOUT,
    title: title ? { text: title, font: { color: '#e7ecf3', size: 14 } } : undefined,
    xaxis: { ...DARK_LAYOUT.xaxis, title: { text: xLabel, font: { color: '#97a3b8' } } },
    yaxis: { ...DARK_LAYOUT.yaxis, title: { text: yLabel, font: { color: '#97a3b8' } } },
    height: 500,
  };

  Plotly.newPlot(containerId, Object.values(traces), layout, CONFIG);
}

/* ---------- Cluster size distribution ---------- */
function renderClusterBar(containerId, distribution) {
  const entries = Object.entries(distribution).map(([k, v]) => [parseInt(k), v]).sort((a, b) => a[0] - b[0]);
  const labels  = entries.map(([k]) => `Cluster ${k}`);
  const values  = entries.map(([, v]) => v);
  const colors  = entries.map(([k]) => CLUSTER_COLORS[k % CLUSTER_COLORS.length]);
  const total   = values.reduce((s, x) => s + x, 0);
  const pcts    = values.map(v => ((v / total) * 100).toFixed(1) + '%');

  const trace = {
    type: 'bar',
    x: labels,
    y: values,
    text: pcts,
    textposition: 'outside',
    textfont: { color: '#e7ecf3', family: 'JetBrains Mono, monospace', size: 11 },
    marker: { color: colors, line: { width: 0, color: 'transparent' } },
    hovertemplate: '<b>%{x}</b><br>Cells: %{y}<br>%{text}<extra></extra>',
  };

  const layout = {
    ...DARK_LAYOUT,
    height: 360,
    yaxis: { ...DARK_LAYOUT.yaxis, title: { text: 'Cells', font: { color: '#97a3b8' } } },
    showlegend: false,
    bargap: 0.35,
  };

  Plotly.newPlot(containerId, [trace], layout, CONFIG);
}

/* ---------- PCA cumulative variance ---------- */
function renderVariance(containerId, cumulative, variance) {
  const n = cumulative.length;
  const x = Array.from({ length: n }, (_, i) => i + 1);

  const bars = {
    type: 'bar',
    x, y: variance.map(v => v * 100),
    name: 'Per-PC variance',
    marker: { color: 'rgba(76, 242, 255, 0.4)' },
    hovertemplate: 'PC%{x}<br>%{y:.2f}%<extra></extra>',
  };
  const line = {
    type: 'scatter', mode: 'lines+markers',
    x, y: cumulative.map(v => v * 100),
    name: 'Cumulative',
    line: { color: '#c8ff3a', width: 2.5 },
    marker: { size: 6, color: '#c8ff3a' },
    yaxis: 'y2',
    hovertemplate: 'PC%{x}<br>Cumulative: %{y:.1f}%<extra></extra>',
  };

  const layout = {
    ...DARK_LAYOUT,
    height: 360,
    xaxis: { ...DARK_LAYOUT.xaxis, title: { text: 'Principal Component', font: { color: '#97a3b8' } } },
    yaxis: { ...DARK_LAYOUT.yaxis, title: { text: 'Variance %', font: { color: '#97a3b8' } } },
    yaxis2: {
      title: { text: 'Cumulative %', font: { color: '#c8ff3a' } },
      tickfont: { color: '#c8ff3a' },
      overlaying: 'y', side: 'right',
      gridcolor: 'transparent', range: [0, 105],
    },
    legend: { ...DARK_LAYOUT.legend, orientation: 'h', x: 0, y: 1.12 },
  };

  Plotly.newPlot(containerId, [bars, line], layout, CONFIG);
}

/* ---------- Volcano plot of markers ---------- */
function renderVolcano(containerId, markers) {
  if (!markers || markers.length === 0) {
    document.getElementById(containerId).innerHTML = '<p class="text-dim text-sm">No markers to plot.</p>';
    return;
  }
  const x = markers.map(m => m.log_fc);
  const y = markers.map(m => -Math.log10(Math.max(m.p_value, 1e-300)));
  const labels = markers.map(m => m.gene);

  const trace = {
    type: 'scattergl',
    mode: 'markers+text',
    x, y, text: labels,
    textposition: 'top center',
    textfont: { size: 9, color: '#97a3b8', family: 'JetBrains Mono, monospace' },
    marker: {
      size: 11, color: x, colorscale: [[0, '#4cf2ff'], [0.5, '#ffb74c'], [1, '#c8ff3a']],
      line: { color: 'rgba(255,255,255,0.2)', width: 0.5 },
      showscale: true,
      colorbar: { title: { text: 'log2 FC', font: { color: '#97a3b8' } }, tickfont: { color: '#5d6a82' } },
    },
    hovertemplate: '<b>%{text}</b><br>log2 FC: %{x:.2f}<br>-log10(p): %{y:.2f}<extra></extra>',
  };

  const layout = {
    ...DARK_LAYOUT,
    height: 420,
    xaxis: { ...DARK_LAYOUT.xaxis, title: { text: 'log2 Fold Change', font: { color: '#97a3b8' } } },
    yaxis: { ...DARK_LAYOUT.yaxis, title: { text: '-log10(p-value)', font: { color: '#97a3b8' } } },
    shapes: [
      { type: 'line', x0: 0.5, x1: 0.5, y0: 0, y1: 1, yref: 'paper', line: { color: 'rgba(200,255,58,0.3)', dash: 'dash', width: 1 } },
      { type: 'line', x0: -10, x1: 10, y0: -Math.log10(0.05), y1: -Math.log10(0.05), line: { color: 'rgba(255,96,121,0.4)', dash: 'dash', width: 1 } },
    ],
    showlegend: false,
  };

  Plotly.newPlot(containerId, [trace], layout, CONFIG);
}

/* ============================================================
   Charts namespace — adapts raw API result objects to the
   primitive chart renderers above.
   ============================================================ */
const Charts = {
  CLUSTER_COLORS,

  // Accept either raw arrays or PCA dict { variance_ratio, cumulative_variance }
  renderVariance(containerId, pca) {
    renderVariance(containerId, pca.cumulative_variance, pca.variance_ratio);
  },

  // Accept clusters dict { distribution }
  renderClusterBar(containerId, clusters) {
    renderClusterBar(containerId, clusters.distribution || {});
  },

  // Accept embedding dict { coords } and a labels array
  renderScatter2D(containerId, embed, labels, xLabel = 'X', yLabel = 'Y') {
    renderScatter2D(containerId, embed.coords || [], labels || [], '', xLabel, yLabel);
  },

  // Accept the markers dict { "Cluster_0": [...], "Cluster_1": [...] }
  // and flatten to a single volcano array
  renderVolcano(containerId, markersDict) {
    const flat = [];
    Object.entries(markersDict || {}).forEach(([cid, arr]) => {
      (arr || []).forEach(g => flat.push({
        gene: g.gene,
        log_fc: g.log_fc,
        p_value: Math.max(g.p_value, 1e-300),
        cluster: cid,
      }));
    });
    renderVolcano(containerId, flat);
  },
};
