/* Static Bloom audio: a data-driven synth engine. Every sound is generated at runtime; no audio files ship. */
const Snd=(()=>{
'use strict';
const N2M={c:0,d:2,e:4,f:5,g:7,a:9,b:11},mtof=m=>440*Math.pow(2,(m-69)/12);
const note=s=>{const m=/^([a-g])(#?)(\d)$/.exec(s);return N2M[m[1]]+(m[2]?1:0)+12*(+m[3]+1)};
function chord(name){const m=/^([A-G])(#?)(m?)(7?)$/.exec(name),root=N2M[m[1].toLowerCase()]+(m[2]?1:0),iv=[0,m[3]?3:4,7];if(m[4])iv.push(10);
  const tones=iv.map(i=>55+(((root+i-55)%12)+12)%12).sort((a,b)=>a-b);
  return{bass:28+(((root-28)%12)+12)%12,tones,arp:[...tones.slice(0,3),tones[0]+12]}}
const mel=str=>str.split('|').map(b=>{let p=0;const o=[];for(const tk of b.trim().split(/\s+/)){const[n,l]=tk.split('/');if(n!=='r')o.push([p,note(n),+l]);p+=+l}return o});

/* ---- the score ---- */
const TRACKS=[
{name:'Neon Tithe',zone:'Chrome Estates',bpm:124,sw:0,bass:'roll',arp:'pluck',clap:0,lead:{w:'sawtooth',cut:3400,oct:0,v:.8},padCut:1150,
 dr:{k:'x...x...x...x...',s:'....x.......x...',h:'x.x.x.x.x.x.x.x.',o:'..x...x...x...x.'},bs:'0080008000800808',ap:'0123210123210123',
 S:{A:{ch:'Am F C G'},
    B:{ch:'Am F C G',ld:'e5/6 d5/2 c5/4 d5/4|c5/6 a4/2 c5/8|g5/6 e5/2 d5/4 e5/4|d5/8 b4/4 d5/4|e5/4 a5/4 g5/4 e5/4|f5/6 e5/2 c5/8|e5/4 g5/4 c6/6 b5/2|b5/8 g5/4 b5/4'},
    A2:{ch:'Am F Dm E',hi:1},
    C:{ch:'F G Am Am F G E E',hi:1,ld:'a5/4 c6/4 a5/4 f5/4|b5/4 d6/4 b5/4 g5/4|c6/8 b5/4 a5/4|e5/12 a5/4|a5/4 c6/4 a5/4 f5/4|b5/4 d6/4 b5/4 g5/4|e6/8 d6/4 b5/4|g#5/16'},
    K:{ch:'F F G G Am Am E E',brk:1}},form:'A B A2 C K B C A2'},
{name:'Low Tide',zone:'Freeport Nine',bpm:96,sw:.16,bass:'reese',arp:'bell',clap:1,lead:{w:'triangle',cut:5200,oct:12,v:.95},padCut:900,
 dr:{k:'x.....x...x.....',s:'........x.......',h:'x.xxx.x.x.xxx.x.',o:'..............x.'},bs:'0-----0---0-----',ap:'0..2..3...2..1..',
 S:{A:{ch:'Dm A# Gm A'},
    B:{ch:'Dm A# Gm A',ld:'a4/8 f4/4 g4/4|f4/8 d4/8|a#4/8 g4/4 a4/4|a4/12 e4/4|d5/8 c5/4 a4/4|a#4/8 f4/8|g4/4 a#4/4 d5/4 g5/4|e5/16'},
    A2:{ch:'Dm C A# A',hi:1},
    C:{ch:'Gm A# Dm C Gm A# A A',hi:1,ld:'g4/6 a#4/2 d5/8|f4/6 a#4/2 d5/8|f4/4 a4/4 d5/4 f5/4|e5/8 c5/4 g4/4|g4/6 a#4/2 d5/8|f4/6 a#4/2 f5/8|e5/8 c#5/8|a4/16'},
    K:{ch:'A# A# Gm Gm Dm Dm A A',brk:1}},form:'A B A2 C K B C A2'},
{name:'Sovereign',zone:'Sovereign Mall',bpm:132,sw:0,bass:'roll',arp:'pluck',clap:1,lead:{w:'sawtooth',cut:4200,oct:-12,v:.85},padCut:1400,
 dr:{k:'x...x...x...x...',s:'....x.......x...',h:'x.x.x.x.x.x.x.x.',o:'..x...x...x...x.'},bs:'0.000.000.000.80',ap:'0123012301230123',
 S:{A:{ch:'Em C G D'},
    B:{ch:'Em C G D',ld:'b5/4 r/2 g5/2 b5/4 e6/4|e6/6 d6/2 c6/8|d6/4 r/2 b5/2 d6/4 g6/4|f#6/8 d6/4 a5/4|b5/4 r/2 g5/2 b5/4 e6/4|g6/6 e6/2 c6/8|b5/4 d6/4 g6/6 f#6/2|f#6/8 a6/8'},
    A2:{ch:'Em C Am B',hi:1},
    C:{ch:'C D Em Em C D B B',hi:1,ld:'e6/4 g6/4 e6/4 c6/4|f#6/4 a6/4 f#6/4 d6/4|g6/8 f#6/4 e6/4|b5/12 e6/4|e6/4 g6/4 e6/4 c6/4|f#6/4 a6/4 f#6/4 d6/4|b6/8 a6/4 f#6/4|d#6/16'},
    K:{ch:'C C D D Em Em B B',brk:1}},form:'A B A2 C K B C A2'},
{name:'Cold Stack',zone:'The Stacks',bpm:140,sw:.08,bass:'acid',arp:'stab',clap:0,lead:{w:'square',cut:2400,oct:0,v:.6},padCut:1000,
 dr:{k:'x.........x.....',s:'....x.......x...',g:'.......x.x......',h:'x.xxx.xxx.xxx.xx',o:''},bs:'0.00.0.80.00.870',ap:'x..x..x...x..x..',
 S:{A:{ch:'F#m D E C#'},
    B:{ch:'F#m D E C#',ld:'c#5/12 b4/4|a4/12 f#4/4|g#4/8 b4/8|f5/8 g#4/8|c#5/8 e5/4 f#5/4|f#5/12 d5/4|e5/8 g#5/8|g#5/16'},
    A2:{ch:'F#m F#m D E',hi:1},
    C:{ch:'D E F#m F#m D E C# C#',hi:1,ld:'a5/4 f#5/4 d5/4 f#5/4|b5/4 g#5/4 e5/4 g#5/4|c#6/8 a5/8|f#5/16|a5/4 f#5/4 d5/4 f#5/4|b5/4 g#5/4 e5/4 b5/4|c#6/8 g#5/8|f5/16'},
    K:{ch:'D D E E F#m F#m C# C#',brk:1}},form:'A B A2 C K B C A2'},
{name:'Null Set',zone:'Null District',bpm:118,sw:0,bass:'fm',arp:'bell',clap:1,lead:{w:'square',cut:3000,oct:0,v:.6},padCut:800,
 dr:{k:'x...x...x...x...',s:'....x.......x...',h:'..x...x...x...x.',o:''},bs:'..0...0...0...00',ap:'3..0.2..3..1.0.2',
 S:{A:{ch:'Cm G# Fm G'},
    B:{ch:'Cm G# Fm G',ld:'g5/2 r/2 g5/2 d#5/2 r/4 c5/2 d5/2|d#5/2 r/2 d#5/2 c5/2 r/4 g#4/2 c5/2|f5/2 r/2 f5/2 c5/2 r/4 g#4/2 c5/2|d5/2 r/2 d5/2 b4/2 r/4 g4/2 b4/2|g5/2 r/2 g5/2 d#5/2 r/4 c5/2 d5/2|d#5/2 r/2 d#5/2 c5/2 r/4 g#4/2 c5/2|f5/2 r/2 f5/2 c5/2 r/4 g#4/2 c5/2|g5/4 d5/4 b4/4 g5/4'},
    A2:{ch:'Cm Cm G# G',hi:1},
    C:{ch:'G# A# Cm Cm G# A# G G',hi:1,ld:'c6/6 g#5/2 d#5/8|d6/6 a#5/2 f5/8|d#6/4 d6/4 c6/4 g5/4|c6/16|c6/6 g#5/2 d#5/8|d6/6 a#5/2 f6/8|d6/8 b5/8|g5/16'},
    K:{ch:'G# G# A# A# Cm Cm G G',brk:1}},form:'A B A2 C K B C A2'}];
for(const T of TRACKS){T.formL=T.form.split(' ');for(const k in T.S){const s=T.S[k];s.chords=s.ch.split(' ').map(chord);if(s.ld)s.mel=mel(s.ld)}}

/* ---- engine: works on a live or an offline context ---- */
function makeEngine(ctx,dest){
  const sr=ctx.sampleRate,TAU=Math.PI*2;
  const buf=(len,fn)=>{const b=ctx.createBuffer(1,sr*len|0,sr);fn(b.getChannelData(0));return b};
  const mkG=(v,to)=>{const n=ctx.createGain();n.gain.value=v;if(to)n.connect(to);return n};
  const flt=(type,f,q)=>{const b=ctx.createBiquadFilter();b.type=type;b.frequency.value=f;if(q)b.Q.value=q;return b};
  const pn=p=>{const n=ctx.createStereoPanner();n.pan.value=p;return n};
  const osc=(type,f,t,dur,det)=>{const o=ctx.createOscillator();o.type=type;o.frequency.value=f;if(det)o.detune.value=det;o.start(t);o.stop(t+dur);return o};
  const env=(g,t,peak,a,d)=>{g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(peak,t+a);g.gain.setTargetAtTime(0,t+a,d/4)};
  /* drum samples, synthesised once */
  const metal=(d,decay,nz)=>{const fr=[3270,4081,5413,6227,7873,9341],ph=[0,0,0,0,0,0];let l1=0,l2=0;
    for(let i=0;i<d.length;i++){const t=i/sr;let v=0;for(let k=0;k<6;k++){ph[k]+=fr[k]/sr;v+=(ph[k]%1)<.5?1:-1}v=v/6+(Math.random()*2-1)*nz;
      l1+=(v-l1)*.45;const h1=v-l1;l2+=(h1-l2)*.45;d[i]=(h1-l2)*Math.exp(-t*decay)*(t<.002?t/.002:1)}};
  const S={
    kick:buf(.5,d=>{let ph=0;for(let i=0;i<d.length;i++){const t=i/sr;ph+=TAU*(47+185*Math.exp(-t*36))/sr;let v=Math.sin(ph)*Math.exp(-t*7.2);if(t<.004)v+=(Math.random()*2-1)*.5*(1-t/.004);d[i]=Math.tanh(v*1.9)*.92}}),
    snare:buf(.42,d=>{let lp=0,p1=0,p2=0;for(let i=0;i<d.length;i++){const t=i/sr,n=Math.random()*2-1;lp+=(n-lp)*.22;p1+=TAU*(176+70*Math.exp(-t*45))/sr;p2+=TAU*329/sr;
      d[i]=Math.tanh(((n-lp)*.85*Math.exp(-t*15)+Math.sin(p1)*.65*Math.exp(-t*22)+Math.sin(p2)*.25*Math.exp(-t*30))*1.5)*.8}}),
    clap:buf(.45,d=>{let a=0,b=0;for(let i=0;i<d.length;i++){const t=i/sr,n=Math.random()*2-1;a+=(n-a)*.4;b+=(n-b)*.07;let e=0;for(const o of[0,.011,.023])if(t>=o)e=Math.max(e,Math.exp(-(t-o)*230));
      if(t>.03)e=Math.max(e,.7*Math.exp(-(t-.03)*15));d[i]=Math.tanh((a-b)*e*3.2)*.8}}),
    hat:buf(.12,d=>metal(d,58,.35)),ohat:buf(.5,d=>metal(d,9,.3)),crash:buf(1.8,d=>metal(d,2.4,.7)),
    tick:buf(.06,d=>{for(let i=0;i<d.length;i++){const t=i/sr;d[i]=Math.sin(TAU*2400*t)*Math.exp(-t*90)*.6}}),
    noise:buf(1.5,d=>{for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1})};
  /* mix: buses -> master filter -> saturation -> glue compressor -> limiter */
  const out=mkG(1),duck=mkG(1,out);
  const B={drum:mkG(.74,out),snr:mkG(.7,out),bass:mkG(.6,duck),pad:mkG(1,duck),arp:mkG(.85,duck),lead:mkG(.4,out),fx:mkG(.6,out)};
  const lp=flt('lowpass',19000,.7),sat=ctx.createWaveShaper(),comp=ctx.createDynamicsCompressor(),lim=ctx.createDynamicsCompressor(),vol=mkG(.9,dest);
  const cv=new Float32Array(1024);for(let i=0;i<1024;i++){const x=i/511.5-1;cv[i]=Math.tanh(x*1.6)/Math.tanh(1.6)}sat.curve=cv;sat.oversample='2x';
  comp.threshold.value=-18;comp.ratio.value=3;comp.attack.value=.012;comp.release.value=.22;comp.knee.value=8;
  lim.threshold.value=-5;lim.ratio.value=20;lim.attack.value=.001;lim.release.value=.06;lim.knee.value=0;
  const trim=mkG(.5),air=flt('highshelf',6500);air.gain.value=3.5;out.connect(lp);lp.connect(air);air.connect(trim);trim.connect(sat);sat.connect(comp);comp.connect(lim);lim.connect(vol);
  /* reverb: decaying noise that darkens as it fades */
  const rvIn=mkG(1),conv=ctx.createConvolver(),rv=mkG(.5,out);
  {const L=sr*3|0,ib=ctx.createBuffer(2,L,sr),pre=sr*.018|0;for(let c=0;c<2;c++){const d=ib.getChannelData(c);let y=0;for(let i=pre;i<L;i++){const t=(i-pre)/L,k=.5*Math.pow(1-t,2.2)+.03;y+=((Math.random()*2-1)-y)*k;d[i]=y*Math.pow(1-t,2.6)*2.4}}conv.buffer=ib}
  rvIn.connect(conv);conv.connect(rv);
  /* ping-pong delay */
  const dlIn=mkG(1),dL=ctx.createDelay(1.5),dR=ctx.createDelay(1.5),fb=mkG(.42),df=flt('lowpass',2800),pL=pn(-.75),pR=pn(.75);
  dlIn.connect(dL);dL.connect(df);df.connect(dR);dR.connect(fb);fb.connect(dL);dL.connect(pL);dR.connect(pR);pL.connect(out);pR.connect(out);
  mkG(.3,dlIn).gain.value=.3;const send=(from,to,v)=>{const g=mkG(v,to);from.connect(g)};
  send(B.arp,dlIn,.32);send(B.arp,rvIn,.14);send(B.lead,dlIn,.3);send(B.lead,rvIn,.28);send(B.pad,rvIn,.4);send(B.snr,rvIn,.22);send(B.fx,rvIn,.4);
  /* persistent mono lead with glide and vibrato */
  const LD={o:[],f:flt('lowpass',3000,1.5),g:mkG(0),cut:3000,oct:0};
  {const lfo=ctx.createOscillator(),lg=mkG(5);lfo.frequency.value=5.4;lfo.connect(lg);lfo.start(0);
   for(const d of[-11,0,11,0]){const o=ctx.createOscillator();o.detune.value=d;lg.connect(o.detune);o.connect(LD.f);o.start(0);LD.o.push(o)}LD.f.connect(LD.g);LD.g.connect(B.lead)}
  function leadNote(t,m,dur,v){const f=mtof(m+LD.oct);LD.o.forEach((o,i)=>o.frequency.setTargetAtTime(i===3?f/2:f,t,.012));
    LD.f.frequency.setValueAtTime(LD.cut*.45,t);LD.f.frequency.linearRampToValueAtTime(LD.cut,t+.07);
    LD.g.gain.setTargetAtTime(v,t,.008);LD.g.gain.setTargetAtTime(0,t+dur*.9,.045)}
  const smp=(b,t,v,to,p,rate)=>{const s=ctx.createBufferSource();s.buffer=b;if(rate)s.playbackRate.value=rate;const g=mkG(v);s.connect(g);if(p){const q=pn(p);g.connect(q);q.connect(to)}else g.connect(to);s.start(t)};
  function duckAt(t,d){duck.gain.cancelScheduledValues(t);duck.gain.setValueAtTime(.3,t);duck.gain.linearRampToValueAtTime(1,t+d)}
  function pad(t,tones,dur,cut,v){const g=ctx.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+.3);g.gain.setValueAtTime(v,t+dur-.1);g.gain.linearRampToValueAtTime(0,t+dur+.4);g.connect(B.pad);
    for(const s of[-1,1]){const f=flt('lowpass',cut,.7),p=pn(s*.65);f.frequency.setValueAtTime(cut*.7,t);f.frequency.linearRampToValueAtTime(cut*1.3,t+dur);
      for(const n of tones)osc('sawtooth',mtof(n),t,dur+.45,s*9+(n%3)).connect(f);f.connect(p);p.connect(g)}}
  function pluck(t,m,bright,v,p){const f=flt('lowpass',600,4),g=ctx.createGain(),q=pn(p);f.frequency.setValueAtTime(bright?5200:2300,t);f.frequency.setTargetAtTime(bright?950:520,t,.05);env(g,t,v,.003,.24);
    osc('sawtooth',mtof(m),t,.4).connect(f);osc('square',mtof(m),t,.4,8).connect(f);f.connect(g);g.connect(q);q.connect(B.arp)}
  function bell(t,m,v,p){const f=mtof(m),c=osc('sine',f,t,1.5),md=osc('sine',f*3.5,t,1.5),mg=ctx.createGain(),g=ctx.createGain(),q=pn(p);
    mg.gain.setValueAtTime(f*2.4,t);mg.gain.setTargetAtTime(f*.12,t,.07);md.connect(mg);mg.connect(c.frequency);env(g,t,v,.002,1);c.connect(g);g.connect(q);q.connect(B.arp)}
  function stab(t,tones,v,bright){const f=flt('lowpass',500,3),g=ctx.createGain();f.frequency.setValueAtTime(bright?4200:2200,t);f.frequency.setTargetAtTime(600,t,.06);env(g,t,v,.003,.22);
    for(const n of tones){osc('sawtooth',mtof(n+12),t,.35,-6).connect(f);osc('sawtooth',mtof(n+12),t,.35,6).connect(f)}f.connect(g);g.connect(B.arp)}
  function bass(t,m,len,type,acc){const g=ctx.createGain();g.connect(B.bass);
    if(type==='reese'){const f=flt('lowpass',340,2);f.frequency.setValueAtTime(260,t);f.frequency.linearRampToValueAtTime(620,t+len);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.3,t+.02);g.gain.setValueAtTime(.3,t+len-.04);g.gain.linearRampToValueAtTime(0,t+len+.03);
      osc('sawtooth',mtof(m+12),t,len+.1,-19).connect(f);osc('sawtooth',mtof(m+12),t,len+.1,19).connect(f);f.connect(g);const s=osc('sine',mtof(m),t,len+.1),sg=mkG(1.1,g);s.connect(sg)}
    else if(type==='acid'){const f=flt('lowpass',300,13);f.frequency.setValueAtTime(acc?3000:1500,t);f.frequency.setTargetAtTime(250,t,.055);env(g,t,.42,.003,len*1.3);osc('sawtooth',mtof(m+12),t,len+.2).connect(f);const s=osc('sine',mtof(m),t,len+.2),sg=mkG(.9,g);s.connect(sg);f.connect(g)}
    else if(type==='fm'){const f=mtof(m+12),c=osc('sine',f,t,len+.25),md=osc('sine',f*2,t,len+.25),mg=ctx.createGain();mg.gain.setValueAtTime(f*5,t);mg.gain.setTargetAtTime(f*.4,t,.05);md.connect(mg);mg.connect(c.frequency);env(g,t,.62,.003,len*1.6);c.connect(g);const s=osc('sine',mtof(m),t,len+.25),sg=mkG(.7,g);s.connect(sg)}
    else{const f=flt('lowpass',160,6);f.frequency.setValueAtTime(160,t);f.frequency.linearRampToValueAtTime(1150,t+.012);f.frequency.setTargetAtTime(210,t+.012,len*.5);env(g,t,.5,.004,len*1.2);
      osc('sawtooth',mtof(m+12),t,len+.15,-7).connect(f);osc('sawtooth',mtof(m+12),t,len+.15,7).connect(f);osc('square',mtof(m),t,len+.15).connect(f);f.connect(g)}}
  function riser(t,dur,v){const s=ctx.createBufferSource();s.buffer=S.noise;s.loop=true;const f=flt('bandpass',300,2.5),g=ctx.createGain();f.frequency.setValueAtTime(300,t);f.frequency.exponentialRampToValueAtTime(7000,t+dur);
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+dur);g.gain.linearRampToValueAtTime(0,t+dur+.03);s.connect(f);f.connect(g);g.connect(B.fx);s.start(t);s.stop(t+dur+.1)}
  function impact(t){smp(S.crash,t,.5,B.fx);const o=osc('sine',90,t,1.1),g=ctx.createGain();o.frequency.exponentialRampToValueAtTime(32,t+.7);env(g,t,.9,.004,.9);o.connect(g);g.connect(B.drum)}

  const E={ctx,B,lp,vol,out,T:TRACKS[0],menu:false,d16:60/124/4,mood:{boost:0,danger:0},
    setTrack(i){E.menu=i==='menu';E.T=TRACKS[E.menu?0:i];E.d16=60/E.T.bpm/4;const l=E.T.lead;LD.cut=l.cut;LD.oct=l.oct;LD.o.forEach((o,k)=>o.type=k===3?'square':l.w);
      const t=ctx.currentTime;dL.delayTime.setValueAtTime(E.d16*3,t);dR.delayTime.setValueAtTime(E.d16*3,t);E.silence(t)},
    silence(t){LD.g.gain.cancelScheduledValues(t);LD.g.gain.setTargetAtTime(0,t,.02)},
    impact,
    tick(st,t0){
      const T=E.T,d=E.d16,s=st%16,bar=Math.floor(st/16),b=bar%8,t=t0+(s%2?T.sw*d:0);
      if(E.menu){const c=T.S.K.chords[b];if(s===0)pad(t,c.tones,d*16,800,.075);if(s%4===0||s===14)bell(t,c.arp[(st*7+b)%4]+12,.11,((st%3)-1)*.6);if(b%4===0&&s===0)bass(t,c.bass,d*14,'reese');return}
      const sn=Math.floor(bar/8),key=T.formL[sn%T.formL.length],sec=T.S[key],c=sec.chords[b%sec.chords.length],D=T.dr,hi=sec.hi||E.mood.boost,x=(p,i)=>p&&p[i]==='x';
      if(s===0){pad(t,c.tones,d*16,T.padCut*(hi?1.25:1),sec.brk?.085:.06);if(b===0&&sn>0&&!sec.brk)impact(t);if(b===7&&!sec.brk)riser(t,d*16,.22)}
      /* arp layer */
      const a=T.ap[s];
      if(T.arp==='stab'){if(a==='x')stab(t,c.tones,sec.brk?.1:.085,hi)}
      else if(a!=='.'){const n=c.arp[+a]+12,p=(s%4<2?-.45:.45);T.arp==='bell'?bell(t,n+12,.17,p):pluck(t,n,hi||sec.brk&&b>3,sec.brk?.13:.11,p)}
      if(sec.brk){
        if(b<4&&s===0)bass(t,c.bass,d*15,'reese');
        if(b>=4){if(s%4===0){smp(S.kick,t,.8,B.drum);duckAt(t,d*2)}if(b>=6&&(b===7?s%2===0||s>=8:s%4===2))smp(S.snare,t,.3+(b===7?s*.035:.1),B.snr)}
        if(b===6&&s===0)riser(t,d*32,.4);return}
      /* drums */
      if(x(D.k,s)){smp(S.kick,t,1,B.drum);duckAt(t,d*2)}
      if(x(D.s,s))smp(T.clap?S.clap:S.snare,t,.85,B.snr);
      if(x(D.g,s))smp(S.snare,t,.22,B.snr,0,1.15);
      if(b===7&&s>=12)smp(S.snare,t,.4+(s-12)*.12,B.snr,0,1+(s-12)*.04);
      if(x(D.h,s))smp(S.hat,t,s%4===0?.5:.72,B.drum,.25);else if(hi)smp(S.hat,t,.34,B.drum,-.3);
      if(x(D.o,s))smp(S.ohat,t,.42,B.drum,-.2);
      if(b===0&&s===0&&sn>0)smp(S.crash,t,.3,B.drum);
      if(E.mood.danger&&s%4===2)smp(S.tick,t,.5,B.fx,0,s===14?1.5:1);
      /* bass */
      const ch=T.bs[s];
      if(ch!=='.'&&ch!=='-'){let len=1;while(s+len<16&&T.bs[s+len]==='-')len++;const off=ch==='8'?12:ch==='7'?10:ch==='5'?7:0;bass(t,c.bass+off,d*len*(T.bass==='reese'?1:.95),T.bass,off>0)}
      /* lead */
      if(sec.mel)for(const n of sec.mel[b])if(n[0]===s)leadNote(t,n[1],n[2]*d,T.lead.v);
    }};
  return E}

/* ---- live playback ---- */
let AC=null,E=null,sfxBus=null,nextT=0,step=0,lpT=0,cur='menu',vm=.8,vs=.8;
function init(){
  if(AC){if(AC.state!=='running')AC.resume();return}
  const A=window.AudioContext||window.webkitAudioContext;if(!A)return;
  try{AC=new A({latencyHint:'interactive'})}catch(e){AC=null;return}
  E=makeEngine(AC,AC.destination);E.vol.gain.value=vm;
  const sc=AC.createDynamicsCompressor();sc.threshold.value=-10;sc.ratio.value=6;sfxBus=AC.createGain();sfxBus.gain.value=vs*.75;sfxBus.connect(sc);sc.connect(AC.destination);
  E.setTrack(cur);nextT=AC.currentTime+.08;step=0;setInterval(pump,25)}
function pump(){if(!AC||AC.state!=='running')return;if(nextT<AC.currentTime-.25)nextT=AC.currentTime+.05;
  while(nextT<AC.currentTime+.2){E.tick(step,nextT);nextT+=E.d16;step++}}
function play(id,hit){cur=id;if(!AC)return;E.setTrack(id);step=0;nextT=AC.currentTime+.07;if(hit)E.impact(AC.currentTime+.02)}
function mood(lpHz,boost,danger){if(!AC)return;E.mood.boost=boost;E.mood.danger=danger;if(lpHz!==lpT){lpT=lpHz;E.lp.frequency.setTargetAtTime(lpHz,AC.currentTime,lpHz>5000?.25:.12)}}
function volume(m,s){vm=m;vs=s;if(AC){E.vol.gain.setTargetAtTime(m,AC.currentTime,.03);sfxBus.gain.setTargetAtTime(s*.75,AC.currentTime,.03)}}
/* sfx */
const o=(type,f,t,dur)=>{const n=AC.createOscillator();n.type=type;n.frequency.value=f;n.start(t);n.stop(t+dur);return n};
const g=(t,peak,a,d)=>{const n=AC.createGain();n.gain.setValueAtTime(0,t);n.gain.linearRampToValueAtTime(peak,t+a);n.gain.setTargetAtTime(0,t+a,d/4);n.connect(sfxBus);return n};
const nz=(t,dur)=>{const s=AC.createBufferSource();s.buffer=E.noiseBuf||(E.noiseBuf=(()=>{const b=AC.createBuffer(1,AC.sampleRate,AC.sampleRate),d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;return b})());s.loop=true;s.start(t,Math.random());s.stop(t+dur);return s};
const bq=(type,f,q)=>{const b=AC.createBiquadFilter();b.type=type;b.frequency.value=f;if(q)b.Q.value=q;return b};
const tone=(type,f0,f1,dur,v,delay)=>{const t=AC.currentTime+(delay||0),n=o(type,f0,t,dur+.1);if(f1)n.frequency.exponentialRampToValueAtTime(f1,t+dur);n.connect(g(t,v,.003,dur))};
const noise=(ft,f0,f1,dur,v,q)=>{const t=AC.currentTime,f=bq(ft,f0,q);if(f1)f.frequency.exponentialRampToValueAtTime(f1,t+dur);const n=nz(t,dur+.1);n.connect(f);f.connect(g(t,v,.01,dur))};
const ok=fn=>(...a)=>{if(AC&&AC.state==='running'&&vs>0)try{fn(...a)}catch(e){}};
const sfx={
  zap:ok(()=>{tone('sawtooth',1900,180,.17,.3);tone('square',2600,900,.06,.12)}),
  whoosh:ok(()=>{noise('bandpass',300,5200,.55,.5,1.5);tone('sawtooth',110,880,.5,.14)}),
  blip:ok(n=>tone('square',mtof(81+[0,3,7,10,12][n%5]),0,.11,.15)),
  crash:ok(()=>{noise('lowpass',700,0,.4,.8);tone('sine',110,30,.32,.7)}),
  miss:ok(()=>noise('bandpass',3000,900,.11,.22,2)),
  dry:ok(()=>tone('square',160,90,.08,.12)),
  lock:ok(()=>tone('sine',1320,0,.05,.1)),
  clear:ok(()=>[69,72,76,81,84,88].forEach((m,i)=>tone('square',mtof(m),0,.25,.15,i*.075))),
  over:ok(()=>{tone('sawtooth',440,40,1.2,.28);noise('lowpass',2000,200,1.1,.25)}),
  snow:ok(()=>{noise('highpass',800,0,.9,.45);tone('square',58,0,.7,.28)}),
  shield:ok(()=>{tone('sine',523,1046,.25,.2);tone('sine',784,1568,.25,.14,.06)}),
  shieldBreak:ok(()=>{noise('highpass',2500,600,.3,.4);tone('triangle',900,200,.3,.25)}),
  power:ok(()=>[57,64,69,76].forEach((m,i)=>tone('sawtooth',mtof(m),0,.2,.12,i*.04))),
  pay:ok(()=>[76,83,88].forEach((m,i)=>tone('sine',mtof(m),0,.3,.2,i*.09))),
  ui:ok(()=>tone('sine',880,0,.05,.12)),
  buy:ok(()=>{tone('square',660,0,.08,.12);tone('square',990,0,.16,.12,.08)}),
  deny:ok(()=>tone('square',140,110,.14,.14))};
/* offline render for mix checks: returns level statistics for a track */
async function analyze(track,secs,solo){
  const oc=new OfflineAudioContext(2,44100*secs,44100),e=makeEngine(oc,oc.destination);e.setTrack(track);
  if(solo)for(const k in e.B)if(k!==solo&&!(solo==='drum'&&k==='snr'))e.B[k].gain.value=0;
  let t=.05,st=0;while(t<secs-.6){e.tick(st,t);t+=e.d16;st++}
  const b=await oc.startRendering(),L=b.getChannelData(0),R=b.getChannelData(1),n=L.length;
  let pk=0,sq=0,lo=0,mid=0,hi=0,l1=0,l2=0,clip=0,dc=0,lr=0,ll=0,rr=0;const k1=1-Math.exp(-2*Math.PI*150/44100),k2=1-Math.exp(-2*Math.PI*2500/44100);
  const secN=Math.floor(e.d16*128*44100),secs8=[];let acc=0,cnt=0;
  for(let i=0;i<n;i++){const m=(L[i]+R[i])/2,a=Math.max(Math.abs(L[i]),Math.abs(R[i]));if(a>pk)pk=a;if(a>=.999)clip++;sq+=m*m;dc+=m;l1+=(m-l1)*k1;l2+=(m-l2)*k2;lo+=l1*l1;mid+=(l2-l1)*(l2-l1);hi+=(m-l2)*(m-l2);lr+=L[i]*R[i];ll+=L[i]*L[i];rr+=R[i]*R[i];
    acc+=m*m;if(++cnt===secN){secs8.push(+(10*Math.log10(acc/cnt+1e-12)).toFixed(1));acc=0;cnt=0}}
  const db=v=>+(10*Math.log10(v/n+1e-12)).toFixed(1);
  return{peak:+(20*Math.log10(pk+1e-9)).toFixed(2),rms:db(sq),lo:db(lo),mid:db(mid),hi:db(hi),clip,dc:+(dc/n).toFixed(5),corr:+(lr/Math.sqrt(ll*rr+1e-12)).toFixed(2),sections:secs8}}
return{init,play,mood,volume,sfx,analyze,TRACKS,suspend(){if(AC)AC.suspend()},resume(){if(AC)AC.resume()},get on(){return!!AC}};
})();
