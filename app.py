"""
Sento Analytics Builder — FastAPI backend
Proxy to Ubidots API + HTML report generator
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import httpx
import json
from typing import Any, Optional
from datetime import datetime, timezone, timedelta
import math

app = FastAPI(title="Sento Analytics Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UBIDOTS_BASE = "https://industrial.api.ubidots.com"

# ─────────────────────────────────────────────
# Ubidots proxy endpoints
# ─────────────────────────────────────────────

@app.get("/api/devices")
async def get_devices(token: str, page: int = 1, page_size: int = 100):
    """List devices using Ubidots v2.0 API."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{UBIDOTS_BASE}/api/v2.0/devices/",
            headers={"X-Auth-Token": token},
            params={"page_size": page_size, "page": page},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json()
        results = [
            {"label": d.get("label", ""), "name": d.get("name", d.get("label", "")), "id": d.get("id", "")}
            for d in data.get("results", [])
        ]
        return {"results": results, "count": data.get("count", len(results))}


@app.get("/api/variables")
async def get_variables(token: str, device_label: str, page_size: int = 200):
    """List variables for a device using Ubidots v2.0 API with ~ label prefix."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{UBIDOTS_BASE}/api/v2.0/devices/~{device_label}/variables/",
            headers={"X-Auth-Token": token},
            params={"page_size": page_size},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json()
        results = [
            {"label": v.get("label", ""), "name": v.get("name", v.get("label", "")), "id": v.get("id", "")}
            for v in data.get("results", [])
        ]
        return {"results": results, "count": data.get("count", len(results))}


class FetchDataRequest(BaseModel):
    token: str
    device_label: str
    var_label: str
    start_ms: int
    end_ms: int
    page_size: int = 10000


@app.post("/api/fetch_data")
async def fetch_data(req: FetchDataRequest):
    """Fetch raw values for a variable using v1.6 device/variable path (same as notebook)."""
    url = (
        f"{UBIDOTS_BASE}/api/v1.6/devices/{req.device_label}/{req.var_label}/values/"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            url,
            headers={"X-Auth-Token": req.token},
            params={"start": req.start_ms, "end": req.end_ms, "page_size": req.page_size},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


# ─────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    token: str
    config: dict  # report metadata
    components: list[dict]  # component definitions
    all_data: dict  # pre-fetched data keyed by "device_label::var_label"


@app.post("/api/generate")
async def generate_report(req: GenerateRequest):
    html = build_html(req.config, req.components, req.all_data)
    return {"html": html}


def build_html(config: dict, components: list[dict], all_data: dict) -> str:
    title = config.get("titulo", "Informe Operativo")
    subtitle = config.get("subtitulo", "")
    author = config.get("autor", "")
    fecha_inicio = config.get("fecha_inicio", "")
    fecha_fin = config.get("fecha_fin", "")
    tz_offset = config.get("tz_offset", -5)
    dosis_objetivo = float(config.get("dosis_objetivo", 0.6))
    date_str = datetime.now().strftime("%d de %B, %Y")

    # Build R (data object) for the report JS
    report_data: dict[str, list] = {}
    report_components: dict = {"chart_series": [], "bars_series": [], "pie_series": [], "table_periods": {}}
    report_meta: dict = {"dosis_esperada": dosis_objetivo, "pump_excel_totals": {}}
    report_historical: list = []

    # Process components to build data keys and component config
    for comp in components:
        ctype = comp.get("type")

        if ctype == "kpi_row":
            # KPI cards — each card references a daily var for total
            for card in comp.get("cards", []):
                key = card.get("data_key")
                if key and key in all_data:
                    report_data[key] = all_data[key]

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
                        period_list.append({"var": key, "label": s.get("label", key), "unit": s.get("unit", "")})
                if period_list:
                    report_components["table_periods"][period_name] = period_list

        elif ctype == "historical":
            report_historical = comp.get("rows", [])

    # Compute pump totals for meta
    for s in report_components.get("bars_series", []):
        key = s["var"]
        pts = report_data.get(key, [])
        total = sum(p.get("value", 0) for p in pts)
        report_meta["pump_excel_totals"][s["label"]] = round(total, 1)

    total_inhimold = sum(report_meta["pump_excel_totals"].values())
    report_meta["total_inhimold_excel"] = round(total_inhimold, 1)
    report_meta["total_maiz"] = float(config.get("total_maiz", 0))

    R_json = json.dumps({
        "data": report_data,
        "components": report_components,
        "historical": report_historical,
        "meta": report_meta,
    }, ensure_ascii=False)

    # ── Generate sections HTML ──
    sections_html = _build_sections(components, config)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
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
        .section-title {{ font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 1rem; }}
        .kpi {{ transition: transform 0.2s; }}
        .kpi:hover {{ transform: translateY(-2px); }}
        .maiz-input {{ background: transparent; border: none; border-bottom: 2px dashed #f59e0b; font-family: 'JetBrains Mono', monospace; font-size: 1.875rem; font-weight: 900; color: #b45309; text-align: center; width: 140px; outline: none; }}
        .maiz-input:focus {{ border-bottom-color: #d97706; }}
    </style>
</head>
<body>
<div class="hoja">
    <!-- HEADER -->
    <div class="px-10 pt-12 pb-6 border-b border-slate-100 flex justify-between items-start">
        <div>
            <p class="text-xs font-bold text-blue-600 uppercase tracking-widest mb-1">{subtitle}</p>
            <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">{title}</h1>
            <p class="text-sm text-slate-400 mt-2">Autor: <span class="text-slate-600 font-semibold">{author}</span> | {date_str}</p>
        </div>
        <img src="https://sento-logo-publico.s3.us-east-1.amazonaws.com/Sento+Logo+jul+2024+2.png" class="h-10 opacity-80">
    </div>

    <!-- FILTER BAR -->
    <div class="bg-white/95 backdrop-blur border-y border-slate-200 px-10 py-3 sticky top-0 z-50 flex items-center gap-4 shadow-sm">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Rango:</span>
        <input type="date" id="dStart" class="ctrl" value="{fecha_inicio}" onchange="renderAll()">
        <span class="text-slate-300">—</span>
        <input type="date" id="dEnd" class="ctrl" value="{fecha_fin}" onchange="renderAll()">
    </div>

    <div class="px-10 py-8 bg-white flex-grow" id="reportBody">
        {sections_html}
    </div>

    <div class="bg-white border-t border-slate-100 text-slate-400 text-[10px] text-center py-6">
        Sento Analytics | Informe generado automáticamente
    </div>
</div>

<script>
var R = {R_json};
var DATA = R.data;
var C = R.components;
var HIST = R.historical;
var META = R.meta;

Object.keys(DATA).forEach(function(k){{ DATA[k].forEach(function(d){{ d.dt = new Date(d.timestamp); }}); }});

var MS = {{'1h':3600000,'2h':7200000,'6h':21600000,'12h':43200000,'1d':86400000}};
function range(){{ var s=new Date(document.getElementById('dStart').value); var e=new Date(document.getElementById('dEnd').value); e.setHours(23,59,59); return {{s:s,e:e}}; }}
function filt(pts){{ var r=range(); return (pts||[]).filter(function(d){{return d.dt>=r.s && d.dt<=r.e;}}); }}
function agg(arr,m){{ if(!arr.length)return 0; if(m==='sum')return arr.reduce(function(a,b){{return a+b}},0); if(m==='max')return Math.max.apply(null,arr); if(m==='min')return Math.min.apply(null,arr); return arr.reduce(function(a,b){{return a+b}},0)/arr.length; }}
function toggleRaw(){{ var b=document.getElementById('rawBox'),a=document.getElementById('rawArrow'); if(b.classList.contains('open')){{b.classList.remove('open');a.style.transform='rotate(0)';}}else{{b.classList.add('open');a.style.transform='rotate(180deg)';}} }}
function fmt(v,d){{ return v.toLocaleString('es-GT',{{minimumFractionDigits:d||0,maximumFractionDigits:d||0}}); }}

function getPumpTotals(){{
    var series=C.bars_series||[]; var totals={{}}; var grand=0;
    series.forEach(function(s){{ var pts=filt(DATA[s.var]||[]); var sum=pts.reduce(function(a,d){{return a+d.value;}},0); totals[s.label]=sum; grand+=sum; }});
    return {{pumps:totals,total:grand,series:series}};
}}

function recalcDosis(){{
    var pt=getPumpTotals(); var totalInhimold=pt.total;
    var maizEl=document.getElementById('inputMaiz'); var maiz=maizEl?parseFloat(maizEl.value)||0:META.total_maiz||0;
    var dosis=maiz>0?totalInhimold/maiz:0; var esperada=META.dosis_esperada||0;
    var pct=esperada>0?(dosis/esperada*100):0;
    var kiEl=document.getElementById('kpiInhimold'); if(kiEl)kiEl.innerText=fmt(totalInhimold,1);
    var dv=document.getElementById('dosisVal'); if(dv)dv.innerText=dosis.toFixed(4);
    var dp=document.getElementById('dosisPct'); if(dp)dp.innerText=pct.toFixed(1)+'%';
    var card=document.getElementById('dosisCard'); var dot=document.getElementById('dosisDot'); var bg=document.getElementById('dosisBg'); var val=document.getElementById('dosisVal');
    if(card&&esperada>0){{
        var diff=Math.abs(pct-100);
        if(diff<=5){{ card.className='kpi p-5 rounded-xl border border-green-200/60 text-center relative overflow-hidden bg-gradient-to-br from-green-50 to-green-100/50'; if(dot)dot.className='w-3 h-3 rounded-full bg-green-500 shadow-lg shadow-green-500/50'; if(bg)bg.className='absolute inset-0 opacity-10 bg-green-500'; if(val)val.className='text-3xl font-black text-green-600 relative z-10'; }}
        else if(diff<=15){{ card.className='kpi p-5 rounded-xl border border-yellow-200/60 text-center relative overflow-hidden bg-gradient-to-br from-yellow-50 to-yellow-100/50'; if(dot)dot.className='w-3 h-3 rounded-full bg-yellow-400'; if(bg)bg.className='absolute inset-0 opacity-10 bg-yellow-400'; if(val)val.className='text-3xl font-black text-yellow-600 relative z-10'; }}
        else{{ card.className='kpi p-5 rounded-xl border border-red-200/60 text-center relative overflow-hidden bg-gradient-to-br from-red-50 to-red-100/50'; if(dot)dot.className='w-3 h-3 rounded-full bg-red-500'; if(bg)bg.className='absolute inset-0 opacity-10 bg-red-500'; if(val)val.className='text-3xl font-black text-red-600 relative z-10'; }}
    }}
    var sb=document.getElementById('summaryBody');
    if(sb){{
        var html=''; var colors=['#3b82f6','#8b5cf6','#10b981','#f59e0b']; var idx=0;
        Object.keys(pt.pumps).forEach(function(k){{ html+='<tr><td class="py-2 text-sm" style="color:'+colors[idx%4]+'">'+k+' (L)</td><td class="py-2 text-sm text-right font-mono font-bold text-slate-800">'+fmt(pt.pumps[k],1)+'</td></tr>'; idx++; }});
        html+='<tr><td class="py-2 text-sm font-bold text-slate-700">Total Inhimold (L)</td><td class="py-2 text-sm text-right font-mono font-black text-blue-700">'+fmt(totalInhimold,1)+'</td></tr>';
        html+='<tr><td class="py-2 text-sm text-slate-500">Maíz (Ton)</td><td class="py-2 text-sm text-right font-mono text-slate-700">'+fmt(maiz,0)+'</td></tr>';
        html+='<tr><td class="py-2 text-sm text-slate-500">Dosis Aplicada (L/Ton)</td><td class="py-2 text-sm text-right font-mono font-bold text-slate-800">'+dosis.toFixed(4)+'</td></tr>';
        html+='<tr><td class="py-2 text-sm text-slate-500">Dosis Objetivo (L/Ton)</td><td class="py-2 text-sm text-right font-mono text-slate-700">'+esperada.toFixed(2)+'</td></tr>';
        sb.innerHTML=html;
    }}
    var pc=document.getElementById('pumpCards');
    if(pc){{
        var phtml='<div class="grid gap-4 mb-4" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">';
        var pcolors=['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#06b6d4'];
        var pi=0;
        Object.keys(pt.pumps).forEach(function(k){{
            var c=pcolors[pi%pcolors.length];
            phtml+='<div class="kpi p-4 rounded-xl border text-center" style="border-color:'+c+'22;background:linear-gradient(135deg,'+c+'08,'+c+'15)">'
                +'<p class="text-[10px] font-bold uppercase tracking-wider" style="color:'+c+'">'+k+'</p>'
                +'<p class="text-2xl font-black mt-1" style="color:'+c+'">'+fmt(pt.pumps[k],1)+'</p>'
                +'<p class="text-xs mt-1" style="color:'+c+'88">Litros</p>'
                +'</div>';
            pi++;
        }});
        phtml+='</div>'; pc.innerHTML=phtml;
    }}
}}

function renderChart(){{
    var series=C.chart_series||[]; if(!series.length)return;
    var op=document.getElementById('aggSel'); var freq=document.getElementById('freqSel');
    var aggOp=op?op.value:'sum'; var freqMs=MS[freq?freq.value:'1h']||3600000;
    var traces=[];
    series.forEach(function(s){{
        var pts=filt(DATA[s.var]||[]);
        var buckets={{}}; pts.forEach(function(d){{ var b=Math.floor(d.dt.getTime()/freqMs)*freqMs; buckets[b]=(buckets[b]||[]); buckets[b].push(d.value); }});
        var xs=[],ys=[]; Object.keys(buckets).sort().forEach(function(b){{ xs.push(new Date(+b)); ys.push(agg(buckets[b],aggOp)); }});
        traces.push({{x:xs,y:ys,name:s.label,type:'scatter',mode:'lines+markers',line:{{color:s.color,width:2}},marker:{{size:4}}}});
    }});
    var el=document.getElementById('plotChart'); if(el)Plotly.newPlot(el,traces,{{margin:{{t:20,b:40,l:50,r:20}},legend:{{orientation:'h',y:-0.2}},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',yaxis:{{gridcolor:'#f1f5f9'}},xaxis:{{gridcolor:'#f1f5f9'}}}},{{responsive:true,displayModeBar:false}});
}}

function renderBars(){{
    var series=C.bars_series||[]; if(!series.length)return;
    var traces=[]; var r=range();
    series.forEach(function(s){{
        var pts=filt(DATA[s.var]||[]);
        var xs=pts.map(function(d){{return d.timestamp.split('T')[0];}});
        var ys=pts.map(function(d){{return d.value;}});
        traces.push({{x:xs,y:ys,name:s.label,type:'bar',marker:{{color:s.color}}}});
    }});
    var el=document.getElementById('plotBars'); if(el)Plotly.newPlot(el,traces,{{barmode:'group',margin:{{t:20,b:40,l:50,r:20}},legend:{{orientation:'h',y:-0.3}},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',yaxis:{{gridcolor:'#f1f5f9'}},xaxis:{{gridcolor:'#f1f5f9'}}}},{{responsive:true,displayModeBar:false}});
}}

function renderPie(){{
    var series=C.pie_series||[]; if(!series.length)return;
    var labels=[],values=[],colors=[];
    series.forEach(function(s){{
        var pts=filt(DATA[s.var]||[]);
        var total=pts.reduce(function(a,d){{return a+d.value;}},0);
        labels.push(s.label); values.push(total); colors.push(s.color);
    }});
    var el=document.getElementById('plotPie');
    if(el)Plotly.newPlot(el,[{{labels:labels,values:values,type:'pie',hole:0.5,marker:{{colors:colors}},textinfo:'percent',hoverinfo:'label+value'}}],{{margin:{{t:20,b:20,l:20,r:20}},paper_bgcolor:'rgba(0,0,0,0)',showlegend:false}},{{responsive:true,displayModeBar:false}});
    var tb=document.getElementById('pieTable'); if(!tb)return;
    var total=values.reduce(function(a,b){{return a+b;}},0);
    var html=''; labels.forEach(function(l,i){{ var pct=total>0?(values[i]/total*100):0; html+='<tr><td class="py-2 text-xs font-bold" style="color:'+colors[i]+'">'+l+'</td><td class="py-2 font-mono font-bold text-right text-slate-700">'+fmt(values[i],1)+'</td><td class="py-2 font-mono text-right text-slate-500">'+pct.toFixed(1)+'%</td></tr>'; }});
    tb.innerHTML=html;
}}

function renderDataTable(){{
    var period=document.getElementById('tablePeriod'); var pname=period?period.value:'Diario';
    var periods=C.table_periods||{{}}; var series=periods[pname]||[];
    if(!series.length)return;
    var pts_by_var={{}};
    series.forEach(function(s){{ pts_by_var[s.var]=filt(DATA[s.var]||[]); }});
    var dates={{}}; series.forEach(function(s){{ pts_by_var[s.var].forEach(function(d){{ dates[d.timestamp]=1; }}); }});
    var sorted=Object.keys(dates).sort();
    var hd=document.getElementById('dtHead'); var bd=document.getElementById('dtBody'); var ft=document.getElementById('dtFoot');
    if(!hd)return;
    hd.innerHTML='<th>Fecha</th>'+series.map(function(s){{return '<th>'+s.label+' ('+s.unit+')</th>';}}).join('');
    var totals=series.map(function(){{return 0;}});
    var rows=''; sorted.forEach(function(ts){{
        var cells='<td>'+ts.split('T')[0]+'</td>';
        series.forEach(function(s,i){{
            var pt=pts_by_var[s.var].find(function(d){{return d.timestamp===ts;}});
            var v=pt?pt.value:0; totals[i]+=v;
            cells+='<td>'+fmt(v,2)+'</td>';
        }});
        rows+='<tr>'+cells+'</tr>';
    }});
    bd.innerHTML=rows;
    ft.innerHTML='<td class="font-bold">Total</td>'+totals.map(function(t){{return '<td>'+fmt(t,1)+'</td>';}}).join('');
}}

function renderRaw(){{
    var allPts=[];
    Object.keys(DATA).forEach(function(k){{ filt(DATA[k]||[]).forEach(function(d){{ allPts.push({{ts:d.timestamp,var:k,val:d.value}}); }}); }});
    allPts.sort(function(a,b){{return a.ts>b.ts?1:-1;}});
    document.getElementById('rawCount').innerText='('+allPts.length+' puntos)';
    var rh=document.getElementById('rawHead'); var rb=document.getElementById('rawBody');
    if(rh) rh.innerHTML='<th>Timestamp</th><th>Variable</th><th>Valor</th>';
    if(rb) rb.innerHTML=allPts.map(function(p){{return '<tr><td>'+p.ts+'</td><td>'+p.var+'</td><td>'+fmt(p.val,3)+'</td></tr>';}}).join('');
}}

function renderHistorical(){{
    var hb=document.getElementById('histBody'); if(!hb||!HIST.length)return;
    var currentShip='{subtitle}';
    hb.innerHTML=HIST.map(function(r){{
        var isCurrent=(r.barco&&currentShip.indexOf(r.barco)>=0);
        return '<tr'+(isCurrent?' class="current"':'')+'>'
            +'<td>'+r.year+'</td><td class="text-left">'+r.barco+'</td>'
            +'<td>'+fmt(r.inhimold||0,0)+'</td><td>'+fmt(r.maiz||0,0)+'</td>'
            +'<td class="font-bold">'+((r.dosis||0).toFixed(4))+'</td>'
            +'<td>'+((r.dosis_esperada||0)>0?(r.dosis_esperada||0).toFixed(2):'—')+'</td>'
            +'</tr>';
    }}).join('');
}}

function renderAll(){{
    recalcDosis();
    renderChart();
    renderBars();
    renderPie();
    renderDataTable();
    renderRaw();
    renderHistorical();
}}

window.onload = function(){{ renderAll(); }};
</script>
</body>
</html>"""


