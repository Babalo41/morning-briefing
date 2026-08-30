"use strict";
/*═══════════════════════════════════════════════════════════════════
  Morning Briefing — render engine.
  All content comes from window.EDITION_DATA (defined in data.js):
    { editions:[...], glossary:{...}, charts:{...}, learn:[...], generated_at }
  See DATA_SCHEMA.md for the exact shape. Nothing in this file should
  need to change when tonight's content changes — only data.js does.
═══════════════════════════════════════════════════════════════════*/

const DATA = window.EDITION_DATA || { editions: [], glossary: {}, charts: {}, learn: [], generated_at: null };
const EDITIONS = DATA.editions || [];
const G = DATA.glossary || {};
const CHARTS = DATA.charts || {};
const LEARN = DATA.learn || [];

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const strip=h=>String(h).replace(/<[^>]*>/g,"");
const cv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const store={
  get(k,d){try{const v=localStorage.getItem("bb2."+k);return v==null?d:JSON.parse(v)}catch(_){return d}},
  set(k,v){try{localStorage.setItem("bb2."+k,JSON.stringify(v))}catch(_){}},
  del(k){try{localStorage.removeItem("bb2."+k)}catch(_){}}
};
let stars=store.get("stars",[]), reads=store.get("reads",[]);
let curEd=EDITIONS.length?EDITIONS[0].id:null, curTab="today", filter="all", query="";
const uid=(ed,bi,ii)=>ed+"|"+bi+"|"+ii;
let storyGroups=[], storyGi=0, storySi=0, storyEdId=null;
let storyTimer=null, storyRemainMs=0, storyStartTs=0;

/*═══════════════════════════════════════════════════════════════════
  ENCRYPTION GATE — sensitive blocks/items ship as
  { encrypted:true, ciphertext, iv, salt } (all base64) instead of
  plain fields. A passphrase (entered once, cached in localStorage on
  this device only) derives an AES-GCM key via PBKDF2-SHA256 to
  decrypt them in place. Decrypted fields are merged directly onto
  the data object so re-renders just see plain content afterward.
═══════════════════════════════════════════════════════════════════*/
const b64ToBuf = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0));

async function deriveKey(passphrase, saltB64) {
  const salt = b64ToBuf(saltB64);
  const baseKey = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    baseKey, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
}

async function decryptNode(node, passphrase) {
  const key = await deriveKey(passphrase, node.salt);
  const iv = b64ToBuf(node.iv);
  const ct = b64ToBuf(node.ciphertext);
  const plainBuf = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return JSON.parse(new TextDecoder().decode(plainBuf));
}

function collectEncrypted() {
  const nodes = [];
  EDITIONS.forEach(ed => (ed.blocks || []).forEach(b => {
    if (b.encrypted) nodes.push(b);
    (b.items || []).forEach(it => { if (it.encrypted) nodes.push(it); });
  }));
  return nodes;
}

async function unlockAll(passphrase) {
  const nodes = collectEncrypted();
  if (!nodes.length) return { tried: 0, ok: 0 };
  let ok = 0;
  for (const node of nodes) {
    try {
      const plain = await decryptNode(node, passphrase);
      delete node.encrypted; delete node.ciphertext; delete node.iv; delete node.salt;
      Object.assign(node, plain);
      ok++;
    } catch (_) { /* wrong passphrase or corrupt payload — leave locked */ }
  }
  return { tried: nodes.length, ok };
}

function lockAll() {
  store.del("passphrase");
  location.reload();
}

function updateLockButton() {
  const btn = $("#lockBtn");
  const hasLocked = collectEncrypted().length > 0;
  btn.hidden = !hasLocked;
  btn.classList.toggle("locked", hasLocked);
  btn.classList.toggle("unlocked", !hasLocked);
  btn.setAttribute("aria-label", hasLocked ? "Unlock personal data" : "Personal data unlocked");
}

function lockPrompt(errorMsg) {
  $("#sheetIn").innerHTML = `<button class="shx" id="shx" aria-label="Close">✕</button>
    <div class="mk"></div><h5>Personal sections are locked</h5>
    <div class="lockform" style="box-shadow:none;border:0;padding:0;margin:0">
      <p>Enter the passphrase to unlock health, family and other personal sections on this device. It's remembered here only — never sent anywhere.</p>
      <div class="row2">
        <input type="password" id="passInput" placeholder="Passphrase" autocomplete="current-password">
        <button id="unlockGo">Unlock</button>
      </div>
      ${errorMsg ? `<div class="err">${esc(errorMsg)}</div>` : ""}
    </div>`;
  $("#sheet").classList.add("on"); $("#scrim").classList.add("on");
  $("#shx").onclick = closeSheet;
  const input = $("#passInput");
  input.focus();
  const submit = async () => {
    const pass = input.value;
    if (!pass) return;
    const res = await unlockAll(pass);
    if (res.ok > 0) { store.set("passphrase", pass); closeSheet(); paint(); }
    else lockPrompt("Wrong passphrase — try again.");
  };
  $("#unlockGo").onclick = submit;
  input.addEventListener("keydown", e => { if (e.key === "Enter") submit(); });
}

