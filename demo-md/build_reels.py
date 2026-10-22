"""Build the reels demos from reels.json:
  reels.html         chooser between the two formats
  reels-scroll.html  TikTok-style vertical feed
  reels-swipe.html   Tinder-style card stack (right = save for later, left = skip, up = read)

Reels are animated data scenes + on-device speech (Web Speech API) + word-by-word captions,
ending with a poll. A finite daily set ends on "You're up to date".
Usage: python build_reels.py
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
e = lambda s: html.escape(str(s or ""), quote=True)

HEAD = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%%TITLE%%</title>
<meta name="theme-color" content="#000000"><meta name="robots" content="noindex,nofollow">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800;900&family=Rubik:wght@400;500;700&display=swap" rel="stylesheet">
<style>%%CSS%%</style></head>'''

CSS = r"""
:root{--head:"Figtree",Arial,sans-serif;--ui:"Rubik",Arial,sans-serif;--ease:cubic-bezier(.32,.72,0,1);--red:#e12929;--yellow:#fff200}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#000;color:#fff;font-family:var(--head);-webkit-font-smoothing:antialiased;overflow:hidden}
a{color:inherit;text-decoration:none}button{font-family:inherit;-webkit-tap-highlight-color:transparent;cursor:pointer}a{-webkit-tap-highlight-color:transparent}
/* top bar */
.top{position:fixed;top:0;left:0;right:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:calc(env(safe-area-inset-top) + 8px) 14px 8px;font:500 13px var(--ui);background:linear-gradient(rgba(0,0,0,.65),transparent);pointer-events:none}
.top>*{pointer-events:auto}.top .back{display:flex;align-items:center;gap:4px;opacity:.9}
.top .ttl{font:800 14px var(--head);text-transform:uppercase;letter-spacing:.06em;text-align:center}.top .ttl small{display:block;font:400 11px var(--ui);text-transform:none;letter-spacing:0;opacity:.75}
.snd{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.14);border:0;color:#fff;display:grid;place-items:center}
/* reel player */
.reel{position:absolute;inset:0;overflow:hidden;background:#0c0c10;--c:#5A79A0}
.reel .bg{position:absolute;inset:-20%;background:radial-gradient(40% 35% at 25% 20%,var(--c),transparent 70%),radial-gradient(35% 30% at 80% 75%,var(--c),transparent 70%);opacity:.55;filter:blur(10px);animation:drift 14s ease-in-out infinite alternate}
@keyframes drift{from{transform:translate3d(-3%,-2%,0) rotate(0)}to{transform:translate3d(3%,2%,0) rotate(8deg)}}
.reel .grain{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.55) 75%,rgba(0,0,0,.85))}
.prog{position:absolute;left:12px;right:12px;top:calc(env(safe-area-inset-top) + 50px);display:flex;gap:4px;z-index:3}
.prog i{flex:1;height:3px;border-radius:2px;background:rgba(255,255,255,.25);overflow:hidden}.prog i b{display:block;height:100%;width:0;background:#fff}
.hdr{position:absolute;left:14px;right:14px;top:calc(env(safe-area-inset-top) + 62px);display:flex;flex-wrap:wrap;gap:6px;z-index:3}
.chip{font:600 11px var(--ui);text-transform:uppercase;letter-spacing:.06em;padding:5px 8px;border-radius:5px;background:rgba(255,255,255,.14)}
.chip--sec{background:var(--c)}.chip--ai{background:rgba(160,120,255,.25);color:#e6dcff}
.stage{position:absolute;left:18px;right:18px;top:calc(env(safe-area-inset-top) + 105px);bottom:210px;z-index:2}
.s{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;opacity:0;transform:translateY(14px) scale(.98);transition:opacity .45s var(--ease),transform .6s var(--ease);pointer-events:none}
.s.on{opacity:1;transform:none;pointer-events:auto}
.s h2{font:900 34px/1.12 var(--head);margin:0 0 14px;letter-spacing:-.01em}
.s h2 span{display:inline-block;opacity:0;transform:translateY(10px)}.s.on h2 span{animation:wordin .5s var(--ease) forwards}
@keyframes wordin{to{opacity:1;transform:none}}
.kick{font:700 12px var(--ui);text-transform:uppercase;letter-spacing:.14em;color:var(--yellow);margin:0 0 10px}
.big{font:900 64px/1 var(--head);letter-spacing:-.03em}.big small{font-size:.42em;font-weight:700;margin-left:6px;opacity:.85}
.lbl{font:500 17px/1.35 var(--head);opacity:.9;margin:10px 0 0;max-width:22em}
.dots{display:grid;grid-template-columns:repeat(20,1fr);gap:5px;margin-top:22px;max-width:320px}
.dots i{aspect-ratio:1;border-radius:50%;background:rgba(255,255,255,.85);opacity:0;transform:scale(.3)}
.s.on .dots i{animation:pop .4s var(--ease) forwards}
@keyframes pop{to{opacity:1;transform:none}}
.ftitle{font:700 13px var(--ui);text-transform:uppercase;letter-spacing:.08em;opacity:.8;margin:0 0 12px}
svg.forest{width:100%;overflow:visible}
svg.forest .axis{stroke:rgba(255,255,255,.35);stroke-width:1}svg.forest .ref{stroke:#fff;stroke-width:1.5;stroke-dasharray:4 4;opacity:.8}
svg.forest text{fill:#fff;font-family:var(--ui)}svg.forest .tick{font-size:11px;opacity:.6}svg.forest .rl{font-size:14px;font-weight:600}svg.forest .rv{font-size:13px;font-weight:700}
svg.forest .ci{stroke:var(--yellow);stroke-width:3;stroke-linecap:round;transform-box:fill-box;transform-origin:center;transform:scaleX(0)}
svg.forest .pt{fill:var(--yellow);transform-box:fill-box;transform-origin:center;transform:scale(0)}
.s.on svg.forest .ci{animation:grow .9s .3s var(--ease) forwards}.s.on svg.forest .pt{animation:grow .5s .15s var(--ease) forwards}
@keyframes grow{to{transform:none}}
.favours{display:flex;justify-content:space-between;font:400 11px var(--ui);opacity:.6;margin-top:4px}
.bars{display:flex;gap:28px;align-items:flex-end;height:230px;margin-top:6px}
.bar{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%}
.bar b{font:900 30px var(--head);margin-bottom:8px}.bar i{width:100%;border-radius:10px 10px 4px 4px;background:var(--yellow);height:0;transition:height 1.1s var(--ease)}
.bar:nth-child(2) i{background:rgba(255,255,255,.75)}.bar span{font:600 14px var(--ui);margin-top:8px;opacity:.9}
.waffle{display:grid;grid-template-columns:repeat(10,1fr);gap:4px;max-width:250px;margin-top:18px}
.waffle i{aspect-ratio:1;border-radius:3px;background:rgba(255,255,255,.18);opacity:0}.waffle i.f{background:var(--yellow)}
.s.on .waffle i{animation:pop .3s var(--ease) forwards}
.card{border-radius:16px;padding:20px;font:800 24px/1.25 var(--head)}
.card .kick{margin-bottom:8px}.card--catch{background:rgba(255,242,0,.12);border:2px solid var(--yellow)}
.card--bottom{background:#fff;color:#111}.card--bottom .kick{color:var(--red)}
.readbtn{display:inline-flex;align-items:center;gap:6px;margin-top:16px;background:#fff;color:#000;border-radius:24px;padding:11px 18px;font:600 15px var(--ui)}
.s--poll h3{font:800 24px/1.25 var(--head);margin:0 0 16px}
.opts{display:flex;flex-direction:column;gap:10px}
.opt{position:relative;overflow:hidden;text-align:left;border:2px solid rgba(255,255,255,.7);background:rgba(255,255,255,.06);color:#fff;border-radius:14px;padding:13px 16px;font:700 17px var(--head)}
.opt .fill{position:absolute;left:0;top:0;bottom:0;width:0;background:rgba(255,255,255,.18);transition:width .9s var(--ease)}
.opt .pc{position:absolute;right:14px;top:50%;transform:translateY(-50%);font:800 16px var(--head);opacity:0;transition:opacity .4s .3s}
.opt span{position:relative}.voted .opt{pointer-events:none}.voted .opt .pc{opacity:1}.opt.mine{border-color:var(--yellow)}.opt.mine .fill{background:rgba(255,242,0,.35)}
.pollnote{font:400 12px var(--ui);opacity:.6;margin:10px 0 0}
.nexthint{font:600 14px var(--ui);margin-top:16px;opacity:0;transition:opacity .4s}.voted~.nexthint,.s--poll.voted .nexthint{opacity:.9}
.caps{position:absolute;left:16px;right:16px;bottom:132px;z-index:3;text-align:center;font:800 21px/1.32 var(--head);text-shadow:0 2px 8px rgba(0,0,0,.8);min-height:84px;display:flex;align-items:flex-end;justify-content:center}
.caps p{margin:0}.caps .w{opacity:.45;transition:opacity .15s}.caps .w.past{opacity:1}
.caps .w.now{opacity:1;background:var(--yellow);color:#000;border-radius:4px;padding:0 3px;text-shadow:none}
.meta{position:absolute;left:16px;right:80px;bottom:calc(76px + env(safe-area-inset-bottom));z-index:3;font:400 13px var(--ui);opacity:.9}
.meta b{font:700 14px var(--head);display:block;margin-bottom:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.paused-ind{position:absolute;inset:0;display:grid;place-items:center;z-index:4;pointer-events:none;opacity:0;transition:opacity .2s}
.paused .paused-ind{opacity:1}.paused-ind i{width:76px;height:76px;border-radius:50%;background:rgba(0,0,0,.45);display:grid;place-items:center}
/* start overlay */
.start{position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.82);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px;gap:14px}
.start h1{font:900 30px/1.15 var(--head);margin:0}.start p{font:400 15px/1.5 var(--ui);opacity:.8;margin:0;max-width:22em}
.start .go{background:#fff;color:#000;border:0;border-radius:30px;padding:15px 28px;font:700 17px var(--ui);margin-top:8px}
.start .mute{background:none;border:0;color:#fff;opacity:.75;font:500 14px var(--ui);text-decoration:underline}
.toast{position:fixed;left:50%;top:calc(env(safe-area-inset-top) + 56px);transform:translate(-50%,-14px);background:rgba(255,255,255,.95);color:#000;font:600 14px var(--ui);padding:9px 16px;border-radius:20px;opacity:0;transition:all .35s var(--ease);z-index:120;pointer-events:none;white-space:nowrap}
.toast.on{opacity:1;transform:translate(-50%,0)}
/* end screen (both) */
.endcard{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:10px;padding:30px;height:100%}
.endcard .check{width:84px;height:84px;border-radius:50%;background:#16a34a;display:grid;place-items:center;font-size:44px;animation:pop .6s var(--ease) both}
.endcard h2{font:900 30px var(--head);margin:6px 0 0}.endcard p{font:400 15px/1.5 var(--ui);opacity:.8;margin:0}
.endcard .next{font:600 14px var(--ui);background:rgba(255,255,255,.12);border-radius:20px;padding:7px 14px;margin-top:4px}
.btn{display:block;width:min(100%,320px);border-radius:28px;padding:14px;font:700 16px var(--ui);text-align:center;border:0}
.btn--w{background:#fff;color:#000}.btn--o{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.6)}
.savedlist{width:min(100%,360px);text-align:left;margin:6px 0}.savedlist a{display:block;background:rgba(255,255,255,.08);border-radius:12px;padding:10px 12px;margin-bottom:6px;font:600 14px/1.35 var(--head)}
.savedlist a small{display:block;font:500 11px var(--ui);text-transform:uppercase;letter-spacing:.06em;opacity:.7;margin-bottom:2px}
"""

SCROLL_CSS = r"""
.feed{position:fixed;inset:0;overflow-y:auto;scroll-snap-type:y mandatory;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}
.feed::-webkit-scrollbar{display:none}
.slot{position:relative;height:100vh;height:100dvh;scroll-snap-align:start;scroll-snap-stop:always}
.scroll .reel .stage{right:78px;bottom:250px}.scroll .reel .s--poll{justify-content:flex-start;bottom:-120px}.scroll .reel .caps{right:76px;left:14px;font-size:19px}
.rail{position:absolute;right:8px;bottom:calc(130px + env(safe-area-inset-bottom));z-index:5;display:flex;flex-direction:column;gap:14px;align-items:center;width:60px}
.rail button,.rail a{background:none;border:0;color:#fff;display:flex;flex-direction:column;align-items:center;gap:3px;font:600 11.5px var(--ui);text-shadow:0 1px 4px rgba(0,0,0,.6)}
.rail .ic{width:46px;height:46px;border-radius:50%;background:rgba(0,0,0,.35);display:grid;place-items:center}
.rail .on .ic{color:var(--yellow)}.rail .liked .ic{color:#ff3b5c}.rail .liked svg,.rail .on svg{fill:currentColor}
.heart-burst{position:absolute;z-index:6;font-size:90px;pointer-events:none;animation:burst .8s var(--ease) forwards}
@keyframes burst{0%{opacity:0;transform:translate(-50%,-50%) scale(.3)}30%{opacity:1;transform:translate(-50%,-50%) scale(1.1)}100%{opacity:0;transform:translate(-50%,-90%) scale(1)}}
.counter{position:fixed;top:calc(env(safe-area-inset-top) + 50px);right:14px;z-index:51}
"""

SWIPE_CSS = r"""
.deckwrap{position:fixed;left:0;right:0;top:calc(env(safe-area-inset-top) + 52px);bottom:calc(128px + env(safe-area-inset-bottom));display:flex;justify-content:center}
.deck{position:relative;width:min(94vw,440px);height:100%}
.cardx{position:absolute;inset:0;border-radius:22px;overflow:hidden;box-shadow:0 18px 40px rgba(0,0,0,.6);transition:transform .45s var(--ease),opacity .3s;touch-action:none;will-change:transform;background:#0c0c10}
.cardx .reel .prog{top:12px}.cardx .reel .hdr{top:24px}.cardx .reel .stage{top:66px;bottom:200px}.cardx .reel .s--poll{justify-content:flex-start;bottom:-130px}
.cardx .reel .caps{bottom:84px}.cardx .reel .meta{bottom:16px;right:16px}
.cardx.dragging{transition:none}
.stamp{position:absolute;top:26px;z-index:8;font:900 30px var(--head);letter-spacing:.06em;padding:4px 12px;border:4px solid;border-radius:10px;opacity:0;pointer-events:none}
.stamp--save{left:20px;color:#22c55e;transform:rotate(-14deg)}.stamp--skip{right:20px;color:#ef4444;transform:rotate(14deg)}
.stamp--read{left:50%;top:auto;bottom:40%;transform:translateX(-50%);color:#60a5fa}
.ctrls{position:fixed;left:0;right:0;bottom:calc(22px + env(safe-area-inset-bottom));display:flex;justify-content:center;align-items:center;gap:22px;z-index:20}
.ctrls button{border:0;border-radius:50%;display:grid;place-items:center;box-shadow:0 6px 18px rgba(0,0,0,.5)}
.ctrls .skip,.ctrls .save{width:66px;height:66px;background:#fff}.ctrls .skip{color:#ef4444}.ctrls .save{color:#16a34a}
.ctrls .mid{width:48px;height:48px;background:rgba(255,255,255,.16);color:#fff}
.swipehint{position:fixed;left:0;right:0;bottom:calc(100px + env(safe-area-inset-bottom));margin:0;text-align:center;font:500 12px var(--ui);opacity:.6;z-index:19}
.endwrap{position:absolute;inset:0;overflow-y:auto}.endwrap .endcard{justify-content:flex-start;height:auto;min-height:100%;padding-top:28px}
"""

ENGINE = r"""
var Reels=(function(){
  var ss=('speechSynthesis' in window)?window.speechSynthesis:null,voice=null;
  var sound=localStorage.getItem('qmed-sound')!=='0'&&!!ss;
  function pickVoice(){if(!ss)return;var vs=ss.getVoices().filter(function(v){return /^en[-_](US|CA|GB|AU)/i.test(v.lang)});
    var pref=/(Premium|Enhanced|Natural|Neural|Siri|Google US English|Samantha|Ava|Allison|Evan|Nathan)/i;
    voice=vs.filter(function(v){return pref.test(v.name)})[0]||vs.filter(function(v){return /en[-_]US/i.test(v.lang)})[0]||vs[0]||null}
  if(ss){pickVoice();ss.onvoiceschanged=pickVoice}
  function unlock(){if(!ss)return;try{var u=new SpeechSynthesisUtterance(' ');u.volume=0;ss.speak(u)}catch(x){}}
  function setSound(v){sound=v&&!!ss;localStorage.setItem('qmed-sound',sound?'1':'0');if(!sound&&ss)ss.cancel()}
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function words(t){return t.split(/\s+/).filter(Boolean)}
  function fmtNum(n){return Math.round(n).toLocaleString('en-US')}
  function countUp(el,to,dec,ms){var t0=null;dec=dec||0;
    function f(t){if(!t0)t0=t;var k=Math.min(1,(t-t0)/(ms||1200)),v=to*(1-Math.pow(1-k,3));el.textContent=dec?v.toFixed(dec):fmtNum(v);if(k<1)el._raf=requestAnimationFrame(f)}
    cancelAnimationFrame(el._raf);el._raf=requestAnimationFrame(f)}
  var POLLS='qmed-polls';function polls(){try{return JSON.parse(localStorage.getItem(POLLS))||{}}catch(x){return{}}}

  // ---- scene builders
  function forestSVG(sc){
    var rows=sc.rows,lo=Math.min.apply(null,rows.map(function(r){return r.lo}).concat([1])),hi=Math.max.apply(null,rows.map(function(r){return r.hi}).concat([1]));
    var L=Math.log,min=L(lo)-0.25,max=L(hi)+0.25,W=340,x0=8,x1=332,H=36+rows.length*62;
    function X(v){return x0+(L(v)-min)/(max-min)*(x1-x0)}
    var ticks=[0.25,0.5,1,2,4].filter(function(t){return L(t)>=min&&L(t)<=max});
    var s='<svg class="forest" viewBox="0 0 '+W+' '+H+'"><line class="axis" x1="'+x0+'" y1="'+(H-22)+'" x2="'+x1+'" y2="'+(H-22)+'"/>'+
      ticks.map(function(t){return '<text class="tick" x="'+X(t)+'" y="'+(H-6)+'" text-anchor="middle">'+t+'</text>'}).join('')+
      '<line class="ref" x1="'+X(1)+'" y1="0" x2="'+X(1)+'" y2="'+(H-22)+'"/>';
    rows.forEach(function(r,i){var y=30+i*62;
      s+='<text class="rl" x="'+x0+'" y="'+(y-12)+'">'+esc(r.label)+'</text>'+
        '<text class="rv" x="'+x1+'" y="'+(y-12)+'" text-anchor="end">'+r.est.toFixed(2)+' ('+r.lo.toFixed(2)+'–'+r.hi.toFixed(2)+')</text>'+
        '<line class="ci" x1="'+X(r.lo)+'" y1="'+y+'" x2="'+X(r.hi)+'" y2="'+y+'"/>'+
        '<rect class="pt" x="'+(X(r.est)-7)+'" y="'+(y-7)+'" width="14" height="14" rx="2"/>'});
    return s+'</svg><div class="favours"><span>‹ lower</span><span>1 = no difference</span><span>higher ›</span></div>'}
  function sceneHTML(sc,reel){
    var t=sc.type;
    if(t==='hook')return '<p class="kick">'+esc(reel.journal)+'</p><h2>'+words(sc.text).map(function(w,i){return '<span style="animation-delay:'+(i*70)+'ms">'+esc(w)+'&nbsp;</span>'}).join('')+'</h2>';
    if(t==='count'){var dots='';for(var i=0;i<60;i++)dots+='<i style="animation-delay:'+(300+i*18)+'ms"></i>';
      return '<div class="big" data-count="'+sc.value+'">0</div><p class="lbl">'+esc(sc.label)+'</p><div class="dots">'+dots+'</div>'}
    if(t==='forest')return '<p class="ftitle">'+esc(sc.title)+'</p>'+forestSVG(sc);
    if(t==='bars'){var mx=Math.max.apply(null,sc.bars.map(function(b){return b.value}))*1.12;
      return '<p class="ftitle">'+esc(sc.title)+'</p><div class="bars">'+sc.bars.map(function(b){return '<div class="bar"><b data-count="'+b.value+'" data-dec="'+(sc.decimals||0)+'">0</b><i data-h="'+(b.value/mx*100)+'"></i><span>'+esc(b.label)+'</span></div>'}).join('')+'</div>'+
        '<p class="lbl" style="opacity:.6;font-size:13px">'+esc(sc.unit==='%'?'Values in %':'')+'</p>'}
    if(t==='number')return '<div class="big">'+esc(sc.value)+'<small>'+esc(sc.unit)+'</small></div><p class="lbl">'+esc(sc.label)+'</p>';
    if(t==='waffle'){var n=Math.round(sc.value),g='';for(var j=0;j<100;j++)g+='<i class="'+(j<n?'f':'')+'" style="animation-delay:'+(200+j*12)+'ms"></i>';
      return '<div class="big"><span data-count="'+sc.value+'" data-dec="1">0</span><small>%</small></div><p class="lbl">'+esc(sc.label)+'</p><div class="waffle">'+g+'</div>'}
    if(t==='catch')return '<div class="card card--catch"><p class="kick">⚠ The catch</p>'+esc(sc.text)+'</div>';
    if(t==='bottom')return '<div class="card card--bottom"><p class="kick">Bottom line</p>'+esc(sc.text)+'</div><a class="readbtn" href="index.html#'+esc(reel.paper)+'">Read the abstract ›</a>';
    if(t==='poll')return '<p class="kick">Quick poll</p><h3>'+esc(sc.q)+'</h3><div class="opts">'+sc.options.map(function(o,i){return '<button class="opt" type="button" data-opt="'+i+'"><span class="fill"></span><span>'+esc(o)+'</span><span class="pc"></span></button>'}).join('')+'</div>'+
      '<p class="pollnote">Votes from internists in the beta · simulated for this demo</p><p class="nexthint">'+esc(sc.hint||'')+'</p>';
    return ''}

  // ---- player
  function Player(root,reel,opts){
    opts=opts||{};var scenes=reel.scenes.slice();scenes.push({type:'poll',q:reel.poll.q,options:reel.poll.options,seed:reel.poll.seed,hint:opts.pollHint,say:'Quick poll. '+reel.poll.q});
    root.classList.add('reel');root.style.setProperty('--c',reel.color);
    root.innerHTML='<div class="bg"></div><div class="grain"></div><div class="prog">'+scenes.map(function(){return '<i><b></b></i>'}).join('')+'</div>'+
      '<div class="hdr"><span class="chip chip--sec">'+esc(reel.section)+'</span><span class="chip">'+esc(reel.study)+'</span><span class="chip chip--ai">AI-narrated · from the abstract</span></div>'+
      '<div class="stage">'+scenes.map(function(sc,i){return '<div class="s s--'+sc.type+'" data-i="'+i+'">'+sceneHTML(sc,reel)+'</div>'}).join('')+'</div>'+
      '<div class="caps"><p></p></div><div class="meta"><b>'+esc(reel.title)+'</b>'+esc(reel.journal)+'</div>'+
      '<div class="paused-ind"><i><svg width="30" height="30" viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z"/></svg></i></div>';
    var sEls=root.querySelectorAll('.s'),bars=root.querySelectorAll('.prog b'),caps=root.querySelector('.caps p');
    var idx=-1,playing=false,timers=[],t0=0,gen=0;
    function clear(){timers.forEach(clearTimeout);timers=[];if(ss)ss.cancel()}
    function est(sc){return Math.max(2600,words(sc.say||sc.text||'').length/2.6*1000+500)}
    function caption(sc){var ws=sc.type==='poll'?[]:words(sc.say||'');caps.innerHTML=ws.map(function(w){return '<span class="w">'+esc(w)+'</span> '}).join('');return caps.querySelectorAll('.w')}
    function hi(wEls,k){for(var i=0;i<wEls.length;i++){wEls[i].classList.toggle('past',i<k);wEls[i].classList.toggle('now',i===k)}}
    function animate(el){el.querySelectorAll('[data-count]').forEach(function(c){countUp(c,parseFloat(c.dataset.count),+(c.dataset.dec||0))});
      el.querySelectorAll('[data-h]').forEach(function(b){b.style.height='0';requestAnimationFrame(function(){requestAnimationFrame(function(){b.style.height=b.dataset.h+'%'})})})}
    function start(i){
      clear();idx=i;var my=++gen,sc=scenes[i];t0=Date.now();
      sEls.forEach(function(s,j){s.classList.toggle('on',j===i)});animate(sEls[i]);
      bars.forEach(function(b,j){b.style.transition='none';b.style.width=j<i?'100%':'0'});
      var dur=est(sc),wEls=caption(sc),bar=bars[i];
      requestAnimationFrame(function(){bar.style.transition='width '+dur+'ms linear';bar.style.width='100%'});
      var gotBoundary=false;
      function done(){if(my!==gen||!playing)return;var wait=Math.max(0,2200-(Date.now()-t0));
        timers.push(setTimeout(function(){if(my!==gen||!playing)return;hi(wEls,wEls.length);bar.style.transition='none';bar.style.width='100%';
          if(sc.type==='poll'){if(opts.onPollShown)opts.onPollShown();return}
          if(i<scenes.length-1)start(i+1)},wait))}
      // timed word highlight (fallback when the voice gives no word boundaries)
      var per=dur/Math.max(1,wEls.length);
      wEls.forEach(function(_,k){timers.push(setTimeout(function(){if(my===gen&&!gotBoundary)hi(wEls,k)},k*per))});
      if(sound&&ss&&sc.say){var u=new SpeechSynthesisUtterance(sc.say);if(voice)u.voice=voice;u.lang=voice?voice.lang:'en-US';u.rate=1.03;
        u.onboundary=function(ev){if(ev.name&&ev.name!=='word')return;gotBoundary=true;var c=ev.charIndex,acc=0,k=0;var ws=words(sc.say);
          for(k=0;k<ws.length;k++){var p=sc.say.indexOf(ws[k],acc);if(p>c){k=Math.max(0,k-1);break}acc=p+ws[k].length}hi(wEls,Math.min(k,ws.length-1))};
        u.onend=done;u.onerror=done;ss.speak(u);timers.push(setTimeout(done,dur*1.9+1500))}
      else timers.push(setTimeout(done,dur));
    }
    // poll
    root.querySelectorAll('.opt').forEach(function(b){b.addEventListener('click',function(ev){ev.stopPropagation();var p=polls(),k=+b.dataset.opt;p[reel.id]=k;localStorage.setItem(POLLS,JSON.stringify(p));showVote(k);
      if(opts.onVote)opts.onVote(k)})});
    function showVote(k){var sc=scenes[scenes.length-1],cnt=sc.seed.slice();cnt[k]+=1;var tot=cnt.reduce(function(a,b){return a+b},0),wrap=root.querySelector('.s--poll');
      wrap.classList.add('voted');wrap.querySelectorAll('.opt').forEach(function(o,i){var pc=Math.round(cnt[i]/tot*100);o.classList.toggle('mine',i===k);o.querySelector('.pc').textContent=pc+'%';o.querySelector('.fill').style.width=pc+'%'});
      wrap.querySelector('.pollnote').textContent=tot+' votes · simulated for this demo'}
    var prev=polls()[reel.id];if(prev!=null)showVote(prev);
    return {
      play:function(){if(playing)return;playing=true;root.classList.remove('paused');start(idx<0||idx>=scenes.length-1&&root.querySelector('.s--poll.voted')?0:Math.max(0,idx))},
      pause:function(){if(!playing)return;playing=false;gen++;clear();root.classList.add('paused')},
      stop:function(){playing=false;gen++;clear();root.classList.remove('paused')},
      restart:function(){playing=true;root.classList.remove('paused');start(0)},
      toggle:function(){playing?this.pause():this.play()},
      isPlaying:function(){return playing}
    }}
  return {Player:Player,unlock:unlock,setSound:setSound,sound:function(){return sound},hasSpeech:!!ss,esc:esc}
})();
function toast(t){var el=document.getElementById('toast');el.textContent=t;el.classList.add('on');clearTimeout(el._t);el._t=setTimeout(function(){el.classList.remove('on')},1800)}
var SAVED='qmed-saved';function loadSaved(){try{return JSON.parse(localStorage.getItem(SAVED))||[]}catch(x){return[]}}
function saveReel(r,on){var l=loadSaved().filter(function(x){return x.id!==r.paper});if(on)l.push({id:r.paper,title:r.title,sec:r.section,color:r.color});localStorage.setItem(SAVED,JSON.stringify(l))}
function isSaved(r){return loadSaved().some(function(x){return x.id===r.paper})}
function soundBtn(){var b=document.getElementById('snd');function paint(){b.innerHTML=Reels.sound()?ICON_SOUND:ICON_MUTE}paint();window.paintSound=paint;
  b.addEventListener('click',function(ev){ev.stopPropagation();Reels.setSound(!Reels.sound());paint();toast(Reels.sound()?'Sound on':'Muted: captions only');if(window.onSoundChange)window.onSoundChange()})}
var ICON_SOUND='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
var ICON_MUTE='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="m16 9 5 6M21 9l-5 6"/></svg>';
function startOverlay(cb){var o=document.getElementById('start');
  o.querySelector('.go').addEventListener('click',function(){Reels.setSound(true);Reels.unlock();if(window.paintSound)paintSound();o.remove();cb()});
  o.querySelector('.mute').addEventListener('click',function(){Reels.setSound(false);if(window.paintSound)paintSound();o.remove();cb()});
  if(!Reels.hasSpeech){o.querySelector('.go').textContent='Start (captions only)'}}
"""

SCROLL_JS = r"""
(function(){
  var feed=document.getElementById('feed'),players=[],active=-1,N=REELS.length;
  REELS.forEach(function(r,i){var slot=document.createElement('section');slot.className='slot';slot.dataset.i=i;
    var el=document.createElement('div');slot.appendChild(el);
    var likes=40+((i*37)%150);
    slot.insertAdjacentHTML('beforeend','<aside class="rail">'+
      '<button type="button" class="like" data-like>'+'<span class="ic"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 21s-7.5-4.6-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2 4.4-9.5 9-9.5 9z"/></svg></span><span class="n">'+likes+'</span></button>'+
      '<button type="button" data-save class="'+(isSaved(r)?'on':'')+'"><span class="ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 3h12v18l-6-4.5L6 21z"/></svg></span><span>Save</span></button>'+
      '<button type="button" data-share><span class="ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M12 15V3M8 7l4-4 4 4M7 11H5v10h14V11h-2"/></svg></span><span>Share</span></button>'+
      '<a href="index.html#'+Reels.esc(r.paper)+'"><span class="ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M14 3H6v18h12V7zM14 3v4h4M9 13h6M9 17h6"/></svg></span><span>Abstract</span></a></aside>');
    feed.appendChild(slot);
    var p=Reels.Player(el,r,{pollHint:i<N-1?'Swipe up for the next one ↑':'Swipe up to finish ↑',onVote:function(){
      setTimeout(function(){if(active===i)feed.scrollTo({top:(i+1)*feed.clientHeight,behavior:'smooth'})},2600)}});
    players.push(p);
    var lastTap=0;
    el.addEventListener('click',function(ev){if(ev.target.closest('a,button'))return;var now=Date.now();
      if(now-lastTap<300){lastTap=0;like(slot,true,ev);return}lastTap=now;setTimeout(function(){if(Date.now()-lastTap>=290&&lastTap===now)p.toggle()},300)});
    slot.querySelector('[data-like]').addEventListener('click',function(ev){like(slot,!slot.querySelector('[data-like]').classList.contains('liked'),ev)});
    slot.querySelector('[data-save]').addEventListener('click',function(){var b=this,on=!b.classList.contains('on');b.classList.toggle('on',on);saveReel(r,on);toast(on?'Saved for later':'Removed from Saved')});
    slot.querySelector('[data-share]').addEventListener('click',function(){var d={title:r.title,url:'https://doi.org/'+r.doi};if(navigator.share)navigator.share(d).catch(function(){});else if(navigator.clipboard){navigator.clipboard.writeText(d.url);toast('Link copied')}});
  });
  function like(slot,on,ev){var b=slot.querySelector('[data-like]'),n=b.querySelector('.n');if(b.classList.contains('liked')===on&&ev&&ev.type!=='click'){}
    if(on!==b.classList.contains('liked')){b.classList.toggle('liked',on);n.textContent=+n.textContent+(on?1:-1)}
    if(on&&ev&&ev.clientX){var h=document.createElement('div');h.className='heart-burst';h.textContent='❤️';h.style.left=ev.clientX+'px';h.style.top=ev.clientY+'px';slot.appendChild(h);setTimeout(function(){h.remove()},800)}}
  // end card
  var end=document.createElement('section');end.className='slot';end.innerHTML='<div class="endcard"><div class="check">✓</div><h2>You\'re up to date</h2><p>'+N+' reels · about '+Math.round(N*0.8)+' minutes</p><span class="next">Next drop at '+NEXT+'</span>'+
    '<a class="btn btn--w" href="index.html" style="margin-top:18px">Read today\'s papers</a><a class="btn btn--o" href="reels-swipe.html">Try the swipe version</a><button class="btn btn--o" type="button" id="again">Watch again</button></div>';
  feed.appendChild(end);
  document.getElementById('again').addEventListener('click',function(){feed.scrollTo({top:0,behavior:'smooth'})});
  var counter=document.getElementById('count');
  function activate(i){if(i===active)return;if(active>=0&&players[active])players[active].stop();active=i;
    counter.textContent=i<N?(i+1)+' / '+N:'Done';if(i<N&&started)players[i].restart()}
  var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting)activate(+en.target.dataset.i)})},{root:feed,threshold:.6});
  feed.querySelectorAll('.slot').forEach(function(s,i){s.dataset.i=i;io.observe(s)});
  var started=false;startOverlay(function(){started=true;if(active<0)activate(0);else if(active<N)players[active].restart()});
  window.onSoundChange=function(){if(active>=0&&active<N&&players[active].isPlaying())players[active].restart()};
  soundBtn();
})();
"""

SWIPE_JS = r"""
(function(){
  var deck=document.getElementById('deck'),N=REELS.length,cur=0,cards=[],players=[],saved=[],started=false;
  REELS.forEach(function(r,i){var c=document.createElement('div');c.className='cardx';c.style.zIndex=N-i;
    var el=document.createElement('div');c.appendChild(el);
    c.insertAdjacentHTML('beforeend','<div class="stamp stamp--save">SAVE</div><div class="stamp stamp--skip">SKIP</div><div class="stamp stamp--read">READ</div>');
    deck.appendChild(c);cards.push(c);
    players.push(Reels.Player(el,r,{pollHint:'Swipe right to save for later, left to skip'}));
    el.addEventListener('click',function(ev){if(ev.target.closest('a,button')||c._moved)return;if(c===cards[cur])players[i].toggle()});
  });
  function layout(){cards.forEach(function(c,i){var k=i-cur;if(k<0)return;c.style.opacity=k>2?0:1;
    c.style.transform=k===0?'none':'translateY('+(k*14)+'px) scale('+(1-k*0.05)+')';c.style.pointerEvents=k===0?'auto':'none'})}
  layout();
  document.getElementById('count').textContent='1 / '+N;
  function decide(dir){var c=cards[cur];if(!c)return;var r=REELS[cur];players[cur].stop();
    if(dir==='right'){saved.push(r);saveReel(r,true);toast('Saved for later')}
    if(dir==='up'){location.href='index.html#'+r.paper;return}
    var x=dir==='right'?1:-1;c.style.transition='transform .45s var(--ease),opacity .45s';
    c.style.transform='translate('+(x*window.innerWidth*1.2)+'px,-40px) rotate('+(x*24)+'deg)';c.style.opacity=0;c.style.pointerEvents='none';
    cur++;setTimeout(function(){c.style.display='none'},460);layout();
    document.getElementById('count').textContent=cur<N?(cur+1)+' / '+N:'Done';
    if(cur<N){if(started)setTimeout(function(){players[cur].restart()},250)}else showEnd()}
  // drag
  var d=null;
  deck.addEventListener('pointerdown',function(ev){var c=cards[cur];if(!c||!c.contains(ev.target)||ev.target.closest('a,button'))return;
    d={x:ev.clientX,y:ev.clientY,c:c,dx:0,dy:0};c._moved=false;c.setPointerCapture(ev.pointerId);c.classList.add('dragging')});
  deck.addEventListener('pointermove',function(ev){if(!d)return;d.dx=ev.clientX-d.x;d.dy=ev.clientY-d.y;if(Math.abs(d.dx)+Math.abs(d.dy)>8)d.c._moved=true;
    d.c.style.transform='translate('+d.dx+'px,'+d.dy+'px) rotate('+(d.dx/18)+'deg)';
    var s=d.c.querySelectorAll('.stamp');s[0].style.opacity=Math.max(0,Math.min(1,d.dx/110));s[1].style.opacity=Math.max(0,Math.min(1,-d.dx/110));
    s[2].style.opacity=Math.abs(d.dx)<60?Math.max(0,Math.min(1,-d.dy/130)):0});
  function up(){if(!d)return;var c=d.c,dx=d.dx,dy=d.dy;d=null;c.classList.remove('dragging');c.querySelectorAll('.stamp').forEach(function(s){s.style.opacity=0});
    if(dx>110)decide('right');else if(dx<-110)decide('left');else if(dy<-130&&Math.abs(dx)<60)decide('up');else{c.style.transform='none'}
    setTimeout(function(){c._moved=false},50)}
  deck.addEventListener('pointerup',up);deck.addEventListener('pointercancel',up);
  document.getElementById('bSkip').addEventListener('click',function(){decide('left')});
  document.getElementById('bSave').addEventListener('click',function(){decide('right')});
  document.getElementById('bReplay').addEventListener('click',function(){if(cur<N)players[cur].restart()});
  function showEnd(){var w=document.createElement('div');w.className='endwrap';
    w.innerHTML='<div class="endcard"><div class="check">✓</div><h2>You\'re up to date</h2><p>'+N+' reels triaged · '+saved.length+' saved for later</p><span class="next">Next drop at '+NEXT+'</span>'+
      (saved.length?'<div class="savedlist">'+saved.map(function(r){return '<a href="index.html#'+Reels.esc(r.paper)+'"><small style="color:'+r.color+'">'+Reels.esc(r.section)+'</small>'+Reels.esc(r.title)+'</a>'}).join('')+'</div>':'')+
      '<a class="btn btn--w" href="index.html#saved">Open my reading list</a><a class="btn btn--o" href="reels-scroll.html">Try the scroll version</a></div>';
    deck.appendChild(w);document.querySelector('.ctrls').style.display='none';document.querySelector('.swipehint').style.display='none'}
  startOverlay(function(){started=true;players[0].restart()});
  window.onSoundChange=function(){if(cur<N&&players[cur].isPlaying())players[cur].restart()};
  soundBtn();
})();
"""

START = '''<div class="start" id="start"><h1>%%H%%</h1><p>%%P%%</p>
<button class="go" type="button">▶ Start with sound</button><button class="mute" type="button">Start muted (captions only)</button></div>'''


def page(title, body_class, extra_css, body, js, data):
    return (HEAD.replace("%%TITLE%%", e(title)).replace("%%CSS%%", CSS + extra_css)
            + f'<body class="{body_class}">' + body
            + '<div class="toast" id="toast"></div>'
            + '<script>var REELS=' + json.dumps(data["reels"], ensure_ascii=False).replace("</", "<\\/")
            + ';var NEXT=' + json.dumps(data.get("next_drop", "12:00")) + ';</script>'
            + "<script>" + ENGINE + js + "</script></body></html>")


def top(label, sub):
    return (f'<div class="top"><a class="back" href="reels.html">‹ Reels</a><div class="ttl">{e(label)}<small>{e(sub)}</small></div>'
            '<div style="display:flex;gap:8px;align-items:center"><span id="count" style="font:600 12px var(--ui);opacity:.85"></span>'
            '<button class="snd" id="snd" type="button" aria-label="Sound"></button></div></div>')


def build():
    data = json.loads((HERE / "reels.json").read_text(encoding="utf-8"))
    n = len(data["reels"])
    start = lambda h, p: START.replace("%%H%%", h).replace("%%P%%", p)

    scroll_body = (top("Today's reels", data["date"]) + '<main class="feed" id="feed"></main>'
                   + start(f"Today: {n} reels", "Swipe up for the next one. Tap to pause, double-tap to like. Each one ends with a quick poll."))
    (HERE / "reels-scroll.html").write_text(page("Reels (scroll) · Le Quotidien Médical", "scroll", SCROLL_CSS, scroll_body, SCROLL_JS, data), encoding="utf-8")

    swipe_body = (top("Today's reels", data["date"])
                  + '<div class="deckwrap"><div class="deck" id="deck"></div></div>'
                  + '<p class="swipehint">Right: save for later · Left: skip · Up: read the abstract</p>'
                  + '<div class="ctrls"><button class="skip" id="bSkip" type="button" aria-label="Skip"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg></button>'
                  + '<button class="mid" id="bReplay" type="button" aria-label="Replay"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/></svg></button>'
                  + '<button class="save" id="bSave" type="button" aria-label="Save for later"><svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-7.5-4.6-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2 4.4-9.5 9-9.5 9z"/></svg></button></div>'
                  + start(f"Today: {n} reels", "Watch, then swipe right to save for later or left to skip. Swipe up to read the abstract. Each reel ends with a quick poll."))
    (HERE / "reels-swipe.html").write_text(page("Reels (swipe) · Le Quotidien Médical", "swipe", SWIPE_CSS, swipe_body, SWIPE_JS, data), encoding="utf-8")

    chooser = (HEAD.replace("%%TITLE%%", "Reels · Le Quotidien Médical").replace("%%CSS%%", CSS + r"""
body{overflow:auto}.choose{min-height:100%;display:flex;flex-direction:column;justify-content:center;gap:16px;padding:calc(env(safe-area-inset-top) + 30px) 20px 40px;max-width:480px;margin:0 auto}
.choose h1{font:900 30px/1.1 var(--head);margin:0}.choose>p{font:400 15px/1.5 var(--ui);opacity:.75;margin:0 0 8px}
.opt2{display:block;border-radius:18px;padding:20px;background:linear-gradient(135deg,#1c1c22,#2a2a33);border:1px solid rgba(255,255,255,.12)}
.opt2 b{display:block;font:800 21px var(--head);margin-bottom:4px}.opt2 span{font:400 14px/1.45 var(--ui);opacity:.8}.opt2 em{font-style:normal;font-size:30px;float:right}
.backlink{font:500 14px var(--ui);opacity:.7;text-align:center;margin-top:8px}""")
               + '<body><div class="choose"><h1>Today\'s reels</h1><p>' + e(data["date"]) + f' · {n} short reels on what\'s new in internal medicine. Try both formats and tell us which you prefer.</p>'
               + '<a class="opt2" href="reels-scroll.html"><em>↕</em><b>Scroll</b><span>TikTok-style: full-screen, swipe up for the next one, double-tap to like.</span></a>'
               + '<a class="opt2" href="reels-swipe.html"><em>↔</em><b>Swipe</b><span>Tinder-style: watch, then swipe right to save for later, left to skip. A quick reading triage.</span></a>'
               + '<a class="backlink" href="index.html">‹ Back to the papers</a></div></body></html>')
    (HERE / "reels.html").write_text(chooser, encoding="utf-8")
    print(f"Wrote reels.html, reels-scroll.html, reels-swipe.html ({n} reels)")


if __name__ == "__main__":
    build()