def _build_sections(components: list[dict], config: dict) -> str:
    """Build HTML sections from component definitions."""
    sections = []
    for comp in components:
        ctype = comp.get("type")
        if ctype == "kpi_row":
            sections.append(_build_kpi_row(comp, config))
        elif ctype == "text_block":
            sections.append(_build_text_block(comp))
        elif ctype == "line_chart":
            sections.append(_build_line_chart(comp))
        elif ctype == "bar_chart":
            sections.append(_build_bar_chart(comp))
        elif ctype == "pie_chart":
            sections.append(_build_pie_chart(comp))
        elif ctype == "data_table":
            sections.append(_build_data_table(comp))
        elif ctype == "summary":
            sections.append(_build_summary(comp))
        elif ctype == "historical":
            sections.append(_build_historical(comp))
        elif ctype == "raw_data":
            sections.append(_build_raw_data())
    return "\n".join(sections)


def _build_kpi_row(comp: dict, config: dict) -> str:
    cards = comp.get("cards", [])
    total_maiz = config.get("total_maiz", 0)
    dosis_obj = config.get("dosis_objetivo", 0.6)
    cards_html = ""

    # Always include standard cards if we have pump data
    cards_html += """
    <div class="kpi p-5 bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-xl border border-blue-200/60 text-center">
        <p class="text-[10px] font-bold text-blue-400 uppercase tracking-wider">Total Inhimold</p>
        <p class="text-3xl font-black text-blue-700 mt-1" id="kpiInhimold">—</p>
        <p class="text-xs text-blue-400 mt-1">Litros (suma bombas)</p>
    </div>
    <div class="kpi p-5 bg-gradient-to-br from-amber-50 to-amber-100/50 rounded-xl border border-amber-200/60 text-center">
        <p class="text-[10px] font-bold text-amber-500 uppercase tracking-wider">Total Maíz</p>
        <input type="number" id="inputMaiz" class="maiz-input mt-1" value="{total_maiz}" onchange="recalcDosis()" onkeyup="recalcDosis()">
        <p class="text-xs text-amber-400 mt-1">Toneladas (editable)</p>
    </div>
    <div class="kpi p-5 rounded-xl border text-center relative overflow-hidden" id="dosisCard">
        <div id="dosisBg" class="absolute inset-0 opacity-10 bg-gray-200"></div>
        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">Dosis Aplicada</p>
        <div class="flex justify-center items-center gap-2 mt-1 relative z-10">
            <div id="dosisDot" class="w-3 h-3 rounded-full bg-gray-400"></div>
            <p class="text-3xl font-black text-slate-700 relative z-10" id="dosisVal">—</p>
        </div>
        <p class="text-xs text-slate-400 mt-1 relative z-10">L/Ton</p>
    </div>
    <div class="kpi p-5 bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-xl border border-slate-200/60 text-center">
        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Dosis Objetivo</p>
        <p class="text-3xl font-black text-slate-700 mt-1">{dosis_obj}</p>
        <p class="text-xs text-slate-400 mt-1">L/Ton | Cumplimiento: <span class="font-bold" id="dosisPct">—</span></p>
    </div>
""".format(total_maiz=total_maiz, dosis_obj=dosis_obj)

    return f"""
<div class="grid grid-cols-4 gap-5 mb-6" id="kpiRow">
    {cards_html}
</div>
<div id="pumpCards" class="mb-2"></div>
<p class="text-sm text-slate-500 mb-10 leading-relaxed">{comp.get('description', '')}</p>
"""


