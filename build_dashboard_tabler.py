"""Render a Tabler-themed interactive dashboard from coded deduction output.

A brighter, richer alternative to ``build_dashboard.py``. It uses the
open-source **Tabler** UI kit (MIT, Bootstrap 5) and **ApexCharts** (MIT),
both vendored locally under ``dashboard-app/assets/`` so the page stays fully
offline and GitHub-Pages-friendly — no CDN, no external data.

Output: ``dashboard-app/index.html`` with:
  * KPI cards (total allocated, deductions coded, splits, customers),
  * a category x channel treemap, a deduction-type donut, a per-customer bar,
  * client-side filters, and a Customer -> Category -> SKU drill-down.

The plain ``build_dashboard.py`` (zero-dependency, single file) remains as a
fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

from build_dashboard import _load_records  # reuse the ledger reader


def build_tabler_dashboard(ledger_path: str | Path, output_path: str | Path) -> Path:
    """Build the Tabler dashboard HTML from ``ledger_path``."""
    ledger_path = Path(ledger_path)
    output_path = Path(output_path)
    records = _load_records(ledger_path)
    html = _TEMPLATE.replace("__DATA__", json.dumps(records))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>FactoryFlow AI — Deduction Coder</title>
<link rel="stylesheet" href="./assets/tabler.min.css">
<style>
  :root{ --ff-accent:#0d9488; }
  body{ background:var(--tblr-body-bg); }
  .kpi-value{ font-variant-numeric:tabular-nums; }
  .page-pretitle{ letter-spacing:.04em; }
  /* Drill-down built on native <details> (no extra JS dependency) */
  #tree details{ border-bottom:1px solid var(--tblr-border-color); }
  #tree > details:last-child{ border-bottom:0; }
  #tree summary{ list-style:none; cursor:pointer; display:grid;
    grid-template-columns:1fr 130px 64px; align-items:center; gap:12px;
    padding:12px 16px; }
  #tree summary::-webkit-details-marker{ display:none; }
  #tree .lvl2 summary{ padding-left:34px; font-weight:500; }
  #tree .caret{ color:var(--tblr-secondary); font-size:.7rem; margin-right:.4rem;
    display:inline-block; transition:transform .15s; }
  #tree details[open] > summary .caret{ transform:rotate(90deg); }
  #tree .amt{ text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }
  #tree .pct{ text-align:right; font-variant-numeric:tabular-nums; color:var(--tblr-secondary); font-size:.8125rem; }
  #tree .skurow{ display:grid; grid-template-columns:1fr 130px 64px; gap:12px;
    padding:8px 16px 8px 54px; border-top:1px dashed var(--tblr-border-color);
    color:var(--tblr-secondary); font-size:.875rem; }
  #tree .name{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .chart-box{ min-height:280px; }
  .empty{ padding:2rem; text-align:center; color:var(--tblr-secondary); }

  /* Dark mode: force pure-white text everywhere (no muted greys) */
  [data-bs-theme="dark"]{
    --tblr-body-color:#ffffff; --tblr-secondary:#ffffff;
    --tblr-secondary-color:#ffffff; --tblr-tertiary-color:#ffffff;
    --tblr-muted:#ffffff; --tblr-emphasis-color:#ffffff;
  }
  [data-bs-theme="dark"] body,
  [data-bs-theme="dark"] .text-secondary,
  [data-bs-theme="dark"] .text-muted,
  [data-bs-theme="dark"] .subheader,
  [data-bs-theme="dark"] .card-title,
  [data-bs-theme="dark"] .page-title,
  [data-bs-theme="dark"] .page-pretitle,
  [data-bs-theme="dark"] .form-label,
  [data-bs-theme="dark"] .form-select,
  [data-bs-theme="dark"] .navbar-brand,
  [data-bs-theme="dark"] #tree,
  [data-bs-theme="dark"] #tree .name,
  [data-bs-theme="dark"] #tree .amt,
  [data-bs-theme="dark"] #tree .pct,
  [data-bs-theme="dark"] #tree .skurow,
  [data-bs-theme="dark"] #tree .caret,
  [data-bs-theme="dark"] .footer,
  [data-bs-theme="dark"] .footer code{ color:#ffffff !important; }
</style>
</head>
<body>
<div class="page">
  <header class="navbar navbar-expand-md d-print-none">
    <div class="container-xl">
      <div class="navbar-brand fw-bold" style="font-size:1.05rem;">
        <span style="color:var(--ff-accent)">◆</span> FactoryFlow AI
        <span class="text-secondary fw-normal">— Deduction Coder</span>
      </div>
      <div class="navbar-nav flex-row order-md-last align-items-center">
        <span class="badge bg-teal-lt me-3 d-none d-sm-inline">Synthetic demo data</span>
        <button id="themeBtn" class="btn btn-icon btn-ghost-secondary" type="button" title="Toggle theme">◐</button>
      </div>
    </div>
  </header>

  <div class="page-wrapper">
    <div class="page-header">
      <div class="container-xl">
        <div class="page-pretitle text-uppercase text-secondary">Overview</div>
        <h2 class="page-title">Coded deductions by Invoice → Category → SKU</h2>
        <div class="text-secondary">Weighted by shipped sales-dollar value. No real customers, SKUs, or dollars.</div>
      </div>
    </div>

    <div class="page-body">
      <div class="container-xl">

        <!-- KPIs -->
        <div class="row row-deck row-cards mb-3" id="kpis"></div>

        <!-- Filters -->
        <div class="card mb-3">
          <div class="card-body">
            <div class="row g-2 align-items-end">
              <div class="col-12 col-md-3">
                <label class="form-label">Invoice lookup</label>
                <input id="fInvoice" type="search" class="form-control" placeholder="e.g. INV-100477" autocomplete="off"></div>
              <div class="col-6 col-md">
                <label class="form-label">Customer</label>
                <select id="fCustomer" class="form-select"></select></div>
              <div class="col-6 col-md">
                <label class="form-label">Category</label>
                <select id="fCategory" class="form-select"></select></div>
              <div class="col-6 col-md">
                <label class="form-label">Channel</label>
                <select id="fChannel" class="form-select"></select></div>
              <div class="col-6 col-md">
                <label class="form-label">Deduction type</label>
                <select id="fType" class="form-select"></select></div>
              <div class="col-auto">
                <label class="form-label d-none d-md-block">&nbsp;</label>
                <button id="reset" class="btn btn-outline-secondary w-100" type="button">Reset</button></div>
            </div>
          </div>
        </div>

        <!-- Charts -->
        <div class="row row-cards mb-3">
          <div class="col-12 col-lg-8">
            <div class="card"><div class="card-header"><h3 class="card-title">Allocated by category × channel</h3></div>
              <div class="card-body"><div id="chTreemap" class="chart-box"></div></div></div>
          </div>
          <div class="col-12 col-lg-4">
            <div class="card"><div class="card-header"><h3 class="card-title">By deduction type</h3></div>
              <div class="card-body"><div id="chDonut" class="chart-box"></div></div></div>
          </div>
          <div class="col-12">
            <div class="card"><div class="card-header"><h3 class="card-title">Allocated by customer</h3></div>
              <div class="card-body"><div id="chBar" style="min-height:260px"></div></div></div>
          </div>
        </div>

        <!-- Drill-down -->
        <div class="card">
          <div class="card-header"><h3 class="card-title">Drill-down</h3></div>
          <div id="tree"></div>
        </div>

      </div>
    </div>

    <footer class="footer footer-transparent d-print-none">
      <div class="container-xl text-secondary" style="font-size:.8125rem">
        Generated by <code>build_dashboard_tabler.py</code> from <code>ledger.json</code>.
        Built with Tabler (MIT) + ApexCharts (MIT). Demo scaffold — see <code>DISCLAIMER.md</code>.
      </div>
    </footer>
  </div>
</div>

<script src="./assets/apexcharts.min.js"></script>
<script>
const DATA = __DATA__;
const PALETTE = ["#0d9488","#6366f1","#d97706","#db2777","#0891b2","#65a30d","#7c3aed","#dc2626"];
const $ = id => document.getElementById(id);
const fmt = n => n.toLocaleString("en-US",{style:"currency",currency:"USD"});
const pct = (n,t) => t ? (100*n/t).toFixed(1)+"%" : "0.0%";
const uniq = k => [...new Set(DATA.map(r=>r[k]))].sort();
const sum = rows => rows.reduce((a,r)=>a+r.amount,0);
function group(rows,k){ const m={}; rows.forEach(r=>{(m[r[k]]=m[r[k]]||[]).push(r);}); return m; }
let charts = {};

function isDark(){ return document.documentElement.getAttribute("data-bs-theme")==="dark"; }

function fillSelect(el, vals){
  el.innerHTML = '<option value="">All</option>' + vals.map(v=>`<option>${v}</option>`).join("");
}
function filters(){ return {invoice:$("fInvoice").value.trim().toLowerCase(),
  customer:$("fCustomer").value, category:$("fCategory").value,
  channel:$("fChannel").value, deduction_type:$("fType").value}; }
function apply(rows,f){ return rows.filter(r =>
  (!f.invoice||String(r.invoice_ref).toLowerCase().includes(f.invoice))&&
  (!f.customer||r.customer===f.customer)&&(!f.category||r.category===f.category)&&
  (!f.channel||r.channel===f.channel)&&(!f.deduction_type||r.deduction_type===f.deduction_type)); }

function renderKpis(rows){
  const total = sum(rows);
  const cards = [
    ["Total allocated", fmt(total), "teal"],
    ["Deductions coded", new Set(rows.map(r=>r.deduction_id)).size, "indigo"],
    ["Coded splits", rows.length, "orange"],
    ["Customers", new Set(rows.map(r=>r.customer)).size, "cyan"],
  ];
  $("kpis").innerHTML = cards.map(([l,v,c])=>`
    <div class="col-6 col-lg-3"><div class="card card-sm"><div class="card-body">
      <div class="subheader">${l}</div>
      <div class="h1 mb-0 mt-1 kpi-value text-${c}">${v}</div>
    </div></div></div>`).join("");
}

function apexBase(){ return { chart:{ fontFamily:"inherit", background:"transparent", toolbar:{show:false},
  animations:{enabled:false}, foreColor: isDark()?"#ffffff":"#1c2128" },
  theme:{ mode: isDark()?"dark":"light" }, colors:PALETTE,
  legend:{ labels:{ colors: isDark()?"#ffffff":undefined } },
  tooltip:{ y:{ formatter:v=>fmt(v) } }, dataLabels:{enabled:false} }; }

function renderCharts(rows){
  Object.values(charts).forEach(c=>{ try{c.destroy();}catch(e){} }); charts={};
  const txt = isDark()?"#ffffff":"#1c2128";

  // Treemap: category x channel
  const cc={}; rows.forEach(r=>{ const k=r.category+" × "+r.channel; cc[k]=(cc[k]||0)+r.amount; });
  const tm = Object.entries(cc).map(([x,y])=>({x, y:+y.toFixed(2)}));
  charts.tm = new ApexCharts($("chTreemap"), Object.assign(apexBase(), {
    series:[{data: tm.length?tm:[{x:"—",y:0}]}], chart:Object.assign(apexBase().chart,{type:"treemap",height:280}),
    legend:{show:false}, plotOptions:{treemap:{distributed:true, enableShades:false}},
  })); charts.tm.render();

  // Donut: deduction type
  const dt={}; rows.forEach(r=>{ dt[r.deduction_type]=(dt[r.deduction_type]||0)+r.amount; });
  const dl=Object.keys(dt), ds=dl.map(k=>+dt[k].toFixed(2));
  charts.dn = new ApexCharts($("chDonut"), Object.assign(apexBase(), {
    series:ds.length?ds:[1], labels:dl.length?dl:["—"],
    chart:Object.assign(apexBase().chart,{type:"donut",height:280}),
    legend:{position:"bottom",fontSize:"12px",labels:{colors:txt}}, tooltip:{y:{formatter:v=>fmt(v)}},
  })); charts.dn.render();

  // Horizontal bar: customer
  const cu={}; rows.forEach(r=>{ cu[r.customer]=(cu[r.customer]||0)+r.amount; });
  const ce=Object.entries(cu).sort((a,b)=>b[1]-a[1]);
  charts.br = new ApexCharts($("chBar"), Object.assign(apexBase(), {
    series:[{name:"Allocated", data:ce.map(([,v])=>+v.toFixed(2))}],
    chart:Object.assign(apexBase().chart,{type:"bar",height:260}),
    plotOptions:{bar:{horizontal:true,borderRadius:3,barHeight:"62%",distributed:true,
      dataLabels:{position:"bottom"}}},
    dataLabels:{enabled:true, textAnchor:"start", offsetX:6, style:{fontSize:"12px",colors:["#fff"]},
      formatter:v=>fmt(v)},
    legend:{show:false},
    xaxis:{categories:ce.map(([k])=>k), tickAmount:5,
      labels:{formatter:v=>"$"+Math.round(v), style:{colors:txt}}},
    yaxis:{labels:{maxWidth:240, style:{fontSize:"13px", colors:txt}}},
  })); charts.br.render();
}

function renderTree(rows){
  const total = sum(rows), el=$("tree");
  if(!rows.length){ el.innerHTML='<div class="empty">No data for the current filters.</div>'; return; }
  const byInv=group(rows,"invoice_ref");
  const invKeys=Object.keys(byInv).sort((a,b)=>sum(byInv[b])-sum(byInv[a]));
  // Auto-expand categories when a single invoice is in view (a lookup hit).
  const single = invKeys.length===1;
  el.innerHTML = invKeys.map(inv=>{
    const iRows=byInv[inv], iTot=sum(iRows), iW=(100*iTot/(total||1)).toFixed(1);
    const cust=iRows[0].customer||"";
    const types=[...new Set(iRows.map(r=>r.deduction_type))].join(", ");
    const byCat=group(iRows,"category");
    const catKeys=Object.keys(byCat).sort((a,b)=>sum(byCat[b])-sum(byCat[a]));
    const cats=catKeys.map(cat=>{
      const cr=byCat[cat], catTot=sum(cr), bySku=group(cr,"sku");
      const skuKeys=Object.keys(bySku).sort((a,b)=>sum(bySku[b])-sum(bySku[a]));
      const skus=skuKeys.map(sku=>{
        const sTot=sum(bySku[sku]), desc=bySku[sku][0].description||"";
        return `<div class="skurow"><div class="name">${sku}${desc?` — ${desc}`:""}</div>
          <div class="amt">${fmt(sTot)}</div><div class="pct">${pct(sTot,total)}</div></div>`;
      }).join("");
      return `<details class="lvl2"${single?" open":""}><summary><span class="name"><span class="caret">▶</span>${cat}</span>
        <span class="amt">${fmt(catTot)}</span><span class="pct">${pct(catTot,total)}</span></summary>${skus}</details>`;
    }).join("");
    return `<details open><summary><span class="name"><span class="caret">▶</span>
      <span class="fw-bold">${inv}</span>
      <span class="text-secondary" style="font-weight:400"> · ${cust} · ${types}</span></span>
      <span class="amt">${fmt(iTot)}</span><span class="pct">${iW}%</span></summary>${cats}</details>`;
  }).join("");
}

function render(){ const rows=apply(DATA,filters()); renderKpis(rows); renderCharts(rows); renderTree(rows); }

function init(){
  fillSelect($("fCustomer"),uniq("customer")); fillSelect($("fCategory"),uniq("category"));
  fillSelect($("fChannel"),uniq("channel")); fillSelect($("fType"),uniq("deduction_type"));
  ["fCustomer","fCategory","fChannel","fType"].forEach(id=>$(id).addEventListener("change",render));
  $("fInvoice").addEventListener("input",render);
  $("reset").addEventListener("click",()=>{
    ["fInvoice","fCustomer","fCategory","fChannel","fType"].forEach(id=>$(id).value=""); render();});

  const root=document.documentElement;
  try{ const s=localStorage.getItem("ff_theme"); if(s) root.setAttribute("data-bs-theme",s); }catch(e){}
  $("themeBtn").addEventListener("click",()=>{
    const next = isDark()?"light":"dark"; root.setAttribute("data-bs-theme",next);
    try{ localStorage.setItem("ff_theme",next); }catch(e){} render();
  });
  render();
}
init();
</script>
</body>
</html>
"""


def main() -> int:
    from factoryflow.config import PROJECT_ROOT

    ledger = PROJECT_ROOT / "ledger.json"
    out = PROJECT_ROOT / "dashboard-app" / "index.html"
    path = build_tabler_dashboard(ledger, out)
    print(f"Tabler dashboard written to: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
