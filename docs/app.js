const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const PROFILE_KEY = 'airwindows-kome-profile-v1';
const profile = loadProfile();
let releases = [], catalog = [], installPrompt = null;

function loadProfile(){
  try { return JSON.parse(localStorage.getItem(PROFILE_KEY)) || {ratings:{},tried:{},weights:{},seenDiscover:{}}; }
  catch { return {ratings:{},tried:{},weights:{},seenDiscover:{}}; }
}
function saveProfile(){ localStorage.setItem(PROFILE_KEY, JSON.stringify(profile)); renderStats(); }
function feedbackCount(){ return Object.keys(profile.ratings).length; }
function categoryScore(categories=[]){
  if (!categories.length || feedbackCount() < 3) return null;
  const vals = categories.map(c => profile.weights[c] || 0);
  return vals.reduce((a,b)=>a+b,0) / Math.max(1, vals.length);
}
function matchLabel(item){
  const s = categoryScore(item.categories);
  if (s === null) return '相性：学習中';
  const pct = Math.max(5, Math.min(95, Math.round(50 + s * 18)));
  return `コメ向け度 ${pct}%`;
}
function rate(id, categories, value){
  const old = profile.ratings[id];
  if (old !== undefined) categories.forEach(c => profile.weights[c] = (profile.weights[c] || 0) - old);
  profile.ratings[id] = value;
  categories.forEach(c => profile.weights[c] = (profile.weights[c] || 0) + value);
  saveProfile(); renderAll();
}
function itemCard(item, kind='release'){
  const el = $('#itemTemplate').content.firstElementChild.cloneNode(true);
  const id = item.id;
  const title = item.title || item.name;
  const link = item.link || item.search_url;
  el.querySelector('.title').textContent = title;
  const jaPreview = item.description_ja && item.description_ja.split(/\n\s*\n/)[0];
  el.querySelector('.summary').textContent = jaPreview || item.summary_ja || '日本語説明を生成できませんでした。';
  const translated = el.querySelector('.translated-details');
  if (item.description_ja) {
    translated.hidden = false;
    translated.querySelector('.translated').textContent = item.description_ja;
  }
  el.querySelector('.original').textContent = item.description_original || item.excerpt_original || '原文なし';
  el.querySelector('.match').textContent = matchLabel(item);
  const date = item.published_at ? new Date(item.published_at).toLocaleString('ja-JP',{dateStyle:'medium'}) : '既存プラグイン';
  el.querySelector('.meta').textContent = `${date}${profile.tried[id] ? ' ・ 試した' : ''}`;
  if (profile.tried[id]) el.querySelector('.meta').classList.add('badge-tried');
  const chipWrap = el.querySelector('.chips');
  (item.categories || []).forEach(c => { const x=document.createElement('span'); x.className='chip'; x.textContent=c; chipWrap.append(x); });
  el.querySelectorAll('[data-rate]').forEach(btn => {
    const v = Number(btn.dataset.rate);
    if (profile.ratings[id] === v) btn.classList.add('selected');
    btn.onclick = () => rate(id, item.categories || [], v);
  });
  el.querySelector('[data-tried]').onclick = () => { profile.tried[id] = !profile.tried[id]; saveProfile(); renderAll(); };
  const a = el.querySelector('.official'); a.href = link; a.textContent = kind === 'release' ? '公式記事を見る' : '公式で検索';
  return el;
}
function renderList(target, items, kind){
  target.innerHTML='';
  if(!items.length){ target.innerHTML='<div class="empty">まだここには何もない。</div>'; return; }
  items.forEach(x=>target.append(itemCard(x,kind)));
}
function renderNew(){
  let items=[...releases];
  if($('#newSort').value==='match') items.sort((a,b)=>(categoryScore(b.categories)??-999)-(categoryScore(a.categories)??-999));
  renderList($('#newList'),items,'release');
}
function dailySeed(){ const d=new Date(); return Number(`${d.getFullYear()}${d.getMonth()+1}${d.getDate()}`); }
function seededShuffle(arr, seed){
  const out=[...arr]; let x=seed||1;
  for(let i=out.length-1;i>0;i--){ x=(x*1664525+1013904223)%4294967296; const j=x%(i+1); [out[i],out[j]]=[out[j],out[i]]; }
  return out;
}
function discoveryCandidates(extra=0){
  const unrated = catalog.filter(x => profile.ratings[x.id] === undefined);
  const rated = catalog.filter(x => profile.ratings[x.id] !== undefined);
  const pool = [...seededShuffle(unrated,dailySeed()+extra), ...seededShuffle(rated,dailySeed()+777+extra)];
  // Once learned, gently promote matching items without eliminating surprises.
  return pool.slice(0,24).sort((a,b)=>((categoryScore(b.categories)??0)-(categoryScore(a.categories)??0))*0.25).slice(0,5);
}
let reroll=0;
function renderDiscover(){ renderList($('#discoverList'),discoveryCandidates(reroll),'catalog'); }
function renderFavorites(){
  const all=[...releases,...catalog];
  renderList($('#favoriteList'),all.filter(x=>(profile.ratings[x.id]||0)>=1),'catalog');
}
function renderWeights(){
  const w=$('#weights'); w.innerHTML='';
  const entries=Object.entries(profile.weights).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).slice(0,12);
  if(!entries.length){w.innerHTML='<div class="muted">まだ学習データなし。</div>';return;}
  const max=Math.max(1,...entries.map(([,v])=>Math.abs(v)));
  entries.forEach(([name,v])=>{const row=document.createElement('div');row.className='weight-row';const width=Math.abs(v)/max*100;row.innerHTML=`<span>${name}</span><div class="bar"><i style="width:${width}%"></i></div><b>${v>0?'+':''}${v}</b>`;w.append(row);});
}
function renderStats(){ $('#feedbackCount').textContent=feedbackCount(); renderWeights(); }
function renderAll(){ renderNew(); renderDiscover(); renderFavorites(); renderStats(); }
async function loadData(){
  try{
    const [r,c,s]=await Promise.all([
      fetch('./data/releases.json',{cache:'no-store'}).then(x=>x.json()),
      fetch('./data/catalog.json',{cache:'no-store'}).then(x=>x.json()),
      fetch('./data/status.json',{cache:'no-store'}).then(x=>x.json())
    ]);
    releases=r.items||[]; catalog=c.items||[];
    $('#statusDot').classList.add('ok');
    $('#statusText').textContent=`最終確認 ${new Date(s.last_checked_at).toLocaleString('ja-JP')} ・ 新規 ${s.new_count||0}件`;
  }catch(e){ $('#statusText').textContent='データ取得に失敗。オフライン表示中。'; }
  renderAll();
}
$$('.tab').forEach(btn=>btn.onclick=()=>{$$('.tab').forEach(x=>x.classList.remove('active'));$$('.panel').forEach(x=>x.classList.remove('active'));btn.classList.add('active');$(`#panel-${btn.dataset.tab}`).classList.add('active');});
$('#newSort').onchange=renderNew;
$('#rerollBtn').onclick=()=>{reroll++;renderDiscover();};
$('#resetBtn').onclick=()=>{if(confirm('好み学習をリセットしますか？')){localStorage.removeItem(PROFILE_KEY);location.reload();}};
$('#exportBtn').onclick=()=>{const blob=new Blob([JSON.stringify(profile,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='airwindows-kome-profile.json';a.click();URL.revokeObjectURL(a.href);};
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('#installBtn').hidden=false;});
$('#installBtn').onclick=async()=>{if(installPrompt){installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('#installBtn').hidden=true;}};
if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js');
loadData();