/* ── charts ── */
function barChart(d){
  const W=520,rowH=36,pT=6,pB=8,pR=58,pL=d.catW||120,H=pT+d.rows.length*rowH+pB;
  const max=Math.max(...d.rows.map(r=>r.v))*1.14, x=v=>pL+(v/max)*(W-pL-pR);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto">`;
  [.5,1].forEach(f=>{const g=x(max*f);s+=`<line class="grid" x1="${g}" y1="${pT}" x2="${g}" y2="${pT+d.rows.length*rowH}"/>`});
  d.rows.forEach((r,i)=>{
    const y=pT+i*rowH,bh=16,by=y+(rowH-bh)/2,c=r.hero?cv('--red'):cv('--rec'),w=r.v<=0?0:Math.max(2,x(r.v)-pL);
    s+=`<text class="lbl" x="${pL-11}" y="${by+bh-3}" text-anchor="end">${esc(r.k)}</text>`;
    if(w)s+=`<rect x="${pL}" y="${by}" width="${w}" height="${bh}" fill="${c}" rx="2"/>`;
    s+=`<text class="dlbl" x="${pL+w+8}" y="${by+bh-3}" fill="${c}">${esc(r.lab)}</text>`;
    s+=`<rect class="hit" x="0" y="${y}" width="${W}" height="${rowH}" data-tip="${esc(r.k+' — '+(r.tip||r.lab))}"/>`});
  return s+`<line class="base" x1="${pL}" y1="${pT}" x2="${pL}" y2="${pT+d.rows.length*rowH}"/></svg>`;
}
function rangeChart(d){
  const W=520,rowH=42,pT=10,pB=26,pR=22,pL=d.catW||150,H=pT+d.rows.length*rowH+pB;
  const hi=Math.max(...d.rows.map(r=>r.hi))*1.1, x=v=>pL+(v/hi)*(W-pL-pR);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto">`;
  (d.ticks||[]).forEach(t=>{s+=`<line class="grid" x1="${x(t)}" y1="${pT}" x2="${x(t)}" y2="${pT+d.rows.length*rowH}"/>
    <text class="lbl" x="${x(t)}" y="${pT+d.rows.length*rowH+15}" text-anchor="middle">${t}</text>`});
  d.rows.forEach((r,i)=>{
    const y=pT+i*rowH+rowH/2-3,c=r.hero?cv('--red'):cv('--rec');
    s+=`<text class="lbl" x="${pL-11}" y="${y+4}" text-anchor="end">${esc(r.k)}</text>
      <line x1="${x(r.lo)}" y1="${y}" x2="${x(r.hi)}" y2="${y}" stroke="${c}" stroke-width="3"/>
      <circle cx="${x(r.lo)}" cy="${y}" r="5" fill="${c}" stroke="${cv('--chartbg')}" stroke-width="2"/>
      <circle cx="${x(r.hi)}" cy="${y}" r="5" fill="${c}" stroke="${cv('--chartbg')}" stroke-width="2"/>
      <text class="dlbl" x="${x(r.lo)}" y="${y-10}" fill="${c}" text-anchor="middle">${r.lo}</text>
      <text class="dlbl" x="${x(r.hi)}" y="${y-10}" fill="${c}" text-anchor="middle">${r.hi}</text>
      <rect class="hit" x="0" y="${pT+i*rowH}" width="${W}" height="${rowH}" data-tip="${esc(r.k+' — €'+r.lo+'k to €'+r.hi+'k')}"/>`});
  return s+`<line class="base" x1="${pL}" y1="${pT+d.rows.length*rowH}" x2="${W-pR}" y2="${pT+d.rows.length*rowH}"/></svg>`;
}
function lineChart(d){
  const W=520,H=200,pT=12,pB=28,pL=36,pR=50;
  const xs=d.series[0].pts.map(p=>p[0]),xmin=Math.min(...xs),xmax=Math.max(...xs);
  const ymax=Math.max(...d.series.flatMap(s=>s.pts.map(p=>p[1])))*1.2;
  const X=v=>pL+((v-xmin)/(xmax-xmin||1))*(W-pL-pR), Y=v=>pT+(1-v/ymax)*(H-pT-pB);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto">`;
  (d.yticks||[]).forEach(t=>{s+=`<line class="grid" x1="${pL}" y1="${Y(t)}" x2="${W-pR}" y2="${Y(t)}"/>
    <text class="lbl" x="${W-pR+8}" y="${Y(t)+4}">${t}</text>`});
  d.series.forEach(se=>{
    const c=se.hero?cv('--red'):cv('--blue');
    s+=`<polyline fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"
      points="${se.pts.map(p=>X(p[0])+','+Y(p[1])).join(' ')}"/>`;
    se.pts.forEach(p=>{s+=`<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="4" fill="${c}" stroke="${cv('--chartbg')}" stroke-width="2"/>`});
    const L=se.pts[se.pts.length-1];
    s+=`<text class="dlbl" x="${X(L[0])-6}" y="${Y(L[1])-11}" fill="${c}" text-anchor="end">${esc(se.name)}</text>`});
  d.series[0].pts.forEach((p,i)=>{
    s+=`<rect class="hit" x="${X(p[0])-17}" y="${pT}" width="34" height="${H-pT-pB}"
      data-tip="${esc(d.xlabels[i]+': '+d.series.map(se=>se.name+' '+se.pts[i][1]).join(' · '))}"/>
      <text class="lbl" x="${X(p[0])}" y="${Y(0)+16}" text-anchor="middle">${esc(d.xlabels[i])}</text>`});
  return s+`<line class="base" x1="${pL}" y1="${Y(0)}" x2="${W-pR}" y2="${Y(0)}"/></svg>`;
}
function chartCard(k){
  const d=CHARTS[k]; if(!d)return"";
  const svg=d.kind==='bar'?barChart(d):d.kind==='range'?rangeChart(d):lineChart(d);
  return `<div class="cc"><div class="mk"></div><h4>${esc(d.title)}</h4>
    <p class="sb">${esc(d.sub)}</p><div class="sc">${svg}</div>
    <p class="sr">Source: ${esc(d.source)}</p></div>`;
}

