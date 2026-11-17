/* Static Bloom: game, rendering and interface. */
(()=>{
'use strict';
const $=id=>document.getElementById(id),cv=$('c'),ctx=cv.getContext('2d',{alpha:false});
const CY='#19f0ff',MG='#ff2bd6',AM='#ffb300',INK='#e8f7ff';
const lerp=(a,b,t)=>a+(b-a)*t,clamp=(v,a,b)=>v<a?a:v>b?b:v;
const easeIn=(a,b,t)=>a+(b-a)*t*t,easeIO=(a,b,t)=>a+(b-a)*(-Math.cos(t*Math.PI)/2+.5);
function rng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function mk(w,h,fn){const c=document.createElement('canvas');c.width=w;c.height=h;fn(c.getContext('2d'),w,h);return c}

/* ---------- tuning ---------- */
const SEG=200,RUMBLE=3,ROADW=2000,CAMH=1000,DRAW=200,camDepth=1/Math.tan(50*Math.PI/180),playerZ=CAMH*camDepth;
const MAXSP=SEG*60,ACCEL=MAXSP/4,BRAKE=-MAXSP,OFFDEC=-MAXSP/1.6,OFFLIM=MAXSP/3.5,CENT=.22,LANES=[-.62,0,.62];
const TH=[
 {name:'CHROME ESTATES',sky:['#030110','#150638','#5a0f78','#ff2b9a'],sun:['#fff39a','#ff8a3c','#ff1f8e'],halo:'255,60,170',fog:'#2a0a4c',fogc:'42,10,76',grid:'#ff2bd6',edge:'#19f0ff',edgeD:'#0a5a78',lane:'#ff9df0',line:'#baffff',road:['#110e2a','#0c0a1e'],ground:['#0b051c','#070313'],far:'#2a0f55',near:'#0a0518',acc:'#ff2bd6'},
 {name:'FREEPORT NINE',sky:['#010a0c','#03222a','#0b5a5a','#39ffb0'],sun:['#f4fff8','#bff5e0','#58cdb4'],halo:'60,255,180',fog:'#06302f',fogc:'6,48,47',grid:'#19ffa0',edge:'#ffe14a',edgeD:'#6a5a10',lane:'#d9fff0',line:'#fff6c0',road:['#0d1a1c','#0a1416'],ground:['#041012','#030b0c'],far:'#0c3a3a',near:'#02100f',acc:'#19ffa0'},
 {name:'SOVEREIGN MALL',sky:['#0d0204','#3a0812','#a3231a','#ffb347'],sun:['#fff6c0','#ffb347','#ff4a2a'],halo:'255,140,60',fog:'#4a1210',fogc:'74,18,16',grid:'#ff7a1a',edge:'#ffd21f',edgeD:'#7a5a0a',lane:'#fff0c0',line:'#fff4d0',road:['#1c1210','#150d0c'],ground:['#140806','#0d0504'],far:'#5a1a14',near:'#120503',acc:'#ff7a1a'},
 {name:'THE STACKS',sky:['#01030f','#07123a','#1b2f8a','#6fb7ff'],sun:['#ffffff','#cfe4ff','#7aa8ff'],halo:'110,170,255',fog:'#101c4c',fogc:'16,28,76',grid:'#3c7bff',edge:'#b0f0ff',edgeD:'#2a5a78',lane:'#e0f0ff',line:'#ffffff',road:['#0d1024','#090b1a'],ground:['#060818','#04050f'],far:'#16226a',near:'#040616',acc:'#3c7bff',storm:1},
 {name:'NULL DISTRICT',sky:['#050505','#161616','#3a3a3a','#e8e8e8'],sun:['#ffffff','#ff5a6e','#ff1030'],halo:'255,60,80',fog:'#262626',fogc:'38,38,38',grid:'#ff2244',edge:'#ffffff',edgeD:'#666666',lane:'#ffffff',line:'#ffffff',road:['#141414','#0e0e0e'],ground:['#0a0a0a','#060606'],far:'#333333',near:'#0a0a0a',acc:'#ff2244',nul:1}];
const UPG=[{k:'range',n:'Longline',d:'The harpoon reaches further and locks wider.'},{k:'sling',n:'Capacitor',d:'Slingshots burn longer.'},
 {k:'window',n:'Dispatch Favor',d:'More time on the clock in every zone.'},{k:'magnet',n:'Shard Magnet',d:'Pulls shards in from further out. Each is worth more time.'}];
const COST=[150,400,900,1800,3500];
const CON=[
 {id:'near',t:n=>'Skim traffic '+n+' times in one run',n:[10,18,28],r:[120,220,400]},
 {id:'sling',t:n=>'Land '+n+' slingshots in one run',n:[8,15,25],r:[120,220,400]},
 {id:'shard',t:n=>'Collect '+n+' shards in one run',n:[30,50,80],r:[100,200,350]},
 {id:'zone',t:n=>'Reach zone '+n,n:[2,3,4,5],r:[100,200,350,600]},
 {id:'purge',t:n=>'Purge '+n+' statics while boosting in one run',n:[2,4,6],r:[150,250,400]},
 {id:'combo',t:n=>'Hit a ×'+n+' multiplier',n:[6,9],r:[120,300]},
 {id:'clean',t:n=>'Clear '+n+' zone'+(n>1?'s':'')+' in one run without an impact',n:[1,2],r:[200,450]}];

/* ---------- save data ---------- */
const KEY='staticbloom.v2',DEF={v:2,best:0,daily:{d:'',s:0},cred:0,up:{range:0,sling:0,window:0,magnet:0},con:[],clv:{},tut:false,set:{mus:.8,sfx:.8,hap:true,calm:false},runs:0};
let SV=(()=>{const d=JSON.parse(JSON.stringify(DEF));try{const j=JSON.parse(localStorage.getItem(KEY));if(j&&j.v===2)return Object.assign(d,j,{up:Object.assign(d.up,j.up),set:Object.assign(d.set,j.set)});d.best=+localStorage.getItem('staticbloom.best')||0}catch(e){}return d})();
const persist=()=>{try{localStorage.setItem(KEY,JSON.stringify(SV))}catch(e){}};
function fillContracts(){SV.con=SV.con.filter(c=>!c.done&&CON.some(k=>k.id===c.id));let guard=0;
  while(SV.con.length<3&&guard++<50){const k=CON[Math.random()*CON.length|0];if(SV.con.some(c=>c.id===k.id))continue;SV.con.push({id:k.id,lv:Math.min(SV.clv[k.id]||0,k.n.length-1)})}}
fillContracts();
const conDef=c=>CON.find(k=>k.id===c.id),conText=c=>{const k=conDef(c);return k.t(k.n[c.lv])};
const today=()=>{const d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()};
const hash=s=>{let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0};

/* ---------- state ---------- */
let W=0,H=0,u=10,resMax=1400,sa={t:0,r:0,b:0,l:0},state='title',time=0,segs=[],cars=[],finishIdx=0,stage=0,theme=TH[0],mode='std',seedBase=1;
let pos=0,px=0,speed=0,steerVis=0,timeLeft=0,score=0,combo=1,comboT=0,ts=1;
let boost=0,tether=null,target=null,hadTarget=false,infect=0,glitch=0,flash=0,shake=0,clearT=0,bgOff=0,shardRun=0,shield=false,bolt=0,boltT=5,touchSeen=false,tut=0,tutT=0,hitThisZone=false;
let dryT=0,popups=[],parts=[],R={},paid=0,perfAcc=0,perfN=0;
const keys={left:false,right:false,brake:false};
const calm=()=>SV.set.calm;
function hap(kind){if(!SV.set.hap)return;try{const C=window.Capacitor;
  if(C&&C.isNativePlatform&&C.isNativePlatform()){const st=kind==='heavy'?'HEAVY':kind==='medium'?'MEDIUM':'LIGHT';
    if(C.Plugins&&C.Plugins.Haptics)C.Plugins.Haptics.impact({style:st});else if(C.nativePromise)C.nativePromise('Haptics','impact',{style:st});return}
  if(navigator.vibrate)navigator.vibrate(kind==='heavy'?40:kind==='medium'?18:8)}catch(e){}}

/* ---------- sprites ---------- */
let SP=null,noise=[],scanPat=null,vig=null,bgSky=null,skyFar=null,skyNear=null,bloomC=null,bloomX=null;
const CARCOL=[MG,CY,AM,'#ff3355','#8cff3a'];
function carSprite(col,tall){const h=tall?200:124;return mk(200,h,g=>{
  g.shadowColor=col;g.shadowBlur=18;g.fillStyle=col;g.globalAlpha=.55;g.fillRect(26,h-12,148,5);g.globalAlpha=1;g.shadowBlur=0;
  g.fillStyle='#000';g.fillRect(20,h-20,34,18);g.fillRect(146,h-20,34,18);
  const top=tall?8:h-114,bg=g.createLinearGradient(0,top,0,h);bg.addColorStop(0,'#1a1436');bg.addColorStop(1,'#07060f');g.fillStyle=bg;
  if(tall)g.fillRect(18,top,164,h-top-14);
  else{g.beginPath();g.moveTo(14,h-14);g.lineTo(14,h-66);g.lineTo(26,h-80);g.lineTo(44,h-80);g.lineTo(58,top);g.lineTo(142,top);g.lineTo(156,h-80);g.lineTo(174,h-80);g.lineTo(186,h-66);g.lineTo(186,h-14);g.closePath();g.fill();
    g.fillStyle='#2a1f66';g.beginPath();g.moveTo(52,h-84);g.lineTo(63,top+6);g.lineTo(137,top+6);g.lineTo(148,h-84);g.closePath();g.fill();g.fillStyle='rgba(255,255,255,.12)';g.fillRect(64,top+8,30,3)}
  g.strokeStyle=col;g.globalAlpha=.35;g.lineWidth=2;
  if(tall){g.strokeRect(19,top+1,162,h-top-16);g.globalAlpha=.22;g.fillStyle=col;for(let y=top+14;y<h-80;y+=14)g.fillRect(30,y,140,2)}
  g.globalAlpha=1;g.shadowColor=col;g.shadowBlur=16;g.fillStyle=col;
  if(tall){g.fillRect(22,top+6,6,h-top-30);g.fillRect(172,top+6,6,h-top-30)}
  g.fillRect(22,h-60,156,8);g.shadowBlur=0;g.fillStyle='#fff';g.globalAlpha=.75;g.fillRect(28,h-58,144,2);g.globalAlpha=1;g.fillStyle='#0d0d1a';g.fillRect(78,h-44,44,14)})}
function towerSprite(seed){return mk(240,720,(g,w,h)=>{const r=rng(seed),top=r()*160|0,bg=g.createLinearGradient(0,top,0,h);bg.addColorStop(0,'#1a0f3c');bg.addColorStop(1,'#080512');g.fillStyle=bg;g.fillRect(20,top,200,h-top);
  g.fillStyle='#0d0822';g.fillRect(60,top-40,90,40);const cols=[CY,MG,AM,'#fff'];
  for(let y=top+14;y<h-10;y+=16)for(let x=30;x<206;x+=14)if(r()<.36){g.fillStyle=cols[r()*4|0];g.globalAlpha=.25+r()*.6;g.fillRect(x,y,8,9)}
  g.globalAlpha=1;const c=cols[r()*3|0];g.shadowColor=c;g.shadowBlur=14;g.fillStyle=c;g.fillRect(r()<.5?20:216,top,4,h-top);
  if(r()<.7){const sx=40+r()*120|0,sh=120+r()*200|0,sy=top+40+r()*120|0;g.globalAlpha=.85;g.fillRect(sx,sy,22,sh);g.fillStyle='#05020d';g.shadowBlur=0;for(let y=sy+8;y<sy+sh-10;y+=22)g.fillRect(sx+5,y,12,12)}
  g.globalAlpha=1;g.shadowBlur=0;g.fillStyle='#333';g.fillRect(104,top-90,3,50);g.shadowColor='#f00';g.shadowBlur=12;g.fillStyle='#ff2244';g.fillRect(102,top-96,7,7)})}
function signSprite(txt,col){return mk(300,330,g=>{g.fillStyle='#15102a';g.fillRect(142,110,16,220);g.fillStyle='#0a0718';g.fillRect(10,14,280,100);
  g.shadowColor=col;g.shadowBlur=18;g.strokeStyle=col;g.lineWidth=5;g.strokeRect(14,18,272,92);g.fillStyle=col;g.font='900 36px Orbitron,sans-serif';g.textAlign='center';g.textBaseline='middle';
  const m=g.measureText(txt).width;if(m>250)g.font='900 '+(36*250/m|0)+'px Orbitron,sans-serif';g.fillText(txt,150,66);g.shadowBlur=0;g.fillStyle='#fff';g.globalAlpha=.55;g.fillText(txt,150,66)})}
function buildSprites(){
  const cs=CARCOL.map(c=>carSprite(c,false));cs.push(carSprite(AM,true),carSprite(CY,true));
  const lamp=mk(140,440,g=>{g.fillStyle='#1b1533';g.fillRect(18,30,8,410);g.fillRect(18,26,104,7);g.shadowColor='#fff';g.shadowBlur=26;g.fillStyle='#ffd9f6';g.fillRect(96,33,26,7);g.fillStyle='#fff';g.fillRect(100,34,18,4);
    g.shadowBlur=0;const cone=g.createLinearGradient(0,40,0,300);cone.addColorStop(0,'rgba(255,220,250,.22)');cone.addColorStop(1,'rgba(255,220,250,0)');g.fillStyle=cone;g.beginPath();g.moveTo(98,40);g.lineTo(120,40);g.lineTo(140,300);g.lineTo(60,300);g.closePath();g.fill()});
  const shard=mk(80,130,g=>{g.shadowColor=CY;g.shadowBlur=22;const gr=g.createLinearGradient(0,10,0,110);gr.addColorStop(0,'#fff');gr.addColorStop(.5,CY);gr.addColorStop(1,'#0a6cff');g.fillStyle=gr;
    g.beginPath();g.moveTo(40,10);g.lineTo(64,56);g.lineTo(40,106);g.lineTo(16,56);g.closePath();g.fill();g.shadowBlur=0;g.fillStyle='rgba(255,255,255,.7)';g.beginPath();g.moveTo(40,10);g.lineTo(64,56);g.lineTo(40,50);g.closePath();g.fill()});
  const hex=(g,cx,cy,r)=>{g.beginPath();for(let i=0;i<6;i++){const a=Math.PI/6+i*Math.PI/3;g[i?'lineTo':'moveTo'](cx+Math.cos(a)*r,cy+Math.sin(a)*r)}g.closePath()};
  const shieldP=mk(140,150,g=>{g.shadowColor='#7dffb0';g.shadowBlur=24;g.strokeStyle='#7dffb0';g.lineWidth=9;hex(g,70,72,50);g.stroke();g.fillStyle='rgba(125,255,176,.25)';g.fill();g.shadowBlur=8;g.fillStyle='#fff';hex(g,70,72,18);g.fill()});
  const overP=mk(140,150,g=>{g.shadowColor=AM;g.shadowBlur=24;g.strokeStyle=AM;g.lineWidth=14;g.lineJoin='round';for(const y of[92,58]){g.beginPath();g.moveTo(26,y+22);g.lineTo(70,y-18);g.lineTo(114,y+22);g.stroke()}
    g.shadowBlur=0;g.strokeStyle='#fff';g.lineWidth=4;for(const y of[92,58]){g.beginPath();g.moveTo(26,y+22);g.lineTo(70,y-18);g.lineTo(114,y+22);g.stroke()}});
  const player=mk(160,210,g=>{g.shadowColor=CY;g.shadowBlur=20;g.fillStyle=CY;g.beginPath();g.moveTo(31,180);g.lineTo(129,180);g.lineTo(134,185);g.lineTo(129,190);g.lineTo(31,190);g.lineTo(26,185);g.closePath();g.fill();
    g.shadowColor=MG;g.fillStyle=MG;g.fillRect(30,192,20,8);g.fillRect(110,192,20,8);g.shadowBlur=0;
    g.fillStyle='#0b0a16';g.beginPath();g.moveTo(60,118);g.lineTo(78,118);g.lineTo(70,182);g.lineTo(46,182);g.closePath();g.fill();g.beginPath();g.moveTo(82,118);g.lineTo(100,118);g.lineTo(114,182);g.lineTo(90,182);g.closePath();g.fill();
    g.fillStyle='#14122a';g.beginPath();g.moveTo(46,58);g.lineTo(114,58);g.lineTo(104,124);g.lineTo(56,124);g.closePath();g.fill();
    g.beginPath();g.moveTo(46,60);g.lineTo(18,104);g.lineTo(28,110);g.lineTo(56,80);g.closePath();g.fill();g.beginPath();g.moveTo(114,60);g.lineTo(142,104);g.lineTo(132,110);g.lineTo(104,80);g.closePath();g.fill();
    g.fillStyle=MG;g.fillRect(20,100,10,4);g.fillRect(130,100,10,4);g.fillStyle='#07060f';g.fillRect(54,62,52,50);g.shadowColor=AM;g.shadowBlur=14;g.strokeStyle=AM;g.lineWidth=3;g.strokeRect(55,63,50,48);
    g.fillStyle=AM;g.beginPath();g.moveTo(80,72);g.lineTo(92,87);g.lineTo(80,102);g.lineTo(68,87);g.closePath();g.fill();g.shadowBlur=0;
    g.fillStyle='#0b0a16';g.beginPath();g.arc(80,36,21,0,7);g.fill();g.shadowColor=CY;g.shadowBlur=12;g.fillStyle=CY;g.fillRect(60,40,40,4);g.shadowBlur=0});
  const T=[['NOODLES',MG],['24H RAMEN',AM],['KATANA BAR',CY],['MEGACRED',AM],['SYNTH/SKIN',MG],['DATA PAWN',CY],['GHOST VPN','#8cff3a'],['CHROME DOC',MG]];
  SP={cars:cs,lamp,shard,shieldP,overP,player,towers:[1,2,3,4].map(s=>towerSprite(s*977)),signs:T.map(t=>signSprite(t[0],t[1]))};
  for(let i=0;i<4;i++)noise.push(mk(96,96,(g,w,h)=>{const d=g.createImageData(w,h);for(let p=0;p<d.data.length;p+=4){const v=Math.random()<.5?255:Math.random()*60;d.data[p]=d.data[p+1]=d.data[p+2]=v;d.data[p+3]=255}g.putImageData(d,0,0)}))}
function skyline(w,h,seed,base,win){return mk(w,h,g=>{const r=rng(seed);let x=0;const cols=[theme.edge,theme.grid,AM];
  while(x<w){const bw=18+r()*52,bh=h*(.2+r()*r()*.78);g.fillStyle=base;g.fillRect(x,h-bh,bw,bh);
    for(let yy=h-bh+4;yy<h-3;yy+=6)for(let xx=x+3;xx<x+bw-4;xx+=5)if(r()<win){g.fillStyle=cols[r()*3|0];g.globalAlpha=.3+r()*.6;g.fillRect(xx,yy,2,3)}
    g.globalAlpha=1;if(r()<.3){g.fillStyle=base;g.fillRect(x+bw/2,h-bh-16,2,16);g.fillStyle='#ff2244';g.fillRect(x+bw/2-1,h-bh-18,4,3)}x+=bw+r()*5}})}
function buildStatic(){
  const T=theme;skyFar=skyline(1024,220,11,T.far,.10);skyNear=skyline(1024,300,29,T.near,.3);
  bgSky=mk(W,H,g=>{const hz=H/2,gr=g.createLinearGradient(0,0,0,hz);[0,.45,.8,1].forEach((s,i)=>gr.addColorStop(s,T.sky[i]));g.fillStyle=gr;g.fillRect(0,0,W,hz+2);
    const r=rng(7);for(let i=0;i<160;i++){g.fillStyle='rgba(255,255,255,'+(.2+r()*.7)+')';const s=r()<.9?1:2;g.fillRect(r()*W,r()*hz*.7,s,s)}
    const Rd=Math.min(H*.27,W*.3),cx=W*.5,cy=hz-Rd*.35,halo=g.createRadialGradient(cx,cy,Rd*.6,cx,cy,Rd*2.2);halo.addColorStop(0,'rgba('+T.halo+',.45)');halo.addColorStop(1,'rgba('+T.halo+',0)');g.fillStyle=halo;g.fillRect(0,0,W,hz);
    g.save();g.beginPath();g.arc(cx,cy,Rd,0,7);g.clip();const sg=g.createLinearGradient(0,cy-Rd,0,cy+Rd);sg.addColorStop(0,T.sun[0]);sg.addColorStop(.45,T.sun[1]);sg.addColorStop(1,T.sun[2]);g.fillStyle=sg;g.fillRect(cx-Rd,cy-Rd,Rd*2,Rd*2);
    g.globalCompositeOperation='destination-out';for(let i=0;i<9;i++){const y=cy-Rd*.05+i*i*Rd*.014+i*Rd*.06;g.fillRect(cx-Rd,y,Rd*2,1+i*Rd*.012)}g.restore();g.fillStyle=T.fog;g.fillRect(0,hz,W,H-hz)});
  vig=mk(W,H,g=>{const gr=g.createRadialGradient(W/2,H/2,Math.min(W,H)*.35,W/2,H/2,Math.hypot(W,H)*.6);gr.addColorStop(0,'rgba(0,0,0,0)');gr.addColorStop(1,'rgba(0,0,0,.72)');g.fillStyle=gr;g.fillRect(0,0,W,H)});
  scanPat=ctx.createPattern(mk(2,4,g=>{g.fillStyle='rgba(0,0,0,.26)';g.fillRect(0,3,2,1)}),'repeat');
  bloomC=mk(Math.max(8,W/8|0),Math.max(8,H/8|0),()=>{});bloomX=bloomC.getContext('2d')}
function resize(){const r=cv.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,3),cw=r.width||innerWidth,chh=r.height||innerHeight,w=cw*d,h=chh*d,k=Math.min(1,resMax/Math.max(w,h));
  W=cv.width=Math.max(320,Math.round(w*k));H=cv.height=Math.max(240,Math.round(h*k));u=Math.sqrt(W*H)/85;
  const cs=getComputedStyle($('sa')),rootPad=parseFloat(getComputedStyle(document.documentElement).paddingTop)||0,f=W/cw;
  sa={t:rootPad?0:(parseFloat(cs.paddingTop)||0)*f,r:(parseFloat(cs.paddingRight)||0)*f,b:rootPad?0:(parseFloat(cs.paddingBottom)||0)*f,l:(parseFloat(cs.paddingLeft)||0)*f};
  if(SP)buildStatic()}
function setTheme(i){theme=TH[i%TH.length];if(SP&&W)buildStatic()}

/* ---------- track ---------- */
function buildTrack(st,seed,first){
  const r=rng(seed);segs=[];cars=[];
  const lastY=()=>segs.length?segs[segs.length-1].p2.wy:0;
  const add=(curve,y)=>{const n=segs.length;segs.push({index:n,p1:{wy:lastY(),wz:n*SEG},p2:{wy:y,wz:(n+1)*SEG},curve,sprites:[],gate:0,clip:0,lamp:n%20===10,dark:Math.floor(n/RUMBLE)%2})};
  const road=(en,ho,le,c,y)=>{const sy=lastY(),ey=sy+y*SEG,t=en+ho+le;for(let n=0;n<en;n++)add(easeIn(0,c,n/en),easeIO(sy,ey,n/t));for(let n=0;n<ho;n++)add(c,easeIO(sy,ey,(en+n)/t));for(let n=0;n<le;n++)add(easeIO(c,0,n/le),easeIO(sy,ey,(en+ho+n)/t))};
  const len=2400+Math.min(st,8)*260,cm=Math.min(5,3+st*.35);
  road(20,first?90:30,20,0,0);
  while(segs.length<len){const n=25+r()*45|0,c=[0,0,.5,-.5,.75,-.75,1,-1][r()*8|0]*cm,hl=[0,0,20,-20,40,-40,60,-60][r()*8|0];road(n,n,n,c,hl)}
  finishIdx=segs.length;road(50,400,50,0,0);
  const N=segs.length,lane=()=>LANES[r()*3|0];
  for(let i=10;i<N;i+=20)segs[i].sprites.push({img:SP.lamp,off:-1.3,w:520,flip:false},{img:SP.lamp,off:1.3,w:520,flip:true});
  for(let i=6;i<N;i+=5+(r()*5|0)){const side=r()<.5?-1:1;segs[i].sprites.push({img:SP.towers[r()*4|0],off:side*(2.6+r()*4),w:1700+r()*1500,flip:r()<.5});
    if(r()<.5&&segs[i+1])segs[i+1].sprites.push({img:SP.towers[r()*4|0],off:-side*(2.6+r()*4),w:1700+r()*1500,flip:r()<.5})}
  for(let i=30;i<N;i+=28+(r()*20|0))segs[i].sprites.push({img:SP.signs[r()*8|0],off:(r()<.5?-1:1)*1.75,w:900,flip:false});
  for(let i=180;i<finishIdx-60;i+=220)segs[i].gate=1;segs[finishIdx].gate=2;
  for(let i=first?230:120;i<finishIdx-40;i+=90+(r()*60|0)){const l=lane();for(let k=0;k<5;k++)segs[i+k*6].sprites.push({img:SP.shard,off:l,w:190,kind:'shard',taken:false})}
  for(let i=520,k=st;i<finishIdx-80;i+=640+(r()*200|0),k++)segs[i].sprites.push(k%2?{img:SP.overP,off:lane(),w:300,kind:'over',taken:false}:{img:SP.shieldP,off:lane(),w:300,kind:'shield',taken:false});
  const nc=(len/15|0)+Math.min(st,10)*16,mkCar=(z,off,sp,tall)=>({z,off,to:off,lt:2+r()*5,speed:sp,img:SP.cars[tall?5+(r()*2|0):r()*5|0],w:tall?640:560,snow:false,dead:false,pdz:1,scr:null,osc:0,ph:0});
  if(first)cars.push(mkCar(150*SEG,0,MAXSP*.3,false));
  for(let i=0;i<nc;i++){const tall=r()<.22;cars.push(mkCar(((first?220:90)+r()*(N-320))*SEG,lane()+(r()-.5)*.1,MAXSP*(.22+r()*.33),tall))}
  const ns=(first?3:5)+Math.min(st,10)*3+(theme.nul?6:0),snow=(z,off,osc)=>cars.push({z,off,to:off,lt:0,speed:0,img:null,w:520,snow:true,dead:false,pdz:1,scr:null,osc,ph:r()*6.28});
  for(let i=0;i<ns;i++){const z=((first?700:300)+r()*(finishIdx-(first?800:400)))*SEG;
    if(st>=1&&r()<.3){const a=r()*3|0;snow(z,LANES[a],0);snow(z,LANES[(a+1)%3],0)}else snow(z,st>=2&&r()<.3?0:lane(),st>=2&&r()<.3?.62:0)}
}
const segAt=z=>segs[clamp(Math.floor(z/SEG),0,segs.length-1)];

/* ---------- run flow ---------- */
const up=k=>SV.up[k]||0;
function pop(txt,col){popups.push({txt,col,t:0});if(popups.length>4)popups.shift()}
function burst(x,y,n,col,sp){for(let i=0;i<n&&parts.length<160;i++){const a=Math.random()*6.283,v=(.3+Math.random())*sp;parts.push({x,y,vx:Math.cos(a)*v,vy:Math.sin(a)*v-sp*.4,l:.5+Math.random()*.5,c:col})}}
function count(k,v){R[k]=v===undefined?(R[k]||0)+1:Math.max(R[k]||0,v);
  for(const c of SV.con){if(c.done||c.id!==k)continue;const d=conDef(c);if(R[k]>=d.n[c.lv]){c.done=true;const rw=d.r[c.lv];SV.cred+=rw;paid+=rw;SV.clv[k]=c.lv+1;persist();pop('CONTRACT PAID  +'+rw+' CRED','#7dffb0');Snd.sfx.pay();hap('medium')}}}
function startRun(m){
  Snd.init();Snd.volume(SV.set.mus,SV.set.sfx);mode=m;seedBase=m==='daily'?hash(today()):(Date.now()^Math.random()*1e9)>>>0;
  stage=0;setTheme(0);const first=!SV.tut;buildTrack(0,seedBase,first);
  pos=0;px=0;speed=0;score=0;combo=1;comboT=0;boost=0;tether=null;infect=0;clearT=0;popups=[];parts=[];R={};paid=0;shield=false;ts=1;hitThisZone=false;hadTarget=false;
  tut=first?1:0;tutT=0;timeLeft=finishIdx/60/.68+up('window')*3+(first?12:0);state='play';flash=calm()?0:.8;
  Snd.play(0,true);show(null);$('pauseBtn').hidden=false;pop(m==='daily'?'DAILY RUN // PACKAGE ARMED':'PACKAGE ARMED','#fff');cv.focus()}
function gameOver(){
  state='over';Snd.sfx.over();hap('heavy');if(!calm())glitch=1;$('pauseBtn').hidden=true;
  const sc=Math.floor(score),earned=Math.floor(sc/150)+(R.shard||0)*2,isBest=sc>SV.best;SV.cred+=earned;SV.runs++;if(isBest)SV.best=sc;
  if(mode==='daily'){if(SV.daily.d!==today())SV.daily={d:today(),s:0};if(sc>SV.daily.s)SV.daily.s=sc}
  const done=SV.con.filter(c=>c.done).map(conText);fillContracts();persist();
  $('oZone').textContent='The window closed in '+theme.name+'.';$('oScore').textContent=sc.toLocaleString();$('oBest').hidden=!isBest;
  $('oStats').innerHTML='';[['Zones cleared',stage],['Slingshots',R.sling||0],['Near misses',R.near||0],['Shards',R.shard||0],['Cred earned','+'+(earned+paid)]].forEach(([a,b])=>{const li=document.createElement('li');li.innerHTML='<span></span><b></b>';li.firstChild.textContent=a;li.lastChild.textContent=b;$('oStats').appendChild(li)});
  $('oCon').hidden=!done.length;$('oCon').textContent=done.length?'Contracts paid: '+done.join(' · '):'';
  setTimeout(()=>{if(state==='over'){show('over');Snd.play('menu')}},calm()?300:900)}
function toTitle(){state='title';$('pauseBtn').hidden=true;setTheme(0);buildTrack(0,4242,false);pos=0;boost=0;tether=null;infect=0;clearT=0;popups=[];Snd.play('menu');refreshTitle();show('title')}
function fire(){if(state!=='play'||tether||dryT>0)return;if(target){tether={car:target,t:0};Snd.sfx.zap();hap('light');if(tut===2){tut=3;tutT=0}}else{Snd.sfx.dry();dryT=.6}}
function bump(n){combo=Math.min(9,combo+n);comboT=5;count('combo',combo)}
function crashFx(){combo=1;hitThisZone=true;if(!calm()){glitch=.6;shake=1}burst(W/2,H*.8,22,'#ffd0a0',u*30);hap('heavy')}

function update(rdt){
  time+=rdt;flash=Math.max(0,flash-rdt*1.6);glitch=Math.max(0,glitch-rdt*1.8);shake=Math.max(0,shake-rdt*3);bolt=Math.max(0,bolt-rdt*3);
  for(const p of popups)p.t+=rdt;popups=popups.filter(p=>p.t<1.6);
  for(const p of parts){p.l-=rdt;p.x+=p.vx*rdt;p.y+=p.vy*rdt;p.vy+=u*60*rdt}parts=parts.filter(p=>p.l>0);
  if(theme.storm&&!calm()){boltT-=rdt;if(boltT<=0){bolt=1;boltT=3+Math.random()*7}}
  if(state==='pause')return;
  ts+=((tut===2?.22:1)-ts)*Math.min(1,rdt*8);const dt=rdt*ts;
  const pseg=segAt(pos+playerZ),old=pos,R_=11000+up('range')*2200,LW=.5+up('range')*.07;
  if(state==='play'){
    infect=Math.max(0,infect-dt);dryT=Math.max(0,dryT-dt);
    let steer=(keys.right?1:0)-(keys.left?1:0);if(infect>0)steer+=Math.sin(time*19)*.7;
    steerVis+=(steer-steerVis)*Math.min(1,rdt*9);
    const sp=speed/MAXSP,dx=dt*2.3*Math.min(1,sp*1.6+.1);
    px+=steer*dx-dx*Math.min(1,sp)*pseg.curve*CENT;px=clamp(px,-2.2,2.2);
    const max=(boost>0||tether?MAXSP*1.5:MAXSP)*(infect>0?.55:1),brk=keys.brake||(keys.left&&keys.right&&touchSeen);
    if(brk&&!tether)speed+=BRAKE*dt;else speed+=ACCEL*(boost>0||tether?5:1)*dt;
    if(speed>max)speed=Math.max(max,speed-ACCEL*2.5*dt);
    if(Math.abs(px)>1.05&&speed>OFFLIM)speed+=OFFDEC*dt;
    speed=clamp(speed,0,MAXSP*1.5);
    if(boost>0){boost-=dt;if(Math.random()<.6)parts.push({x:W/2+(Math.random()-.5)*u*6,y:H*.96,vx:(Math.random()-.5)*u*20,vy:-u*10,l:.35,c:CY})}
    if(comboT>0){comboT-=dt;if(comboT<=0)combo=1}
    if(tether){tether.t+=dt;const dz=tether.car.z-(pos+playerZ);
      if(tether.t>.55||dz<500||tether.car.dead){tether=null;boost=2.6+up('sling')*.35;bump(1);count('sling');timeLeft+=.5;score+=300*combo;Snd.sfx.whoosh();hap('medium');pop('SLINGSHOT  +'+300*combo,CY);if(!calm())shake=.4;
        if(tut===3){tut=4;tutT=0;SV.tut=true;persist()}}}
    if(tut){tutT+=rdt;if(tut===1&&tutT>4)tut=1.5;if(tut===4&&tutT>4)tut=0}
  }else{speed=MAXSP*.42;px=Math.sin(time*.4)*.3;steerVis=Math.cos(time*.4)*.3}
  pos+=speed*dt;
  if(state!=='play'&&pos>(finishIdx-20)*SEG){pos=0;for(const c of cars)c.pdz=1}
  bgOff+=pseg.curve*(pos-old)/SEG*.0009;
  const pz=pos+playerZ;target=null;let bestD=1e9;
  for(const c of cars){if(c.dead)continue;
    c.z+=c.speed*dt;if(c.z>(segs.length-3)*SEG){c.dead=true;continue}
    if(c.snow){if(c.osc)c.off=Math.sin(time*1.1+c.ph)*c.osc}
    else if(stage>=1){c.lt-=dt;if(c.lt<=0){c.lt=3+Math.random()*5;if(Math.random()<.35){const i=LANES.reduce((b,l,k)=>Math.abs(l-c.to)<Math.abs(LANES[b]-c.to)?k:b,0);c.to=LANES[clamp(i+(Math.random()<.5?-1:1),0,2)]}}c.off+=clamp(c.to-c.off,-.7*dt,.7*dt)}
    const dz=c.z-pz,dxx=Math.abs(c.off-px);
    if(state==='play'){
      if(c.pdz>0&&dz<=0){
        const hit=dxx<(c.snow?.44:.42),bst=boost>0||tether;
        if(hit&&c.snow){c.dead=true;
          if(bst){score+=500;count('purge');pop('PURGED  +500','#fff');Snd.sfx.crash();burst(W/2,H*.7,26,'#fff',u*40);hap('medium')}
          else if(shield){shield=false;Snd.sfx.shieldBreak();pop('SHIELD BURNED','#7dffb0');burst(W/2,H*.8,20,'#7dffb0',u*30);hap('medium')}
          else{infect=3;timeLeft-=3;speed*=.4;crashFx();if(!calm())shake=1;Snd.sfx.snow();pop('STATIC BLOOM  −3s','#ff3355')}}
        else if(hit&&!bst){
          if(shield){shield=false;Snd.sfx.shieldBreak();pop('SHIELD BURNED','#7dffb0');burst(W/2,H*.8,20,'#7dffb0',u*30);hap('medium')}
          else{speed=c.speed*.7;pos=c.z-playerZ-30;crashFx();Snd.sfx.crash();pop('IMPACT','#ff3355');c.pdz=1;continue}}
        else if(!hit&&dxx<.85&&!c.snow){bump(1);count('near');timeLeft+=.3;score+=100*combo;Snd.sfx.miss();hap('light');pop('NEAR MISS  +'+100*combo,MG)}
      }
      if(!c.snow&&dz>350&&dz<R_&&dxx<LW&&dz<bestD&&!(tether&&tether.car===c)){bestD=dz;target=c}
    }
    c.pdz=dz;
  }
  if(state==='play'){
    if(target&&!hadTarget){Snd.sfx.lock();if(tut&&tut<2&&bestD<7000){tut=2;tutT=0}}hadTarget=!!target;
    if(tut===2&&!target)tut=1.5;
    const a=Math.floor((old+playerZ)/SEG),b=Math.floor(pz/SEG),mw=.36+up('magnet')*.12;
    for(let i=a;i<=b&&i<segs.length;i++)for(const s of segs[i].sprites){if(!s.kind||s.taken)continue;const d=Math.abs(s.off-px);
      if(s.kind==='shard'&&d<mw){s.taken=true;timeLeft+=.6+up('magnet')*.06;score+=50*combo;count('shard');Snd.sfx.blip(shardRun++);comboT=Math.max(comboT,2);burst(W/2+(s.off-px)*W*.3,H*.82,6,CY,u*18)}
      else if(s.kind==='shield'&&d<.45){s.taken=true;shield=true;Snd.sfx.shield();pop('SHIELD UP','#7dffb0');hap('light')}
      else if(s.kind==='over'&&d<.45){s.taken=true;boost=Math.max(boost,4);Snd.sfx.power();Snd.sfx.whoosh();pop('OVERCLOCK',AM);hap('medium')}}
    score+=speed*dt*.004*combo;
    if(clearT>0){clearT-=rdt;if(clearT<=0){stage++;count('zone',stage+1);setTheme(stage);buildTrack(stage,seedBase+stage*7919,false);pos=0;px=0;tether=null;hitThisZone=false;
        timeLeft+=finishIdx/60/.84+up('window')*1.5;if(!calm()){flash=1;glitch=.5}Snd.play(stage%Snd.TRACKS.length,true);pop('ZONE '+(stage+1)+' // '+theme.name,AM)}}
    else{timeLeft-=dt;
      if(pz>=finishIdx*SEG){clearT=2.6;const bn=Math.floor(timeLeft*100);score+=bn;Snd.sfx.clear();hap('medium');pop('DELIVERED  +'+bn,AM);if(!calm())flash=.6;if(!hitThisZone)count('clean')}
      else if(timeLeft<=0){timeLeft=0;gameOver()}}
  }
  Snd.mood(state==='play'?(infect>0?420:19000):state==='pause'?380:1500,state==='play'&&(boost>0||tether)?1:0,state==='play'&&timeLeft<10&&clearT<=0?1:0);
}

/* ---------- render ---------- */
function project(p,camX,camY,camZ){p.cz=p.wz-camZ;const s=p.scale=camDepth/p.cz;p.sx=Math.round(W/2-s*camX*W/2);p.sy=Math.round(H/2-s*(p.wy-camY)*H/2);p.sw=s*ROADW*W/2}
function quad(x1,y1,x2,y2,x3,y3,x4,y4,c){ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.lineTo(x3,y3);ctx.lineTo(x4,y4);ctx.closePath();ctx.fill()}
function drawSeg(s,n){
  const a=s.p1,b=s.p2,h=a.sy-b.sy,T=theme;
  ctx.fillStyle=T.ground[s.dark];ctx.fillRect(0,b.sy,W,h);
  if(s.index%RUMBLE===0){ctx.globalAlpha=.42;ctx.fillStyle=T.grid;ctx.fillRect(0,a.sy-Math.max(1,h*.14),W,Math.max(1,h*.14))}
  ctx.globalAlpha=.5;
  for(const k of[1.7,2.7,4.2,6.5,10]){const w1=a.sw*.012+.5,w2=b.sw*.012+.5;
    quad(a.sx-a.sw*k-w1,a.sy,a.sx-a.sw*k+w1,a.sy,b.sx-b.sw*k+w2,b.sy,b.sx-b.sw*k-w2,b.sy,T.grid);quad(a.sx+a.sw*k-w1,a.sy,a.sx+a.sw*k+w1,a.sy,b.sx+b.sw*k+w2,b.sy,b.sx+b.sw*k-w2,b.sy,T.grid)}
  ctx.globalAlpha=1;
  const r1=a.sw/7,r2=b.sw/7,l1=a.sw/40,l2=b.sw/40,rc=s.dark?T.edgeD:T.edge;
  quad(a.sx-a.sw-r1,a.sy,a.sx-a.sw,a.sy,b.sx-b.sw,b.sy,b.sx-b.sw-r2,b.sy,rc);quad(a.sx+a.sw+r1,a.sy,a.sx+a.sw,a.sy,b.sx+b.sw,b.sy,b.sx+b.sw+r2,b.sy,rc);
  quad(a.sx-a.sw,a.sy,a.sx+a.sw,a.sy,b.sx+b.sw,b.sy,b.sx-b.sw,b.sy,T.road[s.dark]);
  if(s.lamp||s.index%20===9||s.index%20===11){ctx.globalAlpha=s.lamp?.16:.08;quad(a.sx-a.sw,a.sy,a.sx+a.sw,a.sy,b.sx+b.sw,b.sy,b.sx-b.sw,b.sy,'#ffd0f4');ctx.globalAlpha=1}
  if(!s.dark)for(const k of[-1/3,1/3])quad(a.sx+a.sw*k-l1,a.sy,a.sx+a.sw*k+l1,a.sy,b.sx+b.sw*k+l2,b.sy,b.sx+b.sw*k-l2,b.sy,T.lane);
  quad(a.sx-a.sw,a.sy,a.sx-a.sw+l1*1.5,a.sy,b.sx-b.sw+l2*1.5,b.sy,b.sx-b.sw,b.sy,T.line);quad(a.sx+a.sw-l1*1.5,a.sy,a.sx+a.sw,a.sy,b.sx+b.sw,b.sy,b.sx+b.sw-l2*1.5,b.sy,T.line);
  const f=1-1/Math.exp((n/DRAW)*(n/DRAW)*5);if(f>.02){ctx.globalAlpha=f;ctx.fillStyle=T.fog;ctx.fillRect(0,b.sy,W,h);ctx.globalAlpha=1}
}
function drawSprite(img,ww,scale,sx,sy,clipY,flip,alpha,lift){
  const dw=ww*scale*W/2,dh=dw*img.height/img.width,y=sy-dh-(lift||0),ch=Math.max(0,y+dh-clipY);
  if(ch>=dh||dw<1.5||sx+dw/2<0||sx-dw/2>W)return;
  ctx.globalAlpha=alpha;const sh=img.height*(1-ch/dh);
  if(flip){ctx.save();ctx.translate(sx,0);ctx.scale(-1,1);ctx.drawImage(img,0,0,img.width,sh,-dw/2,y,dw,dh-ch);ctx.restore()}else ctx.drawImage(img,0,0,img.width,sh,sx-dw/2,y,dw,dh-ch);
  ctx.globalAlpha=1}
function tile(img,th,off,yb){const tw=th*img.width/img.height;let x=-(((off*tw)%tw)+tw)%tw;for(;x<W;x+=tw)ctx.drawImage(img,x,yb-th,tw+1,th)}
const buckets=[];for(let i=0;i<DRAW;i++)buckets.push([]);
const rain=[];for(let i=0;i<90;i++)rain.push({x:Math.random(),y:Math.random(),l:.03+Math.random()*.05,v:.9+Math.random()*.8});
function render(dt){
  const hz=H/2,T=theme;
  ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';
  ctx.drawImage(bgSky,0,0);
  /* searchlights and air traffic */
  ctx.globalCompositeOperation='lighter';ctx.fillStyle='rgba('+T.halo+',.07)';
  for(let i=0;i<3;i++){const bx=(((.2+i*.3-bgOff*.3)%1)+1)%1*W,an=-Math.PI/2+Math.sin(time*.25+i*2.1)*.55,L=H*.55;ctx.beginPath();ctx.moveTo(bx,hz);ctx.lineTo(bx+Math.cos(an-.035)*L,hz+Math.sin(an-.035)*L);ctx.lineTo(bx+Math.cos(an+.035)*L,hz+Math.sin(an+.035)*L);ctx.closePath();ctx.fill()}
  for(let i=0;i<12;i++){const dir=i%2?1:-1,x=((((i*.137+time*(.02+i%3*.012)*dir-bgOff*.4)%1.2)+1.2)%1.2-.1)*W,y=hz-H*(.05+(i%4)*.028);ctx.fillStyle=i%3?'rgba(255,255,255,.8)':'rgba(255,60,80,.9)';ctx.fillRect(x,y,u*.28,u*.16);ctx.fillStyle='rgba(255,255,255,.18)';ctx.fillRect(x-dir*u*1.6,y,u*1.6,u*.12)}
  if(bolt>0){ctx.fillStyle='rgba(200,225,255,'+bolt*.35+')';ctx.fillRect(0,0,W,hz)}
  ctx.globalCompositeOperation='source-over';
  tile(skyFar,H*.2,bgOff*.5,hz+2);tile(skyNear,H*.26,bgOff,hz+2);
  const hg=ctx.createLinearGradient(0,hz-H*.1,0,hz+2);hg.addColorStop(0,'rgba('+T.fogc+',0)');hg.addColorStop(1,T.fog);ctx.fillStyle=hg;ctx.fillRect(0,hz-H*.1,W,H*.1+3);
  const sk=shake>0?(Math.random()-.5)*shake*u*1.5:0;ctx.translate(sk,sk*.6);

  const base=segAt(pos),bp=(pos%SEG)/SEG,pseg=segAt(pos+playerZ),pp=((pos+playerZ)%SEG)/SEG,camY=CAMH+lerp(pseg.p1.wy,pseg.p2.wy,pp);
  for(let i=0;i<DRAW;i++)buckets[i].length=0;
  for(const c of cars){c.scr=null;if(c.dead)continue;const i=Math.floor(c.z/SEG)-base.index;if(i>0&&i<DRAW)buckets[i].push(c)}
  let maxy=H,x=0,dx=-(base.curve*bp),nmax=0;
  for(let n=0;n<DRAW;n++){const s=segs[base.index+n];if(!s)break;nmax=n+1;
    project(s.p1,px*ROADW-x,camY,pos);project(s.p2,px*ROADW-x-dx,camY,pos);x+=dx;dx+=s.curve;s.clip=maxy;
    if(s.p1.cz<=camDepth||s.p2.sy>=s.p1.sy||s.p2.sy>=maxy)continue;drawSeg(s,n);maxy=s.p2.sy}
  for(let n=nmax-1;n>0;n--){const s=segs[base.index+n],a=s.p1;if(a.cz<=camDepth)continue;
    const al=clamp((DRAW-n)/35,0,1);
    if(s.gate){const gw=a.sw*1.28,gh=a.sw*1.15,col=s.gate===2?AM:T.edge,lw=Math.max(1.5,a.sw*.05);
      ctx.save();ctx.beginPath();ctx.rect(0,0,W,s.clip);ctx.clip();ctx.lineJoin='round';
      for(const[wd,c,ga]of[[lw*3,col,.25],[lw,col,1],[lw*.3,'#fff',.9]]){ctx.globalAlpha=al*ga;ctx.strokeStyle=c;ctx.lineWidth=wd;ctx.beginPath();ctx.moveTo(a.sx-gw,a.sy);ctx.lineTo(a.sx-gw,a.sy-gh);ctx.lineTo(a.sx+gw,a.sy-gh);ctx.lineTo(a.sx+gw,a.sy);ctx.stroke()}
      if(s.gate===2&&a.sw>30){ctx.globalAlpha=al;ctx.fillStyle=AM;ctx.font='900 '+(a.sw*.2)+'px Orbitron,sans-serif';ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillText('DROP ZONE',a.sx,a.sy-gh-lw*2)}
      ctx.restore();ctx.globalAlpha=1}
    for(const sp of s.sprites){if(sp.taken)continue;const lift=sp.kind?a.sw*(.1+Math.sin(time*5+s.index)*.03):0;drawSprite(sp.img,sp.w,a.scale,a.sx+sp.off*a.sw,a.sy,s.clip,sp.flip,al,lift)}
    for(const c of buckets[n]){const pc=(c.z%SEG)/SEG,sc=lerp(a.scale,s.p2.scale,pc),cx=lerp(a.sx,s.p2.sx,pc)+sc*c.off*ROADW*W/2,cy=lerp(a.sy,s.p2.sy,pc),dw=c.w*sc*W/2;
      c.scr={x:cx,y:cy,w:dw};
      if(c.snow){const y=cy-dw*1.1;if(y+dw<s.clip&&dw>2){ctx.globalAlpha=al;ctx.imageSmoothingEnabled=false;ctx.drawImage(noise[calm()?0:(time*20+c.z|0)&3],cx-dw/2,y,dw,dw);ctx.imageSmoothingEnabled=true;
          ctx.strokeStyle=calm()||(time*12|0)%2?'#ff3355':'#fff';ctx.lineWidth=Math.max(1,dw*.05);ctx.strokeRect(cx-dw/2,y,dw,dw);
          if(!calm()&&(time*9|0)%3===0){ctx.fillStyle='#ff3355';ctx.fillRect(cx-dw*.7,y+dw*Math.random(),dw*1.4,dw*.06)}ctx.globalAlpha=1}}
      else drawSprite(c.img,c.w,sc,cx,cy,s.clip,false,al,0)}
  }
  /* reticle, tether, player */
  const port=W<H,pw=350/CAMH*W/2*(port?1.5:1),ph=pw*210/160,pxs=W/2+steerVis*pw*.12,pys=H-sa.b*.5-ph*.04+Math.sin(time*30)*speed/MAXSP*u*.08;
  if(state==='play'&&target&&target.scr&&!tether){const t=target.scr,s=Math.max(t.w*.75,u*2.2),cyy=t.y-t.w*.3,k=s*.3;ctx.strokeStyle=CY;ctx.lineWidth=Math.max(1.5,u*.18);ctx.globalAlpha=calm()?.9:.6+Math.sin(time*14)*.3;
    ctx.beginPath();for(const[sx,sy]of[[-1,-1],[1,-1],[1,1],[-1,1]]){ctx.moveTo(t.x+sx*s,cyy+sy*s-sy*k);ctx.lineTo(t.x+sx*s,cyy+sy*s);ctx.lineTo(t.x+sx*s-sx*k,cyy+sy*s)}ctx.stroke();ctx.globalAlpha=1}
  if(tether){const t=tether.car.scr||{x:W/2,y:hz,w:10},x0=pxs+pw*.3,y0=pys-ph*.52,x1=t.x,y1=t.y-t.w*.25;
    ctx.globalCompositeOperation='lighter';for(const[wd,c]of[[u*.9,'rgba(25,240,255,.3)'],[u*.25,'#eaffff']]){ctx.strokeStyle=c;ctx.lineWidth=wd;ctx.beginPath();ctx.moveTo(x0,y0);
      for(let i=1;i<6;i++){const f=i/6;ctx.lineTo(lerp(x0,x1,f)+(Math.random()-.5)*u*1.2,lerp(y0,y1,f)+(Math.random()-.5)*u*1.2)}ctx.lineTo(x1,y1);ctx.stroke()}ctx.globalCompositeOperation='source-over'}
  if(state!=='title'){
    const bst=boost>0||tether;
    ctx.globalCompositeOperation='lighter';const gl=ctx.createRadialGradient(pxs,pys-ph*.06,0,pxs,pys-ph*.06,pw*.8);gl.addColorStop(0,bst?'rgba(255,255,255,.55)':'rgba(25,240,255,.4)');gl.addColorStop(1,'rgba(25,240,255,0)');
    ctx.fillStyle=gl;ctx.save();ctx.translate(pxs,pys-ph*.06);ctx.scale(1,.22);ctx.beginPath();ctx.arc(0,0,pw*.8,0,7);ctx.restore();ctx.fill();
    if(bst){for(let i=1;i<4;i++){ctx.globalAlpha=.22/i;ctx.drawImage(SP.player,pxs-pw/2*(1+i*.12),pys-ph*(1+i*.12)+i*u*.8,pw*(1+i*.12),ph*(1+i*.12))}ctx.globalAlpha=1}
    ctx.globalCompositeOperation='source-over';
    ctx.save();ctx.translate(pxs,pys);ctx.rotate(steerVis*.16);if(infect>0&&!calm())ctx.translate((Math.random()-.5)*u,0);ctx.drawImage(SP.player,-pw/2,-ph,pw,ph);ctx.restore();
    if(shield){ctx.globalCompositeOperation='lighter';ctx.strokeStyle='rgba(125,255,176,'+(.55+Math.sin(time*6)*.2)+')';ctx.lineWidth=u*.35;ctx.beginPath();ctx.ellipse(pxs,pys-ph*.5,pw*.62,ph*.58,0,0,7);ctx.stroke();ctx.fillStyle='rgba(125,255,176,.07)';ctx.fill();ctx.globalCompositeOperation='source-over'}
  }
  ctx.setTransform(1,0,0,1,0,0);
  /* particles, rain, speed lines */
  ctx.globalCompositeOperation='lighter';for(const p of parts){ctx.globalAlpha=clamp(p.l*2,0,1);ctx.fillStyle=p.c;ctx.fillRect(p.x,p.y,u*.35,u*.35)}ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';
  const sp=speed/MAXSP;ctx.strokeStyle='rgba(170,220,255,.28)';ctx.lineWidth=Math.max(1,u*.09);ctx.beginPath();
  for(const r of rain){r.y+=r.v*dt*(1.1+sp);r.x+=(r.x-.5)*sp*dt*1.4;if(r.y>1.05||r.x<-.05||r.x>1.05){r.y=-.08;r.x=Math.random()}ctx.moveTo(r.x*W,r.y*H);ctx.lineTo((r.x+(r.x-.5)*sp*.05)*W,(r.y+r.l*(1+sp))*H)}ctx.stroke();
  if(boost>0||tether){ctx.globalCompositeOperation='lighter';ctx.strokeStyle='rgba(25,240,255,.35)';ctx.lineWidth=u*.14;ctx.beginPath();
    for(let i=0;i<26;i++){const an=Math.random()*6.283,r0=(.35+Math.random()*.4)*Math.hypot(W,H)*.6,r1=r0*(1.15+Math.random()*.4);ctx.moveTo(W/2+Math.cos(an)*r0,hz+Math.sin(an)*r0);ctx.lineTo(W/2+Math.cos(an)*r1,hz+Math.sin(an)*r1)}ctx.stroke();ctx.globalCompositeOperation='source-over'}
  /* bloom, vignette, damage */
  if(resMax>800){bloomX.drawImage(cv,0,0,bloomC.width,bloomC.height);ctx.globalCompositeOperation='lighter';ctx.globalAlpha=.3;ctx.drawImage(bloomC,0,0,W,H);ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over'}
  ctx.drawImage(vig,0,0);
  if(infect>0||state==='over'){ctx.globalAlpha=state==='over'?.14:Math.min(calm()?.25:.75,infect*.4);ctx.save();ctx.scale(4,4);if(!calm())ctx.translate(-Math.random()*96,-Math.random()*96);ctx.imageSmoothingEnabled=false;
    ctx.fillStyle=ctx.createPattern(noise[calm()?0:(time*30|0)&3],'repeat');ctx.fillRect(0,0,W/4+96,H/4+96);ctx.restore();ctx.imageSmoothingEnabled=true;ctx.globalAlpha=1}
  const g=calm()?0:Math.max(glitch,infect>0?.5:0);
  if(g>0){for(let i=0;i<7;i++){const y=Math.random()*H|0,h=Math.random()*H*.07+2|0,d=(Math.random()-.5)*W*.09*g|0;ctx.drawImage(cv,0,y,W,h,d,y,W,h)}
    ctx.globalCompositeOperation='screen';ctx.globalAlpha=.3*g;ctx.drawImage(cv,u*.8*g,0);ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over'}
  if(state==='play'||state==='pause')drawHUD();
  ctx.fillStyle=scanPat;ctx.fillRect(0,0,W,H);
  if(flash>0){ctx.globalAlpha=Math.min(1,flash);ctx.fillStyle='#fff';ctx.fillRect(0,0,W,H);ctx.globalAlpha=1}
}
const FD=s=>'900 '+(s*u)+'px Orbitron,"Arial Black",sans-serif',FM=s=>(s*u)+'px "Share Tech Mono",Menlo,monospace';
function glow(txt,x,y,col,blur){ctx.shadowColor=col;ctx.shadowBlur=(blur||1.2)*u;ctx.fillStyle=col;ctx.fillText(txt,x,y);ctx.shadowBlur=0}
function split(txt,x,y){ctx.globalCompositeOperation='lighter';const o=u*.35+(calm()?0:Math.sin(time*3)*u*.15);ctx.fillStyle=MG;ctx.fillText(txt,x-o,y);ctx.fillStyle=CY;ctx.fillText(txt,x+o,y);ctx.globalCompositeOperation='source-over';ctx.fillStyle='#fff';ctx.fillText(txt,x,y)}
function fit(txt,size,maxW){ctx.font=FD(size);const m=ctx.measureText(txt).width;if(m>maxW)ctx.font=FD(size*maxW/m)}
function drawHUD(){
  const m=u*2.2,port=W<H,L=m+sa.l,Rt=W-m-sa.r,Tp=m+sa.t,Bt=H-m-sa.b;ctx.textBaseline='top';
  ctx.textAlign='left';ctx.font=FM(1.5);ctx.fillStyle='rgba(232,247,255,.75)';ctx.fillText('ZONE '+String(stage+1).padStart(2,'0')+' // '+theme.name,L,Tp);ctx.fillText(mode==='daily'?'DAILY WINDOW':'DELIVERY WINDOW',L,Tp+u*2.2);
  const low=timeLeft<10&&clearT<=0,tc=low?(calm()||(time*4|0)%2?'#ff3355':'#fff'):AM;ctx.font=FD(5);glow(timeLeft.toFixed(1),L,Tp+u*4,tc,1.5);
  ctx.textAlign='right';ctx.font=FM(1.5);ctx.fillStyle='rgba(232,247,255,.75)';ctx.fillText('SCORE',Rt,Tp);ctx.font=FD(3);glow(String(Math.floor(score)).padStart(7,'0'),Rt,Tp+u*2,CY,1);
  if(combo>1){ctx.font=FD(2.4);glow('×'+combo,Rt,Tp+u*6,MG,1.2);ctx.fillStyle='rgba(255,43,214,.8)';ctx.fillRect(Rt-u*8*comboT/5,Tp+u*9.2,u*8*comboT/5,u*.35)}
  if(shield){ctx.font=FM(1.4);ctx.fillStyle='#7dffb0';ctx.fillText('SHIELD ◆',Rt,Tp+u*(combo>1?10.4:6))}
  const bw=Math.min(W*.5,u*40),bx=(W-bw)/2,by=port?Tp+u*11.5:Tp+u*6.2,pr=clamp((pos+playerZ)/(finishIdx*SEG),0,1);
  ctx.fillStyle='rgba(232,247,255,.18)';ctx.fillRect(bx,by,bw,u*.5);ctx.shadowColor=AM;ctx.shadowBlur=u;ctx.fillStyle=AM;ctx.fillRect(bx,by,bw*pr,u*.5);ctx.shadowBlur=0;ctx.fillStyle='#fff';ctx.fillRect(bx+bw*pr-u*.2,by-u*.4,u*.4,u*1.3);
  ctx.textAlign='center';ctx.font=FM(1.2);ctx.fillStyle='rgba(232,247,255,.6)';ctx.fillText('DROP ZONE '+Math.max(0,((1-pr)*finishIdx*SEG/20000)).toFixed(1)+' KM',W/2,by+u*1.4);
  ctx.textAlign='right';ctx.textBaseline='bottom';ctx.font=FD(4);const bst=boost>0||tether;glow(String(speed/MAXSP*260|0),Rt,Bt-u*1.6,bst?'#fff':CY,bst?2.5:1);
  ctx.font=FM(1.4);ctx.fillStyle='rgba(232,247,255,.75)';ctx.fillText(bst?'KPH // SLINGSHOT':'KPH',Rt,Bt);
  ctx.textAlign='left';ctx.fillStyle=target?CY:'rgba(232,247,255,.45)';ctx.fillText(tether?'HARPOON ▸ REELING':dryT>0?'HARPOON ▸ REARMING':target?'HARPOON ▸ LOCK':'HARPOON ▸ LINE UP BEHIND A RIDE',L,Bt);
  if(touchSeen){ctx.globalAlpha=.16;ctx.fillStyle='#fff';ctx.font=FD(4);ctx.textBaseline='middle';ctx.textAlign='center';ctx.fillText('◀',W*.1,H*.72);ctx.fillText('▶',W*.9,H*.72);ctx.globalAlpha=1}
  ctx.textAlign='center';ctx.textBaseline='middle';
  popups.forEach((p,i)=>{ctx.globalAlpha=clamp(1.6-p.t,0,1);fit(p.txt,2.5,W*.9);glow(p.txt,W/2,H*.3-p.t*u*3+i*u*3.4,p.col,1.4)});ctx.globalAlpha=1;
  if(clearT>0){fit('PACKAGE DELIVERED',5,W*.9);split('PACKAGE DELIVERED',W/2,H*.42)}
  if(tut&&state==='play'){const msg=tut<2?(touchSeen?'HOLD THE LEFT OR RIGHT EDGE TO STEER':'← →  STEER'):tut===2?(touchSeen?'TAP THE CENTRE — FIRE THE HARPOON':'SPACE — FIRE THE HARPOON'):tut===3?'REELING IN…':'SLINGSHOT: YOU PHASE THROUGH TRAFFIC';
    if(tut!==1.5){fit(msg,2.6,W*.88);const y=H*.58;ctx.fillStyle='rgba(5,2,13,.7)';const mw=ctx.measureText(msg).width;ctx.fillRect(W/2-mw/2-u*2,y-u*2.4,mw+u*4,u*4.8);glow(msg,W/2,y,tut===2?CY:'#fff',1)}}
}

/* ---------- interface ---------- */
const SCREENS=['title','garage','settings','howto','pause','over'];
function show(id){for(const s of SCREENS)$(s).hidden=s!==id;$('ui').hidden=!id;if(id){const f=$(id).querySelector('[data-focus]');if(f&&!touchSeen)f.focus({preventScroll:true})}}
function refreshTitle(){$('tBest').textContent=SV.best.toLocaleString();$('tCred').textContent=SV.cred.toLocaleString();
  $('tDaily').textContent=SV.daily.d===today()&&SV.daily.s?'best '+SV.daily.s.toLocaleString():'new route today';
  const ul=$('tContracts');ul.innerHTML='';for(const c of SV.con){const li=document.createElement('li'),d=conDef(c);li.innerHTML='<span></span><b></b>';li.firstChild.textContent=conText(c);li.lastChild.textContent='+'+d.r[c.lv];ul.appendChild(li)}}
function buildGarage(){$('gCred').textContent=SV.cred.toLocaleString();const ul=$('gList');ul.innerHTML='';
  for(const U of UPG){const lv=up(U.k),li=document.createElement('li'),max=lv>=COST.length,cost=COST[lv];
    li.innerHTML='<div class="gi"><h3></h3><p></p><div class="pips" aria-hidden="true"></div></div><button class="btn small"></button>';
    li.querySelector('h3').textContent=U.n;li.querySelector('p').textContent=U.d;li.querySelector('.pips').innerHTML=COST.map((_,i)=>'<i class="'+(i<lv?'on':'')+'"></i>').join('');
    const b=li.querySelector('button');b.textContent=max?'Maxed':cost+' cred';b.disabled=max;b.setAttribute('aria-label',U.n+', level '+lv+' of '+COST.length+(max?', maxed':', upgrade for '+cost+' cred'));if(!max&&SV.cred<cost)b.classList.add('poor');
    b.onclick=()=>{if(SV.cred<cost){Snd.sfx.deny();return}SV.cred-=cost;SV.up[U.k]=lv+1;persist();Snd.sfx.buy();hap('light');buildGarage()};ul.appendChild(li)}}
function buildSettings(){$('sMus').value=SV.set.mus*100;$('sSfx').value=SV.set.sfx*100;$('sHap').checked=SV.set.hap;$('sCalm').checked=SV.set.calm;
  const ul=$('sTracks');ul.innerHTML='';Snd.TRACKS.forEach((t,i)=>{const li=document.createElement('li'),b=document.createElement('button');b.className='btn small';b.textContent='▶ '+t.name;b.setAttribute('aria-label','Play '+t.name);
    const s=document.createElement('span');s.textContent=t.zone+' · '+t.bpm+' BPM';b.onclick=()=>{Snd.init();Snd.volume(SV.set.mus,SV.set.sfx);Snd.play(i,true);juke=true};li.append(b,s);ul.appendChild(li)})}
let juke=false,resetArm=0;
const click=(id,fn)=>$(id).addEventListener('click',()=>{Snd.init();Snd.volume(SV.set.mus,SV.set.sfx);Snd.sfx.ui();fn()});
function leaveSettings(){if(juke){juke=false;Snd.play('menu')}}
click('bRun',()=>startRun('std'));click('bDaily',()=>startRun('daily'));
click('bGarage',()=>{buildGarage();show('garage')});click('bSettings',()=>{buildSettings();show('settings')});
click('gBack',()=>{refreshTitle();show('title')});click('sBack',()=>{leaveSettings();persist();refreshTitle();show('title')});
click('sHow',()=>show('howto'));click('hBack',()=>show('settings'));
click('pResume',()=>togglePause());click('pRestart',()=>startRun(mode));click('pQuit',toTitle);
click('oAgain',()=>startRun(mode));click('oGarage',()=>{buildGarage();show('garage')});click('oTitle',toTitle);
click('pauseBtn',()=>togglePause());
$('sMus').addEventListener('input',e=>{SV.set.mus=e.target.value/100;Snd.volume(SV.set.mus,SV.set.sfx)});
$('sSfx').addEventListener('input',e=>{SV.set.sfx=e.target.value/100;Snd.volume(SV.set.mus,SV.set.sfx)});$('sSfx').addEventListener('change',()=>Snd.sfx.blip(2));
$('sHap').addEventListener('change',e=>{SV.set.hap=e.target.checked;hap('medium');persist()});$('sCalm').addEventListener('change',e=>{SV.set.calm=e.target.checked;persist()});
$('sReset').addEventListener('click',()=>{const b=$('sReset');if(Date.now()-resetArm<4000){SV=JSON.parse(JSON.stringify(DEF));fillContracts();persist();buildSettings();b.textContent='Progress erased';resetArm=0;Snd.volume(SV.set.mus,SV.set.sfx)}else{resetArm=Date.now();b.textContent='Tap again to erase everything';setTimeout(()=>{if(resetArm&&Date.now()-resetArm>=3900){b.textContent='Erase progress';resetArm=0}},4000)}});
function togglePause(){if(state==='play'){state='pause';show('pause');$('pauseBtn').hidden=true}else if(state==='pause'){state='play';show(null);$('pauseBtn').hidden=false;Snd.init();cv.focus()}}

/* ---------- input ---------- */
addEventListener('keydown',e=>{const k=e.code,inUI=e.target&&e.target.closest&&e.target.closest('#ui');
  if(state==='play'&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Space'].includes(k))e.preventDefault();
  if(k==='ArrowLeft'||k==='KeyA')keys.left=true;else if(k==='ArrowRight'||k==='KeyD')keys.right=true;else if(k==='ArrowDown'||k==='KeyS')keys.brake=true;
  if(e.repeat)return;
  if(k==='Space'&&state==='play')fire();
  else if(k==='Enter'&&!inUI){if(state==='title'&&!$('title').hidden)startRun('std');else if(state==='pause')togglePause()}
  else if((k==='KeyP'||k==='Escape')&&(state==='play'||state==='pause'))togglePause()});
addEventListener('keyup',e=>{const k=e.code;if(k==='ArrowLeft'||k==='KeyA')keys.left=false;else if(k==='ArrowRight'||k==='KeyD')keys.right=false;else if(k==='ArrowDown'||k==='KeyS')keys.brake=false});
const ptrs=new Map();
function syncPtr(){let l=false,r=false;for(const z of ptrs.values()){if(z<0)l=true;if(z>0)r=true}keys.left=l;keys.right=r}
addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse')touchSeen=true},true);
cv.addEventListener('pointerdown',e=>{if(state!=='play')return;e.preventDefault();
  if(e.pointerType==='mouse'){fire();return}
  const f=e.clientX/cv.clientWidth,z=f<.33?-1:f>.67?1:0;if(z===0)fire();else{ptrs.set(e.pointerId,z);syncPtr()}});
const pup=e=>{if(ptrs.delete(e.pointerId))syncPtr()};
addEventListener('pointerup',pup);addEventListener('pointercancel',pup);cv.addEventListener('contextmenu',e=>e.preventDefault());
document.addEventListener('visibilitychange',()=>{if(document.hidden){if(state==='play')togglePause();Snd.suspend()}else Snd.resume()});
addEventListener('resize',resize);addEventListener('orientationchange',()=>setTimeout(resize,250));
addEventListener('blur',()=>{keys.left=keys.right=keys.brake=false;ptrs.clear()});

/* ---------- boot ---------- */
let last=0;
function frame(t){const raw=(t-last)/1000||0,dt=Math.min(.05,raw);last=t;
  if(state==='play'&&raw<.2){perfAcc+=raw;if(++perfN>=90){if(perfAcc/perfN>.0215&&resMax>720){resMax=Math.round(resMax*.85);resize()}perfAcc=0;perfN=0}}
  update(dt);render(dt);requestAnimationFrame(frame)}
function boot(){if(SP)return;buildSprites();resize();buildTrack(0,4242,false);refreshTitle();show('title');requestAnimationFrame(frame)}
const fl=document.fonts&&document.fonts.load?Promise.all([document.fonts.load('900 20px Orbitron'),document.fonts.load('16px "Share Tech Mono"')]):Promise.resolve();
fl.then(boot,boot);setTimeout(boot,1500);
if(window.claude&&window.claude.hot&&window.claude.hot.snapshot)try{window.claude.hot.snapshot(()=>({}))}catch(e){}
window.__sb={get s(){return{state,pos,speed,timeLeft,score,stage,W,H,resMax,tut,cred:SV.cred}},
  dbg(o){if(o.res){resMax=o.res;resize()}if(o.zone!==undefined){stage=o.zone;setTheme(stage);buildTrack(stage,99+stage,false);pos=o.pos||40000;px=0}if(o.time)timeLeft=o.time;if(o.boost)boost=o.boost;if(o.score)score=o.score;if(o.combo){combo=o.combo;comboT=5}if(o.shield)shield=true;if(o.cred!==undefined){SV.cred=o.cred}if(o.notut){SV.tut=true}if(o.px!==undefined)px=o.px}};
})();
