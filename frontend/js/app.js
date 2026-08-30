/* ═══════════════════════════════════════
   山河游记 · 前端渲染引擎 v3
   出发地+目的地地图 / 一键导航 / 穷游展示
   ═══════════════════════════════════════ */
var PAGES=[{e:'🏠',l:'首页',id:'home'},{e:'🌤️',l:'天气',id:'weather'},{e:'🗺️',l:'路线',id:'map'},{e:'📅',l:'行程',id:'days'},{e:'📸',l:'景点',id:'spots'},{e:'🍜',l:'美食',id:'food'},{e:'🎭',l:'文化',id:'culture'},{e:'💰',l:'预算',id:'budget'}];
var guide=null,amap=null,page=0;

function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
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
      s.src='https://webapi.amap.com/maps?v=2.0&key='+(cfg.amap_key||'')+'&plugin=AMap.Polyline,AMap.Marker';
      s.onload=res;s.onerror=rej;document.head.appendChild(s);
    })
  }).catch(function(e){console.warn('AMap load failed:',e);return null})
}

// ═══ Progress ═══
var PROG_STAGES=[{e:'🧳',t:'理解需求',h:'解析目的地与偏好'},{e:'🗺️',t:'规划路线',h:'串联城市，计算节奏'},{e:'📿',t:'发掘秘境',h:'搜集景点美食文化'},{e:'🌤️',t:'查询天气',h:'查看出行气象'},{e:'✨',t:'即将完成',h:'整理专属攻略'}];
function showProgress(n){var s=PROG_STAGES[n]||PROG_STAGES[0];document.getElementById('prog-emoji').textContent=s.e;document.getElementById('prog-text').textContent=s.t;document.getElementById('prog-hint').textContent=s.h;document.querySelectorAll('#progress-overlay .prog-dot').forEach(function(d,i){d.className='prog-dot'+(i<n?' done':'')+(i===n?' active':'')})}

async function startGenerate(){
  var inp=document.getElementById('query-input'),btn=document.getElementById('gen-btn'),q=inp.value.trim()||'想去安阳玩3天';
  btn.disabled=true;btn.textContent='生成中...';document.getElementById('progress-overlay').classList.add('show');
  var stage=0,stageTimer=setInterval(function(){stage=Math.min(stage+1,4);showProgress(stage)},2000);showProgress(0);
  try{var r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});guide=await r.json();
    clearInterval(stageTimer);showProgress(4);
    setTimeout(function(){document.getElementById('progress-overlay').classList.remove('show');renderAll();switchPage(0);document.getElementById('navbar').classList.add('show');document.getElementById('dots').classList.add('show')},600)}catch(e){alert('Generation failed: '+e.message);document.getElementById('progress-overlay').classList.remove('show')}
  btn.disabled=false;btn.textContent='✦ 生成攻略'}

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
function findCoord(name){for(var k in COORDS){if(name.indexOf(k)>-1||k.indexOf(name)>-1)return COORDS[k]}var h=0;for(var i=0;i<name.length;i++)h+=name.charCodeAt(i);return[104+h%20*.8,30+h%15*.7]}

// ═══ Map (含出发地) ═══
function initAmap(){
  if(amap){amap.destroy();amap=null}var el=document.getElementById('amap-container');if(!el||!guide)return;
  // 出发地 + 目的地
  var dept=guide.departure_city||'';
  var allCities=dept?[dept].concat(guide.destinations||[]):(guide.destinations||[]);
  var pts=[],colors=['#ff6b9d','#4ec0e8','#5ce0b8','#ffd166','#a78bfa','#ff8a65'];
  allCities.forEach(function(c){pts.push(findCoord(c))});
  if(!pts.length)return;
  amap=new AMap.Map('amap-container',{zoom:7,center:[pts[0][0],pts[0][1]],mapStyle:'amap://styles/light'});
  var path=[];
  pts.forEach(function(p,i){
    path.push([p[0],p[1]]);
    var label=i===0&&dept?'起':'';
    var mk=new AMap.Marker({position:[p[0],p[1]],title:allCities[i],label:label?{content:label,offset:new AMap.Pixel(0,-22)}:{content:String(dept?i:i+1),offset:new AMap.Pixel(0,-22)}});
    mk.on('click',function(){window.open('https://uri.amap.com/navigation?to='+p[0]+','+p[1]+','+encodeURIComponent(allCities[i])+'&mode=car&src=shanhe&coordinate=gaode&callnative=0','_blank')});amap.add(mk)});
  // 出发地→第一站 虚线
  amap.add(new AMap.Polyline({path:path,strokeColor:'#ff6b9d',strokeWeight:3,strokeStyle:'dashed',strokeOpacity:.7}));
  amap.setFitView(null,false,[60,60,60,60]);
}