/* ── item rendering ── */
const starSvg=`<svg viewBox="0 0 24 24"><path d="m12 3 2.7 5.8 6.3.8-4.6 4.4 1.2 6.2L12 17.3 6.4 20.2l1.2-6.2L3 9.6l6.3-.8Z"/></svg>`;
const lockSvg=`<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>`;
const REL_LABEL={home:"Home",family:"Family",friend:"Friend",interest:"Interest"};
function tagBadgeHTML(it){
  // it.tag/it.rel come from Tagged Interests (config/interests.yaml) —
  // only present on items a tag-aware section (e.g. Near Home) produced.
  // See TAGGED_INTERESTS_ARCHITECTURE.md.
  if(!it.tag)return"";
  const rel=it.rel||"interest";
  return `<span class="tagbadge" data-rel="${esc(rel)}">${esc(it.tag)} · ${REL_LABEL[rel]||"Interest"}</span>`;
}
function itemHTML(it,id,pri){
  if (it.encrypted) {
    return `<div class="row" data-id="${id}">
      <button class="lockrow" data-act="unlock">${lockSvg}<span>Locked — tap to unlock</span></button>
    </div>`;
  }
  const on=stars.includes(id), rd=reads.includes(id);
  const src=it.u?`<a class="src" href="${it.u}" target="_blank" rel="noopener">${esc(it.src)}</a>`
                :`<span class="src">${esc(it.src)}</span>`;
  return `<div class="row${pri?" pri":""}${rd?" done":""}" data-id="${id}">
      <button class="rowbtn" data-act="open"><span class="dot"></span><span class="rowtx">
        <h4>${esc(it.t)}</h4>${tagBadgeHTML(it)}<p class="pv">${esc(strip(it.b))}</p></span></button>
      <button class="star" data-act="star" aria-pressed="${on}" aria-label="Save">${starSvg}</button>
    </div>
    <div class="body"><p class="tx">${it.b} ${src}</p>
      ${it.teach?`<details class="teach"><summary>${esc(it.teach.s)}</summary>
        <div class="tb">${it.teach.b}</div></details>`:""}</div>`;
}
function match(it,b,ed){
  if(!query)return true;
  if(it.encrypted)return false;
  const q=query.toLowerCase();
  return (it.t+" "+strip(it.b)+" "+b.h+" "+ed.date).toLowerCase().includes(q);
}

