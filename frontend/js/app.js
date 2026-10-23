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
  rain: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16" y1="13" x2="16" y2="21"/><line x1="8" y1="13" x2="8" y2="21"/><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/></svg>',
  prep: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 12h18"/></svg>'
};

var PAGES = [
  { id: 'home', l: '概览', icon: ICONS.home },
  { id: 'map', l: '路线', icon: ICONS.map },
  { id: 'days', l: '日程', icon: ICONS.days },
  { id: 'spots', l: '景点', icon: ICONS.spots },
  { id: 'food', l: '风味', icon: ICONS.food },
  { id: 'culture', l: '民俗', icon: ICONS.culture },
  { id: 'weather', l: '气象', icon: ICONS.weather },
  { id: 'budget', l: '预算', icon: ICONS.budget },
  { id: 'prep', l: '行前', icon: ICONS.prep }
];

var guide = null;
var activeGenerationController = null;
var amap = null;
var page = 0;
var mapDayFilter = null;
var mapActivityMarkers = [];
var mapCityMarkers = [];
var mapRouteLines = [];
var modelProfilesCache = [];
var modelCredentialStoreAvailable = false;
var modelDiagnosticResults = Object.create(null);
var modelProfileDiagnosticRevisions = Object.create(null);
var modelDiagnosticRunTokens = Object.create(null);
var deepSeekSearchProfiles = [];
var MODEL_PROVIDER_PRESETS = {
  custom: { protocol: 'openai_compatible', base_url: 'http://127.0.0.1:15721/v1', model: 'deepseek-v4-flash' },
  deepseek: { protocol: 'openai_compatible', base_url: 'https://api.deepseek.com', model: 'deepseek-flash' },
  qwen: { protocol: 'openai_compatible', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { protocol: 'openai_compatible', base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-5-turbo' },
  moonshot: { protocol: 'openai_compatible', base_url: 'https://api.moonshot.cn/v1', model: 'kimi-k2.6' },
  doubao: { protocol: 'openai_compatible', base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-seed-2-1-pro-260915' },
  anthropic: { protocol: 'anthropic', base_url: 'https://api.anthropic.com', model: 'claude-sonnet-4-6' },
  gemini: { protocol: 'google_genai', base_url: 'https://generativelanguage.googleapis.com', model: 'gemini-3.8-flash' }
};
var MODEL_PROVIDER_NAMES = {
  custom: '自定义', deepseek: 'DeepSeek', qwen: 'Qwen / DashScope', glm: 'GLM',
  moonshot: 'Moonshot / Kimi', doubao: '豆包 / 火山方舟', anthropic: 'Claude', gemini: 'Gemini'
};
var MODEL_PROTOCOL_NAMES = {
  openai_compatible: 'OpenAI 兼容', anthropic: 'Anthropic 原生', google_genai: 'Google GenAI 原生'
};

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
  h += '<p class="empty-desc">当前尚未生成专属旅行路线。请在开场主屏输入您心仪的目的地与旅行偏好，点击「生成专属攻略」，AI 编排引擎将实时为您深度生成涵盖路线、日程、景点机位、特色风味、在地民俗、气象、预算、行程可执行性与行前准备的 9 大维度画报。</p>';
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
  return '/js/placeholder-landscape.svg';
}

function photoSourceLabel(source) {
  return ({
    amap_poi_photo: '高德 POI 图片',
    wikimedia_commons: 'Wikimedia 图片',
    static_map: '位置示意图 · 非实景',
    deepseek_web_image: '网页图片 · 内容与授权未核验',
    local_unknown: '本地图片 · 来源未核实',
    none: '暂无实景图'
  })[source || 'none'] || '图片来源待核实';
}

function sourceTimestamp(value) {
  if (!value) return '';
  var date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '';
  if (window.Intl && Intl.DateTimeFormat) {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'
    }).format(date);
  }
  return String(value).slice(0, 10);
}

function webTimestamp(value) {
  if (!value) return '';
  var date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '';
  if (window.Intl && Intl.DateTimeFormat) {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    }).format(date);
  }
  return String(value).replace('T', ' ').slice(0, 16);
}

function safeWebUrl(value) {
  if (!value || /[\u0000-\u0020]/.test(String(value))) return '';
  try {
    var url = new URL(String(value));
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return '';
    var host = url.hostname.toLowerCase().replace(/^\[|\]$/g, '');
    if (host === 'localhost' || /\.(localhost|local|internal|test)$/.test(host)) return '';
    if (/^(10\.|127\.|169\.254\.|192\.168\.|0\.)/.test(host) ||
        /^172\.(1[6-9]|2\d|3[01])\./.test(host) || host === '::1' || host === '::') return '';
    url.hash = '';
    return url.href;
  } catch (_error) {
    return '';
  }
}

function webSourceLink(label, value, className) {
  var url = safeWebUrl(value);
  if (!url) return '<span class="web-source-invalid">来源链接无效</span>';
  return '<a' + (className ? ' class="' + className + '"' : '') +
    ' href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(label || '网页来源') + '</a>';
}

function webResearchStatusText(status) {
  return ({
    disabled: '联网检索已关闭，本景点未发起 Search/Fetch。',
    unavailable: '联网检索已启用，但 Search 凭据不可用，本景点未检索。',
    skipped_limit: '超过本次 3 个景点上限，未检索。',
    no_city_match: '未找到能匹配城市名的搜索结果；未采纳票价或图片。',
    no_spot_match: '同城结果未匹配景点名称；未采纳票价或图片。',
    page_unmatched: '抓取正文未匹配目标城市和景点；该页票价与图片未采纳。',
    no_results: '本次未检索到结果。',
    error: '联网检索遇到问题，本景点资料待核实。'
  })[status || 'disabled'] || '';
}

function webEvidenceHtml(guideData, spot, spotIndex) {
  var research = guideData.web_research || {};
  var spotResearch = (research.spots || []).find(function(item) {
    return Number(item.spot_index) === Number(spotIndex);
  });
  var evidence = spotResearch && Array.isArray(spotResearch.evidence) ? spotResearch.evidence : [];
  var h = '<div class="web-evidence-panel">';
  h += '<strong>网页线索 · 未作官方核验</strong>';
  if (!evidence.length) {
    var state = spotResearch ? spotResearch.status : research.status;
    h += '<p>' + esc(webResearchStatusText(state)) + '</p></div>';
    return h;
  }
  evidence.slice(0, 3).forEach(function(item) {
    h += '<div class="web-evidence-item">';
    h += '<div class="web-evidence-source">' + webSourceLink(item.title || '网页来源', item.url) + '</div>';
    h += '<p class="web-evidence-meta">' +
      (item.fetched_at ? '抓取于 ' + esc(webTimestamp(item.fetched_at)) : '搜索结果，未抓取正文') +
      ' · 城市匹配线索，景点关联和来源机构仍需核对</p>';
    if (item.snippet) h += '<p class="web-evidence-snippet"><b>搜索摘要：</b>' + esc(item.snippet) + '</p>';
    if ((item.price_quotes || []).length) {
      h += '<div class="web-price-leads"><b>网页票价线索（不计入预算）</b><small>票种、日期与适用条件待核实</small><ul>';
      item.price_quotes.slice(0, 5).forEach(function(line) { h += '<li>' + esc(line) + '</li>'; });
      h += '</ul></div>';
    }
    if ((item.quotes || []).length) {
      h += '<details class="web-evidence-quotes"><summary>查看 ' + item.quotes.length + ' 条页面摘录</summary><ul>';
      item.quotes.slice(0, 8).forEach(function(line) { h += '<li>' + esc(line) + '</li>'; });
      h += '</ul></details>';
    }
    if (item.fetch_status === 'mismatch') {
      h += '<p class="web-evidence-warning">抓取正文与目标景点不匹配，正文中的票价和图片未采纳。</p>';
    }
    var images = Array.isArray(item.image_candidates) ? item.image_candidates : [];
    if (images.length) {
      h += '<div class="web-image-leads"><b>来源页图片候选</b><small>图片内容、景点关联及使用授权未核验</small><ul>';
      images.slice(0, 5).forEach(function(candidate) {
        var label = candidate.alt || '查看网页图片候选';
        h += '<li>' + webSourceLink(label, candidate.url);
        if (candidate.local_url && /^\/static\/photos\/web-research\/[a-f0-9]{64}\.(jpg|png|webp|gif)$/.test(candidate.local_url)) {
          h += ' · <a href="' + esc(candidate.local_url) + '" target="_blank" rel="noopener noreferrer">本机安全缓存图</a>';
        } else {
          h += ' <span class="web-image-fallback">（下载未成功，保留来源页图片链接）</span>';
        }
        h += '</li>';
      });
      h += '</ul></div>';
    } else if (item.status === 'fetched') {
      h += '<p class="web-evidence-meta">来源页未提取到可用图片链接，未使用网站图标代替景点照片。</p>';
    }
    h += '</div>';
  });
  h += '</div>';
  return h;
}

function generationRuntimeLabel(metrics) {
  metrics = metrics || {};
  var elapsed = Number(metrics.elapsed_ms);
  var seconds = Number.isFinite(elapsed) ? (elapsed / 1000).toFixed(1) + ' 秒' : '未知';
  var llm = metrics.llm || {};
  var tokens;
  if (llm.total_tokens != null) {
    tokens = '模型 Token ' + Number(llm.total_tokens).toLocaleString('zh-CN');
  } else if (llm.input_tokens != null || llm.output_tokens != null) {
    tokens = '模型 Token 输入 ' + (llm.input_tokens == null ? '未知' : Number(llm.input_tokens).toLocaleString('zh-CN')) +
      ' / 输出 ' + (llm.output_tokens == null ? '未知' : Number(llm.output_tokens).toLocaleString('zh-CN'));
  } else {
    tokens = '模型用量未知';
  }
  return '生成耗时 ' + seconds + ' · ' + tokens;
}

function photoSourceDetail(source, checkedAt) {
  var label = photoSourceLabel(source);
  var date = sourceTimestamp(checkedAt);
  if (date && source !== 'local_unknown' && source !== 'none') label += ' · 获取于 ' + date;
  return label;
}

