/* ═══════════════════════════════════════════════════════════
   山河游记 · STILLMIND EDITORIAL & MOTION JAVASCRIPT ENGINE
   纯净SVG图标 · 水墨触控涟漪 · 杂志画报级排版 · 高德一键导航
   ═══════════════════════════════════════════════════════════ */

/* ── 统一纯净 SVG 图标系统 (告别廉价 Emoji) ── */
var ICONS = {
  home: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  map: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>',
  days: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
  spots: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
  food: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>',
  culture: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  weather: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
  budget: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>',
  nav: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 19 21 12 17 5 21 12 2"/></svg>',
  pin: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  hotel: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4v16"/><path d="M2 8h18a2 2 0 0 1 2 2v10"/><path d="M2 17h20"/><circle cx="6" cy="11" r="2"/></svg>',
  transit: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="16" rx="2"/><path d="M4 11h16"/><path d="M8 15h.01"/><path d="M16 15h.01"/><path d="M6 19l-2 2"/><path d="M18 19l2 2"/></svg>',
  sun: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>',
  rain: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16" y1="13" x2="16" y2="21"/><line x1="8" y1="13" x2="8" y2="21"/><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/></svg>'
};

var PAGES = [
  { id: 'home', l: '概览', icon: ICONS.home },
  { id: 'map', l: '路线', icon: ICONS.map },
  { id: 'days', l: '日程', icon: ICONS.days },
  { id: 'spots', l: '景点', icon: ICONS.spots },
  { id: 'food', l: '风味', icon: ICONS.food },
  { id: 'culture', l: '民俗', icon: ICONS.culture },
  { id: 'weather', l: '气象', icon: ICONS.weather },
  { id: 'budget', l: '预算', icon: ICONS.budget }
];

var guide = null;
var amap = null;
var page = 0;

/* ── 待启画卷（未生成状态下优雅留白） ── */
function renderEmptyState() {
  var h = '<div class="empty-guide-wrap">';
  h += '<div class="empty-guide-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<div class="empty-emblem">';
  h += '<svg viewBox="0 0 24 24" width="44" height="44" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">';
  h += '<polygon points="12 2 19 21 12 17 5 21 12 2"/>';
  h += '</svg>';
  h += '</div>';
  h += '<h2 class="empty-title">山河浩渺 · 待君启卷</h2>';
  h += '<p class="empty-desc">当前尚未生成专属旅行路线。请在开场主屏输入您心仪的目的地与旅行偏好，点击「生成专属攻略」，AI 编排引擎将实时为您深度生成涵盖路线、日程、景点机位、特色风味、在地民俗、气象与预算的 8 大维度画报。</p>';
  h += '<div class="empty-btn-wrap">';
  h += '<button class="pill-btn primary-btn magnetic-elem" onclick="scrollToHero()">';
  h += '<span>前往主屏定制行程 ➔</span>';
  h += '</button>';
  h += '</div>';
  h += '</div>';
  h += '</div>';
  return h;
}

/* ── 基础工具函数 ── */
function esc(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function pic(w, h, seed) {
  return 'https://picsum.photos/seed/' + (seed || 'shanhe').replace(/\s+/g, '-').toLowerCase().slice(0, 40) + '/' + w + '/' + h;
}

function nav(city, place, coord) {
  if (coord && coord.length === 2) {
    var to = coord[0] + ',' + coord[1] + ',' + encodeURIComponent(place || city || '目的地');
    return '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/navigation?to=' + to + '&mode=car&policy=1&src=shanhe&coordinate=gaode&callnative=0" target="_blank" rel="noopener">' + ICONS.nav + ' <span>导航</span></a>';
  }
  return '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/search?keyword=' + encodeURIComponent((city || '') + ' ' + (place || '')) + '" target="_blank" rel="noopener">' + ICONS.nav + ' <span>导航</span></a>';
}

function imgFallback(img) {
  var fb = img.getAttribute('data-fb');
  if (fb && img.src !== fb) {
    img.src = fb;
    img.removeAttribute('data-fb');
  } else {
    img.style.display = 'none';
  }
}

function imgTag(real, seed, w, h, alt, cls) {
  var fb = pic(w, h, seed);
  var src = real ? esc(real) : fb;
  return '<img src="' + src + '"' + (cls ? ' class="' + cls + '"' : '') + ' alt="' + esc(alt || '') + '" loading="lazy" onclick="lightboxShow(this.src)" onerror="imgFallback(this)"' + (real ? ' data-fb="' + fb + '"' : '') + '>';
}

function lightboxShow(src) {
  var ov = document.getElementById('lightbox');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'lightbox';
    ov.onclick = function() { ov.classList.remove('show'); };
    document.body.appendChild(ov);
  }
  ov.innerHTML = '<img src="' + String(src).replace(/"/g, '&quot;') + '" alt="图片放大预览">';
  ov.classList.add('show');
}

function showToast(msg) {
  var t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() {
    t.classList.remove('show');
  }, 2400);
}

function copyGuideHighlights() {
  if (!guide) {
    showToast('尚未生成攻略，请先定制行程');
    return;
  }
  var text = '【山河游记 · ' + (guide.title || '') + '】\n' +
    '📍 目的地：' + (guide.destinations || []).join(' ➔ ') + '\n' +
    '📅 天数：' + (guide.days || 0) + '天 | 预算：约¥' + ((guide.budget || {}).total || 0) + '/人\n' +
    '✨ 行程概览：\n';
  ((guide.route || {}).daily_plan || []).forEach(function(d) {
    text += 'Day ' + d.day + ' (' + d.city + '): ';
    var acts = [];
    if (d.morning && d.morning.name) acts.push(d.morning.name);
    if (d.afternoon && d.afternoon.name) acts.push(d.afternoon.name);
    if (d.evening && d.evening.name) acts.push(d.evening.name);
    text += acts.join(' ➔ ') + (d.stay ? ' | 宿: ' + d.stay : '') + '\n';
  });
  text += '\n（由山河游记 AI 智能生成）';

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function() {
      showToast('✓ 攻略摘要已复制到剪贴板');
    }).catch(function() {
      showToast('✓ 复制成功');
    });
  } else {
    showToast('✓ 复制成功');
  }
}

function printGuide() {
  if (!guide) {
    showToast('尚未生成攻略，请先定制行程后再导出打印');
    return;
  }
  window.print();
}