/* ── stories (Instagram-style swipe-through) ── */
function buildStoryGroups(ed){
  const groups=[{h:"Today",special:"lede",items:[{}]}];
  ed.blocks.forEach((b,bi)=>{
    if(b.encrypted)return;
    const items=(b.items||[]).map((it,ii)=>({it,ii})).filter(o=>!o.it.encrypted);
    if(!items.length)return;
    groups.push({h:b.h,bi,items});
  });
  return groups;
}
function renderStoryRail(ed){
  const groups=buildStoryGroups(ed);
  return `<div class="srail">${groups.map((g,gi)=>{
    const unread=g.special==="lede"?!reads.includes("lede|"+ed.id)
      :g.items.some(o=>!reads.includes(uid(ed.id,g.bi,o.ii)));
    const letter=g.special==="lede"?"☀":g.h.charAt(0);
    return `<button class="sring${unread?" unread":""}" data-act="story" data-si="${gi}">
      <span class="sc"><span>${esc(letter)}</span></span>
      <span class="lab">${esc(g.special==="lede"?"Today":g.h)}</span>
    </button>`;
  }).join("")}</div>`;
}
function openStories(startGi){
  const ed=EDITIONS.find(e=>e.id===curEd); if(!ed||ed.encrypted)return;
  storyGroups=buildStoryGroups(ed); storyEdId=ed.id;
  storyGi=Math.min(Math.max(0,startGi||0),storyGroups.length-1);
  storySi=0;
  $("#stories").classList.add("on"); $("#stories").classList.remove("paused");
  $("#stories").setAttribute("aria-hidden","false");
  renderStorySlide();
}
function closeStories(){
  clearTimeout(storyTimer);
  $("#stories").classList.remove("on","paused");
  $("#stories").setAttribute("aria-hidden","true");
  paint();
}
function armStoryTimer(ms){
  clearTimeout(storyTimer);
  storyRemainMs=ms; storyStartTs=Date.now();
  storyTimer=setTimeout(nextStory,ms);
}
function pauseStories(){
  $("#stories").classList.add("paused");
  clearTimeout(storyTimer);
  storyRemainMs=Math.max(50,storyRemainMs-(Date.now()-storyStartTs));
}
function resumeStories(){
  $("#stories").classList.remove("paused");
  storyStartTs=Date.now();
  storyTimer=setTimeout(nextStory,storyRemainMs);
}
function nextStory(){
  const g=storyGroups[storyGi]; if(!g)return closeStories();
  if(storySi<g.items.length-1){storySi++}
  else if(storyGi<storyGroups.length-1){storyGi++;storySi=0}
  else return closeStories();
  renderStorySlide();
}
function prevStory(){
  if(storySi>0){storySi--}
  else if(storyGi>0){storyGi--;storySi=storyGroups[storyGi].items.length-1}
  else return;
  renderStorySlide();
}
function renderStorySlide(){
  const g=storyGroups[storyGi]; if(!g)return closeStories();
  const ed=EDITIONS.find(e=>e.id===storyEdId); if(!ed)return closeStories();
  $("#stSegs").innerHTML=g.items.map((_,i)=>
    `<div class="sseg"><span class="sfill ${i<storySi?"done":i===storySi?"run":""}"></span></div>`).join("");
  $("#stSec").textContent=g.h;
  $("#stCnt").textContent=(storyGi+1)+"/"+storyGroups.length;
  $("#stStage").querySelector(".st-star")?.remove();
  let cardHtml, words;
  if(g.special==="lede"){
    if(!reads.includes("lede|"+ed.id)){reads=[...reads,"lede|"+ed.id];store.set("reads",reads)}
    cardHtml=`<div class="sk">${esc(ed.date)}</div><h2>${esc(ed.headline)}</h2><p>${esc(ed.stand)}</p>`;
    words=strip(ed.stand).split(/\s+/).length;
  } else {
    const {it,ii}=g.items[storySi];
    const id=uid(ed.id,g.bi,ii);
    if(!reads.includes(id)){reads=[...reads,id];store.set("reads",reads)}
    const on=stars.includes(id);
    const src=it.u?`<a class="ssrc sctrl" href="${it.u}" target="_blank" rel="noopener">${esc(it.src)}</a>`
                  :`<span class="ssrc">${esc(it.src)}</span>`;
    cardHtml=`<div class="sk">${esc(g.h)}</div><h2>${esc(it.t)}</h2><p>${it.b}</p>${src}`;
    $("#stStage").insertAdjacentHTML("beforeend",
      `<button class="st-star sctrl" data-act="ststar" data-id="${id}" aria-pressed="${on}" aria-label="Save">${starSvg}</button>`);
    words=strip(it.b).split(/\s+/).length;
  }
  $("#stCard").innerHTML=cardHtml;
  wireTerms();
  const ms=Math.max(3500,Math.min(10000,words*220));
  const run=$("#stSegs .sfill.run");
  if(run)run.style.setProperty("--sdur",ms+"ms");
  armStoryTimer(ms);
}
let sdX=0,sdY=0,sdT=0,sHoldTimer=null,sIsHold=false,sDown=false;
function stageDown(e){
  if(e.target.closest(".sctrl")){sDown=false;return}
  sDown=true;sdX=e.clientX;sdY=e.clientY;sdT=Date.now();sIsHold=false;
  clearTimeout(sHoldTimer);
  sHoldTimer=setTimeout(()=>{sIsHold=true;pauseStories()},220);
}
function stageUp(e){
  if(!sDown)return; sDown=false; clearTimeout(sHoldTimer);
  if(sIsHold){resumeStories();return}
  const dx=e.clientX-sdX, dy=e.clientY-sdY;
  if(Math.abs(dy)>80&&Math.abs(dy)>Math.abs(dx)){closeStories();return}
  if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)){dx<0?nextStory():prevStory();return}
  const rect=$("#stStage").getBoundingClientRect();
  const relX=(e.clientX-rect.left)/rect.width;
  relX<0.3?prevStory():nextStory();
}
$("#stStage").addEventListener("pointerdown",stageDown);
$("#stStage").addEventListener("pointerup",stageUp);
$("#stStage").addEventListener("pointercancel",()=>{sDown=false;clearTimeout(sHoldTimer);resumeStories()});

