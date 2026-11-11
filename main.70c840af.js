/* Touch vs mouse: a finger press marks the page .touch (hover styles off, so
a tapped button never keeps a stuck hover look); moving a mouse clears it. */
(function(r){function on(e){if(e.pointerType==='touch')r.classList.add('touch');}
function off(e){if(e.pointerType==='mouse')r.classList.remove('touch');}
addEventListener('pointerdown',on,true);addEventListener('pointermove',off,true);
addEventListener('touchstart',function(){r.classList.add('touch');},{capture:true,passive:true});})(document.documentElement);