function applyPreset(text) {
  var inp = document.getElementById('query-input');
  if (inp) {
    inp.value = text;
    inp.focus();
    updateClearBtn();
    inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function clearQuery() {
  var inp = document.getElementById('query-input');
  if (inp) {
    inp.value = '';
    inp.focus();
    updateClearBtn();
  }
}

function updateClearBtn() {
  var inp = document.getElementById('query-input');
  var clr = document.getElementById('clear-btn');
  if (inp && clr) {
    clr.style.display = inp.value.trim() ? 'block' : 'none';
  }
}

/* ── 双阶段视口平滑过渡 (Hero ➔ Workspace) ── */
function enterWorkspace() {
  if (!guide) {
    var inp = document.getElementById('query-input');
    if (inp && inp.value.trim()) {
      startGenerate();
      return;
    } else {
      showToast('请先输入目的地心愿，点击「生成专属攻略」');
      if (inp) {
        inp.focus();
        inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }
  }
  var ws = document.getElementById('workspace-section');
  if (ws) {
    ws.scrollIntoView({ behavior: 'smooth' });
    setTimeout(function() {
      if (amap && typeof amap.resize === 'function') {
        amap.resize();
      }
    }, 600);
  }
}

function scrollToHero() {
  var hero = document.getElementById('landing-hero');
  if (hero) {
    hero.scrollIntoView({ behavior: 'smooth' });
  }
}

/* ═══════════════════════════════════════════
   🌟 交互物理微系统 (水墨触控涟漪 + Canvas 微粒 + 视差)
   ═══════════════════════════════════════════ */

var mousePos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
var auraPos = { x: mousePos.x, y: mousePos.y };

/* ── 1. 水墨微触控涟漪 (DOM 硬件加速，极度自然) ── */
function initInkRipple() {
  window.addEventListener('pointerdown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    var rip = document.createElement('div');
    rip.className = 'ink-ripple';
    rip.style.left = e.clientX + 'px';
    rip.style.top = e.clientY + 'px';
    document.body.appendChild(rip);
    setTimeout(function() {
      if (rip.parentNode) rip.parentNode.removeChild(rip);
    }, 600);
  });
}

/* ── 2. 禅意微粒群背景 ── */
function initZenCanvas() {
  var canvas = document.getElementById('zen-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var width = (canvas.width = window.innerWidth);
  var height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', function() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  var PARTICLE_COUNT = Math.min(Math.floor(window.innerWidth / 28), 45);
  var particles = [];
  var colors = [
    'rgba(195, 100, 59, ',   // 丹霞赭石
    'rgba(184, 139, 66, ',   // 茶金
    'rgba(35, 67, 57, ',     // 松墨绿
    'rgba(54, 110, 103, '    // 烟岚青
  ];

  for (var i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      size: Math.random() * 2.2 + 1.2,
      baseAlpha: Math.random() * 0.3 + 0.12,
      color: colors[Math.floor(Math.random() * colors.length)],
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: Math.random() * 0.018 + 0.01
    });
  }

  function animateCanvas() {
    ctx.clearRect(0, 0, width, height);

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < -10) p.x = width + 10;
      else if (p.x > width + 10) p.x = -10;
      if (p.y < -10) p.y = height + 10;
      else if (p.y > height + 10) p.y = -10;

      p.pulse += p.pulseSpeed;
      var currentAlpha = p.baseAlpha + Math.sin(p.pulse) * 0.1;

      // 鼠标流体排斥
      var dx = mousePos.x - p.x;
      var dy = mousePos.y - p.y;
      var dist = Math.sqrt(dx * dx + dy * dy);
      var maxDist = 110;

      if (dist < maxDist) {
        var force = (1 - dist / maxDist) * 1.5;
        p.x -= (dx / dist) * force;
        p.y -= (dy / dist) * force;
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color + Math.max(currentAlpha, 0.05) + ')';
      ctx.fill();

      // 微粒轻柔连线
      for (var j = i + 1; j < particles.length; j++) {
        var p2 = particles[j];
        var dist2 = Math.hypot(p.x - p2.x, p.y - p2.y);
        if (dist2 < 75) {
          var lineAlpha = (1 - dist2 / 75) * 0.07;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = 'rgba(184, 139, 66, ' + lineAlpha + ')';
          ctx.lineWidth = 0.75;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(animateCanvas);
  }

  animateCanvas();
}

/* ── 3. 鼠标流光跟随与远山视差 ── */
function initMouseEffects() {
  var aura = document.getElementById('cursor-aura');
  var mountainLayerBack = document.querySelector('.mountain-layer.layer-back');
  var mountainLayerMid = document.querySelector('.mountain-layer.layer-mid');

  window.addEventListener('mousemove', function(e) {
    mousePos.x = e.clientX;
    mousePos.y = e.clientY;

    document.documentElement.style.setProperty('--mouse-x', e.clientX + 'px');
    document.documentElement.style.setProperty('--mouse-y', e.clientY + 'px');

    if (mountainLayerBack && mountainLayerMid) {
      var offsetX = (e.clientX - window.innerWidth / 2) / window.innerWidth;
      var offsetY = (e.clientY - window.innerHeight / 2) / window.innerHeight;
      mountainLayerBack.style.transform = 'translate3d(' + (offsetX * -16) + 'px, ' + (offsetY * -5) + 'px, 0)';
      mountainLayerMid.style.transform = 'translate3d(' + (offsetX * -28) + 'px, ' + (offsetY * -10) + 'px, 0)';
    }
  });

  function updateAura() {
    auraPos.x += (mousePos.x - auraPos.x) * 0.12;
    auraPos.y += (mousePos.y - auraPos.y) * 0.12;
    if (aura) {
      aura.style.left = auraPos.x + 'px';
      aura.style.top = auraPos.y + 'px';
    }
    requestAnimationFrame(updateAura);
  }
  updateAura();
}

/* ── 4. 3D 悬浮视差与反光 Sheen ── */
function attach3DTiltCards() {
  var cards = document.querySelectorAll('.tilt-card');
  cards.forEach(function(card) {
    if (!card.querySelector('.card-sheen')) {
      var sheen = document.createElement('div');
      sheen.className = 'card-sheen';
      card.appendChild(sheen);
    }

    card.onmousemove = function(e) {
      var rect = card.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      var cx = rect.width / 2;
      var cy = rect.height / 2;

      var rotateX = ((y - cy) / cy) * -6;
      var rotateY = ((x - cx) / cx) * 6;

      card.style.transform = 'perspective(900px) rotateX(' + rotateX.toFixed(2) + 'deg) rotateY(' + rotateY.toFixed(2) + 'deg) scale3d(1.015, 1.015, 1.015)';
      card.style.setProperty('--sheen-x', x + 'px');
      card.style.setProperty('--sheen-y', y + 'px');
    };

    card.onmouseleave = function() {
      card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
    };
  });
}

/* ── 5. 磁性吸附按键 ── */
function attachMagneticElements() {
  var elems = document.querySelectorAll('.magnetic-elem');
  elems.forEach(function(el) {
    el.onmousemove = function(e) {
      var rect = el.getBoundingClientRect();
      var mx = (e.clientX - (rect.left + rect.width / 2)) * 0.25;
      var my = (e.clientY - (rect.top + rect.height / 2)) * 0.25;
      el.style.transform = 'translate3d(' + mx.toFixed(1) + 'px, ' + my.toFixed(1) + 'px, 0)';
    };
    el.onmouseleave = function() {
      el.style.transform = 'translate3d(0, 0, 0)';
    };
  });
}

/* ── 高德 JS SDK 懒加载 ── */
var amapLoading = null;
function loadAmap() {
  if (amapLoading) return amapLoading;
  amapLoading = fetch('/api/config')
    .then(function(r) { return r.json(); })
    .then(function(cfg) {
      window._AMapSecurityConfig = { securityJsCode: cfg.amap_secret || '' };
      return new Promise(function(res, rej) {
        var s = document.createElement('script');
        s.src = 'https://webapi.amap.com/maps?v=2.0&key=' + (cfg.amap_key || '') + '&plugin=AMap.Geocoder,AMap.Polyline,AMap.Marker';
        s.onload = res;
        s.onerror = rej;
        document.head.appendChild(s);
      });
    })
    .catch(function(e) {
      console.warn('高德地图 SDK 加载提示:', e);
      return null;
    });
  return amapLoading;
}

/* ── 流式进度展示 ── */
function showProgress(pct, stage, message) {
  var overlay = document.getElementById('progress-overlay');
  if (overlay) overlay.classList.add('show');

  var textEl = document.getElementById('prog-text');
  if (textEl) textEl.textContent = message || '正在沉浸编排旅程...';

  var hintEl = document.getElementById('prog-hint');
  if (hintEl) hintEl.textContent = 'AI 正在为你梳理山河动线与在地风物';

  var fillEl = document.getElementById('prog-fill');
  if (fillEl) fillEl.style.width = Math.max(pct || 0, 6) + '%';

  var pctEl = document.getElementById('prog-pct');
  if (pctEl) pctEl.textContent = (pct || 0) + '%';

  var stepMap = {
    intent: 'st-intent',
    route: 'st-route',
    content: 'st-enrich',
    enrich: 'st-enrich',
    compile: 'st-compile'
  };
  var activeStepId = stepMap[stage];
  if (activeStepId) {
    document.querySelectorAll('.step-dot').forEach(function(el) { el.classList.remove('active'); });
    var target = document.getElementById(activeStepId);
    if (target) target.classList.add('active');
  }
}

function showGenError(msg) {
  var overlay = document.getElementById('progress-overlay');
  if (overlay) overlay.classList.remove('show');
  var bar = document.getElementById('error-bar');
  if (bar) {
    bar.textContent = '⚠️ ' + msg;
    bar.classList.add('show');
  }
}

/* ── 核心流式生成 ── */
async function startGenerate() {
  var inp = document.getElementById('query-input');
  var btn = document.getElementById('gen-btn');
  var q = inp ? inp.value.trim() : '';

  if (!q) {
    showToast('请输入您的旅行目的地或心愿（如：想去西安玩3天）');
    if (inp) {
      inp.focus();
      inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return;
  }

  btn.disabled = true;
  btn.innerHTML = ICONS.nav + ' <span class="btn-text">正在规划...</span>';

  var eb = document.getElementById('error-bar');
  if (eb) eb.classList.remove('show');

  showProgress(4, 'intent', '正在洞察旅人心愿...');
  guide = null;

  try {
    var resp = await fetch('/api/generate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });

    if (!resp.ok || !resp.body) {
      throw new Error('服务端响应异常 (HTTP ' + resp.status + ')');
    }

    var reader = resp.body.getReader();
    var dec = new TextDecoder();
    var buf = '';

    for (;;) {
      var r = await reader.read();
      if (r.done) break;
      buf += dec.decode(r.value, { stream: true });
      var lines = buf.split('\n');
      buf = lines.pop();

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line) continue;
        var ev;
        try {
          ev = JSON.parse(line);
        } catch (e) {
          continue;
        }

        if (ev.type === 'progress') {
          showProgress(ev.progress, ev.stage, ev.message);
        } else if (ev.type === 'error') {
          throw new Error(ev.message || '生成失败');
        } else if (ev.type === 'guide') {
          guide = ev.guide;
        }
      }
    }

    if (!guide) throw new Error('未收到完整的攻略数据');

    var overlay = document.getElementById('progress-overlay');
    if (overlay) overlay.classList.remove('show');

    renderAll();
    switchPage(0);
    showToast('✨ 攻略已为您精美编排入卷');
    setTimeout(function() {
      enterWorkspace();
    }, 400);
  } catch (e) {
    showGenError(e.message || String(e));
  }

  btn.disabled = false;
  btn.innerHTML = ICONS.nav + ' <span class="btn-text">生成专属攻略</span>';
}

/* ── 导航初始化与阶梯动画切换 ── */
function initNav() {
  var n = document.getElementById('navbar');
  var d = document.getElementById('dots');
  if (!n || !d) return;

  n.innerHTML = '';
  d.innerHTML = '';

  PAGES.forEach(function(p, i) {
    var b = document.createElement('button');
    b.className = 'nav-btn magnetic-elem' + (i === page ? ' active' : '');
    b.innerHTML = p.icon + ' <span>' + p.l + '</span>';
    b.onclick = function() { switchPage(i); };
    n.appendChild(b);

    var dt = document.createElement('button');
    dt.className = 'page-dot' + (i === page ? ' active' : '');
    dt.title = p.l;
    dt.onclick = function() { switchPage(i); };
    d.appendChild(dt);
  });
}

function switchPage(n) {
  if (!guide) {
    showToast('尚未生成攻略，请先在主屏定制行程');
    scrollToHero();
    return;
  }
  page = n;
  document.querySelectorAll('.nav-btn').forEach(function(b, i) {
    b.classList.toggle('active', i === n);
  });
  document.querySelectorAll('.page-dot').forEach(function(d, i) {
    d.classList.toggle('active', i === n);
  });

  document.querySelectorAll('.page').forEach(function(p, i) {
    var isActive = i === n;
    p.classList.toggle('active', isActive);
    if (isActive) {
      var cards = p.querySelectorAll('.tilt-card, .kpi-card, .dossier-card, .weather-city-card, .culture-card, .itinerary-day-card');
      cards.forEach(function(c, cIdx) {
        c.style.setProperty('--stagger-i', cIdx);
        c.classList.remove('stagger-in');
        void c.offsetWidth;
        c.classList.add('stagger-in');
      });
    }
  });

  attach3DTiltCards();
  attachMagneticElements();

  if (n === 1 && guide) {
    if (window.AMap) {
      initAmap();
    } else {
      loadAmap().then(function() {
        if (page === 1 && guide && window.AMap) initAmap();
      });
    }
  }
}

/* ── 坐标字典 ── */
var COORDS = {
  北京: [116.40, 39.90], 上海: [121.47, 31.23], 广州: [113.26, 23.13], 深圳: [114.06, 22.54],
  成都: [104.07, 30.57], 重庆: [106.55, 29.57], 杭州: [120.15, 30.28], 苏州: [120.59, 31.30],
  南京: [118.80, 32.06], 武汉: [114.30, 30.60], 西安: [108.94, 34.26], 长沙: [112.94, 28.23],
  昆明: [102.83, 24.88], 大理: [100.23, 25.61], 丽江: [100.23, 26.86], 香格里拉: [99.70, 27.83],
  西双版纳: [100.80, 22.01], 桂林: [110.29, 25.27], 贵阳: [106.71, 26.57], 拉萨: [91.13, 29.65],
  西宁: [101.78, 36.62], 兰州: [103.83, 36.06], 敦煌: [94.66, 40.14], 哈尔滨: [126.64, 45.74],
  沈阳: [123.43, 41.80], 大连: [121.61, 38.91], 青岛: [120.38, 36.07], 厦门: [118.08, 24.48],
  三亚: [109.51, 18.25], 郑州: [113.62, 34.75], 洛阳: [112.45, 34.62], 安阳: [114.39, 36.10],
  林州: [113.81, 36.08], 开封: [114.31, 34.80], 太原: [112.55, 37.87], 石家庄: [114.51, 38.04],
  济南: [117.00, 36.67], 天津: [117.20, 39.13], 南宁: [108.37, 22.82], 福州: [119.30, 26.07],
  合肥: [117.23, 31.82], 南昌: [115.86, 28.68], 太行山: [113.62, 35.90], 邯郸: [114.47, 36.61],
  张家界: [110.48, 29.12], 黄山: [118.17, 30.13], 九寨沟: [103.90, 33.26], 雪乡: [128.09, 44.35],
  长白山: [128.10, 42.10], 呼和浩特: [111.75, 40.84], 银川: [106.23, 38.47], 乌鲁木齐: [87.62, 43.82]
};

function matchCoord(name) {
  if (!name) return null;
  for (var k in COORDS) {
    if (name.indexOf(k) > -1 || k.indexOf(name) > -1) return COORDS[k];
  }
  return null;
}

/* ── 高德地图初始化 ── */
function initAmap() {
  if (amap) {
    amap.destroy();
    amap = null;
  }
  var el = document.getElementById('amap-container');
  if (!el || !guide) return;

  var dept = guide.departure_city || '';
  var allCities = dept ? [dept].concat(guide.destinations || []) : (guide.destinations || []);
  if (!allCities.length) return;

  amap = new AMap.Map('amap-container', {
    zoom: 7,
    center: [104, 30],
    mapStyle: 'amap://styles/whitesmoke'
  });

  var pts = new Array(allCities.length);
  var resolved = 0;
  var done = false;

  function checkRender() {
    if (!done && resolved >= allCities.length) {
      done = true;
      render();
    }
  }

  function render() {
    if (!amap) return;
    var path = [];
    pts.forEach(function(p, i) {
      if (!p) return;
      path.push(p);
      var label = (dept && i === 0) ? '起' : String(dept ? i : i + 1);
      var mk = new AMap.Marker({
        position: p,
        title: allCities[i],
        label: {
          content: '<div style="background:#234339;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.2);">' + label + ' · ' + allCities[i] + '</div>',
          offset: new AMap.Pixel(0, -26)
        }
      });
      mk.on('click', function() {
        window.open('https://uri.amap.com/navigation?to=' + p[0] + ',' + p[1] + ',' + encodeURIComponent(allCities[i]) + '&mode=car&src=shanhe&coordinate=gaode&callnative=0', '_blank');
      });
      amap.add(mk);
    });

    if (path.length > 1) {
      amap.add(new AMap.Polyline({
        path: path,
        strokeColor: '#C3643B',
        strokeWeight: 4,
        strokeStyle: 'dashed',
        strokeOpacity: 0.85
      }));
    }
    if (path.length) {
      amap.setFitView(null, false, [60, 60, 60, 60]);
    }
  }

  allCities.forEach(function(c, i) {
    var known = matchCoord(c);
    if (known) {
      pts[i] = known;
      resolved++;
      return;
    }
    if (window.AMap.Geocoder) {
      (new AMap.Geocoder({ city: '全国' })).getLocation(c, function(status, result) {
        if (!done && status === 'complete' && result.geocodes && result.geocodes.length) {
          var loc = result.geocodes[0].location;
          pts[i] = [loc.lng, loc.lat];
        }
        resolved++;
        checkRender();
      });
    } else {
      resolved++;
    }
  });

  checkRender();
  setTimeout(function() {
    if (!done) {
      done = true;
      render();
    }
  }, 4000);
}

/* ═══════════════════════════════════════════
   8 大篇章 HTML 渲染 (清晰编辑画报布局)
   ═══════════════════════════════════════════ */
function renderAll() {
  initNav();
  var c = document.getElementById('pages-container');
  if (!c) return;

  if (!guide) {
    c.innerHTML = renderEmptyState();
    attach3DTiltCards();
    attachMagneticElements();
    return;
  }

  var g = guide;
  var d = (g.destinations || []).join(' ');

  c.innerHTML =
    rHome(g, d) +
    rMap(g) +
    rDays(g) +
    rSpots(g) +
    rFood(g) +
    rCult(g) +
    rWeather(g) +
    rBudg(g);

  attach3DTiltCards();
  attachMagneticElements();
}

/* ── TAB 1: 首页概览 (杂志画报级精排) ── */
function rHome(g, d) {
  var t = esc((g.title || '').replace(/[《》]/g, ''));
  var hero = '';
  (g.spots || []).forEach(function(s) {
    if (!hero && s.photo) hero = s.photo;
  });

  var totalSpots = (g.spots || []).length;
  var totalDays = g.days || 0;
  var totalCities = (g.destinations || []).length;
  var totalBudget = (g.budget || {}).total || 0;

  var h = '<div class="page active" id="p-home">';

  // 1. 顶部大画幅封面
  h += '<div class="overview-hero-card tilt-card">';
  h += imgTag(hero, d + '-landscape', 1200, 600, d, 'overview-banner-img');
  h += '<div class="overview-gradient-overlay"></div>';
  h += '<div class="card-sheen"></div>';
  h += '<div class="overview-hero-content">';
  h += '<div class="overview-meta-tag">SHANHE VOYAGE · 东方山河漫游画卷</div>';
  h += '<h2 class="overview-title">《' + t + '》</h2>';
  h += '<p class="overview-subtitle">' + esc(g.subtitle || '') + '</p>';
  h += '</div></div>';

  // 2. 4 列核心 KPI 数据条
  h += '<div class="kpi-metrics-grid">';
  h += '<div class="kpi-card">';
  h += '<div class="kpi-icon-wrap">' + ICONS.days + '</div>';
  h += '<div class="kpi-body"><span class="kpi-label">行程天数</span><span class="kpi-val">' + totalDays + '天</span><span class="kpi-sub">慢行节奏 · 张弛有度</span></div>';
  h += '</div>';

  h += '<div class="kpi-card">';
  h += '<div class="kpi-icon-wrap">' + ICONS.map + '</div>';
  h += '<div class="kpi-body"><span class="kpi-label">途经城邑</span><span class="kpi-val">' + totalCities + '座</span><span class="kpi-sub">' + esc((g.destinations || []).join(' · ')) + '</span></div>';
  h += '</div>';

  h += '<div class="kpi-card">';
  h += '<div class="kpi-icon-wrap">' + ICONS.spots + '</div>';
  h += '<div class="kpi-body"><span class="kpi-label">核心名胜</span><span class="kpi-val">' + totalSpots + '处</span><span class="kpi-sub">历史遗址与自然胜景</span></div>';
  h += '</div>';

  h += '<div class="kpi-card">';
  h += '<div class="kpi-icon-wrap">' + ICONS.budget + '</div>';
  h += '<div class="kpi-body"><span class="kpi-label">预估人均</span><span class="kpi-val">¥' + totalBudget + '</span><span class="kpi-sub">含城际交通与特色住宿</span></div>';
  h += '</div>';
  h += '</div>';

  // 3. 结构化行程档案拆分 (左: 行程提要，右: 出行指南)
  h += '<div class="overview-split-row">';
  
  // 左侧: 行程每日动线提要
  h += '<div class="dossier-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<h3>' + ICONS.days + ' <span>动线提要 · 逐日巡礼</span></h3>';
  ((g.route || {}).daily_plan || []).forEach(function(d) {
    var acts = [];
    if (d.morning && d.morning.name) acts.push(d.morning.name);
    if (d.afternoon && d.afternoon.name) acts.push(d.afternoon.name);
    if (d.evening && d.evening.name) acts.push(d.evening.name);
    h += '<div class="dossier-day-item">';
    h += '<div class="dd-badge">D' + d.day + '</div>';
    h += '<div class="dd-content">';
    h += '<div class="dd-title">' + esc(d.city || '') + (d.stay ? ' · 宿 ' + esc(d.stay) : '') + '</div>';
    h += '<div class="dd-spots">' + acts.map(function(a) { return esc(a); }).join(' ➔ ') + '</div>';
    h += '</div></div>';
  });
  h += '</div>';

  // 右侧: 行前准备与气候简报
  h += '<div class="dossier-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<h3>' + ICONS.weather + ' <span>行前锦囊与气候</span></h3>';
  if (g.clothing_tip) {
    h += '<p style="font-size:0.86em;color:var(--ink-body);line-height:1.65;margin-bottom:18px;"><b>穿衣建议：</b>' + esc(g.clothing_tip) + '</p>';
  }
  var warnings = (g.route || {}).warnings || [];
  if (warnings.length) {
    h += '<div style="background:var(--bg-subtle);padding:14px 18px;border-radius:var(--radius-md);font-size:0.82em;color:var(--ink-muted);line-height:1.6;margin-bottom:20px;">';
    h += '<b style="color:var(--ink-title)">核心提示：</b> ' + esc(warnings[0]);
    h += '</div>';
  }
  h += '<button class="pill-btn ghost-btn magnetic-elem" style="width:100%;justify-content:center;padding:10px 0;" onclick="switchPage(1)">';
  h += ICONS.map + ' <span>开启高德动态路线规划</span>';
  h += '</button>';
  h += '</div>';

  h += '</div>'; // overview-split-row
  h += '</div>'; // page
  return h;
}

/* ── TAB 2: 路线总览与地图 ── */
function rMap(g) {
  var dept = g.departure_city || '';
  var allStops = dept ? [dept].concat(g.destinations || []) : (g.destinations || []);

  var h = '<div class="page" id="p-map">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">TRANSIT & ROUTE</span>';
  h += '<h2>山河经纬 · 路线总览</h2>';
  h += '<p>自 ' + (dept ? esc(dept) : '始发站') + ' 起行，经络相连，全线可一键唤起高德地图路线规划</p>';
  h += '</div>';

  h += '<div class="route-summary-bar">';
  allStops.forEach(function(s, idx) {
    if (idx > 0) h += '<span class="route-arrow">➔</span>';
    h += '<span class="route-stop-node">' + esc(s) + '</span>';
  });
  h += '</div>';

  h += '<div class="map-container-box"><div id="amap-container"></div></div>';
  h += '<p class="map-tip-footer">提示：点击地图中的城市标点，可直接在手机/网页端开启高德驾车或公共交通导航规划。</p>';
  h += '</div>';
  return h;
}

/* ── TAB 3: 每日行程 ── */
function rDays(g) {
  var h = '<div class="page" id="p-days">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">ITINERARY</span>';
  h += '<h2>逐日动线 · 每日行程</h2>';
  h += '<p>晨光、午后与向晚的细致编排，每个点位皆含一键高德导航</p>';
  h += '</div>';

  h += '<div class="timeline-list">';
  ((g.route || {}).daily_plan || []).forEach(function(d) {
    var dayFormatted = d.day < 10 ? '0' + d.day : d.day;
    h += '<div class="itinerary-day-card tilt-card">';
    h += '<div class="card-sheen"></div>';
    h += '<div class="day-badge-col">';
    h += '<div class="day-number-serif">' + dayFormatted + '</div>';
    h += '<span class="day-city-pill">' + esc(d.city || '') + '</span>';
    h += '</div>';

    h += '<div class="day-activities-col">';
    [
      { k: 'morning', t: '上午' },
      { k: 'afternoon', t: '下午' },
      { k: 'evening', t: '向晚' }
    ].forEach(function(act) {
      if (d[act.k] && d[act.k].name) {
        h += '<div class="act-time-block">';
        h += '<span class="act-time-label">' + act.t + '</span>';
        h += '<div class="act-content-wrap">';
        h += '<h4>' + esc(d[act.k].name) + '</h4>';
        if (d[act.k].note) {
          h += '<p>' + esc(d[act.k].note) + '</p>';
        }
        h += '</div>';
        h += nav(d.city || '', d[act.k].name, d[act.k].coordinate);
        h += '</div>';
      }
    });

    if (d.stay) {
      h += '<div class="stay-hotel-bar">';
      h += '<div class="hotel-info">' + ICONS.hotel + ' <b>下榻宿处：</b>' + esc(d.stay) + '</div>';
      h += nav(d.city || '', d.stay, d.stay_coordinate);
      h += '</div>';
    }

    h += '</div></div>';
  });

  var trans = (g.route || {}).transport || [];
  if (trans.length) {
    h += '<div style="margin-top:24px"><h3 style="font-family:var(--font-serif-cn);font-size:1.15em;margin-bottom:12px;">交通接驳</h3>';
    trans.forEach(function(t) {
      var navBtn = '';
      if (t.from_coord && t.to_coord && t.from_coord.length === 2 && t.to_coord.length === 2) {
        navBtn = '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/navigation?from=' + t.from_coord.join(',') + ',' + encodeURIComponent(t.from || '') + '&to=' + t.to_coord.join(',') + ',' + encodeURIComponent(t.to || '') + '&mode=car&src=shanhe&coordinate=gaode&callnative=0" target="_blank" rel="noopener">' + ICONS.nav + ' <span>段内导航</span></a>';
      }
      h += '<div class="transit-segment-card">';
      h += '<div class="transit-desc">' + ICONS.transit + ' <b>' + esc(t.from || '') + ' ➔ ' + esc(t.to || '') + '</b><span>' + esc(t.mode || '') + ' · ' + esc(t.duration || '') + '</span></div>';
      h += '<div style="display:flex;align-items:center;gap:12px"><span class="transit-cost">¥' + (t.cost_est || 0) + '</span>' + navBtn + '</div>';
      h += '</div>';
    });
    h += '</div>';
  }

  h += '</div></div>';
  return h;
}

/* ── TAB 4: 景点图鉴 ── */
function rSpots(g) {
  var h = '<div class="page" id="p-spots">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">DISCOVER</span>';
  h += '<h2>风月留胜 · 精选名胜</h2>';
  h += '<p>典藏级人文胜地、独家摄影机位与实战避坑建议</p>';
  h += '</div>';

  if (!(g.spots || []).length) {
    return h + '<p style="text-align:center;color:var(--ink-muted)">暂无景点数据</p></div>';
  }

  h += '<div class="spots-grid">';
  (g.spots || []).forEach(function(s) {
    var tierLabel = { 1: '必访典藏', 2: '深度探寻', 3: '秘境发现' }[s.tier] || '推荐参访';
    var tierClass = 'tier-badge-' + (s.tier || 1);

    h += '<div class="spot-editorial-card tilt-card">';
    h += '<div class="card-sheen"></div>';
    h += '<div class="spot-cover-wrap">';
    h += imgTag(s.photo, s.name + '-china', 600, 380, s.name, 'spot-cover-img');
    h += '<span class="spot-tier-badge ' + tierClass + '">' + tierLabel + '</span>';
    h += '</div>';

    h += '<div class="spot-card-body">';
    h += '<div class="sc-header-row">';
    h += '<h3 class="sc-title">' + esc(s.name) + '</h3>';
    h += '<span class="sc-price">' + (s.ticket ? '¥' + s.ticket : '免费') + '</span>';
    h += '</div>';

    h += '<div class="sc-meta-line">';
    h += '<span>' + esc(s.type || '观光名胜') + '</span> · <span>游玩 ' + esc(s.duration || '2小时') + '</span>';
    if (s.best_time) h += ' · <span>' + esc(s.best_time) + '</span>';
    h += '</div>';

    if ((s.tags || []).length) {
      h += '<div class="sc-tags-row">';
      s.tags.slice(0, 4).forEach(function(t) {
        h += '<span class="sc-tag">' + esc(t) + '</span>';
      });
      h += '</div>';
    }

    if ((s.photo_spots || []).length) {
      h += '<div class="sc-photo-box">';
      s.photo_spots.slice(0, 2).forEach(function(p) {
        h += '<div><b>最佳机位：</b>' + esc(p.name || '') + (p.best_time ? ' (' + esc(p.best_time) + ')' : '') + '</div>';
      });
      h += '</div>';
    }

    if (s.tips) {
      h += '<div class="sc-tip-box">' + esc(s.tips) + '</div>';
    }

    h += '<div class="spot-card-footer">';
    h += nav(s.city || (g.destinations || [])[0] || '', s.name, s.coordinate);
    h += '</div>';

    h += '</div></div>';
  });

  h += '</div></div>';
  return h;
}

/* ── TAB 5: 在地味道 ── */
function rFood(g) {
  var h = '<div class="page" id="p-food">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">CUISINE & FLAVORS</span>';
  h += '<h2>寻味市井 · 地道食单</h2>';
  h += '<p>老餮私藏的风味老字号与地道寻味指南</p>';
  h += '</div>';

  var total = 0;
  (g.cultures || []).forEach(function(c) {
    total += ((c.cuisine || {}).must_eat || []).length;
  });

  if (!total) {
    return h + '<p style="text-align:center;color:var(--ink-muted)">暂无美食数据</p></div>';
  }

  h += '<div class="food-grid">';
  (g.cultures || []).forEach(function(c) {
    ((c.cuisine || {}).must_eat || []).slice(0, 8).forEach(function(f) {
      h += '<div class="food-card tilt-card">';
      h += '<div class="card-sheen"></div>';
      h += '<div class="food-cover-wrap">';
      h += imgTag(f.photo, f.name || 'chinese-food', 600, 380, f.name || '美食', 'food-cover-img');
      h += '</div>';

      h += '<div class="fc-body">';
      h += '<h4 class="fc-title">' + esc(f.name || '') + '</h4>';
      h += '<p class="fc-reason">' + esc(f.reason || '') + '</p>';

      h += '<div class="fc-details-box">';
      if (f.where) h += '<div class="fc-where">📍 ' + esc(f.where) + '</div>';
      h += '<div class="fc-price-tag">人均 ¥' + (f.price_per_person || 30) + '</div>';
      h += '</div>';

      if (f.tips) {
        h += '<div class="fc-tips">💡 ' + esc(f.tips) + '</div>';
      }

      h += '<div class="food-card-footer">';
      h += nav(c.city || '', f.where || f.name || '', f.coordinate);
      h += '</div>';

      h += '</div></div>';
    });
  });

  h += '</div></div>';
  return h;
}

function fmtChips(v, label) {
  if (!v) return '';
  var items = Array.isArray(v) ? v : [v];
  var chips = items.map(function(x) {
    var s = (typeof x === 'string') ? x : ((x && (x.name || x.title)) || '');
    return s ? '<span class="sc-tag">' + esc(s) + '</span>' : '';
  }).join('');
  return chips ? '<div style="margin-top:10px"><b style="font-size:0.82em;color:var(--ink-title)">' + label + '</b> <div style="display:inline-flex;gap:4px;flex-wrap:wrap;margin-top:4px">' + chips + '</div></div>' : '';
}

/* ── TAB 6: 风土人情 ── */
function rCult(g) {
  var h = '<div class="page" id="p-culture">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">HERITAGE & LORE</span>';
  h += '<h2>文脉掌故 · 风土人情</h2>';
  h += '<p>在地乡音、岁月建筑、风俗礼仪与山河轶事</p>';
  h += '</div>';

  h += '<div class="culture-grid">';
  (g.cultures || []).forEach(function(c) {
    var fc = c.folk_culture || {};
    var dialects = fc.dialect || [];
    var taboos = c.taboos || [];
    var festivals = c.festivals || [];
    var history = c.history || [];

    h += '<div class="culture-card tilt-card">';
    h += '<div class="card-sheen"></div>';
    h += '<div class="culture-city-head">';
    h += '<h3>' + ICONS.culture + ' <span>' + esc(c.city || '在地风物') + '</span></h3>';
    h += '</div>';

    if (fc.architecture) {
      h += '<div class="cult-sec">';
      h += '<div class="cult-sec-title">建筑空间风貌</div>';
      h += '<p class="cult-p">' + esc(fc.architecture) + '</p>';
      h += '</div>';
    }

    if (dialects.length) {
      h += '<div class="cult-sec">';
      h += '<div class="cult-sec-title">地道方言速学</div>';
      h += '<div class="dialect-chips-wrap">';
      dialects.slice(0, 4).forEach(function(d) {
        h += '<div class="dialect-card-chip magnetic-elem">';
        h += '<span class="dialect-phrase">' + esc(d.phrase || '') + '</span>';
        if (d.pinyin) h += '<span class="dialect-pinyin">(' + esc(d.pinyin) + ')</span>';
        if (d.explain) h += '<div style="font-size:0.75em;color:var(--ink-muted);margin-top:2px">' + esc(d.explain) + '</div>';
        h += '</div>';
      });
      h += '</div></div>';
    }

    h += fmtChips((c.cuisine || {}).night_market, '夜市烟火');
    h += fmtChips((c.cuisine || {}).souvenir, '伴手礼风物');

    if (taboos.length) {
      h += '<div class="cult-sec" style="margin-top:14px">';
      h += '<div class="cult-sec-title">风俗禁忌与礼仪</div>';
      taboos.slice(0, 3).forEach(function(t) {
        h += '<div class="taboo-callout">' + esc(t.rule || '') + '</div>';
      });
      h += '</div>';
    }

    if (festivals.length) {
      h += '<div class="cult-sec" style="margin-top:14px">';
      h += '<div class="cult-sec-title">岁时民俗节庆</div>';
      festivals.slice(0, 2).forEach(function(f) {
        h += '<p class="cult-p" style="margin-bottom:4px"><b>' + esc(f.name || '') + '</b>（' + esc(f.date || '') + '）：' + esc(f.what_to_see || '') + '</p>';
      });
      h += '</div>';
    }

    if (history.length) {
      h += '<div class="cult-sec" style="margin-top:14px">';
      h += '<div class="cult-sec-title">山河典故与文脉</div>';
      history.slice(0, 2).forEach(function(x) {
        h += '<div class="story-block">📜 ' + esc(x.story || '') + '</div>';
      });
      h += '</div>';
    }

    h += '</div>';
  });

  h += '</div></div>';
  return h;
}

/* ── TAB 7: 天气与着装 ── */
function rWeather(g) {
  var h = '<div class="page" id="p-weather">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">CLIMATE & WEAR</span>';
  h += '<h2>四时晴雨 · 气象与着装</h2>';
  h += '<p>掌握温差起伏，从容打包行囊</p>';
  h += '</div>';

  if (g.clothing_tip) {
    h += '<div class="clothing-banner">';
    h += '<div class="cb-icon">' + ICONS.weather + '</div>';
    h += '<div><b>穿衣锦囊：</b>' + esc(g.clothing_tip) + '</div>';
    h += '</div>';
  }

  if (!(g.weather || []).length) {
    h += '<div class="clothing-banner"><div class="cb-icon">' + ICONS.sun + '</div><div>暂无实时天气（未配置 AMAP_WEATHER_KEY 或网络查询失败，建议按季节备好常备衣物）</div></div>';
  } else {
    h += '<div class="weather-cards-grid">';
    (g.weather || []).forEach(function(w) {
      h += '<div class="weather-city-card tilt-card">';
      h += '<div class="card-sheen"></div>';
      h += '<div class="wcc-city"><h4>' + esc(w.city || '目的地') + '</h4><span class="wcc-badge">近期预报</span></div>';
      (w.forecast || []).slice(0, 4).forEach(function(f) {
        var isRain = f.dayweather && f.dayweather.indexOf('雨') > -1;
        var icon = isRain ? ICONS.rain : ((f.dayweather && f.dayweather.indexOf('云') > -1) ? ICONS.cloud : ICONS.sun);
        h += '<div class="w-forecast-row">';
        h += '<div class="w-date-col">' + (f.date || '').slice(-5) + ' ' + (f.week || '') + '</div>';
        h += '<div class="w-weather-col"><span>' + icon + '</span><span>' + esc(f.dayweather || '晴') + '</span></div>';
        h += '<div class="w-temp-col">' + (f.nighttemp || '-') + '° ~ ' + (f.daytemp || '-') + '°C</div>';
        h += '</div>';
      });
      h += '</div>';
    });
    h += '</div>';
  }

  h += '</div>';
  return h;
}

/* ── TAB 8: 预算分项与微调 ── */
function rBudg(g) {
  var b = g.budget || {};
  var total = b.total || 1;
  var days = g.days || 1;
  var perDay = Math.round(total / days);

  var h = '<div class="page" id="p-budget">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">FINANCES & TUNING</span>';
  h += '<h2>游资盘点 · 预算与微调</h2>';
  h += '<p>清晰透明的各项开支测算与灵活定制入口</p>';
  h += '</div>';

  h += '<div class="budget-overview-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<div class="budget-total-headline">';
  h += '<div class="bth-label">预估人均总预算 · ' + esc(g.budget_level || '舒适度') + '</div>';
  h += '<div class="bth-amount">¥' + total + '</div>';
  h += '<div class="bth-daily">约 ¥' + perDay + ' / 天 · 共 ' + days + ' 天</div>';
  h += '</div>';

  var categories = [
    { l: '跨城交通', v: b.transport || 0, c: '#234339' },
    { l: '住宿旅居', v: b.accommodation || 0, c: '#366E67' },
    { l: '景点门票', v: b.tickets || 0, c: '#B88B42' },
    { l: '地道餐饮', v: b.food || 0, c: '#C3643B' },
    { l: '备用机动', v: b.other || 0, c: '#74817C' }
  ];

  categories.forEach(function(cat) {
    var pct = Math.max((cat.v / total) * 100, 2);
    h += '<div class="budget-bar-row">';
    h += '<span class="bbr-label">' + cat.l + '</span>';
    h += '<div class="bbr-track"><div class="bbr-fill" style="width:' + pct + '%;background:' + cat.c + '"></div></div>';
    h += '<span class="bbr-val">¥' + cat.v + '</span>';
    h += '</div>';
  });

  var warnings = (g.route || {}).warnings || [];
  if (warnings.length) {
    h += '<div class="warn-callout-box">';
    h += '<h4>行前必读与避坑指引</h4>';
    h += '<ul>';
    warnings.forEach(function(w) {
      h += '<li>' + esc(w) + '</li>';
    });
    h += '</ul></div>';
  }

  h += '</div>';

  h += '<div class="finetune-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<h3>还想针对路线进行个性化微调？</h3>';
  h += '<p>点击下方快捷选项，一键重设需求并重新生成：</p>';
  h += '<div class="finetune-chips-wrap">';
  ['加一天深度游', '节奏再慢一点', '寻找周边避世秘境', '高性价比穷游版', '多安排些特色美食'].forEach(function(tip) {
    h += '<button class="finetune-chip magnetic-elem" onclick="applyPreset(\'' + tip + '\')">' + tip + '</button>';
  });
  h += '</div>';
  h += '</div>';

  h += '</div>';
  return h;
}

/* ── 交互过滤器监听 ── */
function setupFilterListeners() {
  document.querySelectorAll('.filter-pills').forEach(function(group) {
    group.addEventListener('click', function(e) {
      var btn = e.target.closest('.f-pill');
      if (!btn) return;
      group.querySelectorAll('.f-pill').forEach(function(c) { c.classList.remove('active'); });
      btn.classList.add('active');

      var daysBtn = document.querySelector('[data-key="days"] .f-pill.active');
      var themeBtn = document.querySelector('[data-key="theme"] .f-pill.active');
      var inp = document.getElementById('query-input');
      if (inp) {
        var base = inp.value.trim();
        var dVal = daysBtn ? daysBtn.getAttribute('data-val').replace(/慢行|周末|深度|长假/g, '') : '3天';
        var tVal = themeBtn ? themeBtn.getAttribute('data-val') : '人文历史';
        if (base) {
          if (base.indexOf('天') > -1) {
            base = base.replace(/\d+天/g, dVal);
          } else {
            base += dVal;
          }
          if (base.indexOf('喜欢') > -1) {
            base = base.replace(/喜欢.*/g, '喜欢' + tVal);
          } else {
            base += '，喜欢' + tVal;
          }
          inp.value = base;
          updateClearBtn();
        }
      }
    });
  });

  var inp = document.getElementById('query-input');
  if (inp) {
    inp.addEventListener('input', updateClearBtn);
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        startGenerate();
      }
    });
  }
}

/* ── 启动初始化 ── */
window.addEventListener('DOMContentLoaded', function() {
  guide = null;
  renderAll();
  setupFilterListeners();
  updateClearBtn();

  // 启动物理动效
  initInkRipple();
  initZenCanvas();
  initMouseEffects();
  attach3DTiltCards();
  attachMagneticElements();
});