// ═══ Render ═══
function renderAll(){initNav();var g=guide,d=(g.destinations||[]).join(' '),c=document.getElementById('pages-container');
  c.innerHTML=rHome(g,d)+rWeather(g)+rMap(g)+rDays(g)+rSpots(g)+rFood(g)+rCult(g)+rBudg(g)+'<div class="footer">山河游记 · '+(g.generated_at||'').slice(0,10)+'</div>'}

function rHome(g,d){var t=esc((g.title||'').replace(/[《》]/g,''));var hero='';
  (g.spots||[]).forEach(function(s){if(!hero&&s.photo)hero=s.photo});
  return'<div class="page active" id="p-home"><div class="hero-section"><span class="hero-emoji">🧳</span><h1>'+t+'</h1><p class="hero-sub">'+esc(g.subtitle||'')+'</p><div class="hero-meta">'+['📅 '+(g.days||0)+'天','📍 '+(g.destinations||[]).length+'城','🏔️ '+(g.spots||[]).length+'景点','💰 ¥'+(g.budget||{}).total+'/人'].map(function(x){return'<span class="meta-pill">'+x+'</span>'}).join('')+'</div>'+imgTag(hero,d+'-landmark',960,540,d,'hero-banner')+'</div></div>'}

function rWeather(g){var h='<div class="page" id="p-weather"><div class="sec-header"><span class="sec-emoji">🌤️</span><h2>天气预报</h2></div>';
  if(g.clothing_tip)h+='<div class="clothing-bar">🧥 '+esc(g.clothing_tip)+'</div>';
  h+='<div class="w-grid">';(g.weather||[]).forEach(function(w){
    h+='<div class="w-card"><h4>'+esc(w.city||'')+'</h4>';
    (w.forecast||[]).slice(0,3).forEach(function(f){var r=f.dayweather&&f.dayweather.indexOf('雨')>-1;
      h+='<div class="w-row"><span>'+(f.date||'').slice(-5)+' '+(f.week||'')+'</span><span>'+(r?'🌧️':'☀️')+'</span><span class="w-temp">'+(f.nighttemp||'')+'~'+(f.daytemp||'')+'°C</span></div>'});h+='</div>'});return h+'</div></div>'}

function rMap(g){return'<div class="page" id="p-map"><div class="sec-header"><span class="sec-emoji">🗺️</span><h2>路线总览</h2><p>'+(g.departure_city?esc(g.departure_city)+' → ':'')+(g.destinations||[]).join(' → ')+'</p></div><div class="map-block"><div id="amap-container"></div></div></div>'}

function rDays(g){var h='<div class="page" id="p-days"><div class="sec-header"><span class="sec-emoji">📅</span><h2>每日行程</h2></div>';
  var cols=['#ff6b9d','#4ec0e8','#5ce0b8','#ffd166','#a78bfa','#ff8a65'];
  ((g.route||{}).daily_plan||[]).forEach(function(d){var c=cols[(d.day-1)%6];h+='<div class="tl-card" style="border-left:4px solid '+c+'"><div class="tl-num" style="color:'+c+'">'+d.day+'<small>'+esc(d.city||'')+'</small></div><div>';
    [{k:'morning',t:'上午'},{k:'afternoon',t:'下午'},{k:'evening',t:'晚上'}].forEach(function(a){if(d[a.k]&&d[a.k].name)h+='<div class="tl-act"><span class="tl-time">'+a.t+'</span><span>'+esc(d[a.k].name)+'</span>'+nav(d.city||'',d[a.k].name,d[a.k].coordinate)+'</div>'});if(d.stay)h+='<div class="tl-stay">🏨 '+esc(d.stay)+'</div>';h+='</div></div>'});
  // 交通信息
  var trans=(g.route||{}).transport||[];
  if(trans.length){h+='<div style="margin-top:16px"><h3>🚄 交通</h3>';trans.forEach(function(t){h+='<div class="tl-card" style="border-left:4px solid #a78bfa"><div style="padding:8px 0"><b>'+esc(t.from||'')+' → '+esc(t.to||'')+'</b> '+esc(t.mode||'')+' · '+esc(t.duration||'')+' · ¥'+(t.cost_est||0)+'</div></div>'});h+='</div>'}
  return h+'</div>'}

