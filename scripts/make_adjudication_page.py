import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from gold import CODEBOOK

AG = ROOT / "data/processed/agreement"
SHEETS = {
    "codebook": (AG / "gold_disagreements_gold_sheet_v1.csv", ROOT / "data/annotation/gold_sheet_v1_adjudicated.csv"),
    "components": (AG / "gold_disagreements_gold_components_v1.csv", ROOT / "data/annotation/gold_components_v1_adjudicated.csv"),
}


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def codebook_text():
    md = (ROOT / "docs/codebook_v1.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^## \d+\. (\w+) .*?$(.*?)(?=^## |\Z)", md, re.S | re.M):
        body = m.group(2).split("<!-- EXAMPLES")[0].strip()
        out[m.group(1)] = body
    return out


def components():
    return {r["component_id"]: r for r in read(ROOT / "lexicon/components.csv")}


def main():
    cb, comps, items = codebook_text(), components(), []
    for sheet, (dis_path, adj_path) in SHEETS.items():
        ctx = {r["gold_id"]: r for r in read(adj_path)}
        for r in read(dis_path):
            c = ctx.get(r["gold_id"], {})
            if sheet == "codebook":
                values, help_ = CODEBOOK[r["field"]], cb.get(r["field"], "")
            else:
                comp = comps.get(r["field"], {})
                values = ["0", "1"]
                help_ = (f"**{r['field']}** = 1 when the clause carries this meaning: \"{comp.get('gloss_primes', '')}\".\n"
                         f"Hindi example: {comp.get('example_hi', '')}. English example: {comp.get('example_en', '')}.\n"
                         "0 = the clause does not carry it.")
            items.append(dict(sheet=sheet, gold_id=r["gold_id"], lang=r["lang"], field=r["field"],
                              coder1=r["coder1"], coder2=r["coder2"], values=values, help=help_,
                              before=c.get("context_before", ""), clause=c.get("clause_text", r.get("clause_text", "")),
                              after=c.get("context_after", "")))
    html = TEMPLATE.replace("__DATA__", json.dumps(items, ensure_ascii=False))
    out = AG / "adjudicate.html"
    out.write_text(html, encoding="utf-8")
    n = {s: sum(i["sheet"] == s for i in items) for s in SHEETS}
    print(f"{len(items)} disagreements ({n['codebook']} codebook, {n['components']} components) -> {out}")


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gold-set adjudication</title>
<style>
:root{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e1da;--a:#0b6e4f;--b:#1f4e9c;--warn:#b54708}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,system-ui,"Noto Sans Devanagari",sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:20px 16px 80px}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
h1{font-size:20px;margin:0;flex:1}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin:6px 0 16px}.bar i{display:block;height:100%;background:var(--a)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:14px}
.meta{color:var(--mute);font-size:14px;display:flex;gap:14px;flex-wrap:wrap}
.ctx{color:var(--mute)}.clause{font-size:20px;font-weight:600;background:#fff7d6;padding:2px 4px;border-radius:4px}
.field{font-size:18px;margin:4px 0 10px}.field b{font-family:ui-monospace,Menlo,monospace}
.choices{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}
button{font:inherit;border-radius:10px;border:1px solid var(--line);background:#fff;padding:14px;cursor:pointer}
.choice{font-size:18px;text-align:left}.choice small{display:block;color:var(--mute);font-size:13px}
.choice.sel{outline:3px solid var(--a);background:#eef8f3}
.other{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
select,input,textarea{font:inherit;padding:8px;border-radius:8px;border:1px solid var(--line);background:#fff}
textarea{width:100%;min-height:44px}
details{margin-top:10px}summary{cursor:pointer;color:var(--b)}pre{white-space:pre-wrap;font:14px/1.5 inherit;background:#faf9f5;padding:10px;border-radius:8px}
nav{display:flex;gap:10px;justify-content:space-between;flex-wrap:wrap}
.primary{background:var(--a);color:#fff;border-color:var(--a)}.warn{color:var(--warn)}
.tag{font-size:12px;padding:2px 8px;border-radius:999px;background:#eef1f8;color:var(--b)}
@media(max-width:600px){.choices{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<header><h1>Gold-set adjudication</h1>
<label>Decided by <input id="who" placeholder="names" size="18"></label>
<button id="dl" class="primary">Download decisions</button>
<label class="tag" style="cursor:pointer">Load saved CSV<input id="up" type="file" accept=".csv" hidden></label></header>
<div class="meta"><span id="count"></span><span id="left"></span><span>Keys: <b>1</b> coder 1, <b>2</b> coder 2, <b>&larr; &rarr;</b> move</span></div>
<div class="bar"><i id="prog"></i></div>
<div class="card" id="card"></div>
<nav><button id="prev">&larr; Previous</button><button id="skip">Next undecided</button><button id="next">Next &rarr;</button></nav>
<p class="meta" style="margin-top:18px">Decisions save in this browser automatically. When you finish, press <b>Download decisions</b> and put the file
<code>adjudication_decisions.csv</code> in <code>grief-hi-en-corpus/data/processed/agreement/</code>.</p>
</div>
<script>
const ITEMS=__DATA__;const KEY="grasp_adjudication_v1";
let st={i:0,d:{},who:""};try{st=Object.assign(st,JSON.parse(localStorage.getItem(KEY)||"{}"))}catch(e){}
const id=it=>it.sheet+"|"+it.gold_id+"|"+it.field;
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}};
const $=s=>document.querySelector(s);$("#who").value=st.who||"";$("#who").oninput=e=>{st.who=e.target.value;save()};
const esc=s=>(s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function render(){const it=ITEMS[st.i],k=id(it),d=st.d[k]||{};const done=Object.keys(st.d).filter(x=>st.d[x].value).length;
$("#count").textContent=`Item ${st.i+1} of ${ITEMS.length}`;$("#left").textContent=`${done} decided, ${ITEMS.length-done} left`;$("#prog").style.width=(100*done/ITEMS.length)+"%";
const others=it.values.filter(v=>v!==it.coder1&&v!==it.coder2);
$("#card").innerHTML=`<div class="meta"><span class="tag">${it.sheet==="codebook"?"Codebook field":"Semantic component"}</span><span>${it.lang==="hi"?"Hindi":"English"}</span><span>${it.gold_id}</span></div>
<p><span class="ctx">${esc(it.before)}</span> <span class="clause">${esc(it.clause)}</span> <span class="ctx">${esc(it.after)}</span></p>
<div class="field">Field: <b>${it.field}</b></div>
<div class="choices"><button class="choice ${d.value===it.coder1&&d.src!=="other"?"sel":""}" data-v="${esc(it.coder1)}" data-s="coder1"><small>Coder 1 (key 1)</small>${esc(it.coder1)||"(blank)"}</button>
<button class="choice ${d.value===it.coder2&&d.src!=="other"?"sel":""}" data-v="${esc(it.coder2)}" data-s="coder2"><small>Coder 2 (key 2)</small>${esc(it.coder2)||"(blank)"}</button></div>
<div class="other">Neither is right: <select id="oth"><option value="">choose another value</option>${others.map(v=>`<option ${d.src==="other"&&d.value===v?"selected":""}>${v}</option>`).join("")}</select></div>
<p><textarea id="note" placeholder="Note (optional): why">${esc(d.note||"")}</textarea></p>
<details><summary>Codebook definition for ${it.field}</summary><pre>${esc(it.help)}</pre></details>`;
document.querySelectorAll(".choice").forEach(b=>b.onclick=()=>pick(b.dataset.v,b.dataset.s));
$("#oth").onchange=e=>{if(e.target.value)pick(e.target.value,"other")};
$("#note").oninput=e=>{st.d[k]=Object.assign(st.d[k]||{},{note:e.target.value});save()};}
function pick(v,s){const k=id(ITEMS[st.i]);st.d[k]=Object.assign(st.d[k]||{},{value:v,src:s});save();if(st.i<ITEMS.length-1)st.i++;save();render()}
function go(n){st.i=Math.max(0,Math.min(ITEMS.length-1,n));save();render()}
$("#prev").onclick=()=>go(st.i-1);$("#next").onclick=()=>go(st.i+1);
$("#skip").onclick=()=>{for(let j=1;j<=ITEMS.length;j++){const n=(st.i+j)%ITEMS.length;if(!(st.d[id(ITEMS[n])]||{}).value){go(n);return}}alert("All items decided. Press Download decisions.")};
document.addEventListener("keydown",e=>{if(e.target.tagName==="TEXTAREA"||e.target.tagName==="INPUT")return;const it=ITEMS[st.i];
if(e.key==="1")pick(it.coder1,"coder1");if(e.key==="2")pick(it.coder2,"coder2");if(e.key==="ArrowRight")go(st.i+1);if(e.key==="ArrowLeft")go(st.i-1)});
const q=s=>'"'+String(s??"").replace(/"/g,'""')+'"';
$("#dl").onclick=()=>{const rows=[["sheet","gold_id","lang","field","coder1","coder2","decision","source","decided_by","note"]];
ITEMS.forEach(it=>{const d=st.d[id(it)]||{};rows.push([it.sheet,it.gold_id,it.lang,it.field,it.coder1,it.coder2,d.value||"",d.src||"",st.who||"",d.note||""])});
const blob=new Blob(["﻿"+rows.map(r=>r.map(q).join(",")).join("\n")],{type:"text/csv"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="adjudication_decisions.csv";a.click()};
$("#up").onchange=e=>{const f=e.target.files[0];if(!f)return;f.text().then(t=>{const lines=t.replace(/^﻿/,"").split(/\r?\n/).slice(1);
const parse=l=>{const o=[];let c="",q=false;for(let i=0;i<l.length;i++){const ch=l[i];if(q){if(ch=='"'&&l[i+1]=='"'){c+='"';i++}else if(ch=='"')q=false;else c+=ch}else if(ch==','){o.push(c);c=""}else if(ch=='"')q=true;else c+=ch}o.push(c);return o};
lines.filter(Boolean).forEach(l=>{const r=parse(l);if(r[6])st.d[r[0]+"|"+r[1]+"|"+r[3]]={value:r[6],src:r[7],note:r[9]}});save();render()})};
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