def _build_text_block(comp: dict) -> str:
    title = comp.get("title", "")
    text = comp.get("text", "")
    return f"""
<div class="bg-slate-50 rounded-xl border border-slate-200 p-6 mb-8">
    {'<h4 class="section-title">' + title + '</h4>' if title else ''}
    <p class="text-sm text-slate-600 leading-relaxed">{text}</p>
</div>
"""


def _build_line_chart(comp: dict) -> str:
    title = comp.get("title", "Gráfica de Flujo por Hora")
    desc = comp.get("description", "")
    return f"""
<div class="border border-slate-200 rounded-xl p-1 mb-2 shadow-sm">
    <div class="flex justify-between items-center px-5 py-3 bg-slate-50 border-b border-slate-100 rounded-t-xl">
        <span class="text-xs font-bold text-slate-500 uppercase">{title}</span>
        <div class="flex gap-3">
            <div class="flex items-center gap-1">
                <label class="text-[10px] uppercase font-bold text-slate-400">Op:</label>
                <select id="aggSel" class="ctrl bg-white" onchange="renderChart()">
                    <option value="sum" selected>Suma</option>
                    <option value="avg">Promedio</option>
                    <option value="max">Max</option>
                    <option value="min">Min</option>
                </select>
            </div>
            <div class="flex items-center gap-1">
                <label class="text-[10px] uppercase font-bold text-slate-400">Muestreo:</label>
                <select id="freqSel" class="ctrl bg-white" onchange="renderChart()">
                    <option value="1h" selected>1 h</option>
                    <option value="2h">2 h</option>
                    <option value="6h">6 h</option>
                    <option value="12h">12 h</option>
                    <option value="1d">1 día</option>
                </select>
            </div>
        </div>
    </div>
    <div style="height:380px" id="plotChart"></div>
</div>
{'<p class="text-sm text-slate-500 mb-8 leading-relaxed">' + desc + '</p>' if desc else '<div class="mb-8"></div>'}
"""