function rSpots(g){var h='<div class="page" id="p-spots"><div class="sec-header"><span class="sec-emoji">📸</span><h2>景点</h2></div><div class="spot-grid">';
  (g.spots||[]).slice(0,12).forEach(function(s){var ti={1:'必去',2:'深度',3:'小众'}[s.tier]||'',tc='tier-'+(s.tier||1),tg=(s.tags||[]).slice(0,3).map(function(t){return'<span>'+esc(t)+'</span>'}).join('');
    h+='<div class="spot-card">'+imgTag(s.photo,s.name+'-china',500,350,s.name)+'<div class="sc-body"><div class="sc-name">'+esc(s.name)+' <span class="spot-tier '+tc+'">'+ti+'</span></div><div class="sc-meta">'+esc(s.type||'')+' · '+esc(s.duration||'')+' · ¥'+(s.ticket||0)+'</div><div class="sc-tags">'+tg+'</div>'+(s.tips?'<div style="font-size:.78em;color:var(--soft);margin-top:6px">💡 '+esc(s.tips)+'</div>':'')+nav(s.city||(g.destinations||[])[0]||'',s.name,s.coordinate)+'</div></div>'});return h+'</div></div>'}

function rFood(g){var h='<div class="page" id="p-food"><div class="sec-header"><span class="sec-emoji">🍜</span><h2>在地味道</h2></div><div class="food-grid">';
  (g.cultures||[]).forEach(function(c){(c.cuisine||{}).must_eat&&c.cuisine.must_eat.slice(0,6).forEach(function(f){
    h+='<div class="food-card">'+imgTag(f.photo,f.name||'food',500,320,f.name||'')+'<div class="fc-body"><h4>'+esc(f.name||'')+'</h4><div class="fc-reason">'+esc(f.reason||'')+'</div><div class="fc-meta"><span>📍 '+esc(f.where||'')+'</span><span class="food-price">¥'+(f.price_per_person||0)+'/人</span></div>'+nav(c.city||'',f.where||f.name||'',f.coordinate)+'</div></div>'});});return h+'</div></div>'}

function rCult(g){var h='<div class="page" id="p-culture"><div class="sec-header"><span class="sec-emoji">🎭</span><h2>风土人情</h2></div><div class="culture-grid">';
  (g.cultures||[]).forEach(function(c){var fc=c.folk_culture||{},di=(fc.dialect||[]).slice(0,4).map(function(d){return'<span class="dialect-chip"><b>'+esc(d.phrase||'')+'</b> '+esc(d.pinyin||'')+'</span>'}).join('');
    var ta=(c.taboos||[]).slice(0,3).map(function(t){return'<div class="taboo-item">'+esc(t.rule||'')+'</div>'}).join('');
    h+='<div class="culture-card"><h3>🏛️ '+esc(c.city||'')+'</h3>'+di+'<div style="margin-top:10px">'+ta+'</div></div>'});return h+'</div></div>'}

function rBudg(g){var b=g.budget||{},t=b.total||1,h='<div class="page" id="p-budget"><div class="sec-header"><span class="sec-emoji">💰</span><h2>预算分布</h2><p>'+(g.budget_level||'')+'</p></div>';
  [{l:'交通',v:b.transport||0,c:'#ff6b9d'},{l:'住宿',v:b.accommodation||0,c:'#4ec0e8'},{l:'门票',v:b.tickets||0,c:'#5ce0b8'},{l:'餐饮',v:b.food||0,c:'#ffd166'},{l:'其他',v:b.other||0,c:'#a78bfa'}].forEach(function(a){var p=Math.max(a.v/t*100,1);h+='<div class="budget-row"><span class="br-label">'+a.l+'</span><div class="br-track"><div style="width:'+p+'%;background:'+a.c+'"></div></div><span class="br-val">¥'+a.v+'</span></div>'});
  h+='<div class="br-total">合计 ¥'+t+' ('+Math.round(t/(g.days||1))+'元/天)</div>';
  var w=(g.route||{}).warnings||[],ds=(g.destinations||[]).join('、'),dc=g.departure_city||'';
  if(w.length)h+='<div class="warn-box"><ul>'+w.map(function(x){return'<li>'+esc(x)+'</li>'}).join('')+'</ul></div>';
  h+='<div class="ending-card"><h3>还想调整吗？</h3><div class="ending-tags">'+['加一天深度游','节奏再慢一点','想去周边秘境'].map(function(x){return'<span class="ending-tag" onclick="document.getElementById(\'query-input\').value=\''+x+'\';document.getElementById(\'query-input\').focus()">'+x+'</span>'}).join('')+'</div></div>';
  return h+'</div>'}

initNav();
