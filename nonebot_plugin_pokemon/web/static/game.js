(() => {
  'use strict';
  // A tile-size canvas keeps rivers, paths, houses and trees crisp at every viewport size.
  // The location buttons on top come from the player's region and badge progress.
  function drawMap(canvas) {
    const w=360,hgt=165; canvas.width=w; canvas.height=hgt;
    const g=canvas.getContext('2d'); g.imageSmoothingEnabled=false;
    const rect=(x,y,w,h,c)=>{g.fillStyle=c;g.fillRect(Math.round(x),Math.round(y),w,h);};
    const poly=(points,c)=>{g.fillStyle=c;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();};
    let seed=8643;
    const random=()=>{seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296;};
    const coast=x=>137+12*Math.sin(x/33)+6*Math.cos(x/19);
    const river=y=>Math.round(33+Math.sin(y/31)*17+y*.16);
    rect(0,0,w,hgt,'#78b89b');
    for(let x=0;x<w;x+=2){
      const y=Math.round(coast(x));
      rect(x,y-3,2,4,'#e4d295');rect(x,y+1,2,4,'#9cb897');rect(x,y+5,2,32,'#65b6c1');
      rect(x,0,2,y-3,'#92c680');
    }
    for(let y=0;y<157;y+=2){
      const x=river(y), width=10+Math.floor(y/24);
      rect(x-2,y,width+4,2,'#c9c98a');rect(x,y,width,2,'#60afbc');rect(x+1,y,2,2,'#93d2cd');
    }
    for(let i=0;i<1450;i++){
      const x=Math.floor(random()*w),y=Math.floor(random()*hgt),r=river(y);
      if(y>coast(x)+5 || (x>r+2 && x<r+9+y/24)){if(i%3===0)rect(x,y,2+Math.floor(random()*5),1,'#9cd9d4');continue;}
      if(y>coast(x)-4)continue;
      rect(x,y,1+Math.round(random()*2),1,random()>.5?'#a2cd86':'#83b97a');
      if(i%25===0){rect(x,y-1,1,2,'#507f5c');rect(x-1,y-2,2,1,i%50?'#f5de82':'#e6b7ac');}
    }
    const mountain=(x,y,size)=>{
      poly([[x-size,y],[x-4,y-size],[x+3,y-size-4],[x+size,y]],'#719f80');
      poly([[x-size+3,y-1],[x-3,y-size+2],[x+1,y-size],[x-3,y-5]],'#a9bc83');
      poly([[x-6,y-size+4],[x+3,y-size-4],[x+9,y-size+5],[x+3,y-size+2],[x,y-size+5]],'#e4e2ba');
    };
    for(let x=-4;x<w+16;x+=17)mountain(x,14+Math.round(random()*7),17+Math.round(random()*12));
    const road=points=>{
      const steps=[[9,'#b6ab79'],[7,'#ebd59a'],[3,'#eedca7']];
      for(const [width,color] of steps){g.strokeStyle=color;g.lineWidth=width;g.lineJoin='round';g.beginPath();
        points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();}
    };
    road([[-3,105],[62,105],[77,94],[110,94],[133,76],[189,76],[215,63],[215,48],[251,37],[302,37],[327,25],[364,25]]);
    road([[182,76],[196,86],[233,86],[251,102],[282,104],[304,116],[336,116],[361,125]]);
    const bridgeX=river(105);rect(bridgeX-4,101,26,9,'#b68d60');
    for(let x=bridgeX-3;x<bridgeX+22;x+=4)rect(x,102,1,7,'#d2ac76');
    rect(bridgeX-4,100,26,2,'#826851');rect(bridgeX-4,109,26,2,'#826851');
    function tree(x,y,s=1){
      rect(x-3*s,y-1,8*s,3,'#79a776');rect(x-1*s,y-6*s,3*s,7*s,'#826948');
      poly([[x-6*s,y-3*s],[x-7*s,y-6*s],[x-4*s,y-7*s],[x-5*s,y-9*s],[x,y-16*s],[x+6*s,y-9*s],[x+4*s,y-8*s],[x+7*s,y-4*s],[x+4*s,y-2*s]],'#377763');
      poly([[x-5*s,y-6*s],[x-2*s,y-9*s],[x-4*s,y-9*s],[x,y-15*s],[x+2*s,y-10*s],[x+1*s,y-8*s],[x+4*s,y-6*s],[x,y-7*s]],'#589367');
      rect(x-2*s,y-10*s,2*s,2*s,'#86af75');
    }
    for(const [cx,cy,rx,ry] of [[17,59,13,29],[111,37,26,16],[156,127,20,12],[301,74,30,15],[339,51,17,16],[86,145,15,3]]){
      const pts=[];for(let i=0;i<Math.floor(rx*ry/21);i++)pts.push([cx+(random()*2-1)*rx,cy+(random()*2-1)*ry]);
      pts.sort((a,b)=>a[1]-b[1]).forEach(([x,y])=>tree(Math.round(x),Math.round(y),.8+random()*.22));
    }
    function house(x,y,roof){
      rect(x-11,y,24,5,'#79a374');rect(x-9,y-10,19,13,'#ddd6a8');rect(x+5,y-10,5,13,'#b8bb93');
      poly([[x-13,y-9],[x-7,y-18],[x+9,y-18],[x+14,y-9]],roof);
      rect(x-12,y-9,25,2,'#745c55');rect(x+2,y-2,4,5,'#846c50');rect(x-6,y-6,4,4,'#56929a');rect(x-5,y-6,2,1,'#d4e9d1');
      rect(x-7,y-17,15,1,'#e8ab87');rect(x+5,y-22,3,5,'#9e8068');
    }
    {house(95,96,'#c77867');house(111,89,'#b56f65');house(184,73,'#668fa6');house(251,39,'#ce8967');house(274,102,'#ae7462');}

  }

  function drawArena(canvas) {
    const w=360,h=165;canvas.width=w;canvas.height=h;
    const g=canvas.getContext('2d');
    const rect=(x,y,width,height,color)=>{g.fillStyle=color;g.fillRect(x,y,width,height);};
    rect(0,0,w,h,'#96d7d8');
    for(let i=0;i<16;i++){const x=(i*53)%w,y=8+(i*7)%35;
      rect(x,y,24,3,'#d0e9db');rect(x+5,y-3,13,3,'#d0e9db');}
    for(let x=0;x<w;x+=2){
      const ridge=37+18*Math.cos(x/31)+6*Math.sin(x/13);
      rect(x,Math.floor(ridge),2,66,'#82af95');
      const hill=63+10*Math.sin(x/45)+7*Math.sin(x/13);
      rect(x,hill|0,2,82,'#6d9e79');
      const forest=76+8*Math.sin(x/37);
      rect(x,Math.floor(forest)-Math.abs((x%12)-6),2,54,'#498873');
    }
    rect(0,86,w,79,'#85bc7e');
    for(let i=0;i<420;i++){const x=(i*97)%361,y=86+((i*79)%81);rect(x,y,(i%4)+1,1,i%4?'#79af75':'#b3ce8a');}
    for (const [x,y,rx,ry] of [[91,142,67,12],[263,100,51,8]]) {
      for(const [dy,c] of [[3,'#658f68'],[0,'#a8cc82'],[-2,'#b8d48b']]){
        g.fillStyle=c;g.beginPath();g.ellipse(x,y+dy,rx,ry,0,0,Math.PI*2);g.fill();}
    }
  }
  window.pokemonScene = Object.freeze({drawMap,drawArena});
})();
