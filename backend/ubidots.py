"""
UbidotsService — Ubidots API proxy + HTML report generator
"""
import httpx
import json
from datetime import datetime


UBIDOTS_BASE = "https://industrial.api.ubidots.com"


class UbidotsService:

    # ──────────────────────────────────────────
    # Ubidots API methods
    # ──────────────────────────────────────────

    async def get_devices(
        self, token: str, page: int = 1, page_size: int = 50, search: str = ""
    ) -> dict:
        params: dict = {"page_size": page_size, "page": page}
        if search:
            params["label__icontains"] = search
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                f"{UBIDOTS_BASE}/api/v2.0/devices/",
                headers={"X-Auth-Token": token},
                params=params,
            )
            if r.status_code != 200:
                raise Exception(f"Ubidots error {r.status_code}: {r.text}")
            return r.json()

    async def get_variables(
        self,
        token: str,
        device_label: str,
        page: int = 1,
        page_size: int = 100,
        search: str = "",
    ) -> dict:
        params: dict = {"page_size": page_size, "page": page}
        if search:
            params["label__icontains"] = search
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                f"{UBIDOTS_BASE}/api/v2.0/devices/~{device_label}/variables/",
                headers={"X-Auth-Token": token},
                params=params,
            )
            if r.status_code != 200:
                raise Exception(f"Ubidots error {r.status_code}: {r.text}")
            return r.json()

    async def fetch_values_all_pages(
        self,
        token: str,
        device_label: str,
        var_label: str,
        start_ms: int,
        end_ms: int,
        tz_offset: float = -5,
    ) -> list:
        tz_ms = int(tz_offset * 3600000)
        url = f"{UBIDOTS_BASE}/api/v1.6/devices/{device_label}/{var_label}/values/"
        params = {"start": start_ms, "end": end_ms, "page_size": 10000}
        all_points = []

        async with httpx.AsyncClient(timeout=60) as client:
            while url:
                r = await client.get(
                    url,
                    headers={"X-Auth-Token": token},
                    params=params,
                )
                if r.status_code != 200:
                    raise Exception(f"Ubidots error {r.status_code}: {r.text}")
                data = r.json()
                for pt in data.get("results", []):
                    ts_ms = pt.get("timestamp", 0)
                    adjusted_ms = ts_ms + tz_ms
                    dt = datetime.utcfromtimestamp(adjusted_ms / 1000)
                    ts_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
                    all_points.append({"timestamp": ts_str, "value": pt.get("value", 0)})
                next_url = data.get("next")
                url = next_url if next_url else None
                params = {}  # params already embedded in next URL

        return all_points

    # ──────────────────────────────────────────
    # HTML report generator
    # ──────────────────────────────────────────

    def generate_html(self, config: dict, components: list, all_data: dict) -> str:
        title = config.get("titulo", "Informe Operativo")
        subtitle = config.get("subtitulo", "")
        author = config.get("autor", "")
        fecha_inicio = config.get("fecha_inicio", "")
        fecha_fin = config.get("fecha_fin", "")
        tz_offset = config.get("tz_offset", -5)
        dosis_objetivo = float(config.get("dosis_objetivo", 0.6))
        total_maiz_cfg = float(config.get("total_maiz", 0))
        date_str = datetime.now().strftime("%d de %B de %Y")

        # ── Build R data object ──
        report_data: dict = {}
        report_components: dict = {
            "chart_series": [],
            "bars_series": [],
            "pie_series": [],
            "table_periods": {},
            "kpi_rows": [],
        }
        report_meta: dict = {
            "dosis_esperada": dosis_objetivo,
            "total_maiz": total_maiz_cfg,
            "total_inhimold_excel": 0,
            "pump_excel_totals": {},
        }
        report_historical: list = []

        for comp in components:
            ctype = comp.get("type")

            if ctype == "kpi_row":
                comp_id = comp.get("id", f"kpi{len(report_components['kpi_rows'])}")
                row_cards = []
                for i, card in enumerate(comp.get("cards", [])):
                    key = card.get("data_key")
                    if key and key in all_data:
                        report_data[key] = all_data[key]
                    row_cards.append({
                        "data_key": key or "",
                        "label": card.get("label", ""),
                        "unit": card.get("unit", ""),
                        "color": card.get("color", "#3b82f6"),
                        "agg": card.get("agg", "sum"),
                        "card_id": f"kpi_{comp_id}_{i}",
                    })
                report_components["kpi_rows"].append({"comp_id": comp_id, "cards": row_cards})

            elif ctype == "line_chart":
                for s in comp.get("series", []):
                    key = s.get("data_key")
                    if key and key in all_data:
                        report_data[key] = all_data[key]
                        report_components["chart_series"].append({
                            "var": key,
                            "label": s.get("label", key),
                            "color": s.get("color", "#3b82f6"),
                            "unit": s.get("unit", ""),
                            "agg": s.get("agg", "sum"),
                        })

            elif ctype == "bar_chart":
                for s in comp.get("series", []):
                    key = s.get("data_key")
                    if key and key in all_data:
                        report_data[key] = all_data[key]
                        report_components["bars_series"].append({
                            "var": key,
                            "label": s.get("label", key),
                            "color": s.get("color", "#3b82f6"),
                            "unit": s.get("unit", ""),
                        })

            elif ctype == "pie_chart":
                for s in comp.get("series", []):
                    key = s.get("data_key")
                    if key and key in all_data:
                        report_data[key] = all_data[key]
                        report_components["pie_series"].append({
                            "var": key,
                            "label": s.get("label", key),
                            "color": s.get("color", "#3b82f6"),
                            "unit": s.get("unit", ""),
                        })

            elif ctype == "data_table":
                for period_name, period_series in comp.get("periods", {}).items():
                    period_list = []
                    for s in period_series:
                        key = s.get("data_key")
                        if key and key in all_data:
                            report_data[key] = all_data[key]
                            period_list.append({
                                "var": key,
                                "label": s.get("label", key),
                                "unit": s.get("unit", ""),
                            })
                    if period_list:
                        report_components["table_periods"][period_name] = period_list

            elif ctype == "historical":
                report_historical = comp.get("rows", [])

            elif ctype == "raw_data":
                # raw_data uses all data already loaded
                pass

        # ── Compute pump totals for meta ──
        for s in report_components.get("bars_series", []):
            key = s["var"]
            pts = report_data.get(key, [])
            total = sum(p.get("value", 0) for p in pts)
            report_meta["pump_excel_totals"][s["label"]] = round(total, 1)

        total_inhimold = sum(report_meta["pump_excel_totals"].values())
        report_meta["total_inhimold_excel"] = round(total_inhimold, 1)

        R_json = json.dumps(
            {
                "data": report_data,
                "components": report_components,
                "historical": report_historical,
                "meta": report_meta,
            },
            ensure_ascii=False,
        )

        # ── Build section HTML ──
        sections_html = self._build_sections(components, config)

        # ── Assemble final HTML ──
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — {subtitle}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ background-color: #f8fafc; color: #1e293b; padding: 40px 0; font-family: 'Inter', sans-serif; }}
        .hoja {{ background: white; max-width: 1200px; margin: 0 auto; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); min-height: 100vh; display: flex; flex-direction: column; }}
        .ctrl {{ background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 8px; font-size: 12px; font-weight: 600; color: #475569; outline: none; cursor: pointer; }}
        .ctrl:hover {{ border-color: #94a3b8; background: #e2e8f0; }}
        .tbl th {{ background: #f1f5f9; position: sticky; top: 0; z-index: 10; font-size: 11px; padding: 10px; text-align: center; color: #64748b; font-weight: 700; border-bottom: 1px solid #e2e8f0; }}
        .tbl td {{ font-size: 11px; padding: 6px 10px; border-bottom: 1px solid #f1f5f9; color: #64748b; font-family: 'JetBrains Mono', monospace; text-align: center; }}
        .tbl tr:hover td {{ background: #f8fafc; color: #0f172a; }}
        .tbl tr.current td {{ background: #dbeafe; font-weight: 700; color: #1e40af; }}
        .tbl tfoot td {{ background: #f1f5f9; font-weight: 700; color: #1e293b; border-top: 2px solid #cbd5e1; }}
        .accordion {{ transition: max-height 0.4s ease; max-height: 0; overflow: hidden; }}
        .accordion.open {{ max-height: 600px; }}
        .section-title {{ font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 1rem; letter-spacing: 0.05em; }}
        .kpi {{ transition: transform 0.2s; }}
        .kpi:hover {{ transform: translateY(-2px); }}
        .maiz-input {{ background: transparent; border: none; border-bottom: 2px dashed #f59e0b; font-family: 'JetBrains Mono', monospace; font-size: 1.875rem; font-weight: 900; color: #b45309; text-align: center; width: 160px; outline: none; }}
        .maiz-input:focus {{ border-bottom-color: #d97706; }}
        @media print {{
            body {{ background-color: white !important; padding: 0 !important; }}
            .hoja {{ box-shadow: none !important; max-width: 100% !important; }}
            .sticky {{ position: static !important; }}
            #pdfBtn, #rawSection {{ display: none !important; }}
            .accordion {{ max-height: none !important; overflow: visible !important; }}
        }}
    </style>
</head>
<body>
<div class="hoja">
    <!-- HEADER -->
    <div class="px-10 pt-12 pb-6 border-b border-slate-100 flex justify-between items-start">
        <div>
            <p class="text-xs font-bold text-blue-600 uppercase tracking-widest mb-1">{subtitle}</p>
            <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">{title}</h1>
            <p class="text-sm text-slate-400 mt-2">Autor: <span class="text-slate-600 font-semibold">{author}</span> &nbsp;|&nbsp; {date_str}</p>
        </div>
        <img src="https://sento-logo-publico.s3.us-east-1.amazonaws.com/Sento+Logo+jul+2024+2.png" class="h-10 opacity-80" alt="Sento">
    </div>

    <!-- FILTER BAR -->
    <div class="bg-white/95 backdrop-blur border-y border-slate-200 px-10 py-3 sticky top-0 z-50 flex items-center gap-4 shadow-sm">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Rango:</span>
        <input type="date" id="dStart" class="ctrl" value="{fecha_inicio}" onchange="renderAll()">
        <span class="text-slate-300">—</span>
        <input type="date" id="dEnd" class="ctrl" value="{fecha_fin}" onchange="renderAll()">
        <div class="flex-grow"></div>
        <button id="pdfBtn" onclick="window.print()" style="display:flex;align-items:center;gap:8px;padding:7px 18px;background:#2563eb;color:white;font-size:12px;font-weight:700;border:none;border-radius:8px;cursor:pointer;box-shadow:0 2px 6px rgba(37,99,235,0.3)"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>Descargar PDF</button>
    </div>

    <!-- REPORT BODY -->
    <div class="px-10 py-8 bg-white flex-grow" id="reportBody">
        {sections_html}
    </div>

    <div class="bg-white border-t border-slate-100 text-slate-400 text-[10px] text-center py-6">
        Sento Analytics &nbsp;|&nbsp; Informe generado automáticamente
    </div>
</div>

<script>
var R = {R_json};
var DATA = R.data;
var C = R.components;
var HIST = R.historical;
var META = R.meta;

// Parse timestamps to Date objects
Object.keys(DATA).forEach(function(k) {{
    DATA[k].forEach(function(d) {{ d.dt = new Date(d.timestamp); }});
}});

var MS = {{'1h':3600000,'2h':7200000,'6h':21600000,'12h':43200000,'1d':86400000}};

function range() {{
    var s = new Date(document.getElementById('dStart').value);
    var e = new Date(document.getElementById('dEnd').value);
    e.setHours(23, 59, 59, 999);
    return {{s: s, e: e}};
}}

function filt(pts) {{
    var r = range();
    return (pts || []).filter(function(d) {{ return d.dt >= r.s && d.dt <= r.e; }});
}}

function agg(arr, m) {{
    if (!arr.length) return 0;
    if (m === 'sum') return arr.reduce(function(a, b) {{ return a + b; }}, 0);
    if (m === 'max') return Math.max.apply(null, arr);
    if (m === 'min') return Math.min.apply(null, arr);
    return arr.reduce(function(a, b) {{ return a + b; }}, 0) / arr.length;
}}

function toggleRaw() {{
    var b = document.getElementById('rawBox');
    var a = document.getElementById('rawArrow');
    if (b.classList.contains('open')) {{
        b.classList.remove('open');
        a.style.transform = 'rotate(0deg)';
    }} else {{
        b.classList.add('open');
        a.style.transform = 'rotate(180deg)';
    }}
}}

function fmt(v, d) {{
    return Number(v).toLocaleString('es-GT', {{minimumFractionDigits: d || 0, maximumFractionDigits: d || 0}});
}}

function getPumpTotals() {{
    var series = C.bars_series || [];
    var totals = {{}};
    var grand = 0;
    series.forEach(function(s) {{
        var pts = filt(DATA[s.var] || []);
        var sum = pts.reduce(function(a, d) {{ return a + d.value; }}, 0);
        totals[s.label] = sum;
        grand += sum;
    }});
    return {{pumps: totals, total: grand, series: series}};
}}

function recalcDosis() {{
    var pt = getPumpTotals();
    var totalInhimold = pt.total;
    var maizEl = document.getElementById('inputMaiz');
    var maiz = maizEl ? (parseFloat(maizEl.value) || 0) : (META.total_maiz || 0);
    var dosis = maiz > 0 ? totalInhimold / maiz : 0;
    var esperada = META.dosis_esperada || 0;
    var pct = esperada > 0 ? (dosis / esperada * 100) : 0;

    var kiEl = document.getElementById('kpiInhimold');
    if (kiEl) kiEl.innerText = fmt(totalInhimold, 1);

    var dv = document.getElementById('dosisVal');
    if (dv) dv.innerText = dosis.toFixed(4);

    var dp = document.getElementById('dosisPct');
    if (dp) dp.innerText = pct.toFixed(1) + '%';

    var card = document.getElementById('dosisCard');
    var dot = document.getElementById('dosisDot');
    var bg = document.getElementById('dosisBg');
    var val = document.getElementById('dosisVal');

    if (card && esperada > 0) {{
        var diff = Math.abs(pct - 100);
        if (diff <= 5) {{
            card.className = 'kpi p-5 rounded-xl border border-green-200/60 text-center relative overflow-hidden bg-gradient-to-br from-green-50 to-green-100/50';
            if (dot) dot.className = 'w-3 h-3 rounded-full bg-green-500 shadow-lg shadow-green-500/50';
            if (bg) bg.className = 'absolute inset-0 opacity-10 bg-green-500';
            if (val) val.className = 'text-3xl font-black text-green-600 relative z-10';
        }} else if (diff <= 15) {{
            card.className = 'kpi p-5 rounded-xl border border-yellow-200/60 text-center relative overflow-hidden bg-gradient-to-br from-yellow-50 to-yellow-100/50';
            if (dot) dot.className = 'w-3 h-3 rounded-full bg-yellow-400';
            if (bg) bg.className = 'absolute inset-0 opacity-10 bg-yellow-400';
            if (val) val.className = 'text-3xl font-black text-yellow-600 relative z-10';
        }} else {{
            card.className = 'kpi p-5 rounded-xl border border-red-200/60 text-center relative overflow-hidden bg-gradient-to-br from-red-50 to-red-100/50';
            if (dot) dot.className = 'w-3 h-3 rounded-full bg-red-500';
            if (bg) bg.className = 'absolute inset-0 opacity-10 bg-red-500';
            if (val) val.className = 'text-3xl font-black text-red-600 relative z-10';
        }}
    }}

    // Summary table
    var sb = document.getElementById('summaryBody');
    if (sb) {{
        var html = '';
        var colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];
        var idx = 0;
        Object.keys(pt.pumps).forEach(function(k) {{
            html += '<tr><td class="py-2 text-sm" style="color:' + colors[idx % 6] + '">' + k + ' (L)</td>'
                + '<td class="py-2 text-sm text-right font-mono font-bold text-slate-800">' + fmt(pt.pumps[k], 1) + '</td></tr>';
            idx++;
        }});
        html += '<tr class="border-t border-slate-200"><td class="py-2 text-sm font-bold text-slate-700">Total Inhimold (L)</td>'
            + '<td class="py-2 text-sm text-right font-mono font-black text-blue-700">' + fmt(totalInhimold, 1) + '</td></tr>';
        html += '<tr><td class="py-2 text-sm text-slate-500">Ma\u00edz (Ton)</td>'
            + '<td class="py-2 text-sm text-right font-mono text-slate-700">' + fmt(maiz, 0) + '</td></tr>';
        html += '<tr><td class="py-2 text-sm text-slate-500">Dosis Aplicada (L/Ton)</td>'
            + '<td class="py-2 text-sm text-right font-mono font-bold text-slate-800">' + dosis.toFixed(4) + '</td></tr>';
        html += '<tr><td class="py-2 text-sm text-slate-500">Dosis Objetivo (L/Ton)</td>'
            + '<td class="py-2 text-sm text-right font-mono text-slate-700">' + esperada.toFixed(2) + '</td></tr>';
        sb.innerHTML = html;
    }}

    // Pump cards
    var pc = document.getElementById('pumpCards');
    if (pc) {{
        var phtml = '<div class="grid gap-4 mb-4" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">';
        var pcolors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];
        var pi = 0;
        Object.keys(pt.pumps).forEach(function(k) {{
            var c = pcolors[pi % pcolors.length];
            phtml += '<div class="kpi p-4 rounded-xl border text-center" style="border-color:' + c + '22;background:linear-gradient(135deg,' + c + '08,' + c + '15)">'
                + '<p class="text-[10px] font-bold uppercase tracking-wider" style="color:' + c + '">' + k + '</p>'
                + '<p class="text-2xl font-black mt-1" style="color:' + c + '">' + fmt(pt.pumps[k], 1) + '</p>'
                + '<p class="text-xs mt-1" style="color:' + c + '88">Litros</p>'
                + '</div>';
            pi++;
        }});
        phtml += '</div>';
        pc.innerHTML = phtml;
    }}
}}

function renderChart() {{
    var series = C.chart_series || [];
    if (!series.length) return;
    var op = document.getElementById('aggSel');
    var freq = document.getElementById('freqSel');
    var aggOp = op ? op.value : 'sum';
    var freqMs = MS[freq ? freq.value : '1h'] || 3600000;
    var units = [];
    series.forEach(function(s) {{
        var u = s.unit || '';
        if (units.indexOf(u) === -1) units.push(u);
    }});
    var dualAxis = units.length >= 2;
    var traces = [];
    series.forEach(function(s) {{
        var pts = filt(DATA[s.var] || []);
        var buckets = {{}};
        pts.forEach(function(d) {{
            var b = Math.floor(d.dt.getTime() / freqMs) * freqMs;
            if (!buckets[b]) buckets[b] = [];
            buckets[b].push(d.value);
        }});
        var xs = [], ys = [];
        Object.keys(buckets).sort(function(a, b) {{ return +a - +b; }}).forEach(function(b) {{
            xs.push(new Date(+b));
            ys.push(agg(buckets[b], aggOp));
        }});
        var axisIdx = units.indexOf(s.unit || '');
        traces.push({{
            x: xs, y: ys, name: s.label, type: 'scatter', mode: 'lines',
            line: {{color: s.color || undefined, width: 1.5}},
            yaxis: (dualAxis && axisIdx === 1) ? 'y2' : 'y'
        }});
    }});
    var layout = {{
        margin: {{t: 30, l: 55, r: 20, b: 30}},
        legend: {{orientation: 'h', y: 1.08, x: 0, xanchor: 'left'}},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {{family: 'Inter, sans-serif', color: '#64748b', size: 11}},
        xaxis: {{gridcolor: '#f1f5f9', anchor: 'y'}},
        yaxis: {{title: units[0] || '', gridcolor: '#f1f5f9', zerolinecolor: '#e2e8f0', domain: dualAxis ? [0, 0.46] : [0, 1]}}
    }};
    if (dualAxis) {{
        layout.yaxis2 = {{title: units[1] || '', domain: [0.54, 1], gridcolor: '#f1f5f9', zerolinecolor: '#e2e8f0'}};
    }}
    var el = document.getElementById('plotChart');
    if (el) Plotly.newPlot(el, traces, layout, {{responsive: true, displayModeBar: false}});
}}

function renderBars() {{
    var series = C.bars_series || [];
    if (!series.length) return;
    var traces = [];
    series.forEach(function(s) {{
        var pts = filt(DATA[s.var] || []);
        var xs = pts.map(function(d) {{ return d.timestamp.split('T')[0]; }});
        var ys = pts.map(function(d) {{ return d.value; }});
        traces.push({{x: xs, y: ys, name: s.label, type: 'bar', marker: {{color: s.color}}}});
    }});
    var el = document.getElementById('plotBars');
    if (el) Plotly.newPlot(el, traces, {{
        barmode: 'group',
        margin: {{t: 10, l: 50, r: 10, b: 30}},
        legend: {{orientation: 'h', y: 1.1, x: 0, xanchor: 'left'}},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {{family: 'Inter, sans-serif', color: '#64748b', size: 11}},
        yaxis: {{gridcolor: '#f1f5f9', zerolinecolor: '#e2e8f0'}},
        xaxis: {{gridcolor: '#f1f5f9'}}
    }}, {{responsive: true, displayModeBar: false}});
}}

function renderPie() {{
    var series = C.pie_series || [];
    if (!series.length) return;
    var labels = [], values = [], colors = [];
    series.forEach(function(s) {{
        var pts = filt(DATA[s.var] || []);
        var total = pts.reduce(function(a, d) {{ return a + d.value; }}, 0);
        labels.push(s.label);
        values.push(total);
        colors.push(s.color);
    }});
    var el = document.getElementById('plotPie');
    if (el) Plotly.newPlot(el, [{{
        labels: labels, values: values, type: 'pie', hole: 0.6,
        marker: {{colors: colors}},
        textinfo: 'percent', hoverinfo: 'label+value'
    }}], {{
        margin: {{t: 10, l: 10, r: 10, b: 10}},
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: {{family: 'Inter, sans-serif', color: '#64748b', size: 11}},
        showlegend: true,
        legend: {{orientation: 'h', y: -0.1}}
    }}, {{responsive: true, displayModeBar: false}});
    var tb = document.getElementById('pieTable');
    if (!tb) return;
    var total = values.reduce(function(a, b) {{ return a + b; }}, 0);
    var html = '';
    labels.forEach(function(l, i) {{
        var pct = total > 0 ? (values[i] / total * 100) : 0;
        html += '<tr>'
            + '<td class="py-2 text-xs font-bold" style="color:' + colors[i] + '">' + l + '</td>'
            + '<td class="py-2 font-mono font-bold text-right text-slate-700">' + fmt(values[i], 1) + '</td>'
            + '<td class="py-2 font-mono text-right text-slate-500">' + pct.toFixed(1) + '%</td>'
            + '</tr>';
    }});
    tb.innerHTML = html;
}}

function renderDataTable() {{
    var period = document.getElementById('tablePeriod');
    var pname = period ? period.value : '';
    var periods = C.table_periods || {{}};
    if (!pname && Object.keys(periods).length) pname = Object.keys(periods)[0];
    var series = periods[pname] || [];
    if (!series.length) return;
    var pts_by_var = {{}};
    series.forEach(function(s) {{ pts_by_var[s.var] = filt(DATA[s.var] || []); }});
    var dates = {{}};
    series.forEach(function(s) {{ pts_by_var[s.var].forEach(function(d) {{ dates[d.timestamp] = 1; }}); }});
    var sorted = Object.keys(dates).sort();
    var hd = document.getElementById('dtHead');
    var bd = document.getElementById('dtBody');
    var ft = document.getElementById('dtFoot');
    if (!hd) return;
    hd.innerHTML = '<th>Fecha</th>' + series.map(function(s) {{
        return '<th>' + s.label + (s.unit ? ' (' + s.unit + ')' : '') + '</th>';
    }}).join('');
    var totals = series.map(function() {{ return 0; }});
    var rows = '';
    sorted.forEach(function(ts) {{
        var cells = '<td>' + ts.replace('T', ' ').substring(0, 16) + '</td>';
        series.forEach(function(s, i) {{
            var pt = pts_by_var[s.var].find(function(d) {{ return d.timestamp === ts; }});
            var v = pt ? pt.value : 0;
            totals[i] += v;
            cells += '<td>' + fmt(v, 2) + '</td>';
        }});
        rows += '<tr>' + cells + '</tr>';
    }});
    bd.innerHTML = rows;
    ft.innerHTML = '<td class="font-bold">Total</td>' + totals.map(function(t) {{
        return '<td>' + fmt(t, 1) + '</td>';
    }}).join('');
}}

function renderRaw() {{
    var allPts = [];
    Object.keys(DATA).forEach(function(k) {{
        filt(DATA[k] || []).forEach(function(d) {{
            allPts.push({{ts: d.timestamp, var: k, val: d.value}});
        }});
    }});
    allPts.sort(function(a, b) {{ return a.ts > b.ts ? 1 : -1; }});
    var countEl = document.getElementById('rawCount');
    if (countEl) countEl.innerText = '(' + allPts.length + ' puntos)';
    var rh = document.getElementById('rawHead');
    var rb = document.getElementById('rawBody');
    if (rh) rh.innerHTML = '<th>Timestamp</th><th>Variable</th><th>Valor</th>';
    if (rb) rb.innerHTML = allPts.map(function(p) {{
        return '<tr><td>' + p.ts + '</td><td>' + p.var + '</td><td>' + fmt(p.val, 3) + '</td></tr>';
    }}).join('');
}}

function renderHistorical() {{
    var hb = document.getElementById('histBody');
    if (!hb || !HIST.length) return;
    var currentShip = '{subtitle}';
    hb.innerHTML = HIST.map(function(r) {{
        var isCurrent = r.barco && currentShip.indexOf(r.barco) >= 0;
        return '<tr' + (isCurrent ? ' class="current"' : '') + '>'
            + '<td>' + (r.year || '') + '</td>'
            + '<td class="text-left">' + (r.barco || '') + '</td>'
            + '<td>' + fmt(r.inhimold || 0, 0) + '</td>'
            + '<td>' + fmt(r.maiz || 0, 0) + '</td>'
            + '<td class="font-bold">' + ((r.dosis || 0).toFixed(4)) + '</td>'
            + '<td>' + (r.dosis_esperada ? r.dosis_esperada.toFixed(2) : '\u2014') + '</td>'
            + '</tr>';
    }}).join('');
}}

function renderKpiRows() {{
    (C.kpi_rows || []).forEach(function(row) {{
        row.cards.forEach(function(card) {{
            var pts = filt(DATA[card.data_key] || []);
            var vals = pts.map(function(d) {{ return d.value; }});
            var v = agg(vals, card.agg);
            var el = document.getElementById(card.card_id);
            if (el) {{
                var dec = (card.agg === 'avg' || card.agg === 'min' || card.agg === 'max') ? 2 : 1;
                el.innerText = vals.length ? fmt(v, dec) : '\u2014';
            }}
            if (vals.length) {{
                var mn = Math.min.apply(null, vals);
                var mx = Math.max.apply(null, vals);
                var minEl = document.getElementById(card.card_id + '_min');
                var maxEl = document.getElementById(card.card_id + '_max');
                if (minEl) minEl.innerText = fmt(mn, 2);
                if (maxEl) maxEl.innerText = fmt(mx, 2);
            }}
        }});
    }});
}}

function renderAll() {{
    renderKpiRows();
    recalcDosis();
    renderChart();
    renderBars();
    renderPie();
    renderDataTable();
    renderRaw();
    renderHistorical();
}}

window.onload = function() {{ renderAll(); }};

window.addEventListener('beforeprint', function() {{
    document.querySelectorAll('.js-plotly-plot').forEach(function(el) {{
        Plotly.relayout(el, {{autosize: true}});
    }});
}});
window.addEventListener('afterprint', function() {{
    document.querySelectorAll('.js-plotly-plot').forEach(function(el) {{
        Plotly.relayout(el, {{autosize: true}});
    }});
}});
</script>
</body>
</html>"""

    # ──────────────────────────────────────────
    # Section builders
    # ──────────────────────────────────────────

    def _build_sections(self, components: list, config: dict) -> str:
        sections = []
        for comp in components:
            ctype = comp.get("type")
            if ctype == "kpi_row":
                sections.append(self._build_kpi_row(comp, config))
            elif ctype == "text_block":
                sections.append(self._build_text_block(comp))
            elif ctype == "line_chart":
                sections.append(self._build_line_chart(comp))
            elif ctype == "bar_chart":
                sections.append(self._build_bar_chart(comp))
            elif ctype == "pie_chart":
                sections.append(self._build_pie_chart(comp))
            elif ctype == "data_table":
                sections.append(self._build_data_table(comp))
            elif ctype == "summary":
                sections.append(self._build_summary(comp))
            elif ctype == "historical":
                sections.append(self._build_historical(comp))
            elif ctype == "raw_data":
                pass  # always added below
        sections.append(self._build_raw_data())
        return "\n".join(sections)

    def _build_kpi_row(self, comp: dict, config: dict) -> str:
        title = comp.get("title", "")
        cards = comp.get("cards", [])
        comp_id = comp.get("id", "kpi")
        title_html = f'<h4 class="section-title">{title}</h4>' if title else ""
        n = max(len(cards), 1)
        cols = min(n, 4)
        cards_html = ""
        for i, card in enumerate(cards):
            card_id = f"kpi_{comp_id}_{i}"
            color = card.get("color", "#3b82f6")
            label = card.get("label", "")
            unit = card.get("unit", "")
            cards_html += f"""
    <div class="p-4 bg-slate-50 rounded border border-slate-100 text-center">
        <p class="text-[10px] font-bold text-slate-400 uppercase">{label} ({unit})</p>
        <p class="text-2xl font-bold text-slate-800 mt-1" id="{card_id}">\u2014</p>
        <p class="text-xs text-slate-400 mt-1">Min: <span id="{card_id}_min">\u2014</span> | Max: <span id="{card_id}_max">\u2014</span></p>
    </div>"""
        return f"""
<div class="mb-8">
    {title_html}
    <div class="grid gap-5" style="grid-template-columns:repeat({cols},1fr)">
        {cards_html}
    </div>
</div>"""

    def _build_text_block(self, comp: dict) -> str:
        title = comp.get("title", "")
        text = comp.get("text", "")
        title_html = f'<h4 class="section-title">{title}</h4>' if title else ""
        return f"""
<div class="bg-slate-50 rounded-xl border border-slate-200 p-6 mb-8">
    {title_html}
    <p class="text-sm text-slate-600 leading-relaxed">{text}</p>
</div>
"""

    def _build_line_chart(self, comp: dict) -> str:
        title = comp.get("title", "Gr\u00e1fica de Flujo")
        desc = comp.get("description", "")
        desc_html = f'<p class="text-sm text-slate-500 mb-8 leading-relaxed">{desc}</p>' if desc else '<div class="mb-8"></div>'
        return f"""
<div class="border border-slate-200 rounded-xl p-1 mb-2 shadow-sm">
    <div class="flex justify-between items-center px-5 py-3 bg-slate-50 border-b border-slate-100 rounded-t-xl">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-wide">{title}</span>
        <div class="flex gap-3">
            <div class="flex items-center gap-1">
                <label class="text-[10px] uppercase font-bold text-slate-400">Op:</label>
                <select id="aggSel" class="ctrl bg-white" onchange="renderChart()">
                    <option value="sum" selected>Suma</option>
                    <option value="avg">Promedio</option>
                    <option value="max">M\u00e1x</option>
                    <option value="min">M\u00edn</option>
                </select>
            </div>
            <div class="flex items-center gap-1">
                <label class="text-[10px] uppercase font-bold text-slate-400">Muestreo:</label>
                <select id="freqSel" class="ctrl bg-white" onchange="renderChart()">
                    <option value="1h" selected>1 h</option>
                    <option value="2h">2 h</option>
                    <option value="6h">6 h</option>
                    <option value="12h">12 h</option>
                    <option value="1d">1 d\u00eda</option>
                </select>
            </div>
        </div>
    </div>
    <div style="height:380px" id="plotChart"></div>
</div>
{desc_html}
"""

    def _build_bar_chart(self, comp: dict) -> str:
        title = comp.get("title", "Consumo Diario por Bomba")
        desc = comp.get("description", "")
        desc_html = f'<p class="text-sm text-slate-500 mb-8 leading-relaxed">{desc}</p>' if desc else '<div class="mb-8"></div>'
        return f"""
<div class="border border-slate-200 rounded-xl p-5 mb-2 shadow-sm">
    <h4 class="section-title">{title}</h4>
    <div style="height:280px" id="plotBars"></div>
</div>
{desc_html}
"""

    def _build_pie_chart(self, comp: dict) -> str:
        title = comp.get("title", "Distribuci\u00f3n por Variable")
        desc = comp.get("description", "")
        desc_html = f'<p class="text-sm text-slate-500 mb-8 leading-relaxed">{desc}</p>' if desc else '<div class="mb-8"></div>'
        return f"""
<div class="grid grid-cols-3 gap-8 mb-2">
    <div class="col-span-1 border border-slate-200 rounded-xl p-3" style="height:320px">
        <div id="plotPie" style="width:100%;height:100%"></div>
    </div>
    <div class="col-span-2 border border-slate-200 rounded-xl p-5 flex flex-col" style="height:320px">
        <h4 class="section-title">{title}</h4>
        <div class="overflow-auto flex-grow">
            <table class="w-full tbl">
                <thead><tr><th>Variable</th><th>Total</th><th>%</th></tr></thead>
                <tbody id="pieTable"></tbody>
            </table>
        </div>
    </div>
</div>
{desc_html}
"""

    def _build_data_table(self, comp: dict) -> str:
        title = comp.get("title", "Tabla de Datos")
        periods = comp.get("periods", {})
        period_options = "".join(
            f'<option value="{p}">{p}</option>' for p in periods.keys()
        )
        return f"""
<div class="border border-slate-200 rounded-xl p-5 mb-8 shadow-sm">
    <div class="flex justify-between items-center mb-4">
        <h4 class="section-title mb-0">{title}</h4>
        <div class="flex items-center gap-1">
            <label class="text-[10px] uppercase font-bold text-slate-400">Periodo:</label>
            <select id="tablePeriod" class="ctrl bg-white" onchange="renderDataTable()">
                {period_options}
            </select>
        </div>
    </div>
    <div class="overflow-auto" style="max-height:420px">
        <table class="w-full tbl">
            <thead><tr id="dtHead"></tr></thead>
            <tbody id="dtBody"></tbody>
            <tfoot><tr id="dtFoot"></tr></tfoot>
        </table>
    </div>
</div>
"""

    def _build_summary(self, comp: dict) -> str:
        title = comp.get("title", "Resumen de Dosificaci\u00f3n")
        footer = comp.get("footer", "")
        footer_html = f'<p class="text-xs text-slate-400 mt-3">{footer}</p>' if footer else ""
        return f"""
<div class="bg-slate-50 rounded-xl border border-slate-200 p-6 mb-8">
    <h4 class="section-title">{title}</h4>
    <table class="w-full">
        <thead><tr>
            <th class="text-left text-xs font-bold text-slate-500 pb-2 border-b border-slate-200">Variable</th>
            <th class="text-right text-xs font-bold text-slate-500 pb-2 border-b border-slate-200">Total</th>
        </tr></thead>
        <tbody id="summaryBody"></tbody>
    </table>
    {footer_html}
</div>
"""

    def _build_historical(self, comp: dict) -> str:
        title = comp.get("title", "Hist\u00f3rico de Buques")
        return f"""
<div class="mb-8">
    <h4 class="section-title">{title}</h4>
    <div class="overflow-auto rounded-xl border border-slate-200" style="max-height:500px">
        <table class="w-full tbl">
            <thead><tr>
                <th>A\u00f1o</th>
                <th>Buque</th>
                <th>Inhimold (L)</th>
                <th>Ma\u00edz (Ton)</th>
                <th>Dosis (L/Ton)</th>
                <th>Dosis Obj.</th>
            </tr></thead>
            <tbody id="histBody"></tbody>
        </table>
    </div>
</div>
"""

    def _build_raw_data(self) -> str:
        return """
<div id="rawSection" class="border border-slate-200 rounded-xl overflow-hidden bg-white mb-8">
    <button onclick="toggleRaw()" class="w-full px-6 py-3 bg-slate-50 hover:bg-slate-100 flex justify-between items-center text-sm font-bold text-slate-600 transition-colors border-b border-slate-200">
        <span>Datos Crudos <span class="text-xs font-normal text-slate-400 ml-2" id="rawCount"></span></span>
        <span id="rawArrow" class="transition-transform text-slate-400" style="display:inline-block">&#9660;</span>
    </button>
    <div id="rawBox" class="accordion">
        <div class="overflow-auto" style="height:400px">
            <table class="w-full tbl">
                <thead><tr id="rawHead"></tr></thead>
                <tbody id="rawBody"></tbody>
            </table>
        </div>
    </div>
</div>
"""
