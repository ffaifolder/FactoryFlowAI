"""Render an interactive HTML dashboard from coded deduction output.

Reads the synthetic ``ledger.json`` produced by the Post stage and writes a
single, self-contained ``dashboard/index.html``:

* KPIs — total allocated, deductions coded, coded splits, customers.
* Filters — customer / category / channel / deduction type (client-side).
* Drill-down — Customer -> Category -> SKU, each with amount and % of total.

The HTML is fully offline: the data is embedded as JSON, there are no external
scripts or fonts, and it is theme-aware (light/dark) with a manual toggle.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


def _load_records(ledger_path: Path) -> list[dict]:
    entries = json.loads(Path(ledger_path).read_text()) if Path(ledger_path).exists() else []
    records = []
    for e in entries:
        d = e.get("dimensions", {})
        records.append(
            {
                "customer": d.get("customer") or "(unknown)",
                "category": d.get("category") or "Uncategorized",
                "channel": d.get("channel") or "(none)",
                "sku": d.get("sku") or "(none)",
                "description": d.get("description") or "",
                "deduction_type": d.get("deduction_type") or "",
                "invoice_ref": d.get("invoice_ref") or "",
                "deduction_id": d.get("deduction_id") or "",
                "gl_account": e.get("gl_account") or "",
                "amount": float(Decimal(str(e.get("amount", "0")))),
            }
        )
    return records


def build_dashboard(ledger_path: str | Path, output_path: str | Path) -> Path:
    """Build the dashboard HTML from ``ledger_path`` and write ``output_path``."""
    ledger_path = Path(ledger_path)
    output_path = Path(output_path)
    records = _load_records(ledger_path)
    data_json = json.dumps(records)
    html = _TEMPLATE.replace("__DATA__", data_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FactoryFlow AI — Deduction Coder</title>
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#1c2128; --muted:#5b6572;
  --line:#e4e7eb; --accent:#0d9488; --accent-ink:#0b7d73; --bar-bg:#eef0f3;
  --c0:#0d9488; --c1:#6366f1; --c2:#d97706; --c3:#db2777; --c4:#0891b2; --c5:#65a30d;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.1);
}
:root[data-theme="dark"]{
  --bg:#0f1115; --panel:#171a21; --ink:#ffffff; --muted:#ffffff;
  --line:#272b34; --accent:#2dd4bf; --accent-ink:#5eead4; --bar-bg:#20242d;
  --c0:#2dd4bf; --c1:#818cf8; --c2:#fbbf24; --c3:#f472b6; --c4:#22d3ee; --c5:#a3e635;
  --shadow:0 1px 2px rgba(0,0,0,.4);
}
@media (prefers-color-scheme:dark){
  :root[data-theme="auto"]{
    --bg:#0f1115; --panel:#171a21; --ink:#ffffff; --muted:#ffffff;
    --line:#272b34; --accent:#2dd4bf; --accent-ink:#5eead4; --bar-bg:#20242d;
    --c0:#2dd4bf; --c1:#818cf8; --c2:#fbbf24; --c3:#f472b6; --c4:#22d3ee; --c5:#a3e635;
    --shadow:0 1px 2px rgba(0,0,0,.4);
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:24px 16px 8px;max-width:1100px;margin:0 auto}
main{padding:8px 16px 48px;max-width:1100px;margin:0 auto}
h1{font-size:22px;margin:0 0 2px} .sub{color:var(--muted);font-size:13px;margin:0}
.badge{display:inline-block;font-size:11px;color:var(--muted);border:1px solid var(--line);
  border-radius:999px;padding:2px 9px;margin-top:8px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:8px 0 20px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--shadow)}
.kpi .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.kpi .value{font-size:26px;font-weight:650;margin-top:6px;font-variant-numeric:tabular-nums}
.filters{display:flex;gap:10px;flex-wrap:wrap;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;padding:12px;box-shadow:var(--shadow);margin-bottom:20px}
.field{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)}
select,button,input{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:7px 10px}
button{cursor:pointer}
button.ghost{color:var(--muted)}
.theme-btn{border-radius:999px;padding:7px 14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);
  padding:8px 4px;margin-bottom:20px}
.section-title{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:16px 8px 4px}
details{border-bottom:1px solid var(--line)}
details:last-child{border-bottom:none}
summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:1fr auto auto;
  align-items:center;gap:12px;padding:10px 12px}
summary::-webkit-details-marker{display:none}
.row-l2 summary{padding-left:30px}
.row-l3{display:grid;grid-template-columns:1fr auto auto;gap:12px;padding:8px 12px 8px 50px;
  border-top:1px dashed var(--line);color:var(--muted);font-size:14px}
.name{font-weight:600} .row-l2 .name{font-weight:550} .caret{color:var(--muted);font-size:11px;margin-right:6px}
.amt{font-variant-numeric:tabular-nums;font-weight:600;text-align:right;min-width:110px}
.pct{color:var(--muted);font-size:12px;text-align:right;min-width:52px;font-variant-numeric:tabular-nums}
.bar{height:6px;border-radius:4px;background:var(--bar-bg);overflow:hidden;grid-column:1/-1;margin-top:6px}
.bar>span{display:block;height:100%;background:var(--accent)}
.chartcard{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);
  padding:16px;margin-bottom:20px}
.chart-row{display:grid;grid-template-columns:190px 1fr 90px;align-items:center;gap:10px;margin:8px 0;font-size:13px}
.chart-row .track{background:var(--bar-bg);border-radius:6px;height:18px;overflow:hidden}
.chart-row .fill{height:100%;border-radius:6px}
.empty{padding:28px;text-align:center;color:var(--muted)}
footer{max-width:1100px;margin:0 auto;padding:0 16px 40px;color:var(--muted);font-size:12px}
code{background:var(--bar-bg);padding:1px 5px;border-radius:4px}
</style>
</head>
<body>
<header>
  <h1>FactoryFlow AI — Deduction Coder</h1>
  <p class="sub">Coded deductions by Invoice &rarr; Category &rarr; SKU, weighted by shipped sales value.</p>
  <span class="badge">Synthetic demo data — no real customers, SKUs, or dollars</span>
</header>
<main>
  <div class="toolbar">
    <div class="section-title" style="margin:0">Overview</div>
    <button class="theme-btn" id="themeBtn" type="button">◐ Theme</button>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="filters">
    <label class="field">Invoice lookup<input id="fInvoice" type="search" placeholder="e.g. INV-100477" autocomplete="off"></label>
    <label class="field">Customer<select id="fCustomer"></select></label>
    <label class="field">Category<select id="fCategory"></select></label>
    <label class="field">Channel<select id="fChannel"></select></label>
    <label class="field">Deduction type<select id="fType"></select></label>
    <label class="field">&nbsp;<button class="ghost" id="reset" type="button">Reset filters</button></label>
  </div>

  <div class="chartcard">
    <div class="section-title" style="margin:0 0 6px">Allocated by category &times; channel</div>
    <div id="chart"></div>
  </div>

  <div class="section-title">Drill-down</div>
  <div class="card" id="tree"></div>
</main>
<footer>
  Generated by <code>build_dashboard.py</code> from <code>ledger.json</code>.
  This is a demo scaffold — see <code>DISCLAIMER.md</code>.
</footer>

<script>
const DATA = __DATA__;
const PALETTE = ["--c0","--c1","--c2","--c3","--c4","--c5"];
const fmt = n => n.toLocaleString("en-US",{style:"currency",currency:"USD"});
const pct = (n,t) => t ? (100*n/t).toFixed(1)+"%" : "0.0%";
const $ = id => document.getElementById(id);

function uniq(key){ return [...new Set(DATA.map(r=>r[key]))].sort(); }
function fillSelect(el, values){
  el.innerHTML = '<option value="">All</option>' + values.map(v=>`<option>${v}</option>`).join("");
}
function colorFor(cat, cats){
  const i = cats.indexOf(cat);
  return `var(${PALETTE[(i<0?0:i)%PALETTE.length]})`;
}

function currentFilters(){
  return {invoice:$("fInvoice").value.trim().toLowerCase(),
          customer:$("fCustomer").value, category:$("fCategory").value,
          channel:$("fChannel").value, deduction_type:$("fType").value};
}
function applyFilters(rows, f){
  return rows.filter(r =>
    (!f.invoice || String(r.invoice_ref).toLowerCase().includes(f.invoice)) &&
    (!f.customer || r.customer===f.customer) &&
    (!f.category || r.category===f.category) &&
    (!f.channel || r.channel===f.channel) &&
    (!f.deduction_type || r.deduction_type===f.deduction_type));
}

function renderKpis(rows){
  const total = rows.reduce((a,r)=>a+r.amount,0);
  const deductions = new Set(rows.map(r=>r.deduction_id)).size;
  const customers = new Set(rows.map(r=>r.customer)).size;
  const kpis = [
    ["Total allocated", fmt(total)],
    ["Deductions coded", deductions],
    ["Coded splits", rows.length],
    ["Customers", customers],
  ];
  $("kpis").innerHTML = kpis.map(([l,v])=>
    `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div></div>`).join("");
}

function renderChart(rows){
  const cats = uniq("category");
  const map = {};
  rows.forEach(r=>{ const k=r.category+" × "+r.channel;
    map[k]=(map[k]||{amt:0,cat:r.category}); map[k].amt+=r.amount; });
  const items = Object.entries(map).sort((a,b)=>b[1].amt-a[1].amt);
  const max = items.reduce((m,[,v])=>Math.max(m,v.amt),0)||1;
  const el = $("chart");
  if(!items.length){ el.innerHTML='<div class="empty">No data for the current filters.</div>'; return; }
  el.innerHTML = items.map(([k,v])=>{
    const w = (100*v.amt/max).toFixed(1);
    return `<div class="chart-row"><div title="${k}" style="white-space:nowrap;overflow:hidden;
      text-overflow:ellipsis">${k}</div>
      <div class="track"><div class="fill" style="width:${w}%;background:${colorFor(v.cat,cats)}"></div></div>
      <div class="amt">${fmt(v.amt)}</div></div>`;
  }).join("");
}

function group(rows, key){
  const m = {};
  rows.forEach(r=>{ (m[r[key]]=m[r[key]]||[]).push(r); });
  return m;
}
function sum(rows){ return rows.reduce((a,r)=>a+r.amount,0); }

function renderTree(rows){
  const total = sum(rows);
  const cats = uniq("category");
  const el = $("tree");
  if(!rows.length){ el.innerHTML='<div class="empty">No data for the current filters.</div>'; return; }
  const byInv = group(rows,"invoice_ref");
  const invKeys = Object.keys(byInv).sort((a,b)=>sum(byInv[b])-sum(byInv[a]));
  const single = invKeys.length===1;   // auto-expand on an invoice lookup hit
  el.innerHTML = invKeys.map(inv=>{
    const iRows = byInv[inv], iTot = sum(iRows), iW=(100*iTot/(total||1)).toFixed(1);
    const cust = iRows[0].customer||"";
    const types = [...new Set(iRows.map(r=>r.deduction_type))].join(", ");
    const byCat = group(iRows,"category");
    const catKeys = Object.keys(byCat).sort((a,b)=>sum(byCat[b])-sum(byCat[a]));
    const cats_html = catKeys.map(cat=>{
      const catRows=byCat[cat], catTot=sum(catRows);
      const bySku=group(catRows,"sku");
      const skuKeys=Object.keys(bySku).sort((a,b)=>sum(bySku[b])-sum(bySku[a]));
      const sku_html = skuKeys.map(sku=>{
        const sTot=sum(bySku[sku]); const desc=bySku[sku][0].description||"";
        return `<div class="row-l3"><div>${sku}${desc?` — ${desc}`:""}</div>
          <div class="amt">${fmt(sTot)}</div><div class="pct">${pct(sTot,total)}</div></div>`;
      }).join("");
      return `<details class="row-l2"${single?" open":""}><summary><span class="name">
          <span class="caret">▸</span>${cat}</span>
          <span class="amt">${fmt(catTot)}</span><span class="pct">${pct(catTot,total)}</span>
          <span class="bar"><span style="width:${(100*catTot/(iTot||1)).toFixed(1)}%;
            background:${colorFor(cat,cats)}"></span></span></summary>${sku_html}</details>`;
    }).join("");
    return `<details open><summary><span class="name"><span class="caret">▾</span>
        <b>${inv}</b> <span style="color:var(--muted);font-weight:400">· ${cust} · ${types}</span></span>
        <span class="amt">${fmt(iTot)}</span><span class="pct">${iW}%</span>
        <span class="bar"><span style="width:${iW}%"></span></span></summary>${cats_html}</details>`;
  }).join("");
}

function render(){
  const rows = applyFilters(DATA, currentFilters());
  renderKpis(rows); renderChart(rows); renderTree(rows);
}

function init(){
  fillSelect($("fCustomer"), uniq("customer"));
  fillSelect($("fCategory"), uniq("category"));
  fillSelect($("fChannel"), uniq("channel"));
  fillSelect($("fType"), uniq("deduction_type"));
  ["fCustomer","fCategory","fChannel","fType"].forEach(id=>$(id).addEventListener("change",render));
  $("fInvoice").addEventListener("input",render);
  $("reset").addEventListener("click",()=>{
    ["fInvoice","fCustomer","fCategory","fChannel","fType"].forEach(id=>$(id).value=""); render(); });

  const root=document.documentElement;
  try{ const saved=localStorage.getItem("ff_theme"); if(saved) root.setAttribute("data-theme",saved); }catch(e){}
  $("themeBtn").addEventListener("click",()=>{
    const order=["auto","light","dark"];
    const cur=root.getAttribute("data-theme")||"auto";
    const next=order[(order.indexOf(cur)+1)%order.length];
    root.setAttribute("data-theme",next);
    try{ localStorage.setItem("ff_theme",next); }catch(e){}
    $("themeBtn").textContent = "◐ "+next.charAt(0).toUpperCase()+next.slice(1);
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
    out = PROJECT_ROOT / "dashboard" / "index.html"
    path = build_dashboard(ledger, out)
    print(f"Dashboard written to: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