def _build_bar_chart(comp: dict) -> str:
    title = comp.get("title", "Consumo Diario por Bomba (Litros/Día)")
    desc = comp.get("description", "")
    return f"""
<div class="border border-slate-200 rounded-xl p-5 mb-2 shadow-sm">
    <h4 class="section-title">{title}</h4>
    <div style="height:280px" id="plotBars"></div>
</div>
{'<p class="text-sm text-slate-500 mb-8 leading-relaxed">' + desc + '</p>' if desc else '<div class="mb-8"></div>'}
"""


def _build_pie_chart(comp: dict) -> str:
    title = comp.get("title", "Distribución por Variable")
    desc = comp.get("description", "")
    return f"""
<div class="grid grid-cols-3 gap-8 mb-2">
    <div class="col-span-1 border border-slate-200 rounded-xl p-3" style="height:320px">
        <div id="plotPie" style="width:100%;height:100%"></div>
    </div>
    <div class="col-span-2 border border-slate-200 rounded-xl p-5 flex flex-col" style="height:320px">
        <h4 class="section-title">{title}</h4>
        <div class="overflow-auto flex-grow">
            <table class="w-full tbl"><thead><tr><th>Variable</th><th>Total</th><th>%</th></tr></thead><tbody id="pieTable"></tbody></table>
        </div>
    </div>
</div>
{'<p class="text-sm text-slate-500 mb-8 leading-relaxed">' + desc + '</p>' if desc else '<div class="mb-8"></div>'}
"""


