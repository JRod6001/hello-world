// Bundles src/ into one self-contained page: index.html (web build) and www/ (what the iOS app ships).
import {readFileSync as rd,writeFileSync as wr,mkdirSync,existsSync,copyFileSync} from 'node:fs';
const src=f=>rd(new URL('./src/'+f,import.meta.url),'utf8');
const font=(pkg,file)=>rd(new URL('./node_modules/@fontsource/'+pkg+'/files/'+file,import.meta.url)).toString('base64');
const face=(fam,w,b64)=>`@font-face{font-family:'${fam}';font-weight:${w};font-style:normal;font-display:swap;src:url(data:font/woff2;base64,${b64}) format('woff2')}`;
const fonts=[face('Orbitron',500,font('orbitron','orbitron-latin-500-normal.woff2')),face('Orbitron',900,font('orbitron','orbitron-latin-900-normal.woff2')),
  face('Share Tech Mono',400,font('share-tech-mono','share-tech-mono-latin-400-normal.woff2'))].join('\n');
const title='Static Bloom',style=`<style>\n${fonts}\n${src('style.css')}</style>`,script=`<script>\n${src('audio.js')}\n${src('game.js')}</script>`;
// Web build: a page fragment (the host supplies the document shell); also opens directly in a browser.
wr('index.html',`<meta charset="utf-8">\n<title>${title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n${style}\n${src('body.html')}${script}\n`);
// App build: a complete document with the mobile web app metadata.
const sw=`<script>if('serviceWorker'in navigator&&location.protocol==='https:'&&!window.Capacitor)navigator.serviceWorker.register('sw.js').catch(()=>{})</script>`;
mkdirSync('www',{recursive:true});
wr('www/index.html',`<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">\n<title>${title}</title>\n<meta name="theme-color" content="#05020d">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n<link rel="manifest" href="manifest.webmanifest">\n<link rel="apple-touch-icon" href="icon-180.png">\n${style}\n</head>\n<body>\n${src('body.html')}${script}\n${sw}\n</body>\n</html>\n`);
wr('www/manifest.webmanifest',JSON.stringify({name:title,short_name:title,start_url:'.',display:'fullscreen',orientation:'any',background_color:'#05020d',theme_color:'#05020d',
  icons:[{src:'icon-192.png',sizes:'192x192',type:'image/png'},{src:'icon-512.png',sizes:'512x512',type:'image/png'}]},null,1));
wr('www/sw.js',`const C='static-bloom-v1';self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(['./','manifest.webmanifest'])).then(()=>self.skipWaiting())));\nself.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(n=>n!==C).map(n=>caches.delete(n)))).then(()=>self.clients.claim())));\nself.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));return r}).catch(()=>caches.match(e.request)))});\n`);
for(const s of[180,192,512])if(existsSync(`store/icon-${s}.png`))copyFileSync(`store/icon-${s}.png`,`www/icon-${s}.png`);
console.log('built index.html and www/');