function coordinateSourceDetail(verified, source, checkedAt) {
  if (!verified || source !== 'amap_poi') return '位置待核验';
  var date = sourceTimestamp(checkedAt);
  return '高德 POI 坐标已核验' + (date ? ' · ' + date : '') + '（仅位置）';
}

function nav(city, place, coord, verified) {
  if (verified && isValidAmapCoordinate(coord)) {
    var to = coord[0] + ',' + coord[1] + ',' + encodeURIComponent(place || city || '目的地');
    return '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/navigation?to=' + to + '&mode=car&policy=1&src=shanhe&coordinate=gaode&callnative=0" target="_blank" rel="noopener">' + ICONS.nav + ' <span>导航</span></a>';
  }
  return '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/search?keyword=' + encodeURIComponent((city || '') + ' ' + (place || '')) + '" target="_blank" rel="noopener">' + ICONS.nav + ' <span>导航</span></a>';
}

function isValidAmapCoordinate(coord) {
  return Array.isArray(coord) && coord.length === 2 &&
    Number.isFinite(Number(coord[0])) && Number.isFinite(Number(coord[1])) &&
    Number(coord[0]) >= 73 && Number(coord[0]) <= 135 &&
    Number(coord[1]) >= 3 && Number(coord[1]) <= 54;
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

async function copyGuideHighlights() {
  if (!guide) {
    showToast('尚未生成攻略，请先定制行程');
    return;
  }
  var text = '【山河游记 · ' + (guide.title || '') + '】\n' +
    '📍 目的地：' + (guide.destinations || []).join(' ➔ ') + '\n' +
    '📅 天数：' + (guide.days || 0) + '天 | 人均已知费用小计：约¥' + ((guide.budget || {}).total || 0) + '\n' +
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

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      showToast('✓ 攻略摘要已复制到剪贴板');
      return;
    }
    var helper = document.createElement('textarea');
    helper.value = text;
    helper.setAttribute('readonly', '');
    helper.style.position = 'fixed';
    helper.style.opacity = '0';
    document.body.appendChild(helper);
    helper.select();
    var copied = document.execCommand && document.execCommand('copy');
    helper.remove();
    showToast(copied ? '✓ 攻略摘要已复制到剪贴板' : '复制失败，请检查浏览器剪贴板权限。');
  } catch (error) {
    showToast('复制失败，请检查浏览器剪贴板权限。');
  }
}

function closeAppDialog(id) {
  var dialog = document.getElementById(id);
  if (dialog && dialog.open) dialog.close();
}

function showExportOptions() {
  if (!guide) {
    showToast('尚未生成攻略，请先定制行程');
    return;
  }
  var dialog = document.getElementById('guide-export-dialog');
  if (dialog && !dialog.open) dialog.showModal();
}

function safeGuideFilename(extension) {
  var title = String((guide && guide.title) || '山河游记攻略').replace(/[《》]/g, '');
  title = title.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').trim().slice(0, 72) || '山河游记攻略';
  return title + '.' + extension;
}

function downloadGuideBlob(blob, filename) {
  var url = URL.createObjectURL(blob);
  var anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
}

function exportGuideJson() {
  if (!guide) return showToast('尚未生成攻略');
  try {
    var json = JSON.stringify(guide, null, 2);
    downloadGuideBlob(new Blob([json], { type: 'application/json;charset=utf-8' }), safeGuideFilename('json'));
    closeAppDialog('guide-export-dialog');
    showToast('JSON 攻略已开始下载');
  } catch (error) {
    showToast('JSON 导出失败，请重试。');
  }
}

async function exportGuideMarkdown() {
  if (!guide) return showToast('尚未生成攻略');
  try {
    var response = await fetch('/api/export/markdown', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(guide)
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    downloadGuideBlob(await response.blob(), safeGuideFilename('md'));
    closeAppDialog('guide-export-dialog');
    showToast('Markdown 攻略已开始下载');
  } catch (error) {
    showToast('Markdown 导出失败，请重试。');
  }
}

function printGuide() {
  if (!guide) {
    showToast('尚未生成攻略，请先定制行程后再导出打印');
    return;
  }
  closeAppDialog('guide-export-dialog');
  window.print();
}

async function showGuideHistory() {
  var dialog = document.getElementById('guide-history-dialog');
  var list = document.getElementById('guide-history-list');
  if (!dialog || !list) return;
  list.textContent = '正在读取历史…';
  if (!dialog.open) dialog.showModal();
  try {
    var response = await fetch('/api/history');
    var payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || '本机历史暂不可用');
    var items = payload.items || [];
    if (!items.length) {
      list.innerHTML = '<p class="guide-history-empty">还没有保存过攻略。生成成功后会自动保存在本机。</p>';
      return;
    }
    list.innerHTML = items.map(function(item) {
      var title = esc(item.title || '未命名攻略');
      var destinations = esc((item.destinations || []).join(' · ') || '目的地未注明');
      var timestamp = esc(sourceTimestamp(item.saved_at) || '');
      var days = Number(item.days || 0);
      var id = encodeURIComponent(String(item.id || ''));
      return '<button type="button" class="guide-history-item" onclick="loadGuideHistory(\'' + id + '\')">' +
        '<span class="guide-history-title">' + title + '</span>' +
        '<span class="guide-history-meta">' + destinations + ' · ' + days + '天 · 保存于 ' + timestamp + '</span>' +
        '</button>';
    }).join('');
  } catch (error) {
    list.textContent = error.message || '读取历史失败，请重试。';
  }
}

async function loadGuideHistory(historyId) {
  if (activeGenerationController) {
    showToast('请先停止正在运行的生成任务，再打开历史攻略。');
    return;
  }
  try {
    var response = await fetch('/api/history/' + encodeURIComponent(historyId));
    var previousGuide = await response.json();
    if (!response.ok) throw new Error(previousGuide.detail || '攻略历史不存在');
    guide = previousGuide;
    mapDayFilter = null;
    closeAppDialog('guide-history-dialog');
    renderAll();
    switchPage(0);
    showToast('已打开本机历史攻略');
  } catch (error) {
    showToast(error.message || '加载历史攻略失败。');
  }
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
      if (!cfg.amap_key) {
        setMapStatus('尚未配置高德 JS API Key。可在“模型与服务设置”中填写，或继续使用上方文本路线。');
        return null;
      }
      window._AMapSecurityConfig = { securityJsCode: cfg.amap_security_code || '' };
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
      setMapStatus('高德地图暂不可用；路线文字仍可查看，点位导航会使用地点搜索。');
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

/* ── LangChain 模型配置 ── */
async function modelApi(url, options) {
  var response = await fetch(url, options || {});
  var data = {};
  try { data = await response.json(); } catch (e) {}
  if (!response.ok) {
    var detail = data.detail || ('HTTP ' + response.status);
    if (Array.isArray(detail)) detail = '配置字段无效，请检查填写内容';
    throw new Error(detail);
  }
  return data;
}

function renderModelProfileList() {
  var root = document.getElementById('model-profile-list');
  if (!root) return;
  if (!modelProfilesCache.length) {
    root.innerHTML = '<div class="model-profile-empty"><span>山河初启</span><p>还没有模型配置。创建一份配置后即可在生成时选择，也可以设为默认配置。</p></div>';
    return;
  }
  root.innerHTML = modelProfilesCache.map(function(profile) {
    var badges = [];
    if (profile.is_default) badges.push('<span class="profile-badge profile-badge-default">默认</span>');
    if (profile.session_only) badges.push('<span class="profile-badge">仅本次运行</span>');
    badges.push('<span class="profile-badge ' + (profile.has_key ? 'profile-badge-key' : '') + '">' + (profile.has_key ? '密钥已配置' : '未配置密钥') + '</span>');
    var diagnosis = modelDiagnosticResults[profile.profile_id] || {};
    function diagnosisText(result, title) {
      if (!result) return '';
      var stateClass = result.ok === null ? 'is-running' : (result.ok ? 'is-success' : 'is-failure');
      return '<p class="profile-diagnostic-line ' + stateClass + '">' +
        esc(title + '：' + result.message) + '</p>';
    }
    return '<article class="model-profile-card">' +
      '<div class="model-profile-card-main"><div class="model-profile-card-title"><h4>' + esc(profile.name) + '</h4>' + badges.join('') + '</div>' +
      '<p>' + esc(MODEL_PROVIDER_NAMES[profile.provider] || profile.provider || '自定义') + ' <span>·</span> ' + esc(MODEL_PROTOCOL_NAMES[profile.protocol] || profile.protocol || 'OpenAI 兼容') + '</p>' +
      '<p>' + esc(profile.model) + ' <span>·</span> ' + esc(profile.base_url) + '</p>' +
      (diagnosisText(diagnosis.connection, '本次连接诊断') || '<p class="profile-diagnostic-line">连接诊断：未实测</p>') +
      (diagnosisText(diagnosis.structured, '本次结构化诊断') || '<p class="profile-diagnostic-line">结构化能力：未实测</p>') + '</div>' +
      '<div class="model-profile-card-actions">' +
      '<button type="button" data-profile-action="connection-test" data-profile-id="' + esc(profile.profile_id) + '">测试连接</button>' +
      '<button type="button" data-profile-action="structured-test" data-profile-id="' + esc(profile.profile_id) + '">测试结构化</button>' +
      (profile.is_default ? '' : '<button type="button" data-profile-action="default" data-profile-id="' + esc(profile.profile_id) + '">设为默认</button>') +
      '<button type="button" data-profile-action="edit" data-profile-id="' + esc(profile.profile_id) + '">编辑</button>' +
      (profile.has_key ? '<button type="button" class="profile-action-warn" data-profile-action="clear" data-profile-id="' + esc(profile.profile_id) + '">清除密钥</button>' : '') +
      '<button type="button" class="profile-action-warn" data-profile-action="delete" data-profile-id="' + esc(profile.profile_id) + '">删除</button>' +
      '</div></article>';
  }).join('');
}

function invalidateModelProfileDiagnostics(profileId) {
  if (!profileId) return;
  modelProfileDiagnosticRevisions[profileId] = (modelProfileDiagnosticRevisions[profileId] || 0) + 1;
  delete modelDiagnosticResults[profileId];
  renderModelProfileList();
}

async function reloadModelProfiles() {
  var status = document.getElementById('model-credential-status');
  try {
    var data = await modelApi('/api/model-profiles');
    var select = document.getElementById('model-profile-select');
    var previous = select ? select.value : '';
    modelProfilesCache = data.profiles || [];
    modelCredentialStoreAvailable = Boolean(data.credential_store_available);
    renderModelProfileList();
    if (select) {
      select.innerHTML = '<option value="">默认配置 / 环境变量</option>' + modelProfilesCache.map(function(profile) {
        return '<option value="' + esc(profile.profile_id) + '">' + esc(profile.name) + (profile.is_default ? '（默认）' : '') + '</option>';
      }).join('');
      var retained = modelProfilesCache.some(function(profile) { return profile.profile_id === previous; });
      select.value = retained ? previous : (data.default_profile_id || '');
    }
    var hint = document.getElementById('model-profile-hint');
    if (hint) hint.textContent = data.default_profile_id ? '未选择时使用已设为默认的配置' : '未设置默认配置时使用 TRAVEL_LLM_* 环境变量';
    if (status) {
      status.className = 'model-credential-status ' + (modelCredentialStoreAvailable ? 'is-ready' : 'is-limited');
      status.textContent = modelCredentialStoreAvailable
        ? '系统凭据库可用：API Key 会保存在操作系统凭据管理器中。'
        : '系统凭据库不可用：如需填写 API Key，请明确勾选“仅本次运行使用”；密钥只保存在当前服务进程内。';
    }
    await refreshDeepSeekSearchProfiles();
  } catch (error) {
    if (status) {
      status.className = 'model-credential-status is-limited';
      status.textContent = '模型配置暂时无法读取：' + error.message;
    }
  }
}

async function refreshDeepSeekSearchProfiles() {
  var select = document.getElementById('deepseek-search-profile');
  if (!select) return;
  var previous = select.value;
  try {
    var response = await fetch('/api/deepseek-search-settings');
    var data = await response.json();
    if (!response.ok) return;
    deepSeekSearchProfiles = data.official_profiles || [];
    select.innerHTML = '<option value="">请选择已保存档案</option>' + deepSeekSearchProfiles.map(function(profile) {
      return '<option value="' + esc(profile.profile_id) + '">' + esc(profile.name) +
        (profile.has_key ? '' : '（无可用密钥）') + '</option>';
    }).join('');
    var retained = deepSeekSearchProfiles.some(function(profile) { return profile.profile_id === previous; });
    var selected = retained ? previous : (data.profile_id || '');
    select.value = deepSeekSearchProfiles.some(function(profile) { return profile.profile_id === selected; }) ? selected : '';
    var status = document.getElementById('deepseek-search-status');
    if (status && select.value && !deepSeekSearchProfiles.some(function(profile) {
      return profile.profile_id === select.value && profile.has_key;
    })) {
      status.textContent = '所选官方 DeepSeek 档案当前没有可用密钥；请补充密钥或选择其他档案。未保存的联网资料表单内容已保留。';
    }
  } catch (_error) {
    // Profile updates remain usable even when this optional status refresh fails.
  }
}

function showModelSettings() {
  var dialog = document.getElementById('model-settings-dialog');
  if (dialog && !dialog.open) dialog.showModal();
  reloadModelProfiles();
  loadAmapSettings();
  loadDeepSeekSearchSettings();
}

async function loadAmapSettings() {
  var status = document.getElementById('amap-settings-status');
  if (!status) return;
  try {
    var response = await fetch('/api/amap-settings');
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '读取失败');
    var configured = [];
    if (data.has_js_api_key) configured.push('JS Key');
    if (data.has_js_security_code) configured.push('JS 安全码');
    if (data.has_web_service_key) configured.push('Web 服务 Key');
    if (data.has_web_service_secret) configured.push('Web 签名密钥');
    status.className = 'model-credential-status ' + (data.credential_store_available ? 'is-ready' : 'is-limited');
    status.textContent = '当前可用：' + (configured.length ? configured.join('、') : '尚无高德配置') +
      (data.credential_store_available ? '。密钥由系统凭据库保护。' : '。系统凭据库不可用；请配置环境变量后重启服务。');
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '高德配置暂时无法读取：' + error.message;
  }
}