/* ── panels ── */
function renderToday(){
  if(!EDITIONS.length){$("#p-today").innerHTML=`<p class="empty">No edition yet. The pipeline hasn't run.</p>`;return}
  const ed=EDITIONS.find(e=>e.id===curEd)||EDITIONS[0];
  if(ed.encrypted){
    $("#p-today").innerHTML=`<div class="lockform"><p>This edition is locked.</p>
      <button class="rowbtn" data-act="unlock" style="padding:0">${lockSvg} Tap to unlock</button></div>`;
    return;
  }
  const secs=ed.blocks.map(b=>b.h);
  let h=`<div class="lede" data-act="story" data-si="0"><div class="d">${esc(ed.date)}</div>
    <h2>${esc(ed.headline)}</h2><p>${esc(ed.stand)}</p></div>`;
  h+=renderStoryRail(ed);
  h+=`<div class="chips"><button class="chip" data-f="all" aria-pressed="${filter==="all"}">All
    <span class="c">${ed.blocks.reduce((n,b)=>n+(b.encrypted?(b.count||0):b.items.length),0)}</span></button>`+
    secs.map(s=>{const b=ed.blocks.find(x=>x.h===s);
      return `<button class="chip" data-f="${esc(s)}" aria-pressed="${filter===s}">${esc(s)}
        <span class="c">${b.encrypted?(b.count||0):b.items.length}</span></button>`}).join("")+`</div>`;
  let any=false;
  ed.blocks.forEach((b,bi)=>{
    if(filter!=="all"&&b.h!==filter)return;
    if(b.encrypted){
      any=true;
      h+=`<section class="group"><div class="ghead"><h3>${esc(b.h)}</h3>
        <span class="n">${b.count||0}</span></div>
        <div class="list"><div class="row"><button class="lockrow" data-act="unlock">${lockSvg}
          <span>Locked — tap to unlock this section</span></button></div></div></section>`;
      return;
    }
    const its=b.items.map((it,ii)=>({it,ii})).filter(o=>match(o.it,b,ed));
    if(!its.length)return; any=true;
    h+=`<section class="group"><div class="ghead"><h3>${esc(b.h)}</h3>
      <span class="n">${its.length}</span></div>`;
    if(b.stats&&!query) h+=`<div class="stats">${b.stats.map(s=>
      `<div class="st"><div class="n">${esc(s.n)}</div><div class="l">${esc(s.l)}</div></div>`).join("")}</div>`;
    h+=`<div class="list">${its.map(o=>itemHTML(o.it,uid(ed.id,bi,o.ii),b.pri)).join("")}</div>`;
    if(b.chart&&!query)[].concat(b.chart).forEach(c=>h+=chartCard(c));
    if(b.go&&!query)h+=`<div style="padding:10px 2px 0"><a class="go" href="${seed(b.go.q)}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>${esc(b.go.label)}</a></div>`;
    h+=`</section>`;
  });
  if(!any)h+=`<p class="empty">Nothing matches “${esc(query)}” in this edition.<br>Try the Archive tab to search other days.</p>`;
  $("#p-today").innerHTML=h;
}
function renderLearn(){
  const done=store.get("done",[]);
  let h=`<p class="lintro">A library that grows. Tap a lesson to read it, tick it when it lands.
    Dotted words open an explainer you can hear spoken.</p>`;
  LEARN.forEach(c=>{
    const ls=c.lessons.map((l,i)=>({l,i})).filter(o=>!query||
      (o.l.t+" "+o.l.key+" "+strip(o.l.b)+" "+c.title).toLowerCase().includes(query.toLowerCase()));
    if(!ls.length)return;
    const n=c.lessons.filter((_,i)=>done.includes(c.id+"|"+i)).length;
    const pct=Math.round(n/c.lessons.length*100);
    h+=`<section class="course"><div class="chead">
        <div><h3>${esc(c.title)}</h3><p class="cblurb">${esc(c.blurb)}</p></div>
        <span class="cprog">${n}/${c.lessons.length}</span></div>
      <div class="pbar"><span style="width:${pct}%"></span></div>
      <div class="list">`;
    ls.forEach(o=>{
      const id=c.id+"|"+o.i, dn=done.includes(id);
      h+=`<div class="row lrow${dn?" done":""}" data-id="${id}">
          <button class="rowbtn" data-act="lopen"><span class="lnum">${String(o.i+1).padStart(2,"0")}</span>
            <span class="rowtx"><h4>${esc(o.l.t)}</h4><p class="pv">${esc(o.l.key)}</p></span></button>
          <button class="star tick" data-act="tick" aria-pressed="${dn}" aria-label="Mark read">
            <svg viewBox="0 0 24 24"><path d="M4 12.5 9.5 18 20 7"/></svg></button>
        </div>
        <div class="body lbody"><p class="lkey">${esc(o.l.key)}</p>${o.l.b}
          ${o.l.chart?chartCard(o.l.chart):""}</div>`;
    });
    h+=`</div></section>`;
  });
  if(!/class="course"/.test(h))h=`<p class="empty">Nothing in the library matches “${esc(query)}”.</p>`;
  $("#p-learn").innerHTML=h;
}
function renderSaved(){
  let rows=[];
  EDITIONS.forEach(ed=>{ if(ed.encrypted)return; (ed.blocks||[]).forEach((b,bi)=>{ if(b.encrypted)return; (b.items||[]).forEach((it,ii)=>{
    const id=uid(ed.id,bi,ii);
    if(stars.includes(id)&&match(it,b,ed))rows.push({it,id,ed,b});})})});
  $("#p-saved").innerHTML = rows.length
    ? `<div class="group"><div class="ghead"><h3>Saved</h3><span class="n">${rows.length}</span></div>
       <div class="list">${rows.map(r=>itemHTML(r.it,r.id,r.b.pri)).join("")}</div></div>`
    : `<p class="empty">Nothing saved yet.<br>Tap the star on any story to keep it here.</p>`;
}
function renderArchive(){
  const eds=EDITIONS.filter(e=>!query||e.encrypted||(e.headline+" "+e.date+" "+e.stand).toLowerCase().includes(query.toLowerCase()));
  $("#p-archive").innerHTML = eds.length
    ? `<div class="group"><div class="ghead"><h3>All editions</h3><span class="n">${EDITIONS.length}</span></div>
       <div class="arc">${eds.map(e=>`<button class="arcrow" data-ed="${e.id}" aria-current="${e.id===curEd}">
         <span class="arcd">${esc(e.day)}<b>${esc(e.dnum)}</b>${esc(e.mon)}</span>
         <span class="arct">${e.encrypted?"🔒 Locked edition":esc(e.headline)}</span></button>`).join("")}</div></div>`
    : `<p class="empty">No edition matches “${esc(query)}”.</p>`;
}
function renderGlossary(){
  const ks=Object.keys(G).filter(k=>!query||
    (G[k].t+" "+G[k].d+" "+G[k].resp).toLowerCase().includes(query.toLowerCase()))
    .sort((a,b)=>G[a].t.localeCompare(G[b].t));
  $("#p-glossary").innerHTML = ks.length
    ? `<div class="group"><div class="ghead"><h3>Terms explained</h3><span class="n">${ks.length}</span></div>
       <div class="gl">${ks.map(k=>`<button class="glrow" data-term="${k}">
         <span class="glt">${esc(G[k].t)}</span><span class="gli">${esc(G[k].ipa)}</span></button>`).join("")}</div></div>`
    : `<p class="empty">No term matches “${esc(query)}”.</p>`;
}
const seed=q=>`https://claude.ai/new?q=${encodeURIComponent(q)}&surface=cowork&composer=mini`;

