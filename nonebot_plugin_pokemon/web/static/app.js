(() => {
  'use strict';
  const BASE = location.pathname.replace(/\/+$/, '');
  const $ = sel => document.querySelector(sel);
  const screen = $('#screen'), detail = $('#detail'), dialog = $('#dialog');
  const store = {world:null, tab:'冒险', starter:0, group:0, busy:false, snapshot:null, text:'', images:[], page:0, view:0};
  const positions = [[.28,.67],[.52,.51],[.70,.30],[.75,.72]];
  const tabs = ['冒险','队伍','背包','图鉴','排行','小游戏','活动'];
  const h = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  const box = (cls, ...kids) => { const el = h('div', cls); el.append(...kids.filter(Boolean)); return el; };
  function button(label, click, cls='', title='') {
    const el = h('button', cls, label);
    el.type = 'button';
    if (title) { el.title = title; el.setAttribute('aria-label',title); }
    el.onclick = async () => { try { await click(); } catch(e) { notify(e.message); } };
    return el;
  }
  function notify(text) { $('#notice').textContent = text || ''; }
  function modal(title, ...nodes) {
    $('#dialog-title').textContent = title;
    detail.replaceChildren(...nodes);
    if (!dialog.open) dialog.showModal();
    detail.parentElement.scrollTop = 0;
  }
  $('#close').onclick = () => dialog.close();
  dialog.onclick = e => { if (e.target === dialog && (e.clientX < dialog.getBoundingClientRect().left || e.clientX > dialog.getBoundingClientRect().right)) dialog.close(); };
  async function api(path, body) {
    const opts = {credentials:'same-origin', cache:'no-store'};
    if (body !== undefined) {
      const auth = await fetch('/qweb/api/v1/auth/session', opts);
      if (!auth.ok) throw new Error('请先登录七七');
      const token = (await auth.json()).csrf_token;
      if (!token) throw new Error('登录会话已失效');
      Object.assign(opts,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(body)});
    }
    const response = await fetch(BASE + path, opts);
    const data = await response.json();
    if (!response.ok) {
      const msg = data.detail || data.error;
      const error = new Error(typeof msg === 'string' ? msg : '请求未完成（' + response.status + '）');
      error.status = response.status;
      throw error;
    }
    return data;
  }
  function section(title,...nodes) {
    return box('panel',box('section-heading',h('h2','',title)),...nodes);
  }
  function image(src,alt,cls='') {
    const frame = h('span', 'qweb-media '+cls);
    const el = h('img');
    el.alt = alt;
    el.decoding = 'async';
    el.dataset.imageState = src ? 'loading' : 'failed';
    el.onload = () => { el.dataset.imageState='loaded'; };
    el.onerror = () => { el.dataset.imageState='failed'; };
    const halo = h('span','qweb-halo');
    halo.append(h('i'),h('i'),h('i'));
    const indicator = h('span','media-indicator');
    indicator.setAttribute('aria-hidden','true');
    indicator.append(halo,h('span','media-missing',alt.trim()[0] || '◇'));
    frame.append(el,indicator);
    if(src)el.src=src;
    return frame;
  }
  function sprite(mon,cls='sprite') {
    return image(BASE+'/api/game/sprite/'+encodeURIComponent(mon.id),mon.name,cls);
  }
  function preview(src,label) { modal(label, image(src,label,'full-image')); }
  function chip(text) { return h('span','chip',text); }
  function card(mon, click, cls='') {
    const el = button('',click,'mon '+cls);
    const info = h('span');
    info.append(h('b','',mon.name),h('small','',mon.level ? 'Lv.'+mon.level+' · '+(mon.types || []).join(' / ') : (mon.types || []).join(' / ')));
    el.append(sprite(mon), info);
    return el;
  }
  function heading(text, more) { return box('section-heading',h('h2','',text),more); }
  function nav() {
    const labels = [...tabs];
    if (store.world?.identity?.is_admin) labels.push('管理');
    $('#tabs').replaceChildren(...labels.map(label => {
      const btn = button(label,() => go(label)); btn.setAttribute('aria-current',label===store.tab?'page':'false'); return btn;
    }));
  }

  function actionButton(label,action,value,cls='') {
    const btn = button(label,() => act(action,value),cls);
    const active = store.snapshot && !store.snapshot.done;
    btn.disabled = store.busy || (active && !['reply','cancel'].includes(action));
    return btn;
  }
  async function refreshWorld() {
    const world = await api('/api/game/world');
    store.world = world;
    const p = world.profile;
    $('#trainer').replaceChildren(h('b','',p.pokemon_count ? p.nickname : '新训练家'), h('span','','金币 '+p.score), h('span','','精灵 '+p.pokemon_count));
    nav(); ongoing();
  }
  let pollTimer, epoch=0;
  function applySnapshot(s, reset=false) {
    if (reset) { store.text=''; store.images=[]; }
    store.snapshot=s;
    if (s.text) store.text=(store.text+'\n'+s.text).trim().slice(-4500);
    if (s.images?.length) store.images=[...store.images,...s.images].slice(-4);
    if (s.error) notify(s.error);
    ongoing();
  }
  function ongoing(){
    const bar=$('#ongoing'), s=store.snapshot;
    const controls=[];
    if(s?.operation && !s.done){
      const label=currentQuiz()?'退出猜题':s.battle?'退出战斗':'结束本次行动';
      const page=currentQuiz()?'小游戏':'冒险';
      if(store.tab!==page)controls.push(button(currentQuiz()?'返回题目':'返回冒险',()=>go(page)));
      controls.push(actionButton(label,'cancel'));
    }
    if(store.world?.profile.auto_explore){
      controls.push(actionButton('结束自动探索','end_auto',null,'end-auto'));
    }
    bar.replaceChildren(...controls);
  }
  function schedule(s) {
    clearTimeout(pollTimer);
    if (!s.operation || s.done) return;
    const stamp=epoch;
    const poll=async () => {
      if (stamp!==epoch) return;
      try {
        const next=await api('/api/session?'+new URLSearchParams({operation:s.operation,offset:s.offset}));
        if (stamp!==epoch) return;
        if (next.superseded) { await restore(); return; }
        const changed = next.offset!==s.offset || next.done!==s.done || next.awaiting!==s.awaiting;
        applySnapshot(next);
        if (next.done) await refreshWorld();
        if (changed) renderTurn();
        schedule(next);
      } catch(e) { if (stamp===epoch) { notify(e.message); pollTimer=setTimeout(poll,5000); } }
    };
    pollTimer=setTimeout(poll,s.awaiting?3000:750);
  }
  async function restore() {
    const saved=await api('/api/session');
    applySnapshot(saved,true); if(!saved.done && currentQuiz())store.tab='小游戏';
    await refreshWorld(); await go(store.tab); schedule(saved);
  }
  async function perform(task,reset,tab='冒险') {
    if (store.busy) return;
    store.busy=true; epoch++; clearTimeout(pollTimer); notify('');
    if (dialog.open) dialog.close();
    store.tab=tab;nav();ongoing();renderTurn();
    try {
      const result=await task();
      applySnapshot(result,reset);
      if (result.done) await refreshWorld();
      if (result.done && !result.text && !result.images?.length && !result.error && !store.text) notify('本次行动已结束');
    } catch(e) {
      await restore(); notify(e.status===409?'行动状态已更新，请按当前回合选择。':e.message);
    } finally { store.busy=false; ongoing(); renderTurn(); if(store.snapshot) schedule(store.snapshot); }
  }
  function act(action,value) {
    const prev=store.snapshot;
    if(action==='minigame_start' || action==='cancel')store.quizDraft='';
    return perform(() => api('/api/game/action',{action,value,operation:prev?.operation || '',offset:prev?.offset || 0}), action!=='reply', action==='minigame_start' || (['reply','cancel'].includes(action) && currentQuiz())?'小游戏':'冒险');
  }
  function legacy(command) {
    if (store.snapshot && !store.snapshot.done) return notify('请先结束当前行动');
    return perform(() => api('/api/command',{text:command}),true);
  }
  function fighter(mon,side) {
    const hp=h('progress');hp.max=mon.max_hp;hp.value=mon.hp;hp.setAttribute('aria-label',mon.name+' 体力');
    return box('fighter '+side,sprite(mon),box('hp-card',box('row',h('b','',mon.name),h('small','','Lv.'+mon.level)),hp,h('small','',mon.hp+' / '+mon.max_hp)));
  }
  function scene(title,kicker,battle) {
    const c=h('canvas');c.setAttribute('aria-hidden','true');
    const scene=box('scene',c);if(battle) window.pokemonScene.drawArena(c); else window.pokemonScene.drawMap(c);
    scene.append(box('plate',h('small','',kicker),h('h2','',title)));
    return scene;
  }
  const places=()=>(store.world.locations || []).filter(l=>l.region===store.world.profile.region);
  function locationInfo(l) {
    modal(l.name,box('stack',box('chips',chip(l.type),chip(l.region)),h('p','',l.current?'训练家当前所在地点':l.open?'可以前往':'所需徽章 '+l.need),
      l.current || !l.open ? null : actionButton('前往'+l.name,'travel',l.name,'primary')));
  }
  function atlas() {
    const all=(store.world.locations || []).filter(l=>l.region===store.world.profile.region || l.open); const list=box('list');
    for(const l of all)list.append(button(l.name+' · '+l.type+'　'+(l.current?'当前位置':l.open?'可前往':'徽章 '+l.need),()=>locationInfo(l)));
    modal('地区地图',list);
  }
  function travelScene(p) {
    const el=scene(p.map,p.region+' · 地区地图');
    const dest=places().filter(l=>l.name!==p.map && l.open);
    const current=store.world.current?.location || places().find(l=>l.name===p.map);
    const visible = places().filter(l=>l.current || l.open);
    const pages = Math.ceil(visible.length / positions.length);
    if (store.lastMap !== p.map) {
      store.lastMap=p.map;
      store.page=Math.max(0,Math.floor(visible.findIndex(l=>l.current)/positions.length));
    }
    visible.slice(store.page*4,store.page*4+4).forEach((l,i)=>{
      const [x,y]=positions[i];const pin=button((l.current?'◆ ':'')+l.name,()=>locationInfo(l),'map-pin');
      pin.style.left=x*100+'%';pin.style.top=y*100+'%';
      pin.setAttribute('aria-current',String(l.current));el.append(pin);
      if(l.current){
        const avatar=image(BASE+'/static/trainer.png','训练家','map-avatar');
        avatar.style.left=pin.style.left;avatar.style.top=pin.style.top;el.append(avatar);
      }
    });
    const controls=box('scenebar',button('地区地图',atlas));
    if(pages>1)controls.append(button('其他地点 ›',()=>{store.page=(store.page+1)%pages;adventure();}));
    const wild=current?.type==='野外';
    if(wild && !p.auto_explore)controls.prepend(actionButton('野外探索','explore',undefined,'primary'),actionButton('自动探索','start_auto'),actionButton('垂钓','fish'));
    else if(!p.auto_explore && dest.some(l=>l.type==='野外')){
      const field=dest.find(l=>l.type==='野外');
      controls.prepend(actionButton('前往'+field.name,'travel',field.name,'primary'));
    }
    controls.append(button('挑战',()=>modal('选择挑战',box('actions',...Object.entries({gym:'道馆',elite:'四天王',champion:'冠军',tower:'试炼塔',boss:'首领',world_boss:'世界首领'}).map(([key,name])=>actionButton(name,'challenge',key))))));
    return box('',el,controls);
  }
  function starters() {
    const roster=store.world.starters;
    const groups=[...new Set(roster.map(m=>m.region))];
    const selected=roster.filter(m=>m.region===groups[store.group]);
    const pick=selected[store.starter] || selected[0];
    if(!pick)return section('初始伙伴',h('p','empty','暂无可领取的精灵'));
    const el=scene('选择初始伙伴',groups[store.group] || '冒险启程');
    el.append(box('shadow-pad'),sprite(pick,'party-sprite'));
    const region=h('select'); region.setAttribute('aria-label','御三家地区');
    groups.forEach((key,i)=>region.add(new Option(key || '初始伙伴',String(i),false,i===store.group)));
    region.onchange=()=>{store.group=Number(region.value);store.starter=0;adventure();};
    const choices=selected.map((m,i)=>{
      const btn=card(m,()=>{store.starter=i;adventure();},'starter');
      btn.setAttribute('aria-pressed',String(i===store.starter));return btn;
    });
    return box('',el,box('action-panel',heading('初始伙伴',region),box('starter-grid',...choices),
      box('scenebar',actionButton('选择'+pick.name,'claim',pick.id,'primary'),button('查看图鉴',()=>showDex(pick.name)))));
  }
  function regionChoice() {
    const el=scene('选择出发地区','冒险启程');
    return box('',el,box('action-panel',heading('出发地区'),box('grid',...store.world.regions.filter(r=>r.open).map(r=>actionButton(r.name+' · '+r.starter,'choose_region',r.key)))));
  }
  function resultPanel() {
    const s=store.snapshot;
    if(currentQuiz())return null;
    if (!s?.operation && !store.busy) return null;
    const choices=box('actions');
    if(s?.awaiting){
      const replies=(s.options || []).filter(opt=>opt.action==="reply");
      for(const opt of replies) {
        const b=actionButton(opt.label || opt.value,'reply',opt.value,'skill primary');
        if(opt.move)b.append(h('small','',opt.move.type+' · '+opt.move.damage_class));
        choices.append(b);
      }
      if(!replies.length){
        const answer=h('input');answer.placeholder='本轮答案';answer.setAttribute('aria-label','本轮答案');
        choices.append(answer,button('提交选择',()=>answer.value.trim() && act('reply',answer.value.trim())));
      }
    }
    if(s?.canceled || s?.last_action?.action==='cancel')return null;
    const content=box('stack',choices);
    if(store.text){
      const log=h('details');log.append(h('summary','','行动记录'),h('p','result-text',store.text));
      const last=store.text.split('\n').map(t=>t.trim()).filter(Boolean).at(-1) || '';
      if(!s?.awaiting)content.append(h('strong','',last));
      content.append(log);
    }
    for(const src of store.images){const b=button('',()=>preview(src,'行动结果'),'thumb');b.append(image(src,'查看行动结果'));content.append(b);}
    return section(s?.awaiting?'回合行动':store.busy || !s?.done?'行动中…':'行动结果',content);
  }
  function adventure() {
    const w=store.world;if(!w)return; const p=w.profile;
    const battle=store.snapshot?.battle;
    let stage;
    if(battle && battle.player && battle.opponent){
      const end=store.snapshot.done;
      const title=end && battle.finished ? (battle.opponent.hp===0?'胜利':'战败') : '第 '+battle.round+' 回合';
      const el=scene(title,end?'战斗结算':'对战中',true);
      el.append(fighter(battle.player,'player'),fighter(battle.opponent,'opponent'));
      const back=store.snapshot?.done ? button('返回地图',()=>{store.snapshot.battle=null;adventure();}):null;
      stage=box('',el,back && box('scenebar',back));
    } else if(!p.pokemon_count)stage=starters();
    else if(!p.map)stage=regionChoice();
    else stage=travelScene(p);
    const party=w.party || p.team || [];
    const rail=box('rail',section('出战队伍',party.length?box('list',...party.map(m=>card(m,()=>monster(m)))):h('p','empty','尚未编队')),
      section('训练家',...[[ '所在地区',p.region || '待出发'],['当前位置',p.map || '待出发'],['声望',p.reputation],['试炼塔',p.dungeon_floor+' 层']].map(([k,v])=>box('rank-row',h('small','',k),h('b','',v)))));
    screen.replaceChildren(box('layout',box('stack',stage,resultPanel()),rail));
  }
  function stats(values) {
    return box('list',...Object.entries(values || {}).map(([key,val])=>{
      const m=h('meter');m.min=0;m.max=Math.max(185,val);m.value=val;
      return box('stat-row',h('span','',key),m,h('b','',val));
    }));
  }
  function monHeading(m) {
    return box('hero-mon',sprite(m),box('stack',h('small','','No. '+String(m.id).padStart(3,'0')),
      box('chips',...(m.types || []).map(chip)),m.level && h('b','','Lv.'+m.level+' · '+m.nature)));
  }
  async function moveInfo(name) {
    const {entry:m}=await api('/api/move?name='+encodeURIComponent(name));
    modal(name,box('stack',box('chips',chip(m.type),chip(m.damage_class),chip('威力 '+m.power),chip('命中 '+m.accuracy),chip('PP '+m.pp)),h('p','',m.description)));
  }
  async function showDex(name) {
    const {entry:m}=await api('/api/pokedex?name='+encodeURIComponent(name));
    modal(m.name,box('stack',monHeading(m),h('p','',m.description),heading('种族值',h('small','','合计 '+m.base_total)),stats(m.base_stats),
      h('h3','','可学招式'),box('actions',...m.learnset.map(v=>button(v.move+' · Lv.'+v.level,()=>moveInfo(v.move)))),
      h('h3','','进化'),box('actions',...m.evolution.map(v=>button(v.name,()=>showDex(v.name))))));
  }
  function monster(m) {
    const party=store.world.party || [];
    const controls=box('actions',button('图鉴',()=>showDex(m.name)));
    if(!party.some(v=>v.id===m.id) && party.length<6)controls.append(actionButton('加入队伍','party',[...party.map(v=>v.id),m.id],'primary'));
    if(party.some(v=>v.id===m.id) && party[0]?.id!==m.id)controls.append(actionButton('设为首发','party',[m.id,...party.filter(v=>v.id!==m.id).map(v=>v.id)],'primary'));
    if(party.some(v=>v.id===m.id) && party.length>1)controls.append(actionButton('移出队伍','party',party.filter(v=>v.id!==m.id).map(v=>v.id)));
    if(m.held_item)controls.append(actionButton('取下'+m.held_item,'equip',{pokemon:m.name,remove:true}));
    modal(m.name,box('stack',monHeading(m),controls,stats(m.stats),h('h3','','招式'),box('actions',...(m.moves || []).map(v=>button(v,()=>moveInfo(v))))));
  }
  function team() {
    const w=store.world, party=w.party || [], owned=w.owned || [];
    const filter=h('input');filter.placeholder='查找已拥有的精灵';filter.setAttribute('aria-label',filter.placeholder);
    const cards=box('grid');
    function render(){
      const matches=owned.filter(m=>m.name.includes(filter.value.trim()) || String(m.id)===filter.value.trim());
      cards.replaceChildren(...(matches.length?matches.map(m=>card(m,()=>monster(m),'collection')):[h('p','empty','没有匹配的精灵')]));
    }
    filter.oninput=render;render();
    screen.replaceChildren(box('stack',section('出战队伍 · '+party.length+'/6',box('grid',...party.map(m=>card(m,()=>monster(m),'collection')))),
      section('精灵盒 · '+w.owned_total,box('toolbar',filter),cards)));
  }
  const bagKinds = {items:'道具', eggs:'精灵蛋', technical:'学习机'};
  let bagKind = 'items', bagPage = 1;
  function openBag(kind, page=1) {
    bagKind=kind; bagPage=page;
    return go('背包');
  }
  async function bag(version) {
    const w=store.world;
    const kind=bagKind, page=bagPage;
    const controls=box('actions');
    for(const [key,title] of Object.entries(bagKinds)){
      const tab=button(title,()=>openBag(key));
      tab.setAttribute('aria-pressed',String(key===kind));
      controls.append(tab);
    }
    const content=box('stack',h('p','empty','读取中…'));
    screen.replaceChildren(section('背包',controls,content));
    const data=await api('/api/game/inventory/'+kind+'?page='+page);
    if(version!==store.view)return;
    const pages=Math.max(1,Math.ceil(data.total/data.page_size));
    if(page>pages)return openBag(kind,pages);
    async function itemInfo(item){
      const {entry}=await api('/api/item?name='+encodeURIComponent(item.name));
      const equip=['进化石','Z纯晶'].includes(entry.type);
      modal(item.name,box('stack',h('p','',entry.content || entry.description || entry.use || entry.type || ''),chip('持有 '+item.count),
        box('actions',...w.owned.map(m=>equip ? actionButton('给'+m.name+'携带','equip',{item:item.name,pokemon:m.name}) : button('对'+m.name+'使用',()=>legacy('使用道具 '+item.name+' '+m.name+' 1'))))));
    }
    function entryInfo(item){
      if(kind==='technical')return moveInfo(item.name);
      if(kind==='items')return itemInfo(item);
      modal(item.name+'的蛋',box('stack',sprite(item),chip('持有 '+item.count),
        button('孵化',()=>legacy('宝可梦孵化 '+item.name),'primary'),button('查看图鉴',()=>showDex(item.name))));
    }
    const grid=box('bag-grid');
    for(const item of data.items){
      const tile=button('',()=>entryInfo(item),'bag-slot');
      if(kind==='eggs')tile.append(sprite(item));
      tile.append(h('b','',item.name),h('span','amount','× '+item.count));
      grid.append(tile);
    }
    content.replaceChildren(heading(bagKinds[kind],h('small','',data.total+' 种 · 共 '+data.quantity+' 个')),
      data.items.length?grid:h('p','empty','暂无'+bagKinds[kind]));
    if(pages>1){
      const prev=button('上一页',()=>openBag(kind,page-1)), next=button('下一页',()=>openBag(kind,page+1));
      prev.disabled=page<=1; next.disabled=page>=pages;
      content.append(box('actions',prev,h('span','',page+' / '+pages),next));
    }
  }
  function dex() {
    const search=h('input');search.type='search';search.placeholder='名称或图鉴编号';search.setAttribute('aria-label',search.placeholder);
    const grid=box('grid');let revision=0,timer;
    const list=items=>grid.replaceChildren(...(items.length?items.map(m=>card(m,()=>showDex(m.name),'collection')):[h('p','empty','没有找到宝可梦')]));
    list(store.world.starters);
    search.oninput=()=>{
      clearTimeout(timer);const id=++revision;const q=search.value.trim();
      if(!q){list(store.world.starters);return;}
      timer=setTimeout(async()=>{try{const data=await api('/api/pokedex?q='+encodeURIComponent(q));if(id===revision)list(data.items);}catch(e){if(id===revision)grid.replaceChildren(h('p','empty',e.message));}},220);
    };
    screen.replaceChildren(section('宝可梦图鉴',box('toolbar',search),grid));
  }
  async function rankings(version) {
    const sel=h('select');sel.setAttribute('aria-label','排行类别');
    for(const [key,title] of Object.entries({score:'金币排行',pokedex:'图鉴排行',dungeon:'试炼塔排行'}))sel.add(new Option(title,key));
    const list=box('list'),charts=box('actions');
    for(const [kind,name] of Object.entries({team_radar:'队伍能力',team_levels:'队伍等级',team_types:'队伍属性',popular_species:'人气精灵',level_distribution:'等级分布'})){
      charts.append(button(name,()=>preview(BASE+'/api/charts/'+kind,name)));
    }
    screen.replaceChildren(box('stack',section('训练家排行',box('toolbar',sel),list),section('统计图',charts)));
    async function update(){
      const key=sel.value;
      const {items}=await api('/api/leaderboard/'+key);
      if(store.view!==version || key!==sel.value)return;
      list.replaceChildren(...items.map((v,i)=>{
        const groups=v.groups || [];
        const who=box('rank-person',h('b','',v.nickname || '训练家'));
        if(groups.length>2){
          const more=h('details','rank-groups');
          more.append(h('summary','',groups[0]+' 等 '+groups.length+' 个群'),h('small','',groups.join(' · ')));
          who.append(more);
        }else who.append(h('small','',groups.join(' · ') || '暂无共同群信息'));
        return box('rank-row player-rank',h('small','place',String(i+1)),
          image(v.avatar_url || '',v.nickname || '训练家','rank-avatar'),who,
          h('strong','',v.score ?? v.unique_pokemon ?? v.floor));
      }));
      if(!items.length)list.append(h('p','empty','暂无排行'));
    }
    sel.onchange=()=>update().catch(e=>notify(e.message));await update();
  }
  const quizNames=['我是谁','猜图鉴','猜技能','猜属性','猜精灵'];
  const quizHints=['看剪影认宝可梦','读图鉴辨物种','根据线索猜招式','推断属性组合','根据线索认精灵'];
  function currentQuiz(){
    const s=store.snapshot;
    return s?.minigame?.game || null;
  }
  function renderTurn(){
    if(store.tab==='冒险')adventure();
    else if(store.tab==='小游戏')quizzes();
  }
  function quizzes(){
    const s=store.snapshot, name=currentQuiz();
    if(!name || s?.canceled || s?.last_action?.action==='cancel'){
      const games=quizNames.map((n,i)=>{
        const b=actionButton(n,'minigame_start',n,'game-tile');
        b.append(h('small','',quizHints[i]));return b;
      });
      screen.replaceChildren(section('小游戏',box('quiz-grid',...games)));return;
    }
    const focused=document.activeElement?.id==='quiz-answer';
    const content=box('quiz-content');
    for(const src of store.images){
      const zoom=button('',()=>preview(src,name),'quiz-art');
      zoom.append(image(src,name));content.append(zoom);
    }
    const prompt=store.text.split('\n').filter(t=>!/^请在[\d.]+秒内做出选择/.test(t)).join('\n').trim();
    if(prompt)content.append(h('p','quiz-prompt',prompt));
    if(s.awaiting && s.last_action?.action==='reply')content.append(h('small','','上次作答 · '+s.last_action.value));
    if(s.done){
      content.append(box('actions',actionButton('再来一局','minigame_start',name,'primary'),
        button('选择游戏',()=>{store.snapshot={...s,last_action:{},minigame:null};quizzes();})));
    }else if(s.awaiting){
      const form=h('form','quiz-answer');
      const input=h('input');input.id='quiz-answer';input.maxLength=100;
      input.setAttribute('aria-label','答案');input.placeholder=name==='猜属性'?'输入两种属性':'输入答案';
      input.value=store.quizDraft || '';input.oninput=()=>{store.quizDraft=input.value;};
      const send=h('button','primary','猜一下');send.type='submit';send.disabled=store.busy;
      form.onsubmit=e=>{e.preventDefault();const guess=input.value.trim();if(guess && !store.busy){
        store.quizDraft='';act('reply',guess);
      }};
      if(name==='猜属性'){
        const picked=new Set((store.quizDraft || '').split(' ').filter(Boolean));
        const types=box('type-picks');
        for(const type of s.minigame.types){
          const choice=button(type,()=>{
            if(picked.has(type))picked.delete(type);
            else if(picked.size<2)picked.add(type);
            store.quizDraft=[...picked].join(' ');input.value=store.quizDraft;
            for(const b of types.children)b.setAttribute('aria-pressed',String(picked.has(b.textContent)));
            send.disabled=store.busy || picked.size!==2;
          });
          choice.setAttribute('aria-pressed',String(picked.has(type)));types.append(choice);
        }
        input.readOnly=true;send.disabled=store.busy || picked.size!==2;
        content.append(types);
      }
      form.append(input,send);content.append(form);
    }else content.append(h('small','',store.busy?'正在提交…':'正在出题…'));
    screen.replaceChildren(section(name,content));
    if(focused)$('#quiz-answer')?.focus({preventScroll:true});
  }
  function activity(item) {
    const bags={'我的精灵蛋':'eggs','我的道具':'items','我的学习机':'technical'};
    if(bags[item.func])return openBag(bags[item.func]);
    if(['我的精灵列表','精灵状态'].includes(item.func))return refreshWorld().then(()=>go('队伍'));
    if(['精灵图鉴','宝可梦技能'].includes(item.func))return go('图鉴');
    if(item.func==='查看地图')return atlas();
    if(item.func==='我的金钱')return refreshWorld().then(()=>modal('我的金钱',h('strong','',store.world.profile.score+' 金币')));
    if(quizNames.includes(item.func))return act('minigame_start',item.func);
    const trigger=item.triggers.find(t=>t.type==='fullmatch') || item.triggers[0];
    if(!trigger)return;
    const input=h('input');input.setAttribute('aria-label','活动参数');
    const usage=(item.detail_des || '').split('`').find(t=>t.startsWith(trigger.value+' '));
    input.placeholder=usage?.slice(trigger.value.length).trim() || '所需参数';
    const form=box('stack',h('p','',item.brief_des),trigger.type!=='fullmatch' && box('stack',h('small','',input.placeholder),input),
      button('执行'+item.func,()=>legacy(trigger.value+(input.value.trim()?' '+input.value.trim():'')),'primary'));
    modal(item.func,form);
  }
  async function activities(version) {
    const menu=await api('/api/menu');
    if(version!==store.view)return;
    const body=box('stack');
    for(const [category,items] of Object.entries(menu.categories)){
      if(category==='小游戏')continue;
      const available=items.filter(item=>!item.pmn_hidden && item.triggers?.length);
      if(available.length)body.append(section(category,box('actions',...available.map(item=>button(item.func,()=>activity(item))))));
    }
    screen.replaceChildren(body);
  }
  async function admin(version) {
    const data=await api('/api/admin/state');
    if(version!==store.view)return;
    const fields={icons:'精灵图标',star_icons:'闪光图标',menu_entries:'功能',players:'训练家',pokemon_records:'精灵记录',web_sessions:'网页会话'};
    screen.replaceChildren(section('游戏管理',...Object.entries(fields).map(([key,title])=>box('rank-row',h('span','',title),h('b','',data[key]))),
      box('scenebar',button('下载素材',async()=>{await api('/api/admin/resource/download',{});notify('已开始下载素材');}),
        button('重载菜单',async()=>{await api('/api/admin/reload',{});notify('菜单已重载');}))));
  }
  async function go(tab) {
    store.tab=tab;const version=++store.view;nav();ongoing();
    const pages={'冒险':adventure,'队伍':team,'背包':bag,'图鉴':dex,'排行':rankings,'小游戏':quizzes,'活动':activities,'管理':admin};
    try { await pages[tab](version); } catch(e){ if(version===store.view)screen.replaceChildren(section(tab,h('p','empty',e.message),button('重试',()=>go(tab)))); }
  }
  async function start() {
    try { await restore(); } catch(e){screen.replaceChildren(section('读取存档失败',h('p','',e.message),button('重试',start)));}
  }
  start();
})();