async function saveAmapSettings(event) {
  event.preventDefault();
  var status = document.getElementById('amap-settings-status');
  var fields = {
    js_api_key: document.getElementById('amap-js-key').value,
    js_security_code: document.getElementById('amap-js-security-code').value,
    web_service_key: document.getElementById('amap-web-key').value,
    web_service_secret: document.getElementById('amap-web-secret').value
  };
  try {
    var response = await fetch('/api/amap-settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields)
    });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '保存失败');
    document.getElementById('amap-settings-form').querySelectorAll('input[type="password"]').forEach(function(input) { input.value = ''; });
    status.className = 'model-credential-status is-ready';
    status.textContent = '高德配置已保存。密钥不会在页面中回显。';
    await loadAmapSettings();
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '保存失败：' + error.message;
  }
}

async function clearAmapSettings() {
  if (!window.confirm('清除保存在本机凭据库中的高德配置？服务将改用环境变量。')) return;
  var status = document.getElementById('amap-settings-status');
  try {
    var response = await fetch('/api/amap-settings', { method: 'DELETE' });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '清除失败');
    document.getElementById('amap-settings-form').reset();
    status.className = 'model-credential-status is-ready';
    status.textContent = '本地高德配置已清除，现改用环境变量。';
    await loadAmapSettings();
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '清除失败：' + error.message;
  }
}

function toggleDeepSeekSearchAuthFields() {
  var mode = document.getElementById('deepseek-search-auth-mode');
  if (!mode) return;
  var useProfile = mode.value === 'profile';
  document.getElementById('deepseek-search-profile-row').hidden = !useProfile;
  document.getElementById('deepseek-search-base-row').hidden = useProfile;
  document.getElementById('deepseek-search-key-row').hidden = useProfile;
  document.getElementById('deepseek-search-session-only').parentElement.hidden = useProfile;
}

async function loadDeepSeekSearchSettings() {
  var status = document.getElementById('deepseek-search-status');
  if (!status) return;
  try {
    var response = await fetch('/api/deepseek-search-settings');
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '读取失败');
    deepSeekSearchProfiles = data.official_profiles || [];
    var profileSelect = document.getElementById('deepseek-search-profile');
    var options = '<option value="">请选择已保存档案</option>';
    deepSeekSearchProfiles.forEach(function(profile) {
      options += '<option value="' + esc(profile.profile_id) + '">' + esc(profile.name) +
        (profile.has_key ? '' : '（无可用密钥）') + '</option>';
    });
    profileSelect.innerHTML = options;
    document.getElementById('deepseek-search-enabled').checked = Boolean(data.enabled);
    document.getElementById('deepseek-search-auth-mode').value = data.auth_mode || 'profile';
    profileSelect.value = data.profile_id || '';
    document.getElementById('deepseek-search-base-url').value = data.base_url || 'https://api.deepseek.com';
    document.getElementById('deepseek-search-key').value = '';
    document.getElementById('deepseek-search-session-only').checked = false;
    document.getElementById('deepseek-search-enabled').disabled = Boolean(data.enabled_overridden_by_environment);
    document.getElementById('deepseek-search-auth-mode').disabled = Boolean(data.auth_mode_overridden_by_environment);
    profileSelect.disabled = false;
    document.getElementById('deepseek-search-base-url').disabled = Boolean(data.base_url_overridden_by_environment);
    document.getElementById('deepseek-search-key').disabled = Boolean(data.key_overridden_by_environment);
    document.getElementById('deepseek-search-session-only').disabled = Boolean(data.key_overridden_by_environment);
    toggleDeepSeekSearchAuthFields();

    var modeLabel = data.auth_mode === 'profile' ? '官方 DeepSeek 档案' : '独立 Search Key';
    status.className = 'model-credential-status ' +
      (data.credential_store_available ? 'is-ready' : 'is-limited');
    status.textContent = (data.enabled ? '联网检索已启用' : '联网检索已关闭') +
      '；凭据来源：' + modeLabel + '；' + (data.has_key ? '密钥可用。' : '当前未检测到可用密钥。') +
      (data.base_url_overridden_by_environment ? ' 服务地址由环境变量覆盖。' : '') +
      (data.enabled_overridden_by_environment ? ' 联网开关由环境变量覆盖。' : '') +
      (data.auth_mode_overridden_by_environment ? ' 凭据来源由环境变量覆盖。' : '') +
      (data.key_overridden_by_environment ? ' 使用独立环境变量密钥。' : '') +
      (data.credential_store_available ? '独立密钥由系统凭据库保护。' : '系统凭据库不可用；新密钥需明确选择仅本次运行。');
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '联网检索设置暂时无法读取：' + error.message;
  }
}

async function saveDeepSeekSearchSettings(event) {
  event.preventDefault();
  var status = document.getElementById('deepseek-search-status');
  var apiKey = document.getElementById('deepseek-search-key').value;
  var payload = {
    enabled: document.getElementById('deepseek-search-enabled').checked,
    auth_mode: document.getElementById('deepseek-search-auth-mode').value,
    profile_id: document.getElementById('deepseek-search-profile').value || null,
    base_url: document.getElementById('deepseek-search-base-url').value,
    api_key: apiKey,
    session_only: document.getElementById('deepseek-search-session-only').checked
  };
  try {
    var response = await fetch('/api/deepseek-search-settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '保存失败');
    document.getElementById('deepseek-search-key').value = '';
    status.className = 'model-credential-status is-ready';
    status.textContent = '联网资料设置已保存。密钥不会在页面或状态接口中回显。';
    await loadDeepSeekSearchSettings();
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '保存失败：' + error.message;
  }
}

async function clearDeepSeekSearchSettings() {
  var status = document.getElementById('deepseek-search-status');
  try {
    var response = await fetch('/api/deepseek-search-settings', { method: 'DELETE' });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || '清除失败');
    document.getElementById('deepseek-search-settings-form').reset();
    document.getElementById('deepseek-search-base-url').value = 'https://api.deepseek.com';
    status.className = 'model-credential-status is-ready';
    await loadDeepSeekSearchSettings();
    status.textContent += ' 本地设置与系统凭据库中的独立 Key 已清除；环境变量值未改动。';
  } catch (error) {
    status.className = 'model-credential-status is-limited';
    status.textContent = '清除失败：' + error.message;
  }
}