/* ── tabs ── */
const TABS=[
 {k:"today",l:"Today",i:'<path d="M4 5h16v15H4z"/><path d="M4 9h16M9 5v15"/>'},
 {k:"learn",l:"Learn",i:'<path d="M4 5h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H4Z"/><path d="M20 5h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7Z"/>'},
 {k:"saved",l:"Saved",i:'<path d="m12 3 2.7 5.8 6.3.8-4.6 4.4 1.2 6.2L12 17.3 6.4 20.2l1.2-6.2L3 9.6l6.3-.8Z"/>'},
 {k:"archive",l:"Archive",i:'<path d="M3 7h18v13H3z"/><path d="M3 7l2-3h14l2 3M8 12h8"/>'},
 {k:"glossary",l:"Words",i:'<path d="M4 4h11a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3Z"/><path d="M8 9h6M8 13h6"/>'}
];
function renderTabs(){
  $("#tabsTop").innerHTML=TABS.map(t=>
    `<button class="tab" role="tab" data-t="${t.k}" aria-selected="${curTab===t.k}">${t.l}</button>`).join("");
  $("#tabsBot").innerHTML=TABS.map(t=>{
    const b=t.k==="saved"&&stars.length?`<span class="badge">${stars.length}</span>`:"";
    return `<button data-t="${t.k}" aria-selected="${curTab===t.k}">
      <svg viewBox="0 0 24 24">${t.i}</svg>${b}<span>${t.l}</span></button>`}).join("");
}
function paint(){
  renderTabs();
  renderToday();renderLearn();renderSaved();renderArchive();renderGlossary();
  TABS.forEach(t=>$("#p-"+t.k).classList.toggle("on",curTab===t.k));
  wireTerms();wireTips();updateLockButton();
  $("#stamp").textContent=EDITIONS.length?EDITIONS[0].dnum+" "+EDITIONS[0].mon:"";
}
function go(t){curTab=t;store.set("tab",t);paint();scrollTo({top:0,behavior:"smooth"})}