def _build_data_table(comp: dict) -> str:
    title = comp.get("title", "Tabla de Datos")
    periods = comp.get("periods", {})
    period_options = "".join(
        f'<option value="{p}">{p}</option>' for p in periods.keys()
    )
    return f"""
<div class="border border-slate-200 rounded-xl p-5 mb-8 shadow-sm">
    <div class="flex justify-between items-center mb-3">
        <h4 class="section-title mb-0">{title}</h4>
        <div class="flex items-center gap-1">
            <label class="text-[10px] uppercase font-bold text-slate-400">Periodo:</label>
            <select id="tablePeriod" class="ctrl bg-white" onchange="renderDataTable()">
                {period_options}
            </select>
        </div>
    </div>
    <div class="overflow-auto" style="max-height:400px">
        <table class="w-full tbl">
            <thead><tr id="dtHead"></tr></thead>
            <tbody id="dtBody"></tbody>
            <tfoot><tr id="dtFoot"></tr></tfoot>
        </table>
    </div>
</div>
"""


def _build_summary(comp: dict) -> str:
    title = comp.get("title", "Resumen de Dosificación")
    footer = comp.get("footer", "")
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
    <p class="text-xs text-slate-400 mt-3" id="summaryText">{footer}</p>
</div>
"""


def _build_historical(comp: dict) -> str:
    title = comp.get("title", "Histórico de Buques")
    return f"""
<div class="mb-8">
    <h4 class="section-title">{title}</h4>
    <div class="overflow-auto rounded-xl border border-slate-200" style="max-height:500px">
        <table class="w-full tbl">
            <thead><tr>
                <th>Año</th><th>Buque</th><th>Inhimold (L)</th><th>Maíz (Ton)</th><th>Dosis (L/Ton)</th><th>Dosis Obj.</th>
            </tr></thead>
            <tbody id="histBody"></tbody>
        </table>
    </div>
</div>
"""


def _build_raw_data() -> str:
    return """
<div class="border border-slate-200 rounded-xl overflow-hidden bg-white">
    <button onclick="toggleRaw()" class="w-full px-6 py-3 bg-slate-50 hover:bg-slate-100 flex justify-between items-center text-sm font-bold text-slate-600 transition-colors border-b border-slate-200">
        <span>Datos Crudos <span class="text-xs font-normal text-slate-400 ml-2" id="rawCount"></span></span>
        <span id="rawArrow" class="transition-transform text-slate-400">&#9660;</span>
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


# ─────────────────────────────────────────────
# Serve frontend
# ─────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()
