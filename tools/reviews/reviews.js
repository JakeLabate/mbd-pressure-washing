<script>(function(){
var rail=document.getElementById('rv-rail');if(!rail)return;
var prev=document.getElementById('rv-prev'),next=document.getElementById('rv-next'),
    clones=document.getElementById('rv-clones');
var SPEED=22;           /* px per second, a slow read-along drift */
var reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
/* If everything already fits there is nothing to scroll and a drifting rail
   would just jitter. Measured, not assumed. */
var fits=rail.scrollWidth<=rail.clientWidth+8;
/* With a clone set the rail wraps; without one it reverses at each end. */
var loop=!!(clones&&clones.children.length), dir=1;
/* scrollLeft rounds sub-pixel writes away, so a 22px/s drift would never move.
   Position is accumulated as a float here and written out each frame. */
var pos=0, drifting=!reduced&&!fits, hovering=false, hidden=false, last=null;

function step(){var c=rail.firstElementChild;return c?c.getBoundingClientRect().width+20:320;}
function half(){return rail.scrollWidth/2;}

/* Any deliberate action hands the rail over for good. The visitor is reading
   at their own pace now, and yanking it back would fight them. */
function takeOver(){
  if(!drifting)return;
  drifting=false;
  rail.classList.add('rv-snap');
}

function tick(now){
  if(last===null)last=now;
  var dt=(now-last)/1000; last=now;
  if(drifting&&!hovering&&!hidden&&dt<0.5){
    pos+=SPEED*dt*dir;
    if(loop){
      var h=half();
      if(pos>=h)pos-=h;
    }else{
      var max=rail.scrollWidth-rail.clientWidth;
      if(pos>=max){pos=max;dir=-1;}
      else if(pos<=0){pos=0;dir=1;}
    }
    rail.scrollLeft=pos;
  }
  requestAnimationFrame(tick);
}

function nudge(d){
  takeOver();
  if(loop&&d<0&&rail.scrollLeft<step()){rail.scrollLeft+=half();}
  rail.scrollBy({left:d*step(),behavior:reduced?'auto':'smooth'});
}
prev.addEventListener('click',function(){nudge(-1);});
next.addEventListener('click',function(){nudge(1);});

/* Touching, dragging, scrolling or arrowing the rail itself counts too. */
['pointerdown','wheel','touchstart'].forEach(function(ev){
  rail.addEventListener(ev,takeOver,{passive:true});
});
rail.addEventListener('keydown',function(e){
  if(e.key==='ArrowLeft'){nudge(-1);e.preventDefault();}
  if(e.key==='ArrowRight'){nudge(1);e.preventDefault();}
});

/* Wrapping still applies once the visitor is driving. */
rail.addEventListener('scroll',function(){
  if(!loop)return;
  var h=half();
  if(rail.scrollLeft>=h*2-2){rail.scrollLeft-=h;pos-=h;}
  /* Deliberately does NOT copy scrollLeft back into pos while drifting.
     The browser rounds scrollLeft to whole pixels, and feeding that rounded
     value back in ratchets the error upward: the drift ran 36% fast. */
},{passive:true});

/* Hovering or tabbing in is a pause, not a hand-off: someone reading a card
   should not have it slide away, but they have not taken the wheel either. */
rail.addEventListener('pointerenter',function(){hovering=true;});
rail.addEventListener('pointerleave',function(){hovering=false;pos=rail.scrollLeft;last=null;});
rail.addEventListener('focusin',function(){hovering=true;});
rail.addEventListener('focusout',function(){hovering=false;pos=rail.scrollLeft;last=null;});
document.addEventListener('visibilitychange',function(){
  hidden=document.hidden;
  if(!hidden){pos=rail.scrollLeft;last=null;}
});

if(reduced||fits){rail.classList.add('rv-snap');}
if(fits){
  var nav=prev.parentNode; if(nav)nav.style.display='none';
  if(clones&&clones.parentNode)clones.parentNode.removeChild(clones);
  return;
}
requestAnimationFrame(tick);
})();</script>