/* ── glossary sheet ── */
function wireTerms(){
  $$(".jt").forEach(n=>{
    const k=n.dataset.g; if(!G[k])return;
    const b=document.createElement("button");
    b.className="term";b.type="button";b.innerHTML=n.innerHTML;
    b.setAttribute("aria-label","Explain "+G[k].t);
    b.addEventListener("click",e=>{e.stopPropagation();openTerm(k)});
    n.replaceWith(b);
  });
}
function openTerm(k){
  const g=G[k];
  const phon=g.ipa||g.resp?`<span class="ipa">${esc(g.ipa)}</span><span class="resp">${esc(g.resp)}</span>`:"";
  $("#sheetIn").innerHTML=`<button class="shx" id="shx" aria-label="Close">✕</button>
    <div class="mk"></div><h5>${esc(g.t)}</h5>
    <div class="phon">${phon}<button class="say" id="say">▶ Hear it</button></div>
    <p class="def">${esc(g.d)}</p>
    <div class="why"><b>Why it matters to you</b>${esc(g.w)}</div>`;
  $("#sheet").classList.add("on");$("#scrim").classList.add("on");
  $("#shx").onclick=closeSheet;
  const sb=$("#say");
  if(!("speechSynthesis" in window))sb.style.display="none";
  else sb.onclick=()=>say(g,sb);
}
function say(g,btn){
  try{
    speechSynthesis.cancel();
    const u=new SpeechSynthesisUtterance(g.t);
    u.lang=g.lang||"en-GB";u.rate=.78;
    const v=speechSynthesis.getVoices().find(v=>v.lang.replace("_","-").startsWith(u.lang.slice(0,2)));
    if(v)u.voice=v;
    btn.classList.add("on");btn.textContent="▶ Speaking…";
    u.onend=u.onerror=()=>{btn.classList.remove("on");btn.textContent="▶ Hear it"};
    speechSynthesis.speak(u);
  }catch(_){btn.textContent="Not available"}
}
function closeSheet(){$("#sheet").classList.remove("on");$("#scrim").classList.remove("on");
  try{speechSynthesis.cancel()}catch(_){}}

