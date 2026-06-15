"""Interaktif finansal tablo HTML parçası (dashboard tab pane için)."""
from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# CSS — tablo bileşeni stilleri (body/h1/tab-nav harici)
# ---------------------------------------------------------------------------
_FT_CSS = (
    ".ctrl-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;"
    "background:#1e293b;border-bottom:1px solid #334155;padding:9px 12px}"
    ".ctrl-grp{display:flex;flex-wrap:wrap;gap:5px;align-items:center}"
    ".ctrl-lbl{font-size:.7rem;color:#64748b;white-space:nowrap;margin-right:2px}"
    ".period-lbl{display:inline-flex;align-items:center;gap:3px;font-size:.73rem;"
    "color:#94a3b8;cursor:pointer;background:#0f172a;border:1px solid #334155;"
    "border-radius:4px;padding:2px 7px}"
    ".period-lbl input{cursor:pointer;accent-color:#00D4FF}"
    ".pkg-sel{background:#0f172a;color:#f1f5f9;border:1px solid #334155;"
    "border-radius:4px;padding:3px 8px;font-size:.75rem}"
    ".btn-s{background:#0f172a;color:#94a3b8;border:1px solid #334155;"
    "border-radius:4px;padding:3px 9px;cursor:pointer;font-size:.75rem}"
    ".btn-s:hover{color:#f1f5f9;border-color:#64748b}"
    ".btn-p{color:#00D4FF;border-color:#00D4FF55}"
    ".btn-p:hover{background:#00D4FF11}"
    ".btn-d:hover{color:#ef4444;border-color:#ef4444}"
    ".tbl-wrap{overflow:auto}"
    "#fin-tbl{width:100%;border-collapse:collapse;font-size:.88rem}"
    "#fin-tbl thead{position:sticky;top:0;z-index:5}"
    "#fin-tbl thead th{background:#0a1628;color:#64748b;text-align:right;"
    "padding:7px 10px;white-space:nowrap;font-size:.82rem;"
    "border-bottom:2px solid #334155;font-weight:600}"
    "#fin-tbl thead th.kh{text-align:left;min-width:250px;position:sticky;left:0;z-index:6}"
    "#fin-tbl thead th.vh{min-width:150px}"
    ".sec-hdr{cursor:pointer}"
    ".sec-hdr td{color:#00D4FF;font-weight:700;font-size:.78rem;letter-spacing:.07em;"
    "padding:5px 10px;border-top:2px solid #334155;background:#0a1628;user-select:none}"
    ".sec-hdr:hover td{background:#1e293b}"
    ".drow td{padding:6px 10px;border-bottom:1px solid #111827;vertical-align:middle}"
    ".drow:hover td{background:#1a2535}"
    ".drow.hid{display:none}"
    ".kc{text-align:left;position:sticky;left:0;background:#0f172a;z-index:1}"
    ".drow:hover .kc{background:#1a2535}"
    ".klbl{display:flex;align-items:center;gap:5px;color:#cbd5e1}"
    ".klbl input{cursor:pointer;accent-color:#00D4FF;flex-shrink:0}"
    ".vc{text-align:right;white-space:nowrap}"
    ".nv{font-family:'Courier New',monospace;color:#e2e8f0}"
    ".null{color:#475569}"
    ".dp{color:#22c55e;font-size:.75em;margin-left:3px}"
    ".dn{color:#ef4444;font-size:.75em;margin-left:3px}"
    ".dz{color:#64748b;font-size:.75em;margin-left:3px}"
)

