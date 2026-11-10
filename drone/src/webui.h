#pragma once
#include <Arduino.h>

// Interface de pilotagem servida pela propria placa.
// Conecte o celular na rede WiFi do drone e abra http://192.168.4.1
//
// Sem PROGMEM: ESP32 e RP2040 mapeiam a flash em memoria, entao a string e
// lida direto. PROGMEM so faz diferenca no AVR.

static const char WEBUI_HTML[] = R"HTML(<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no,viewport-fit=cover">
<title>Drone ESP32</title>
<style>
*{box-sizing:border-box;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#0d1117;color:#c9d1d9;font:14px/1.4 system-ui,sans-serif;
     height:100dvh;display:flex;flex-direction:column;overflow:hidden;touch-action:none}
header{display:flex;gap:8px;align-items:center;padding:8px 12px;background:#161b22;flex-wrap:wrap}
#link{width:10px;height:10px;border-radius:50%;background:#f85149;flex:none}
#link.on{background:#3fb950}
button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;
       padding:7px 12px;font-size:13px;font-weight:600}
button.on{background:#1f6feb;border-color:#1f6feb;color:#fff}
#arm{margin-left:auto}
#arm.on{background:#da3633;border-color:#da3633;color:#fff}
#tele{display:grid;grid-template-columns:repeat(auto-fit,minmax(72px,1fr));gap:4px;
      padding:6px 12px;font-size:12px;background:#161b22;border-top:1px solid #30363d}
#tele div{background:#0d1117;border-radius:4px;padding:4px 6px}
#tele b{display:block;color:#8b949e;font-size:10px;font-weight:500;text-transform:uppercase}
.warn{color:#f0883e}.bad{color:#f85149}.ok{color:#3fb950}
#pads{flex:1;display:flex;min-height:0}
.pad{flex:1;position:relative;touch-action:none}
.pad canvas{width:100%;height:100%;display:block}
#msg{padding:4px 12px;font-size:12px;color:#8b949e;min-height:22px}
</style></head><body>

<header>
  <span id="link"></span><span id="st">conectando</span>
  <button id="alt" class="on">ALT HOLD</button>
  <button id="pousar">POUSAR</button>
  <button id="arm">ARMAR</button>
</header>

<div id="pads">
  <div class="pad"><canvas id="cL"></canvas></div>
  <div class="pad"><canvas id="cR"></canvas></div>
</div>

<div id="tele">
  <div><b>Roll</b><span id="tr">-</span></div>
  <div><b>Pitch</b><span id="tp">-</span></div>
  <div><b>Yaw</b><span id="ty">-</span></div>
  <div><b>Altura</b><span id="ta">-</span></div>
  <div><b>Vert</b><span id="tv">-</span></div>
  <div><b>Bateria</b><span id="tb">-</span></div>
  <div><b>Loop</b><span id="tl">-</span></div>
</div>
<div id="msg">Arme com o drone no chao e nivelado. ALT HOLD: manche esquerdo no centro = mantem a altura, para cima = sobe. Soltou o direito = fica parado.</div>

<script>
const S={roll:0,pitch:0,yaw:0,thr:0.5,arm:0,alt:1,land:0,armT:0};
let ws,alive=0;

// ---- joysticks ----
function pad(cv,vert,onMove){
  const ctx=cv.getContext('2d');
  let cx=0,cy=0,r=0,px=0,py=0,id=null;
  function size(){
    const d=window.devicePixelRatio||1;
    cv.width=cv.clientWidth*d; cv.height=cv.clientHeight*d;
    ctx.setTransform(d,0,0,d,0,0);
    cx=cv.clientWidth/2; cy=cv.clientHeight/2;
    r=Math.min(cx,cy)*0.72; px=cx; py=cy;
    if(vert && !S.alt) py=cy+r;   // manual: throttle comeca no minimo; ALT HOLD: no centro
    draw();
  }
  function draw(){
    ctx.clearRect(0,0,cv.clientWidth,cv.clientHeight);
    ctx.strokeStyle='#30363d'; ctx.lineWidth=2;
    ctx.beginPath(); ctx.arc(cx,cy,r,0,7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx-r,cy); ctx.lineTo(cx+r,cy);
    ctx.moveTo(cx,cy-r); ctx.lineTo(cx,cy+r); ctx.stroke();
    ctx.fillStyle=id!==null?'#1f6feb':'#484f58';
    ctx.beginPath(); ctx.arc(px,py,r*0.28,0,7); ctx.fill();
  }
  function set(x,y){
    let dx=x-cx, dy=y-cy;
    const d=Math.hypot(dx,dy);
    if(d>r){ dx=dx/d*r; dy=dy/d*r; }
    px=cx+dx; py=cy+dy;
    onMove(dx/r, -dy/r);
    draw();
  }
  function release(){
    id=null;
    // Manual: o throttle fica onde esta. ALT HOLD: tudo volta ao centro (centro = mantem a altura).
    if(vert && !S.alt){ px=cx; onMove(0,-(py-cy)/r); }
    else              { px=cx; py=cy; onMove(0,0); }
    draw();
  }
  cv.addEventListener('pointerdown',e=>{id=e.pointerId;cv.setPointerCapture(id);set(e.offsetX,e.offsetY);});
  cv.addEventListener('pointermove',e=>{if(e.pointerId===id)set(e.offsetX,e.offsetY);});
  cv.addEventListener('pointerup',release);
  cv.addEventListener('pointercancel',release);
  addEventListener('resize',size); setTimeout(size,0);
  return { centro(){ px=cx; py=cy; onMove(0,0); draw(); },
           minimo(){ px=cx; py=cy+r; onMove(0,-1); draw(); } };
}

// esquerda: Y = throttle (mantem posicao), X = yaw
const padL=pad(document.getElementById('cL'),true,(x,y)=>{ S.yaw=x; S.thr=Math.max(0,Math.min(1,(y+1)/2)); });
// direita: X = roll, Y = pitch
pad(document.getElementById('cR'),false,(x,y)=>{ S.roll=x; S.pitch=y; });

// ---- botoes ----
document.getElementById('alt').onclick=function(){
  if(S.arm){ msg('Troque o ALT HOLD com o drone desarmado.'); return; }
  S.alt=S.alt?0:1; this.classList.toggle('on',!!S.alt);
  if(S.alt) padL.centro(); else padL.minimo();
};
document.getElementById('pousar').onclick=function(){
  if(!S.arm) return;
  S.land=1; this.classList.add('on'); msg('Pousando sozinho...');
};
document.getElementById('arm').onclick=function(){
  if(!S.arm && !S.alt && S.thr>0.05){ msg('Baixe o throttle antes de armar.'); return; }
  S.arm=S.arm?0:1; S.armT=Date.now(); S.land=0;
  document.getElementById('pousar').classList.remove('on');
  this.classList.toggle('on',!!S.arm);
  this.textContent=S.arm?'DESARMAR':'ARMAR';
};
function msg(t){ document.getElementById('msg').textContent=t; }

// ---- ligacao ----
function connect(){
  ws=new WebSocket('ws://'+location.hostname+':81/');
  ws.onopen =()=>{ document.getElementById('st').textContent='conectado';
                   document.getElementById('link').classList.add('on'); };
  // pela terra, o ponto verde so acende quando o DRONE responde (ver show)
  ws.onclose=()=>{ document.getElementById('st').textContent='reconectando';
                   document.getElementById('link').classList.remove('on');
                   S.arm=0; setTimeout(connect,700); };
  ws.onmessage=e=>{ try{ show(JSON.parse(e.data)); }catch(_){} };
}
connect();

// 50 Hz de comando: menos que isso e o failsafe de 400 ms comeca a disparar
setInterval(()=>{
  if(!ws||ws.readyState!==1) return;
  const f=(S.arm?1:0)|(S.alt?2:0)|(S.land?8:0);
  // desarmado e no primeiro segundo depois de armar: throttle em zero (o drone exige para armar)
  const thr=(!S.arm||Date.now()-S.armT<1000)?0:S.thr;
  ws.send('C,'+S.roll.toFixed(3)+','+S.pitch.toFixed(3)+','+S.yaw.toFixed(3)
          +','+thr.toFixed(3)+','+f);
},20);

const $=i=>document.getElementById(i);
function dist(v){ return v>0? v.toFixed(2)+' m' : '--'; }
let viaTerra=0;
function show(t){
  // estacao terra: avisa se o drone esta respondendo (pelo ESP-NOW)
  if('terra' in t){
    viaTerra=1;
    $('st').textContent=t.drone?'terra + drone ok':'terra ok, SEM SINAL DO DRONE';
    $('link').classList.toggle('on',!!t.drone);
    return;
  }
  $('tr').textContent=t.r.toFixed(1)+'°';
  $('tp').textContent=t.p.toFixed(1)+'°';
  $('ty').textContent=t.y.toFixed(0)+'°';
  $('ta').textContent=t.alt.toFixed(2)+' m';
  $('ta').className=t.snr?'ok':'';
  $('tv').textContent=t.vz.toFixed(2)+' m/s';
  $('tb').textContent=t.vb.toFixed(2)+' V';
  $('tb').className=t.vb<3.35?'bad':t.vb<3.55?'warn':'ok';
  $('tl').textContent=t.hz+' Hz';
  if(t.st) msg(t.st);
  if(!t.armed && S.arm){   // o drone desarmou sozinho (pousou, failsafe, bateria)
    S.arm=0; S.land=0; $('pousar').classList.remove('on');
    const b=$('arm'); b.classList.remove('on'); b.textContent='ARMAR';
  }
}
</script></body></html>)HTML";