/* ── chart tooltips ── */
function wireTips(){
  const tip=$("#tip");
  $$("svg .hit").forEach(r=>{
    const mv=ev=>{const p=ev.touches?ev.touches[0]:ev;
      tip.textContent=r.dataset.tip;tip.classList.add("on");
      const w=tip.offsetWidth,h=tip.offsetHeight;
      tip.style.left=Math.min(Math.max(8,p.clientX-w/2),innerWidth-w-8)+"px";
      tip.style.top=Math.max(8,p.clientY-h-12)+"px"};
    r.addEventListener("mousemove",mv);
    r.addEventListener("touchstart",mv,{passive:true});
    r.addEventListener("mouseleave",()=>tip.classList.remove("on"));
    r.addEventListener("touchend",()=>tip.classList.remove("on"));
  });
}

/* ── events ── */
document.addEventListener("click",e=>{
  const story=e.target.closest('[data-act="story"]'); if(story){openStories(Number(story.dataset.si));return}
  const stx=e.target.closest('[data-act="stclose"]'); if(stx){closeStories();return}
  const sts=e.target.closest('[data-act="ststar"]');
  if(sts){const id=sts.dataset.id;
    stars=stars.includes(id)?stars.filter(x=>x!==id):[...stars,id];
    store.set("stars",stars);sts.setAttribute("aria-pressed",stars.includes(id));return}
  const tab=e.target.closest("[data-t]"); if(tab){go(tab.dataset.t);return}
  const chip=e.target.closest(".chip"); if(chip){filter=chip.dataset.f;renderToday();wireTerms();wireTips();return}
  const arc=e.target.closest(".arcrow"); if(arc){curEd=arc.dataset.ed;store.set("ed",curEd);go("today");return}
  const gl=e.target.closest(".glrow"); if(gl){openTerm(gl.dataset.term);return}
  const unlock=e.target.closest('[data-act="unlock"]'); if(unlock){lockPrompt();return}
  const st=e.target.closest('[data-act="star"]');
  if(st){const id=st.closest(".row").dataset.id;
    stars=stars.includes(id)?stars.filter(x=>x!==id):[...stars,id];
    store.set("stars",stars);paint();return}
  const tk=e.target.closest('[data-act="tick"]');
  if(tk){const id=tk.closest(".row").dataset.id;let d=store.get("done",[]);
    d=d.includes(id)?d.filter(x=>x!==id):[...d,id];store.set("done",d);
    const wasOpen=tk.closest(".row").classList.contains("open");
    renderLearn();wireTerms();wireTips();
    if(wasOpen){const r=document.querySelector('.lrow[data-id="'+CSS.escape(id)+'"]');if(r)r.classList.add("open")}
    return}
  const lo=e.target.closest('[data-act="lopen"]');
  if(lo){lo.closest(".row").classList.toggle("open");return}
  const op=e.target.closest('[data-act="open"]');
  if(op){const row=op.closest(".row"),id=row.dataset.id;
    row.classList.toggle("open");
    if(!reads.includes(id)){reads=[...reads,id];store.set("reads",reads);row.classList.add("done")}
    return}
});
$("#lockBtn").addEventListener("click",()=>{
  if($("#lockBtn").classList.contains("unlocked")) lockAll();
  else lockPrompt();
});
$("#searchBtn").addEventListener("click",()=>{
  const w=$("#searchWrap"),on=!w.classList.contains("on");
  w.classList.toggle("on",on);$("#searchBtn").setAttribute("aria-pressed",on);
  if(on)$("#q").focus(); else{query="";$("#q").value="";paint()}
});
$("#q").addEventListener("input",e=>{query=e.target.value.trim();paint()});
$("#scrim").addEventListener("click",closeSheet);
document.addEventListener("keydown",e=>{
  if($("#stories").classList.contains("on")){
    if(e.key==="Escape")closeStories();
    else if(e.key==="ArrowRight")nextStory();
    else if(e.key==="ArrowLeft")prevStory();
    return;
  }
  if(e.key==="Escape")closeSheet();
});

if("speechSynthesis" in window){try{speechSynthesis.getVoices()}catch(_){}}

/* ── boot ── */
async function boot(){
  curTab=store.get("tab","today");
  const se=store.get("ed",null); if(se&&EDITIONS.some(e=>e.id===se))curEd=se;
  if(!TABS.some(t=>t.k===curTab))curTab="today";
  const savedPass=store.get("passphrase",null);
  if(savedPass) await unlockAll(savedPass);
  paint();
}
boot();