# ---------------------------------------------------------------------------
# JS — tablo interaktivitesi (showTab harici, Finansal Tablo'ya özgü)
# ---------------------------------------------------------------------------
_FT_JS = r"""
let selPd=new Set(ALL_PERIODS.slice(0,DEFAULT_N));
let hidRows=new Set();
let colSec={};

function fmtV(v){
  if(v===null||v===undefined) return null;
  return (v/1e6).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
}

function badge(c,p){
  if(c===null||c===undefined||p===null||p===undefined||p===0) return '';
  const pct=(c-p)/Math.abs(p)*100;
  if(Math.abs(pct)<0.005) return '<span class="dz"> →0.0%</span>';
  const s=pct>0?'▲':'▼', cls=pct>0?'dp':'dn';
  return '<span class="'+cls+'"> '+s+Math.abs(pct).toFixed(1)+'%</span>';
}

const PKG_KEY='finlab_'+TICKER;
function getPkgs(){try{return JSON.parse(localStorage.getItem(PKG_KEY)||'[]');}catch(e){return[];}}
function setPkgs(pkgs){try{localStorage.setItem(PKG_KEY,JSON.stringify(pkgs));}catch(e){}}

function refreshPkgSel(){
  const sel=document.getElementById('pkg-sel');
  const pkgs=getPkgs();
  sel.innerHTML='<option value="">Paket seç…</option>'+
    pkgs.map((p,i)=>'<option value="'+i+'">'+p.name+'</option>').join('');
}

function renderTable(){
  const vp=ALL_PERIODS.filter(p=>selPd.has(p));
  let hdr='<tr><th class="kh">Kalem <small style="color:#475569;font-weight:400">(mn '+CURRENCY+')</small></th>';
  vp.forEach(p=>{hdr+='<th class="vh">'+p+'</th>';});
  hdr+='</tr>';
  document.getElementById('fin-thead').innerHTML=hdr;
  let body='';
  SECTION_ORDER.forEach(sec=>{
    const sd=RAW_SECTIONS[sec];
    if(!sd||Object.keys(sd).length===0) return;
    const col=!!colSec[sec];
    body+='<tr class="sec-hdr" data-sec="'+sec+'"><td colspan="'+(1+vp.length)+'">'
      +(col?'▶':'▼')+' '+SECTION_LABELS[sec]+'</td></tr>';
    if(col) return;
    Object.entries(sd).forEach(([k,ser])=>{
      const rk=sec+'::'+k;
      const rkE=rk.replace(/&/g,'&amp;').replace(/"/g,'&quot;');
      const vis=!hidRows.has(rk);
      let tds='<td class="kc"><label class="klbl"><input type="checkbox"'
        +(vis?' checked':'')
        +' data-rk="'+rkE+'"> '+k+'</label></td>';
      vp.forEach(p=>{
        const cur=ser[p]!==undefined?ser[p]:null;
        const ai=ALL_PERIODS.indexOf(p);
        const pp=ai+1<ALL_PERIODS.length?ALL_PERIODS[ai+1]:null;
        const prv=pp?(ser[pp]!==undefined?ser[pp]:null):null;
        const fv=fmtV(cur);
        tds+='<td class="vc">'+(fv?'<span class="nv">'+fv+'</span>':'<span class="null">—</span>')
          +badge(cur,prv)+'</td>';
      });
      body+='<tr class="drow'+(vis?'':' hid')+'" data-rk="'+rkE+'">'+tds+'</tr>';
    });
  });
  document.getElementById('fin-tbody').innerHTML=body;
}

document.addEventListener('click',e=>{
  const sh=e.target.closest('.sec-hdr');
  if(sh){colSec[sh.dataset.sec]=!colSec[sh.dataset.sec];renderTable();}
});
document.addEventListener('change',e=>{
  const inp=e.target;
  if(inp.type==='checkbox'&&inp.dataset.rk){
    if(inp.checked) hidRows.delete(inp.dataset.rk); else hidRows.add(inp.dataset.rk);
    const tr=inp.closest('tr');
    if(tr) tr.classList.toggle('hid',!inp.checked);
  }
});

function buildPdSel(){
  const div=document.getElementById('pd-sel');
  ALL_PERIODS.forEach(p=>{
    const lbl=document.createElement('label');
    lbl.className='period-lbl';
    const inp=document.createElement('input');
    inp.type='checkbox';
    inp.checked=selPd.has(p);
    inp.addEventListener('change',()=>{
      if(inp.checked) selPd.add(p); else selPd.delete(p);
      renderTable();
    });
    lbl.appendChild(inp);
    lbl.appendChild(document.createTextNode(' '+p));
    div.appendChild(lbl);
  });
}

function selAllPd(v){
  if(v) selPd=new Set(ALL_PERIODS); else selPd.clear();
  document.querySelectorAll('#pd-sel input').forEach(i=>i.checked=v);
  renderTable();
}

function savePkg(){
  const n=prompt('Paket adı:');
  if(!n||!n.trim()) return;
  const pkgs=getPkgs();
  pkgs.push({name:n.trim(),hidden:[...hidRows]});
  setPkgs(pkgs); refreshPkgSel();
}
function loadPkg(idx){
  if(idx==='') return;
  const pkg=getPkgs()[Number(idx)];
  if(!pkg) return;
  hidRows=new Set(pkg.hidden);
  renderTable();
}
function delPkg(){
  const sel=document.getElementById('pkg-sel');
  if(!sel.value) return;
  if(!confirm('Bu paketi silmek istiyor musunuz?')) return;
  const pkgs=getPkgs(); pkgs.splice(Number(sel.value),1);
  setPkgs(pkgs); refreshPkgSel(); hidRows.clear(); renderTable();
}
function showAll(){hidRows.clear();renderTable();}

buildPdSel(); refreshPkgSel(); renderTable();
"""