function closeModelSettings() {
  var dialog = document.getElementById('model-settings-dialog');
  if (dialog && dialog.open) dialog.close();
}

function resetModelProfileForm() {
  var form = document.getElementById('model-profile-form');
  if (!form) return;
  form.reset();
  document.getElementById('model-profile-id').value = '';
  document.getElementById('model-profile-provider').value = 'custom';
  document.getElementById('model-profile-protocol').value = 'openai_compatible';
  document.getElementById('model-profile-url').value = 'http://127.0.0.1:15721/v1';
  document.getElementById('model-profile-model').value = 'deepseek-v4-flash';
  document.getElementById('model-profile-temperature').value = '';
  document.getElementById('model-profile-timeout').value = '60';
  document.getElementById('model-profile-retries').value = '1';
  document.getElementById('model-profile-max-tokens').value = '8192';
  document.getElementById('model-profile-structured').value = 'function_calling';
  refreshStructuredMethodOptions();
  document.getElementById('model-profile-session-only').disabled = false;
  document.getElementById('model-profile-session-only').checked = false;
  document.getElementById('model-profile-make-default').checked = false;
  document.getElementById('model-profile-key').placeholder = '新建时填写；编辑时留空表示保留现有密钥';
  document.getElementById('model-profile-form-title').textContent = '新建配置';
  document.getElementById('model-profile-form-message').textContent = '';
}

function editModelProfile(profileId) {
  var profile = modelProfilesCache.find(function(item) { return item.profile_id === profileId; });
  if (!profile) return;
  document.getElementById('model-profile-id').value = profile.profile_id;
  document.getElementById('model-profile-name').value = profile.name;
  document.getElementById('model-profile-provider').value = profile.provider || 'custom';
  document.getElementById('model-profile-protocol').value = profile.protocol || 'openai_compatible';
  document.getElementById('model-profile-url').value = profile.base_url;
  document.getElementById('model-profile-model').value = profile.model;
  document.getElementById('model-profile-key').value = '';
  document.getElementById('model-profile-key').placeholder = profile.has_key ? '留空则保留现有密钥' : '填写新密钥（可选）';
  document.getElementById('model-profile-temperature').value = profile.temperature == null ? '' : profile.temperature;
  document.getElementById('model-profile-timeout').value = profile.timeout;
  document.getElementById('model-profile-retries').value = profile.max_retries;
  document.getElementById('model-profile-max-tokens').value = profile.max_tokens;
  refreshStructuredMethodOptions(profile.structured_output_method);
  var sessionOnly = document.getElementById('model-profile-session-only');
  sessionOnly.checked = Boolean(profile.session_only);
  sessionOnly.disabled = true;
  document.getElementById('model-profile-make-default').checked = Boolean(profile.is_default);
  document.getElementById('model-profile-form-title').textContent = '编辑配置';
  document.getElementById('model-profile-form-message').textContent = '';
  document.getElementById('model-profile-name').focus();
}

async function handleModelProfileAction(action, profileId) {
  var profile = modelProfilesCache.find(function(item) { return item.profile_id === profileId; });
  if (!profile) return;
  try {
    if (action === 'connection-test' || action === 'structured-test') {
      var structured = action === 'structured-test';
      if (!modelDiagnosticResults[profileId]) modelDiagnosticResults[profileId] = {};
      var testKey = structured ? 'structured' : 'connection';
      var startingRevision = modelProfileDiagnosticRevisions[profileId] || 0;
      if (!modelDiagnosticRunTokens[profileId]) modelDiagnosticRunTokens[profileId] = {};
      var runToken = (modelDiagnosticRunTokens[profileId][testKey] || 0) + 1;
      modelDiagnosticRunTokens[profileId][testKey] = runToken;
      modelDiagnosticResults[profileId][testKey] = { ok: null, message: '本次诊断进行中…' };
      renderModelProfileList();
      try {
        var result = await modelApi('/api/model-profiles/' + encodeURIComponent(profileId) + '/diagnostics/' + (structured ? 'structured' : 'connection'), { method: 'POST' });
        if (startingRevision === (modelProfileDiagnosticRevisions[profileId] || 0) &&
            modelDiagnosticRunTokens[profileId][testKey] === runToken) {
          modelDiagnosticResults[profileId][testKey] = result;
        }
      } catch (error) {
        if (startingRevision === (modelProfileDiagnosticRevisions[profileId] || 0) &&
            modelDiagnosticRunTokens[profileId][testKey] === runToken) {
          modelDiagnosticResults[profileId][testKey] = { ok: false, message: error.message };
        }
      }
      renderModelProfileList();
      return;
    }
    if (action === 'default') {
      await modelApi('/api/model-profiles/' + encodeURIComponent(profileId) + '/default', { method: 'PUT' });
      await reloadModelProfiles();
      showToast('已切换默认模型配置');
      return;
    }
    if (action === 'clear') {
      if (!window.confirm('清除“' + profile.name + '”的密钥？配置会保留，但后续生成需要重新提供密钥。')) return;
      await modelApi('/api/model-profiles/' + encodeURIComponent(profileId) + '/credential', { method: 'DELETE' });
      invalidateModelProfileDiagnostics(profileId);
      await reloadModelProfiles();
      showToast('已清除模型密钥');
      return;
    }
    if (action === 'delete') {
      if (!window.confirm('删除模型配置“' + profile.name + '”？此操作也会删除系统凭据库中的对应密钥。')) return;
      await modelApi('/api/model-profiles/' + encodeURIComponent(profileId), { method: 'DELETE' });
      invalidateModelProfileDiagnostics(profileId);
      if (document.getElementById('model-profile-id').value === profileId) resetModelProfileForm();
      await reloadModelProfiles();
      showToast('已删除模型配置');
      return;
    }
    if (action === 'edit') editModelProfile(profileId);
  } catch (error) {
    var message = document.getElementById('model-profile-form-message');
    if (message) message.textContent = error.message;
  }
}

