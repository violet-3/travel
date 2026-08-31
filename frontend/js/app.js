/* ═══════════════════════════════════════
   山河游记 · 前端渲染引擎 v3
   出发地+目的地地图 / 一键导航 / 穷游展示
   ═══════════════════════════════════════ */
var PAGES=[{e:'🏠',l:'首页',id:'home'},{e:'🌤️',l:'天气',id:'weather'},{e:'🗺️',l:'路线',id:'map'},{e:'📅',l:'行程',id:'days'},{e:'📸',l:'景点',id:'spots'},{e:'🍜',l:'美食',id:'food'},{e:'🎭',l:'文化',id:'culture'},{e:'💰',l:'预算',id:'budget'}];
var guide=null,amap=null,page=0;

function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function pic(w,h,seed){return'https://picsum.photos/seed/'+(seed||'x').replace(/\s+/g,'-').toLowerCase().slice(0,40)+'/'+w+'/'+h}
// 真实坐标 → 高德导航 URI（手机可唤起高德App，桌面打开网页版路线规划）; 无坐标 → 降级为地点搜索
function nav(city,place,coord){
  if(coord&&coord.length===2){
    var to=coord[0]+','+coord[1]+','+encodeURIComponent(place||city||'目的地');
    return'<a class="tl-nav" href="https://uri.amap.com/navigation?to='+to+'&mode=car&policy=1&src=shanhe&coordinate=gaode&callnative=0" target="_blank" rel="noopener">🧭 一键导航</a>'
  }
  return'<a class="tl-nav" href="https://uri.amap.com/search?keyword='+encodeURIComponent(city+' '+place)+'" target="_blank" rel="noopener">🧭 一键导航</a>'
}
// 图片降级链: 富化层真实图 → picsum 占位 → 隐藏
function imgFallback(img){var fb=img.getAttribute('data-fb');if(fb&&img.src!==fb){img.src=fb;img.removeAttribute('data-fb')}else{img.style.display='none'}}
function imgTag(real,seed,w,h,alt,cls){
  var fb=pic(w,h,seed),src=real?esc(real):fb;
  return'<img src="'+src+'"'+(cls?' class="'+cls+'"':'')+' alt="'+esc(alt||'')+'" loading="lazy" onclick="lightboxShow(this.src)" onerror="imgFallback(this)"'+(real?' data-fb="'+fb+'"':'')+'>'
}
function lightboxShow(src){
  var ov=document.getElementById('lightbox');
  if(!ov){ov=document.createElement('div');ov.id='lightbox';ov.onclick=function(){ov.classList.remove('show')};document.body.appendChild(ov)}
  ov.innerHTML='<img src="'+String(src).replace(/"/g,'&quot;')+'" alt="">';ov.classList.add('show')
}
// 高德 JS SDK 懒加载: Key 从后端 /api/config 获取，前端不再硬编码密钥
var amapLoading=null;
function loadAmap(){
  if(amapLoading)return amapLoading;
  amapLoading=fetch('/api/config').then(function(r){return r.json()}).then(function(cfg){
    window._AMapSecurityConfig={securityJsCode:cfg.amap_secret||''};
    return new Promise(function(res,rej){
      var s=document.createElement('script');
      s.src='https://webapi.amap.com/maps?v=2.0&key='+(cfg.amap_key||'')+'&plugin=AMap.Geocoder,AMap.Polyline,AMap.Marker';
      s.onload=res;s.onerror=rej;document.head.appendChild(s);
    })
  }).catch(function(e){console.warn('AMap load failed:',e);return null})
}

// ═══ Progress (流式真实进度) ═══
var STAGE_EMOJI={intent:'🧳',route:'🗺️',content:'📿',save:'📚',weather:'🌤️',enrich:'📷',compile:'✨',done:'🎉'};
function showProgress(pct,stage,message){
  document.getElementById('prog-emoji').textContent=STAGE_EMOJI[stage]||'🧳';
  document.getElementById('prog-text').textContent=message||'正在生成...';
  document.getElementById('prog-hint').textContent='AI 正在为你编写专属攻略';
  document.getElementById('prog-fill').style.width=Math.max(pct||0,4)+'%';
  document.getElementById('prog-pct').textContent=(pct||0)+'%';
}
function showGenError(msg){
  document.getElementById('progress-overlay').classList.remove('show');
  var bar=document.getElementById('error-bar');
  if(bar){bar.textContent='⚠️ '+msg;bar.classList.add('show')}
}

async function startGenerate(){
  var inp=document.getElementById('query-input'),btn=document.getElementById('gen-btn');
  var q=inp.value.trim()||'想去安阳玩3天';
  btn.disabled=true;btn.textContent='生成中...';
  var eb=document.getElementById('error-bar');if(eb)eb.classList.remove('show');
  document.getElementById('progress-overlay').classList.add('show');
  guide=null;showProgress(4,'intent','正在理解需求...');
  try{
    var resp=await fetch('/api/generate/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});
    if(!resp.ok||!resp.body)throw new Error('服务异常 (HTTP '+resp.status+')');
    var reader=resp.body.getReader(),dec=new TextDecoder(),buf='';
    for(;;){
      var r=await reader.read();if(r.done)break;
      buf+=dec.decode(r.value,{stream:true});
      var lines=buf.split('\n');buf=lines.pop();
      for(var i=0;i<lines.length;i++){
        var line=lines[i].trim();if(!line)continue;
        var ev;try{ev=JSON.parse(line)}catch(e){continue}
        if(ev.type==='progress')showProgress(ev.progress,ev.stage,ev.message);
        else if(ev.type==='error')throw new Error(ev.message||'生成失败');
        else if(ev.type==='guide')guide=ev.guide;
      }
    }
    if(!guide)throw new Error('未收到攻略数据');
    document.getElementById('progress-overlay').classList.remove('show');
    renderAll();switchPage(0);
    document.getElementById('navbar').classList.add('show');document.getElementById('dots').classList.add('show');
  }catch(e){showGenError(e.message||String(e))}
  btn.disabled=false;btn.textContent='✦ 生成攻略';
}

// ═══ Nav ═══
function initNav(){var n=document.getElementById('navbar'),d=document.getElementById('dots');n.innerHTML='';d.innerHTML='';PAGES.forEach(function(p,i){var b=document.createElement('button');b.className='nav-btn'+(i?'':' active');b.textContent=p.e+' '+p.l;b.onclick=function(){switchPage(i)};n.appendChild(b);var dt=document.createElement('button');dt.className='page-dot'+(i?'':' active');dt.onclick=function(){switchPage(i)};d.appendChild(dt)})}
function switchPage(n){page=n;document.querySelectorAll('.nav-btn').forEach(function(b,i){b.classList.toggle('active',i===n)});document.querySelectorAll('.page-dot').forEach(function(d,i){d.classList.toggle('active',i===n)});document.querySelectorAll('.page').forEach(function(p,i){p.classList.toggle('active',i===n)});scrollTo(0,0);
  if(n===2&&guide){
    if(window.AMap){initAmap()}
    else{loadAmap().then(function(){if(page===2&&guide&&window.AMap)initAmap()})}
  }
}

// ═══ Coordinates ═══
var COORDS={北京:[116.40,39.90],上海:[121.47,31.23],广州:[113.26,23.13],深圳:[114.06,22.54],成都:[104.07,30.57],重庆:[106.55,29.57],杭州:[120.15,30.28],苏州:[120.59,31.30],南京:[118.80,32.06],武汉:[114.30,30.60],西安:[108.94,34.26],长沙:[112.94,28.23],昆明:[102.83,24.88],大理:[100.23,25.61],丽江:[100.23,26.86],香格里拉:[99.70,27.83],西双版纳:[100.80,22.01],桂林:[110.29,25.27],贵阳:[106.71,26.57],拉萨:[91.13,29.65],西宁:[101.78,36.62],兰州:[103.83,36.06],敦煌:[94.66,40.14],哈尔滨:[126.64,45.74],沈阳:[123.43,41.80],大连:[121.61,38.91],青岛:[120.38,36.07],厦门:[118.08,24.48],三亚:[109.51,18.25],郑州:[113.62,34.75],洛阳:[112.45,34.62],安阳:[114.39,36.10],开封:[114.31,34.80],太原:[112.55,37.87],石家庄:[114.51,38.04],济南:[117.00,36.67],天津:[117.20,39.13],南宁:[108.37,22.82],福州:[119.30,26.07],合肥:[117.23,31.82],南昌:[115.86,28.68],太行山:[113.62,35.90],邯郸:[114.47,36.61],林州:[113.81,36.08],张家界:[110.48,29.12],黄山:[118.17,30.13],九寨沟:[103.90,33.26],雪乡:[128.09,44.35],亚布力:[128.61,44.78],牡丹江:[129.63,44.58],长白山:[128.10,42.10],延吉:[129.51,42.91],延边:[129.51,42.91],吉林:[126.55,43.84],长春:[125.32,43.90],漠河:[122.53,53.48],齐齐哈尔:[123.97,47.35],呼和浩特:[111.75,40.84],银川:[106.23,38.47],乌鲁木齐:[87.62,43.82],海口:[110.32,20.03],珠海:[113.58,22.27],宁波:[121.54,29.87],温州:[120.70,28.00],无锡:[120.31,31.57],扬州:[119.42,32.39],宜昌:[111.29,30.70],恩施:[109.49,30.27],襄阳:[112.14,32.03]};
function matchCoord(name){for(var k in COORDS){if(name.indexOf(k)>-1||k.indexOf(name)>-1)return COORDS[k]}return null}

// ═══ Map (含出发地; 字典外城市用 AMap.Geocoder 异步真实定位，不再伪造坐标) ═══
function initAmap(){
  if(amap){amap.destroy();amap=null}var el=document.getElementById('amap-container');if(!el||!guide)return;
  var dept=guide.departure_city||'';
  var allCities=dept?[dept].concat(guide.destinations||[]):(guide.destinations||[]);
  if(!allCities.length)return;
  amap=new AMap.Map('amap-container',{zoom:7,center:[104,30],mapStyle:'amap://styles/light'});
  var pts=new Array(allCities.length),resolved=0,done=false;
  function checkRender(){if(!done&&resolved>=allCities.length){done=true;render()}}
  function render(){
    if(!amap)return;
    var path=[];
    pts.forEach(function(p,i){
      if(!p)return;
      path.push(p);
      var label=(dept&&i===0)?'起':String(dept?i:i+1);
      var mk=new AMap.Marker({position:p,title:allCities[i],label:{content:label,offset:new AMap.Pixel(0,-22)}});
      mk.on('click',function(){window.open('https://uri.amap.com/navigation?to='+p[0]+','+p[1]+','+encodeURIComponent(allCities[i])+'&mode=car&src=shanhe&coordinate=gaode&callnative=0','_blank')});
      amap.add(mk);
    });
    if(path.length>1)amap.add(new AMap.Polyline({path:path,strokeColor:'#ff6b9d',strokeWeight:3,strokeStyle:'dashed',strokeOpacity:.7}));
    if(path.length)amap.setFitView(null,false,[60,60,60,60]);
  }
  allCities.forEach(function(c,i){
    var known=matchCoord(c);
    if(known){pts[i]=known;resolved++;return}
    if(window.AMap.Geocoder){
      (new AMap.Geocoder({city:'全国'})).getLocation(c,function(status,result){
        if(!done&&status==='complete'&&result.geocodes&&result.geocodes.length){
          var loc=result.geocodes[0].location;pts[i]=[loc.lng,loc.lat];
        }
        resolved++;checkRender();
      });
    }else{resolved++}   // 无 Geocoder 插件时跳过该点，不伪造坐标
  });
  checkRender();
  setTimeout(function(){if(!done){done=true;render()}},4000);   // 兜底: 4秒后画出已解析的点
}

// ═══ Render ═══
function renderAll(){initNav();var g=guide,d=(g.destinations||[]).join(' '),c=document.getElementById('pages-container');
  c.innerHTML=rHome(g,d)+rWeather(g)+rMap(g)+rDays(g)+rSpots(g)+rFood(g)+rCult(g)+rBudg(g)+'<div class="footer">山河游记 · '+(g.generated_at||'').slice(0,10)+'</div>'}

function rHome(g,d){var t=esc((g.title||'').replace(/[《》]/g,''));var hero='';
  (g.spots||[]).forEach(function(s){if(!hero&&s.photo)hero=s.photo});
  return'<div class="page active" id="p-home"><div class="hero-section"><span class="hero-emoji">🧳</span><h1>'+t+'</h1><p class="hero-sub">'+esc(g.subtitle||'')+'</p><div class="hero-meta">'+['📅 '+(g.days||0)+'天','📍 '+(g.destinations||[]).length+'城','🏔️ '+(g.spots||[]).length+'景点','💰 ¥'+(g.budget||{}).total+'/人'].map(function(x){return'<span class="meta-pill">'+x+'</span>'}).join('')+'</div>'+imgTag(hero,d+'-landmark',960,540,d,'hero-banner')+'</div></div>'}

function rWeather(g){var h='<div class="page" id="p-weather"><div class="sec-header"><span class="sec-emoji">🌤️</span><h2>天气预报</h2></div>';
  if(g.clothing_tip)h+='<div class="clothing-bar">🧥 '+esc(g.clothing_tip)+'</div>';
  if(!(g.weather||[]).length)h+='<div class="clothing-bar">🌤️ 暂无天气数据（未配置 AMAP_WEATHER_KEY 或查询失败，可在 .env 中配置后重试）</div>';
  h+='<div class="w-grid">';(g.weather||[]).forEach(function(w){
    h+='<div class="w-card"><h4>'+esc(w.city||'')+'</h4>';
    (w.forecast||[]).slice(0,3).forEach(function(f){var r=f.dayweather&&f.dayweather.indexOf('雨')>-1;
      h+='<div class="w-row"><span>'+(f.date||'').slice(-5)+' '+(f.week||'')+'</span><span>'+(r?'🌧️':'☀️')+'</span><span class="w-temp">'+(f.nighttemp||'')+'~'+(f.daytemp||'')+'°C</span></div>'});h+='</div>'});return h+'</div></div>'}

function rMap(g){return'<div class="page" id="p-map"><div class="sec-header"><span class="sec-emoji">🗺️</span><h2>路线总览</h2><p>'+(g.departure_city?esc(g.departure_city)+' → ':'')+(g.destinations||[]).join(' → ')+'</p></div><div class="map-block"><div id="amap-container"></div></div></div>'}

function rDays(g){var h='<div class="page" id="p-days"><div class="sec-header"><span class="sec-emoji">📅</span><h2>每日行程</h2></div>';
  var cols=['#ff6b9d','#4ec0e8','#5ce0b8','#ffd166','#a78bfa','#ff8a65'];
  ((g.route||{}).daily_plan||[]).forEach(function(d){var c=cols[(d.day-1)%6];h+='<div class="tl-card" style="border-left:4px solid '+c+'"><div class="tl-num" style="color:'+c+'">'+d.day+'<small>'+esc(d.city||'')+'</small></div><div>';
    [{k:'morning',t:'上午'},{k:'afternoon',t:'下午'},{k:'evening',t:'晚上'}].forEach(function(a){if(d[a.k]&&d[a.k].name)h+='<div class="tl-act"><span class="tl-time">'+a.t+'</span><span>'+esc(d[a.k].name)+'</span>'+nav(d.city||'',d[a.k].name,d[a.k].coordinate)+'</div>'});if(d.stay)h+='<div class="tl-stay">🏨 '+esc(d.stay)+' '+nav(d.city||'',d.stay,d.stay_coordinate)+'</div>';h+='</div></div>'});
  // 交通信息 (from/to 经 by_alias 序列化; 有坐标时可段内导航)
  var trans=(g.route||{}).transport||[];
  if(trans.length){h+='<div style="margin-top:16px"><h3>🚄 交通</h3>';trans.forEach(function(t){
    var tl='';
    if(t.from_coord&&t.to_coord&&t.from_coord.length===2&&t.to_coord.length===2){
      tl='<a class="tl-nav" href="https://uri.amap.com/navigation?from='+t.from_coord.join(',')+','+encodeURIComponent(t.from||'')+'&to='+t.to_coord.join(',')+','+encodeURIComponent(t.to||'')+'&mode=car&src=shanhe&coordinate=gaode&callnative=0" target="_blank" rel="noopener">🧭 段内导航</a>';
    }
    h+='<div class="tl-card" style="border-left:4px solid #a78bfa"><div style="padding:8px 0"><b>'+esc(t.from||'')+' → '+esc(t.to||'')+'</b> '+esc(t.mode||'')+' · '+esc(t.duration||'')+' · ¥'+(t.cost_est||0)+' '+tl+'</div></div>'});h+='</div>'}
  return h+'</div>'}

function rSpots(g){var h='<div class="page" id="p-spots"><div class="sec-header"><span class="sec-emoji">📸</span><h2>景点</h2></div>';
  if(!(g.spots||[]).length)return h+'<p style="text-align:center;color:var(--muted)">暂无景点数据</p></div>';
  h+='<div class="spot-grid">';
  (g.spots||[]).forEach(function(s){var ti={1:'必去',2:'深度',3:'小众'}[s.tier]||'',tc='tier-'+(s.tier||1),tg=(s.tags||[]).slice(0,3).map(function(t){return'<span>'+esc(t)+'</span>'}).join('');
    var ps=(s.photo_spots||[]).slice(0,2).map(function(p){return'<div style="font-size:.76em;color:var(--purple);margin-top:3px">📷 '+esc(p.name||'')+(p.best_time?'（'+esc(p.best_time)+'）':'')+'</div>'}).join('');
    h+='<div class="spot-card">'+imgTag(s.photo,s.name+'-china',500,350,s.name)+'<div class="sc-body"><div class="sc-name">'+esc(s.name)+' <span class="spot-tier '+tc+'">'+ti+'</span></div><div class="sc-meta">'+esc(s.type||'')+' · '+esc(s.duration||'')+' · ¥'+(s.ticket||0)+'</div>'+(s.best_time?'<div style="font-size:.78em;color:var(--blue);margin-top:2px">⏰ '+esc(s.best_time)+'</div>':'')+'<div class="sc-tags">'+tg+'</div>'+ps+(s.tips?'<div style="font-size:.78em;color:var(--soft);margin-top:6px">💡 '+esc(s.tips)+'</div>':'')+nav(s.city||(g.destinations||[])[0]||'',s.name,s.coordinate)+'</div></div>'});
  return h+'</div></div>'}

function rFood(g){var h='<div class="page" id="p-food"><div class="sec-header"><span class="sec-emoji">🍜</span><h2>在地味道</h2></div>';
  var total=0;(g.cultures||[]).forEach(function(c){total+=((c.cuisine||{}).must_eat||[]).length});
  if(!total)return h+'<p style="text-align:center;color:var(--muted)">暂无美食数据</p></div>';
  h+='<div class="food-grid">';
  (g.cultures||[]).forEach(function(c){(c.cuisine||{}).must_eat&&c.cuisine.must_eat.slice(0,6).forEach(function(f){
    h+='<div class="food-card">'+imgTag(f.photo,f.name||'food',500,320,f.name||'')+'<div class="fc-body"><h4>'+esc(f.name||'')+'</h4><div class="fc-reason">'+esc(f.reason||'')+'</div><div class="fc-meta"><span>📍 '+esc(f.where||'')+'</span><span class="food-price">¥'+(f.price_per_person||0)+'/人</span></div>'+(f.tips?'<div style="font-size:.78em;color:var(--soft);margin-top:4px">💡 '+esc(f.tips)+'</div>':'')+nav(c.city||'',f.where||f.name||'',f.coordinate)+'</div></div>'});});return h+'</div></div>'}

// 值可能是字符串 / 字符串数组 / {name} 对象数组，统一渲染成小标签
function fmtChips(v,label){
  if(!v)return'';var items=Array.isArray(v)?v:[v];
  var chips=items.map(function(x){var s=(typeof x==='string')?x:((x&&(x.name||x.title))||'');
    return s?'<span class="dialect-chip">'+esc(s)+'</span>':''}).join('');
  return chips?'<div style="margin-top:8px"><b style="font-size:.82em">'+label+'</b> '+chips+'</div>':'';
}

function rCult(g){var h='<div class="page" id="p-culture"><div class="sec-header"><span class="sec-emoji">🎭</span><h2>风土人情</h2></div><div class="culture-grid">';
  (g.cultures||[]).forEach(function(c){var fc=c.folk_culture||{},di=(fc.dialect||[]).slice(0,4).map(function(d){return'<span class="dialect-chip"><b>'+esc(d.phrase||'')+'</b> '+esc(d.pinyin||'')+'</span>'}).join('');
    var ta=(c.taboos||[]).slice(0,3).map(function(t){return'<div class="taboo-item">'+esc(t.rule||'')+'</div>'}).join('');
    var fe=(c.festivals||[]).slice(0,3).map(function(f){return'<div class="festival-item"><b>'+esc(f.name||'')+'</b>（'+esc(f.date||'')+'）— '+esc(f.what_to_see||'')+'</div>'}).join('');
    var hi=(c.history||[]).slice(0,3).map(function(x){return'<div class="history-block">📜 '+esc(x.story||'')+'</div>'}).join('');
    h+='<div class="culture-card"><h3>🏛️ '+esc(c.city||'')+'</h3>'
      +(fc.architecture?'<p style="font-size:.84em;color:var(--soft);margin-bottom:8px">🏘️ '+esc(fc.architecture)+'</p>':'')
      +(di?'<div>'+di+'</div>':'')
      +fmtChips((c.cuisine||{}).night_market,'🌙 夜市')
      +fmtChips((c.cuisine||{}).souvenir,'🎁 伴手礼')
      +(ta?'<div style="margin-top:10px">'+ta+'</div>':'')
      +(fe?'<div style="margin-top:10px"><b style="font-size:.85em">🎪 节庆</b>'+fe+'</div>':'')
      +(hi?'<div style="margin-top:8px"><b style="font-size:.85em">📜 典故</b>'+hi+'</div>':'')
      +'</div>'});
  return h+'</div></div>'}

function rBudg(g){var b=g.budget||{},t=b.total||1,h='<div class="page" id="p-budget"><div class="sec-header"><span class="sec-emoji">💰</span><h2>预算分布</h2><p>'+(g.budget_level||'')+'</p></div>';
  [{l:'交通',v:b.transport||0,c:'#ff6b9d'},{l:'住宿',v:b.accommodation||0,c:'#4ec0e8'},{l:'门票',v:b.tickets||0,c:'#5ce0b8'},{l:'餐饮',v:b.food||0,c:'#ffd166'},{l:'其他',v:b.other||0,c:'#a78bfa'}].forEach(function(a){var p=Math.max(a.v/t*100,1);h+='<div class="budget-row"><span class="br-label">'+a.l+'</span><div class="br-track"><div style="width:'+p+'%;background:'+a.c+'"></div></div><span class="br-val">¥'+a.v+'</span></div>'});
  h+='<div class="br-total">合计 ¥'+t+' ('+Math.round(t/(g.days||1))+'元/天)</div>';
  var w=(g.route||{}).warnings||[],ds=(g.destinations||[]).join('、'),dc=g.departure_city||'';
  if(w.length)h+='<div class="warn-box"><ul>'+w.map(function(x){return'<li>'+esc(x)+'</li>'}).join('')+'</ul></div>';
  h+='<div class="ending-card"><h3>还想调整吗？</h3><div class="ending-tags">'+['加一天深度游','节奏再慢一点','想去周边秘境'].map(function(x){return'<span class="ending-tag" onclick="document.getElementById(\'query-input\').value=\''+x+'\';document.getElementById(\'query-input\').focus()">'+x+'</span>'}).join('')+'</div></div>';
  return h+'</div>'}

// 点"还想调整吗"标签后，滚回输入框让用户看到已填入的调整需求
document.addEventListener('click',function(e){
  var tag=e.target.closest('.ending-tag');if(!tag)return;
  var inp=document.getElementById('query-input');
  if(inp)inp.scrollIntoView({behavior:'smooth',block:'center'});
});

initNav();