_SECTION_ORDER  = ["bilanco", "gelir", "dipnot", "nakit_akim"]
_SECTION_LABELS = {
    "bilanco":    "BİLANÇO",
    "gelir":      "GELİR TABLOSU",
    "dipnot":     "DİPNOTLAR",
    "nakit_akim": "NAKİT AKIŞ TABLOSU",
}

_CTRL_BAR = (
    "<div class='ctrl-bar'>"
    "<div class='ctrl-grp'>"
    "<span class='ctrl-lbl'>Dönemler:</span>"
    "<div id='pd-sel'></div>"
    "<button class='btn-s' onclick='selAllPd(true)'>Tümü</button>"
    "<button class='btn-s' onclick='selAllPd(false)'>Temizle</button>"
    "</div>"
    "<div class='ctrl-grp'>"
    "<span class='ctrl-lbl'>Görünüm paketi:</span>"
    "<select id='pkg-sel' class='pkg-sel' onchange='loadPkg(this.value)'></select>"
    "<button class='btn-s btn-p' onclick='savePkg()'>&#128190; Kaydet</button>"
    "<button class='btn-s btn-d' onclick='delPkg()'>&#128465; Sil</button>"
    "<button class='btn-s' onclick='showAll()'>Tümünü Göster</button>"
    "</div></div>"
)

_TABLE_HTML = (
    "<div class='tbl-wrap'>"
    "<table id='fin-tbl'>"
    "<thead id='fin-thead'></thead>"
    "<tbody id='fin-tbody'></tbody>"
    "</table></div>"
)


def build_finansal_tablo_pane(m: dict, n: int) -> str:
    """İnteraktif finansal tablo HTML parçası — ana dashboard tab pane'ine gömülür."""
    ticker       = m.get("ticker", "")
    currency     = m.get("currency", "TRY")
    all_periods  = m.get("periods", [])
    raw_sections = m.get("_raw_sections", {})

    data_js = (
        f"const TICKER={json.dumps(ticker)};"
        f"const CURRENCY={json.dumps(currency)};"
        f"const ALL_PERIODS={json.dumps(all_periods, ensure_ascii=False)};"
        f"const RAW_SECTIONS={json.dumps(raw_sections, ensure_ascii=False)};"
        f"const SECTION_ORDER={json.dumps(_SECTION_ORDER)};"
        f"const SECTION_LABELS={json.dumps(_SECTION_LABELS, ensure_ascii=False)};"
        f"const DEFAULT_N={n};"
    )
    return (
        f"<style>{_FT_CSS}</style>"
        + _CTRL_BAR
        + _TABLE_HTML
        + f"<script>{data_js}\n{_FT_JS}</script>"
    )