function setupModelProfileSettings() {
  var list = document.getElementById('model-profile-list');
  if (list) list.addEventListener('click', function(event) {
    var button = event.target.closest('[data-profile-action]');
    if (button) handleModelProfileAction(button.dataset.profileAction, button.dataset.profileId);
  });
  var form = document.getElementById('model-profile-form');
  if (!form) return;
  form.addEventListener('submit', async function(event) {
    event.preventDefault();
    var message = document.getElementById('model-profile-form-message');
    var profileId = document.getElementById('model-profile-id').value;
    var apiKey = document.getElementById('model-profile-key').value;
    var payload = {
      name: document.getElementById('model-profile-name').value,
      base_url: document.getElementById('model-profile-url').value,
      model: document.getElementById('model-profile-model').value,
      temperature: document.getElementById('model-profile-temperature').value.trim() === '' ? null : Number(document.getElementById('model-profile-temperature').value),
      provider: document.getElementById('model-profile-provider').value,
      protocol: document.getElementById('model-profile-protocol').value,
      timeout: Number(document.getElementById('model-profile-timeout').value),
      max_retries: Number(document.getElementById('model-profile-retries').value),
      max_tokens: Number(document.getElementById('model-profile-max-tokens').value),
      structured_output_method: document.getElementById('model-profile-structured').value,
      session_only: document.getElementById('model-profile-session-only').checked,
      make_default: document.getElementById('model-profile-make-default').checked
    };
    if (apiKey) payload.api_key = apiKey;
    message.textContent = '正在保存配置…';
    try {
      await modelApi(profileId ? '/api/model-profiles/' + encodeURIComponent(profileId) : '/api/model-profiles', {
        method: profileId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      invalidateModelProfileDiagnostics(profileId);
      document.getElementById('model-profile-key').value = '';
      resetModelProfileForm();
      await reloadModelProfiles();
      message.textContent = '配置已保存。';
    } catch (error) {
      message.textContent = error.message;
    }
  });
  var provider = document.getElementById('model-profile-provider');
  var protocol = document.getElementById('model-profile-protocol');
  var baseUrl = document.getElementById('model-profile-url');
  if (provider) provider.addEventListener('change', function() {
    var preset = MODEL_PROVIDER_PRESETS[provider.value];
    if (!preset) return;
    protocol.value = preset.protocol;
    baseUrl.value = preset.base_url;
    document.getElementById('model-profile-model').value = preset.model;
    refreshStructuredMethodOptions();
    refreshCredentialChangeMessage();
  });
  if (protocol) protocol.addEventListener('change', function() {
    refreshStructuredMethodOptions();
    refreshCredentialChangeMessage();
  });
  if (baseUrl) baseUrl.addEventListener('input', refreshCredentialChangeMessage);
  var keyInput = document.getElementById('model-profile-key');
  if (keyInput) keyInput.addEventListener('input', refreshCredentialChangeMessage);
}

function refreshStructuredMethodOptions(selected) {
  var select = document.getElementById('model-profile-structured');
  var protocol = document.getElementById('model-profile-protocol');
  if (!select || !protocol) return;
  var previous = selected || select.value;
  var methods = [
    ['function_calling', 'Function calling'],
    ['json_schema', 'JSON Schema'],
    ['strict_json_text', '严格 JSON 文本 + Pydantic 校验']
  ];
  if (protocol.value === 'openai_compatible') methods.splice(2, 0, ['json_mode', 'JSON mode']);
  select.innerHTML = methods.map(function(method) {
    return '<option value="' + method[0] + '">' + esc(method[1]) + '</option>';
  }).join('');
  select.value = methods.some(function(method) { return method[0] === previous; })
    ? previous : (protocol.value === 'openai_compatible' ? 'function_calling' : 'json_schema');
}

function refreshCredentialChangeMessage() {
  var profileId = document.getElementById('model-profile-id').value;
  var profile = modelProfilesCache.find(function(item) { return item.profile_id === profileId; });
  var message = document.getElementById('model-profile-form-message');
  var key = document.getElementById('model-profile-key').value;
  if (!profile || !profile.has_key || key) return;
  var protocol = document.getElementById('model-profile-protocol').value;
  var provider = document.getElementById('model-profile-provider').value;
  var changedTarget = false;
  try {
    var oldUrl = new URL(profile.base_url);
    var newUrl = new URL(document.getElementById('model-profile-url').value);
    changedTarget = oldUrl.protocol !== newUrl.protocol || oldUrl.hostname !== newUrl.hostname || oldUrl.port !== newUrl.port;
  } catch (error) { changedTarget = true; }
  if (provider !== (profile.provider || 'custom') || protocol !== (profile.protocol || 'openai_compatible') || changedTarget) {
    message.textContent = '服务商、协议或接口主机已变化：请重新填写 API Key，或先单独清除旧密钥。';
  } else if (message.textContent.indexOf('服务商、协议或接口主机已变化') === 0) {
    message.textContent = '';
  }
}

/* ── 核心流式生成 ── */
function cancelGeneration() {
  if (!activeGenerationController) return false;
  var text = document.getElementById('prog-text');
  if (text) text.textContent = '正在停止生成并清理模型请求…';
  activeGenerationController.abort();
  return true;
}

async function startGenerate(forceRefresh) {
  if (activeGenerationController) {
    showToast('已有攻略正在生成，请等待完成或先停止当前任务。');
    return;
  }
  var inp = document.getElementById('query-input');
  var btn = document.getElementById('gen-btn');
  var q = inp ? inp.value.trim() : '';
  var travelOverrides = collectTravelOverrides();
  var bypassCache = forceRefresh === true;

  if (!q && !(travelOverrides.destinations && travelOverrides.destinations.length)) {
    showToast('请填写旅行描述或至少一个目的地');
    if (inp && !document.getElementById('travel-destinations').value.trim()) {
      inp.focus();
      inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return;
  }

  btn.disabled = true;
  btn.innerHTML = ICONS.nav + ' <span class="btn-text">正在规划...</span>';
  var controller = new AbortController();
  activeGenerationController = controller;
  var startedAt = performance.now();

  var eb = document.getElementById('error-bar');
  if (eb) eb.classList.remove('show');

  showProgress(4, 'intent', '正在洞察旅人心愿...');
  var streamFinished = false;

  try {
    var resp = await fetch('/api/generate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify(Object.assign({
        query: q,
        profile_id: (document.getElementById('model-profile-select') || {}).value || null,
        force_refresh: bypassCache
      }, travelOverrides))
    });

    if (!resp.ok || !resp.body) {
      var errorText = '服务端响应异常 (HTTP ' + resp.status + ')';
      try {
        var errorPayload = await resp.json();
        var detail = errorPayload.detail;
        if (Array.isArray(detail) && detail.length) detail = detail[0].msg;
        if (typeof detail === 'string' && detail) errorText = detail;
      } catch (error) {}
      throw new Error(errorText);
    }

    var state = await window.TravelGenerationStream.readGenerationStream(
      resp.body, controller, function(progress, stage, message) {
        showProgress(progress, stage, message);
      }
    );
    streamFinished = true;
    if (state.terminal === 'error') {
      var errorMetrics = state.metrics ? ' · ' + generationRuntimeLabel(state.metrics) : '';
      throw new Error(state.error + errorMetrics);
    }
    if (state.terminal !== 'guide' || !state.guide) throw new Error('未收到完整的攻略数据');
    guide = state.guide;
    mapDayFilter = null;

    var overlay = document.getElementById('progress-overlay');
    if (overlay) overlay.classList.remove('show');

    renderAll();
    switchPage(0);
    if (guide.cache_hit) {
      var ageMinutes = Math.max(1, Math.round((Number(guide.cache_age_seconds) || 0) / 60));
      showToast('⚡ 复用 ' + ageMinutes + ' 分钟内的相同请求结果，未重复调用模型');
    } else {
      showToast(guide.history_saved === false
        ? '攻略已生成；本机历史暂未保存。'
        : '✨ 攻略已为您精美编排入卷');
    }
    setTimeout(function() {
      enterWorkspace();
    }, 400);
  } catch (e) {
    if (e && e.name === 'AbortError') {
      var elapsed = Math.max(0, Math.round(performance.now() - startedAt));
      showToast('生成已停止 · 耗时 ' + (elapsed / 1000).toFixed(1) + ' 秒 · 模型用量未知');
      var overlay = document.getElementById('progress-overlay');
      if (overlay) overlay.classList.remove('show');
    } else {
      showGenError(e.message || String(e));
    }
  } finally {
    if (!streamFinished && !controller.signal.aborted) controller.abort();
    if (activeGenerationController === controller) activeGenerationController = null;
    var overlay = document.getElementById('progress-overlay');
    if (overlay) overlay.classList.remove('show');
    btn.disabled = false;
    btn.innerHTML = ICONS.nav + ' <span class="btn-text">生成专属攻略</span>';
  }
}

function collectTravelOverrides() {
  var values = {};
  var destinations = splitTravelValues((document.getElementById('travel-destinations') || {}).value || '');
  if (destinations.length) values.destinations = destinations;

  var departure = ((document.getElementById('travel-departure-city') || {}).value || '').trim();
  if (departure) values.departure_city = departure;
  var travelDate = (document.getElementById('travel-date') || {}).value || '';
  if (travelDate) values.travel_date = travelDate;

  [['travel-days', 'days'], ['travelers', 'travelers'], ['travel-budget', 'budget']].forEach(function(pair) {
    var raw = ((document.getElementById(pair[0]) || {}).value || '').trim();
    if (raw) values[pair[1]] = Number(raw);
  });
  var scope = (document.getElementById('travel-budget-scope') || {}).value || '';
  if (scope) values.budget_scope = scope;
  var pace = (document.getElementById('travel-pace') || {}).value || '';
  if (pace) values.pace = pace;

  var constraints = splitTravelValues((document.getElementById('travel-constraints') || {}).value || '');
  if (constraints.length) values.constraints = constraints;
  var theme = document.querySelector('[data-key="theme"] .f-pill.active');
  if (theme) values.preferences = [theme.getAttribute('data-val')];
  return values;
}

function splitTravelValues(value) {
  return String(value || '').split(/[,，、;；\n]+/).map(function(item) { return item.trim(); }).filter(Boolean);
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

function normalizeMapPlace(value) {
  return String(value || '').replace(/\s+/g, '').replace(/(?:特别行政区|维吾尔自治区|壮族自治区|回族自治区|自治区|自治州|地区|市|县|区)$/g, '');
}

function mapGeocodeMatchesCity(city, geocode) {
  var target = normalizeMapPlace(city);
  var address = geocode && geocode.addressComponent || {};
  return !!target && [address.city, address.province, address.district].some(function(value) {
    return normalizeMapPlace(value) === target;
  });
}

function setMapStatus(message) {
  var status = document.getElementById('amap-status');
  if (status) status.textContent = message || '';
}

function applyMapDayFilter() {
  var dailyPlan = ((guide || {}).route || {}).daily_plan || [];
  var selectedDay = dailyPlan.find(function(day) { return Number(day.day) === Number(mapDayFilter); });
  var selectedCity = selectedDay ? normalizeMapPlace(selectedDay.city) : '';
  mapActivityMarkers.forEach(function(marker) {
    if (mapDayFilter == null || marker.__travelDay === mapDayFilter) marker.show();
    else marker.hide();
  });
  mapCityMarkers.forEach(function(marker) {
    if (mapDayFilter == null || marker.__travelCity === selectedCity) marker.show();
    else marker.hide();
  });
  mapRouteLines.forEach(function(line) {
    if (mapDayFilter == null) line.show();
    else line.hide();
  });
  document.querySelectorAll('[data-map-day]').forEach(function(button) {
    var value = button.getAttribute('data-map-day');
    var active = (mapDayFilter == null && value === 'all') || String(mapDayFilter) === value;
    button.classList.toggle('active', active);
  });
  if (amap) {
    var visible = mapActivityMarkers.filter(function(marker) {
      return mapDayFilter == null || marker.__travelDay === mapDayFilter;
    }).concat(mapCityMarkers.filter(function(marker) {
      return mapDayFilter == null || marker.__travelCity === selectedCity;
    }));
    if (visible.length) amap.setFitView(visible, false, [70, 70, 70, 70]);
  }
}

function showMapDay(dayNumber) {
  mapDayFilter = dayNumber == null || Number(dayNumber) < 0 ? null : Number(dayNumber);
  if (page !== 1) switchPage(1);
  applyMapDayFilter();
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
  var allCities = (dept ? [dept].concat(guide.destinations || []) : (guide.destinations || [])).filter(Boolean);
  if (!allCities.length) return;

  amap = new AMap.Map('amap-container', {
    zoom: 7,
    center: [104, 30],
    mapStyle: 'amap://styles/whitesmoke'
  });

  setMapStatus('正在核对城市位置和每日景点坐标…');
  mapActivityMarkers = [];
  mapCityMarkers = [];
  mapRouteLines = [];
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
    var validCount = 0;
    pts.forEach(function(p, i) {
      if (!p) return;
      validCount++;
      var label = (dept && i === 0) ? '起' : String(dept ? i : i + 1);
      var mk = new AMap.Marker({
        position: p,
        title: allCities[i],
        label: {
          content: '<div style="background:#234339;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.2);">' + label + ' · ' + esc(allCities[i]) + '（概览）</div>',
          offset: new AMap.Pixel(0, -26)
        }
      });
      mk.__travelCity = normalizeMapPlace(allCities[i]);
      mk.on('click', function() {
        window.open('https://uri.amap.com/search?keyword=' + encodeURIComponent(allCities[i]), '_blank', 'noopener');
      });
      amap.add(mk);
      mapCityMarkers.push(mk);
    });

    for (var i = 0; i < pts.length - 1; i++) {
      if (pts[i] && pts[i + 1]) {
        var line = new AMap.Polyline({
          path: [pts[i], pts[i + 1]],
          strokeColor: '#C3643B',
          strokeWeight: 3,
          strokeStyle: 'dashed',
          strokeOpacity: 0.75
        });
        mapRouteLines.push(line);
        amap.add(line);
      }
    }

    var daily = ((guide.route || {}).daily_plan || []);
    var activityCount = 0;
    daily.forEach(function(day) {
      ['morning', 'afternoon', 'evening'].forEach(function(key) {
        var activity = day[key] || {};
        if (!activity.name || !activity.coordinate_verified || !isValidAmapCoordinate(activity.coordinate)) return;
        var marker = new AMap.Marker({
          position: activity.coordinate,
          title: 'Day ' + day.day + ' · ' + activity.name,
          label: { content: '<div class="map-activity-label">D' + day.day + ' · ' + esc(activity.name) + '</div>', offset: new AMap.Pixel(0, -18) }
        });
        marker.__travelDay = Number(day.day);
        if (mapDayFilter != null && marker.__travelDay !== mapDayFilter) marker.hide();
        marker.on('click', function() {
          window.open('https://uri.amap.com/navigation?to=' + activity.coordinate[0] + ',' + activity.coordinate[1] + ',' + encodeURIComponent(activity.name) + '&mode=car&src=shanhe&coordinate=gaode&callnative=0', '_blank', 'noopener');
        });
        mapActivityMarkers.push(marker);
        amap.add(marker);
        activityCount++;
      });
    });

    if (validCount || activityCount) {
      amap.setFitView(null, false, [60, 60, 60, 60]);
    }
    applyMapDayFilter();
    setMapStatus('城市标点仅作位置概览，虚线为城市顺序示意；每日景点仅标出已按城市和名称核验的地点（' + activityCount + ' 个）。');
  }

  allCities.forEach(function(c, i) {
    if (window.AMap.Geocoder) {
      (new AMap.Geocoder({ city: '全国' })).getLocation(c, function(status, result) {
        if (!done && status === 'complete' && result.geocodes && result.geocodes.length) {
          var exact = result.geocodes.find(function(item) {
            var loc = item.location;
            return mapGeocodeMatchesCity(c, item) && loc && isValidAmapCoordinate([loc.lng, loc.lat]);
          });
          if (exact) pts[i] = [exact.location.lng, exact.location.lat];
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
    rBudg(g) +
    rPrep(g);

  attach3DTiltCards();
  attachMagneticElements();
}

/* ── TAB 1 辅助：攻略自检区块 ── */
function qualityBlock(g) {
  var q = g.quality || {};
  if (q.score == null || q.score === '') return '';
  var score = Number(q.score);
  var tone = q.grade === 'A' ? 'ok' : (q.grade === 'D' ? 'bad' : 'warn');
  var dims = q.dimensions || {};

  var h = '<div class="quality-card ' + tone + '">';
  h += '<div class="quality-head">';
  h += '<span class="quality-label">攻略自检</span>';
  h += '<span class="quality-score">' + score + '<small> / 100</small></span>';
  h += '<span class="quality-grade">等级 ' + esc(q.grade || '') + '</span>';
  h += '</div>';

  var keys = Object.keys(dims);
  if (keys.length) {
    h += '<div class="quality-dims">';
    keys.forEach(function(key) {
      var dim = dims[key] || {};
      var value = Number(dim.score || 0);
      h += '<div class="quality-dim">';
      h += '<span class="qd-label">' + esc(dim.label || key) + '</span>';
      h += '<div class="qd-track"><div class="qd-fill" style="width:' + value + '%"></div></div>';
      h += '<span class="qd-val">' + value + '</span>';
      h += '</div>';
    });
    h += '</div>';
  }

  if ((q.issues || []).length) {
    h += '<details class="quality-issues"><summary>自检发现 ' + q.issues.length + ' 项可改进</summary><ul>';
    q.issues.forEach(function(issue) { h += '<li>' + esc(issue) + '</li>'; });
    h += '</ul></details>';
  }

  if ((q.notes || []).length) {
    h += '<p class="quality-note">' + esc(q.notes.join(' ')) + '</p>';
  }

  h += '</div>';
  return h;
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

  if (g.cache_hit) {
    var cacheAge = Math.max(1, Math.round((Number(g.cache_age_seconds) || 0) / 60));
    h += '<div class="cache-notice">';
    h += '<span class="cache-notice-text">本次复用了 ' + cacheAge + ' 分钟内的相同请求结果，没有新增模型或 Search/Fetch 调用。</span>';
    h += '<button class="cache-refresh-btn" type="button" onclick="startGenerate(true)">强制重新生成</button>';
    h += '</div>';
  }

  // 1. 顶部大画幅封面
  h += '<div class="overview-hero-card tilt-card">';
  h += imgTag(hero, d + '-landscape', 1200, 600, d, 'overview-banner-img');
  var heroSpot = (g.spots || []).find(function(s) { return !!s.photo; });
  h += '<span class="photo-source-badge hero-photo-source">' + esc(photoSourceDetail(heroSpot ? heroSpot.photo_source : 'none', heroSpot && heroSpot.photo_checked_at)) + '</span>';
  h += '<div class="overview-gradient-overlay"></div>';
  h += '<div class="card-sheen"></div>';
  h += '<div class="overview-hero-content">';
  h += '<div class="overview-meta-tag">SHANHE VOYAGE · 东方山河漫游画卷</div>';
  h += '<h2 class="overview-title">《' + t + '》</h2>';
  h += '<p class="overview-subtitle">' + esc(g.subtitle || '') + '</p>';
  h += '</div></div>';
  if (g.generation_metrics) {
    h += '<p class="generation-run-meta">' + (g.cache_hit ? '原攻略生成统计：' : '') +
      esc(generationRuntimeLabel(g.generation_metrics)) +
      (g.generation_metrics.llm && g.generation_metrics.llm.requests != null ?
        (g.cache_hit ? ' · 原生成模型请求 ' : ' · 模型请求 ') +
        Number(g.generation_metrics.llm.requests) + ' 次' : '') +
      (g.history_saved === false ? ' · 本机历史未保存' : '') + '</p>';
  }
  var webResearch = g.web_research || { status: 'disabled' };
  var webResearchState = webResearch.status === 'disabled' ? '本次未联网检索' :
    webResearch.status === 'unavailable' ? '联网检索已启用，凭据不可用' :
    'Search ' + Number(webResearch.search_count || 0) + ' 次 · Fetch ' + Number(webResearch.fetch_count || 0) + ' 次';
  h += '<div class="web-research-summary"><b>景点网页资料：</b>' +
    (g.cache_hit ? '原攻略联网统计：' : '') + esc(webResearchState) +
    (webResearch.message ? ' · ' + esc(webResearch.message) : '') +
    '<span>票价、来源机构和图片使用授权尚未核验，网页线索不计入预算。</span></div>';

  var feas = g.feasibility || {};
  if (feas.checked) {
    var feasTone = feas.level === 'A' ? 'ok' : (feas.level === 'D' ? 'bad' : 'warn');
    h += '<div class="feas-summary ' + feasTone + '">';
    h += '<span class="feas-score">可执行性 ' + Number(feas.score) + '<small> / 100</small></span>';
    h += '<span class="feas-level">' + esc(feas.level) + '</span>';
    h += '<span class="feas-note">' + esc((feas.notes || []).join(' ')) + '</span>';
    h += '</div>';
    if ((feas.issues || []).length) {
      h += '<div class="feas-issues"><b>行程紧凑度提醒</b><ul>';
      feas.issues.slice(0, 5).forEach(function(issue) {
        h += '<li>' + esc(issue) + '</li>';
      });
      h += '</ul></div>';
    }
  } else if (feas.notes && feas.notes.length) {
    h += '<div class="feas-summary unknown">';
    h += '<span class="feas-note">' + esc(feas.notes.join(' ')) + '</span>';
    h += '</div>';
  }

  h += qualityBlock(g);

  if (g.request) {
    var request = g.request;
    var requestItems = [
      ['目的地', (request.destinations || []).join('、') || '未注明'],
      ['出发地', request.departure_city || '未注明'],
      ['出行时间', request.travel_date_note || request.travel_date || '未指定'],
      ['天数 / 人数', (request.days || totalDays) + '天 · ' + (request.travelers || 1) + '人'],
      ['预算', request.budget ? ((request.budget_scope === 'total' ? '全体总额' : '人均') + ' ¥' + request.budget) : '未指定'],
      ['节奏', request.pace || '不紧不慢'],
      ['硬约束', (request.constraints || []).join('、') || '无']
    ];
    h += '<div class="request-summary-card"><h3>本次采用的出行条件</h3><div class="request-summary-grid">';
    requestItems.forEach(function(item) {
      h += '<div class="request-summary-item"><span>' + esc(item[0]) + '</span><b>' + esc(item[1]) + '</b></div>';
    });
    h += '</div></div>';
  }

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
  h += '<div class="kpi-body"><span class="kpi-label">人均已知小计</span><span class="kpi-val">¥' + totalBudget + '</span><span class="kpi-sub">未核价交通另计</span></div>';
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

  h += '<div class="map-day-filters">';
  h += '<button type="button" data-map-day="all" class="map-day-filter-btn active" onclick="showMapDay(-1)">全程</button>';
  ((g.route || {}).daily_plan || []).forEach(function(day) {
    h += '<button type="button" data-map-day="' + Number(day.day) + '" class="map-day-filter-btn" onclick="showMapDay(' + Number(day.day) + ')">Day ' + Number(day.day) + '</button>';
  });
  h += '</div>';

  h += '<div class="map-container-box"><div id="amap-container"></div><div id="amap-status" class="map-status">城市路线和每日景点位置将在此显示。</div></div>';
  h += '<p class="map-tip-footer">城市标点用于路线概览，虚线只示意城市顺序，不代表道路或里程规划。每日景点坐标经高德按城市和名称核验；未核实点位请使用文本地点搜索。</p>';
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
    h += '<button class="day-map-link" type="button" onclick="showMapDay(' + Number(d.day) + ')">地图定位</button>';
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
        h += nav(d.city || '', d[act.k].name, d[act.k].coordinate, d[act.k].coordinate_verified);
        h += '</div>';
      }
    });

    if (d.stay) {
      h += '<div class="stay-hotel-bar">';
      h += '<div class="hotel-info">' + ICONS.hotel + ' <b>下榻宿处：</b>' + esc(d.stay) + '</div>';
      h += nav(d.city || '', d.stay, d.stay_coordinate, d.stay_coordinate_verified);
      h += '</div>';
    }

    var dayFeas = null;
    var feasDays = (g.feasibility || {}).days || [];
    for (var fi = 0; fi < feasDays.length; fi++) {
      if (Number(feasDays[fi].day) === Number(d.day)) { dayFeas = feasDays[fi]; break; }
    }
    if (dayFeas && (dayFeas.distance_km != null || (dayFeas.issues || []).length)) {
      h += '<div class="day-feasibility">';
      if (dayFeas.distance_km != null) {
        h += '<span class="df-metric">当天在途约 ' + dayFeas.distance_km + ' km（直线距离）</span>';
      }
      if (dayFeas.estimated_hours != null) {
        h += '<span class="df-metric">粗估含在途 ' + dayFeas.estimated_hours + ' 小时</span>';
      }
      (dayFeas.issues || []).forEach(function(issue) {
        h += '<p class="df-issue">' + esc(issue) + '</p>';
      });
      h += '</div>';
    }

    h += '</div></div>';
  });

  var trans = (g.route || {}).transport || [];
  if (trans.length) {
    h += '<div style="margin-top:24px"><h3 style="font-family:var(--font-serif-cn);font-size:1.15em;margin-bottom:12px;">交通接驳</h3>';
    trans.forEach(function(t) {
      var navBtn = '';
      navBtn = '<a class="nav-link-btn magnetic-elem" href="https://uri.amap.com/search?keyword=' + encodeURIComponent((t.from || '') + ' 到 ' + (t.to || '') + ' 路线') + '" target="_blank" rel="noopener">' + ICONS.nav + ' <span>查询路线</span></a>';
      h += '<div class="transit-segment-card">';
      h += '<div class="transit-desc">' + ICONS.transit + ' <b>' + esc(t.from || '') + ' ➔ ' + esc(t.to || '') + '</b><span>' + esc(t.mode || '') + ' · ' + esc(t.duration || '') + '</span></div>';
      h += '<div style="display:flex;align-items:center;gap:12px"><span class="transit-cost">' + (t.cost_est == null ? '待核价' : '¥' + t.cost_est + ' /人') + '</span>' + navBtn + '</div>';
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
  (g.spots || []).forEach(function(s, spotIndex) {
    var tierLabel = { 1: '必访典藏', 2: '深度探寻', 3: '秘境发现' }[s.tier] || '推荐参访';
    var tierClass = 'tier-badge-' + (s.tier || 1);

    h += '<div class="spot-editorial-card tilt-card">';
    h += '<div class="card-sheen"></div>';
    h += '<div class="spot-cover-wrap">';
    h += imgTag(s.photo, s.name + '-china', 600, 380, s.name, 'spot-cover-img');
    h += '<span class="spot-tier-badge ' + tierClass + '">' + tierLabel + '</span>';
    h += '<span class="photo-source-badge">' + esc(photoSourceDetail(s.photo_source, s.photo_checked_at)) + '</span>';
    h += '</div>';

    h += '<div class="spot-card-body">';
    h += '<div class="sc-header-row">';
    h += '<h3 class="sc-title">' + esc(s.name) + '</h3>';
    var ticketLabel = s.ticket_status === 'free' && Number(s.ticket || 0) === 0
      ? '模型标记免费，待核实'
      : Number(s.ticket || 0) > 0
        ? '模型参考价 ¥' + esc(s.ticket) + '，待核实'
        : '门票待核实';
    h += '<span class="sc-price">' + ticketLabel + '</span>';
    h += '</div>';
    h += '<p class="fact-verification-note">开放时间、预约与无障碍信息未经官方核验，请出行前确认。</p>';

    h += '<div class="sc-meta-line">';
    h += '<span>' + esc(s.type || '观光名胜') + '</span> · <span>游玩时长参考 ' + esc(s.duration || '待确认') + '</span>';
    if (s.best_time) h += ' · <span>' + esc(s.best_time) + '</span>';
    h += '</div>';
    h += '<p class="source-verification-meta">' + esc(coordinateSourceDetail(s.coordinate_verified, s.coordinate_source, s.coordinate_checked_at)) + '</p>';

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

    h += webEvidenceHtml(g, s, spotIndex);

    h += '<div class="spot-card-footer">';
    h += nav(s.city || (g.destinations || [])[0] || '', s.name, s.coordinate, s.coordinate_verified);
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
  h += '<p class="fact-verification-note section-verification-note">店铺营业状态与菜品价格为参考信息，出发前请向商家确认。</p>';

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
      h += '<span class="photo-source-badge">' + esc(photoSourceDetail(f.photo_source, f.photo_checked_at)) + '</span>';
      h += '</div>';

      h += '<div class="fc-body">';
      h += '<h4 class="fc-title">' + esc(f.name || '') + '</h4>';
      h += '<p class="fc-reason">' + esc(f.reason || '') + '</p>';

      h += '<div class="fc-details-box">';
      if (f.where) h += '<div class="fc-where">📍 ' + esc(f.where) + '</div>';
      h += '<div class="fc-price-tag">人均参考 ' + (Number(f.price_per_person) > 0 ? '约¥' + esc(f.price_per_person) : '待确认') + '</div>';
      h += '<div class="source-verification-meta">' + esc(coordinateSourceDetail(f.coordinate_verified, f.coordinate_source, f.coordinate_checked_at)) + '</div>';
      h += '</div>';

      if (f.tips) {
        h += '<div class="fc-tips">💡 ' + esc(f.tips) + '</div>';
      }

      h += '<div class="food-card-footer">';
      h += nav(c.city || '', f.where || f.name || '', f.coordinate, f.coordinate_verified);
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
    h += '<div class="clothing-banner"><div class="cb-icon">' + ICONS.cloud + '</div><div>暂无可用的行程日期预报。补充出行日期并配置高德 Web 服务后，可查询近期天气；更远日期不会用当前天气代替。</div></div>';
  } else {
    var availableWeather = (g.weather || []).filter(function(w) { return (w.forecast || []).length > 0; });
    var unavailableWeather = (g.weather || []).filter(function(w) { return !(w.forecast || []).length; });
    var statusMessages = {
      no_key: '尚未配置高德 Web 服务 Key。',
      date_required: '未指定出行日期，无法将近期预报与行程对齐。',
      outside_forecast_window: '行程日期超出高德当前预报范围，暂无对应天气。',
      not_found: '未能核对该城市的天气区域。',
      error: '天气服务暂不可用。'
    };
    if (availableWeather.length) h += '<div class="weather-cards-grid">';
    availableWeather.forEach(function(w) {
      h += '<div class="weather-city-card tilt-card">';
      h += '<div class="card-sheen"></div>';
      var weatherDates = (w.requested_dates || []).map(function(value) { return String(value).slice(5); });
      var dateLabel = weatherDates.length ? weatherDates.join('、') : (w.requested_start || '');
      if (!weatherDates.length && w.requested_end && w.requested_end !== w.requested_start) dateLabel += ' 至 ' + w.requested_end;
      h += '<div class="wcc-city"><h4>' + esc(w.city || '目的地') + '</h4><span class="wcc-badge">' + esc(dateLabel) + '</span></div>';
      (w.forecast || []).slice(0, 4).forEach(function(f) {
        var dayWeather = f.dayweather || '天气未提供';
        var isRain = dayWeather.indexOf('雨') > -1;
        var icon = isRain ? ICONS.rain : (dayWeather.indexOf('云') > -1 ? ICONS.cloud : (f.dayweather ? ICONS.sun : ICONS.cloud));
        h += '<div class="w-forecast-row">';
        h += '<div class="w-date-col">' + (f.date || '').slice(-5) + ' ' + (f.week || '') + '</div>';
        h += '<div class="w-weather-col"><span>' + icon + '</span><span>' + esc(dayWeather) + '</span></div>';
        h += '<div class="w-temp-col">' + (f.nighttemp || '-') + '° ~ ' + (f.daytemp || '-') + '°C</div>';
        h += '</div>';
      });
      if (w.reporttime) h += '<p class="weather-range-note">预报发布时间：' + esc(w.reporttime) + '</p>';
      if (w.status === 'partial') h += '<p class="weather-range-note">预报仅覆盖行程中的部分日期，其他日期暂无对应预报。</p>';
      h += '</div>';
    });
    if (availableWeather.length) h += '</div>';
    unavailableWeather.forEach(function(w) {
      var message = statusMessages[w.status] || '当前没有可核验的预报。';
      h += '<div class="clothing-banner weather-status-note"><div class="cb-icon">' + ICONS.cloud + '</div><div><b>' + esc(w.city || '目的地') + '：</b>' + message + '</div></div>';
    });
  }

  h += '</div>';
  return h;
}

/* ── TAB 8: 预算分项与微调 ── */
function rBudg(g) {
  var b = g.budget || {};
  var total = Number(b.total || 0);
  var days = g.days || 1;
  var perDay = Math.round(total / days);
  var travelers = b.travelers || (g.request || {}).travelers || 1;
  var groupTotal = b.group_total || (total * travelers);

  var h = '<div class="page" id="p-budget">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">FINANCES & TUNING</span>';
  h += '<h2>游资盘点 · 预算与微调</h2>';
  h += '<p>清晰透明的各项开支测算与灵活定制入口</p>';
  h += '</div>';

  h += '<div class="budget-overview-card tilt-card">';
  h += '<div class="card-sheen"></div>';
  h += '<div class="budget-total-headline">';
  h += '<div class="bth-label">人均已知费用小计 · ' + esc(g.budget_level || '预算档位') + '</div>';
  h += '<div class="bth-amount">¥' + total + '</div>';
  h += '<div class="bth-daily">已知团体小计 ¥' + groupTotal + ' · ' + travelers + ' 人 · ' + (b.nights || 0) + ' 晚</div>';
  h += '<div class="bth-daily">人均已知约 ¥' + perDay + ' / 天 · ' + days + ' 天</div>';
  h += '</div>';

  var categories = [
    { l: '跨城交通', v: b.transport || 0, c: '#234339' },
    { l: '住宿旅居', v: b.accommodation || 0, c: '#366E67' },
    { l: '景点门票', v: b.tickets || 0, c: '#B88B42' },
    { l: '地道餐饮', v: b.food || 0, c: '#C3643B' },
    { l: '备用机动', v: b.other || 0, c: '#74817C' }
  ];

  categories.forEach(function(cat) {
    var pct = Math.max((cat.v / Math.max(total, 1)) * 100, 2);
    var sharePct = total > 0 ? Math.round((cat.v / total) * 100) : 0;
    h += '<div class="budget-bar-row">';
    h += '<span class="bbr-label">' + cat.l + '</span>';
    h += '<div class="bbr-track"><div class="bbr-fill" style="width:' + pct + '%;background:' + cat.c + '"></div></div>';
    h += '<span class="bbr-val">¥' + cat.v + ' <small>' + sharePct + '%</small></span>';
    h += '</div>';
  });

  var ticketKnown = Number(b.tickets_known || 0);
  var ticketEstimated = Number(b.tickets_estimated || 0);
  var pendingSpots = b.tickets_pending_spots || [];
  var freeSpots = b.tickets_free_spots || [];
  var unpricedActivities = b.tickets_unpriced_activities || [];
  if (ticketKnown || ticketEstimated || freeSpots.length) {
    h += '<div class="budget-estimate-notes"><b>门票口径</b><p>模型参考价 ¥' + ticketKnown
      + '，未知价格地点按每处 ¥100 估算 ¥' + ticketEstimated
      + '；模型标记免费 ' + freeSpots.length + ' 处。价格与免费状态均未经官方核验。</p></div>';
  }
  if (pendingSpots.length) {
    h += '<div class="warn-callout-box">';
    h += '<h4>门票待核实 · ' + pendingSpots.length + ' 处</h4><ul>';
    pendingSpots.slice(0, 10).forEach(function(name) { h += '<li>' + esc(name) + '</li>'; });
    h += '</ul><p>这些匹配到的推荐景点没有提供价格，已按估算计入小计，行前请以景区官方公示为准。</p></div>';
  }
  if (freeSpots.length) {
    h += '<div class="budget-estimate-notes"><b>模型标记免费，待核实</b><ul>';
    freeSpots.slice(0, 10).forEach(function(name) { h += '<li>' + esc(name) + '</li>'; });
    h += '</ul></div>';
  }
  if (unpricedActivities.length) {
    h += '<div class="warn-callout-box"><h4>门票未覆盖 · ' + unpricedActivities.length + ' 项活动</h4><ul>';
    unpricedActivities.slice(0, 10).forEach(function(name) { h += '<li>' + esc(name) + '</li>'; });
    h += '</ul><p>这些活动未匹配到同城推荐景点，门票未计入小计；请核实是否收费。</p></div>';
  }
  if ((b.lodging_cities || []).length) {
    h += '<div class="budget-estimate-notes"><b>住宿口径</b><p>基准 ¥' + (b.lodging_night_rate || 0)
      + ' / 晚，按过夜城市等级折算：' + esc((b.lodging_cities || []).join('、'))
      + '。未列入等级表的城市按基准价计算。</p></div>';
  }

  var unknownTransport = b.transport_unknown_segments || [];
  if (b.budget_status === 'within_estimate') {
    h += '<div class="budget-estimate-notes"><b>预算提示</b><p>已知费用估算在需求预算范围内；这不是最终报价，未核价交通费用另计。</p></div>';
  } else if (b.budget_status === 'over_known_budget') {
    h += '<div class="warn-callout-box"><h4>已知费用估算超过需求预算</h4><p>待核价交通费用另计，请调整预算或行程后再确认。</p></div>';
  } else if (b.budget_status === 'needs_transport_quote' && (g.request || {}).budget) {
    h += '<div class="warn-callout-box"><h4>预算暂不能确认</h4><p>仍有交通费用待核价，补充报价后才能判断是否符合需求预算。</p></div>';
  } else if (b.budget_status === 'needs_price_review') {
    h += '<div class="warn-callout-box"><h4>预算暂不能确认</h4><p>部分行程活动门票未覆盖，费用小计不完整，请核价后再判断是否符合预算。</p></div>';
  }

  if (unknownTransport.length) {
    h += '<div class="warn-callout-box">';
    h += '<h4>未计入小计 · 交通待核价</h4><ul>';
    unknownTransport.forEach(function(segment) { h += '<li>' + esc(segment) + '</li>'; });
    h += '</ul><p>确认出发地与班次报价后，再把这些费用计入预算。</p></div>';
  }

  if ((b.estimate_notes || []).length) {
    h += '<div class="budget-estimate-notes"><b>估算口径</b><ul>';
    b.estimate_notes.forEach(function(note) { h += '<li>' + esc(note) + '</li>'; });
    h += '</ul></div>';
  }

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

/* ── TAB 9: 行前准备 ── */
function rPrep(g) {
  var prep = g.prep || {};
  var packing = prep.packing || [];
  var plans = prep.weather_plans || [];
  var notes = prep.notes || [];
  var temp = prep.temperature_range;

  var h = '<div class="page" id="p-prep">';
  h += '<div class="sec-header">';
  h += '<span class="sec-badge">BEFORE YOU GO</span>';
  h += '<h2>行前帖 · 备物与应变</h2>';
  h += '<p>按天气与你的同行条件推导的清单，以及每天遇到坏天气时的替代方案</p>';
  h += '</div>';

  if (!packing.length && !plans.length) {
    h += '<div class="prep-empty">本次没有生成行前清单，可能是天气与行程数据不足。</div>';
    h += '</div>';
    return h;
  }

  h += '<div class="prep-temp-card">';
  if (temp && temp.low != null) {
    h += '<span class="prep-temp-label">预报温度区间</span>';
    h += '<span class="prep-temp-value">' + Number(temp.low) + '℃ ~ ' + Number(temp.high) + '℃</span>';
  } else {
    h += '<span class="prep-temp-label">预报温度区间</span>';
    h += '<span class="prep-temp-value muted">暂无可用预报</span>';
  }
  h += '<span class="prep-temp-hint">预报时效有限，出发前 1 天请再确认</span>';
  h += '</div>';

  if (plans.length) {
    h += '<h3 class="prep-section-title">逐日应变方案</h3>';
    h += '<div class="prep-day-list">';
    plans.forEach(function(p) {
      var tone = p.status === 'ok' ? 'ok' : 'unknown';
      h += '<div class="prep-day-card ' + tone + '">';
      h += '<div class="prep-day-head">';
      h += '<span class="prep-day-num">Day ' + Number(p.day) + '</span>';
      h += '<span class="prep-day-city">' + esc(p.city || '') + '</span>';
      h += '<span class="prep-day-weather">' + esc(p.weather || '无预报') + '</span>';
      h += '</div>';
      if (p.status === 'ok') {
        h += '<ul class="prep-advice-list">';
        (p.advice || []).forEach(function(a) { h += '<li>' + esc(a) + '</li>'; });
        h += '</ul>';
      } else {
        h += '<p class="prep-day-missing">这一天没有对应的天气预报，出行前请自行确认。</p>';
      }
      h += '</div>';
    });
    h += '</div>';
  }

  if (packing.length) {
    h += '<h3 class="prep-section-title">打包清单</h3>';
    h += '<div class="prep-packing-grid">';
    packing.forEach(function(group) {
      h += '<div class="prep-packing-card tilt-card">';
      h += '<div class="card-sheen"></div>';
      h += '<h4>' + esc(group.group || '') + '</h4>';
      h += '<ul>';
      (group.items || []).forEach(function(item) { h += '<li>' + esc(item) + '</li>'; });
      h += '</ul>';
      if (group.basis) {
        h += '<p class="prep-basis">' + esc(group.basis) + '</p>';
      }
      h += '</div>';
    });
    h += '</div>';
  }

  if (notes.length) {
    h += '<div class="budget-estimate-notes"><b>边界说明</b><ul>';
    notes.forEach(function(note) { h += '<li>' + esc(note) + '</li>'; });
    h += '</ul></div>';
  }

  h += '</div>';
  return h;
}

/* ── 交互过滤器监听 ── */
function setupFilterListeners() {
  document.querySelectorAll('.filter-pills').forEach(function(group) {
    group.addEventListener('click', function(e) {
      var btn = e.target.closest('.f-pill');
      if (!btn) return;
      var wasActive = btn.classList.contains('active');
      group.querySelectorAll('.f-pill').forEach(function(c) { c.classList.remove('active'); });
      if (!wasActive) btn.classList.add('active');

      // Quick filters set explicit structured values and never rewrite user text.
      if (group.getAttribute('data-key') === 'days') {
        var days = document.getElementById('travel-days');
        var details = document.getElementById('travel-request-details');
        if (days) days.value = wasActive ? '' : (btn.getAttribute('data-val').match(/^\d+/) || [''])[0];
        if (details && !wasActive) details.open = true;
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

  var dateInput = document.getElementById('travel-date');
  if (dateInput && window.Intl && Intl.DateTimeFormat) {
    var parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(new Date());
    var dateParts = {};
    parts.forEach(function(part) { dateParts[part.type] = part.value; });
    dateInput.min = dateParts.year + '-' + dateParts.month + '-' + dateParts.day;
  }
}

/* ── 启动初始化 ── */
window.addEventListener('DOMContentLoaded', function() {
  guide = null;
  renderAll();
  setupFilterListeners();
  setupModelProfileSettings();
  reloadModelProfiles();
  updateClearBtn();

  // 启动物理动效
  initInkRipple();
  initZenCanvas();
  initMouseEffects();
  attach3DTiltCards();
  attachMagneticElements();
});
