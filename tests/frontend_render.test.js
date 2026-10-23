/**
 * 第13–15轮前端渲染回归：在沙箱里直接调用页面渲染函数，验证新增区块真的产出内容。
 * 只验证字符串产物，不启动浏览器，也不检查视觉样式。
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadApp() {
  const code = fs.readFileSync(path.join(__dirname, '..', 'frontend', 'js', 'app.js'), 'utf8');
  const document = {
    getElementById: () => null,
    querySelectorAll: () => [],
    querySelector: () => null,
    createElement: () => ({ style: {}, classList: { add() {}, remove() {} } }),
    addEventListener: () => {},
    body: { appendChild: () => {} },
  };
  const window = {
    addEventListener: () => {},
    location: { href: 'http://127.0.0.1:8000/' },
    matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  };
  const context = {
    window,
    document,
    console,
    performance: { now: () => 0 },
    fetch: async () => { throw new Error('测试不应发起网络请求'); },
    setTimeout,
    clearTimeout,
    encodeURIComponent,
    URL,
    Intl,
    Date,
    Math,
    JSON,
  };
  context.window.document = document;
  vm.createContext(context);
  vm.runInContext(code, context);
  return context;
}

const app = loadApp();

function baseGuide(overrides) {
  return Object.assign({
    title: '《安阳三日》',
    subtitle: '安阳 · 3天2晚',
    destinations: ['安阳'],
    days: 3,
    budget_level: '中等',
    spots: [],
    cultures: [],
    weather: [],
    route: { route_name: '安阳三日', cities: ['安阳'], daily_plan: [], warnings: [], transport: [] },
    budget: { total: 1000, group_total: 1000, travelers: 1, nights: 2 },
  }, overrides || {});
}

test('导航包含第 9 个「行前」页且顺序稳定', () => {
  assert.strictEqual(app.PAGES.length, 9);
  assert.strictEqual(app.PAGES[0].id, 'home');
  assert.strictEqual(app.PAGES[1].id, 'map', 'switchPage 里 n === 1 仍应指向地图页');
  assert.strictEqual(app.PAGES[8].id, 'prep');
  assert.strictEqual(app.PAGES[8].l, '行前');
});

test('rPrep 渲染温度、逐日方案与打包清单', () => {
  const html = app.rPrep(baseGuide({
    prep: {
      temperature_range: { low: -5, high: 8 },
      weather_plans: [
        { day: 1, city: '安阳', weather: '小雨', status: 'ok', advice: ['当天有降水，把户外点位换成室内类别。'] },
        { day: 2, city: '安阳', status: 'no_forecast', advice: [] },
      ],
      packing: [{ group: '衣物', items: ['羽绒服', '舒适鞋'], basis: '按预报温度推算' }],
      notes: ['天气预报时效有限。'],
    },
  }));

  assert.match(html, /行前帖/);
  assert.match(html, /-5℃ ~ 8℃/);
  assert.match(html, /Day 1/);
  assert.match(html, /小雨/);
  assert.match(html, /室内类别/);
  assert.match(html, /没有对应的天气预报/);
  assert.match(html, /羽绒服/);
  assert.match(html, /按预报温度推算/);
  assert.match(html, /天气预报时效有限/);
});

test('rPrep 在没有数据时给出明确空状态而不是空白页', () => {
  const html = app.rPrep(baseGuide({ prep: {} }));
  assert.match(html, /没有生成行前清单/);
});

test('qualityBlock 渲染分数、维度与可改进项', () => {
  const html = app.qualityBlock(baseGuide({
    quality: {
      score: 82,
      grade: 'B',
      dimensions: {
        structure: { label: '结构完整', score: 100, weight: 0.2 },
        budget: { label: '预算说明', score: 70, weight: 0.15 },
      },
      issues: ['有 2 段城际交通未核价。'],
      notes: ['评分只衡量完整度。'],
    },
  }));

  assert.match(html, /攻略自检/);
  assert.match(html, /82/);
  assert.match(html, /等级 B/);
  assert.match(html, /结构完整/);
  assert.match(html, /预算说明/);
  assert.match(html, /可改进/);
  assert.match(html, /有 2 段城际交通未核价/);
});

test('qualityBlock 在没有评分时返回空串', () => {
  assert.strictEqual(app.qualityBlock(baseGuide({ quality: {} })), '');
  assert.strictEqual(app.qualityBlock(baseGuide({})), '');
});

test('质量分 0 分仍然展示，不被当成空值', () => {
  const html = app.qualityBlock(baseGuide({
    quality: { score: 0, grade: 'D', dimensions: {}, issues: [], notes: [] },
  }));
  assert.match(html, /攻略自检/);
  assert.match(html, /0/);
});

test('rHome 在缓存命中时显示复用提示与强制刷新按钮', () => {
  const html = app.rHome(baseGuide({
    cache_hit: true,
    cache_age_seconds: 420,
    generation_metrics: { elapsed_ms: 1200, llm: { requests: 4, total_tokens: 600 } },
  }), '安阳');
  assert.match(html, /复用/);
  assert.match(html, /7 分钟/);
  assert.match(html, /startGenerate\(true\)/);
  assert.match(html, /原攻略生成统计/);
  assert.match(html, /原生成模型请求 4 次/);
});

test('rHome 在未命中缓存时不显示复用提示', () => {
  const html = app.rHome(baseGuide({ cache_hit: false }), '安阳');
  assert.doesNotMatch(html, /本次复用了/);
});

test('rHome 渲染可执行性摘要与逐日通勤', () => {
  const guide = baseGuide({
    feasibility: {
      checked: true,
      score: 72,
      level: 'B',
      notes: ['按已核验坐标计算直线距离。'],
      issues: ['第1天第1段通勤约90公里，建议核对是否同城。'],
      days: [{ day: 1, city: '安阳', activities: 2, distance_km: 90, max_leg_km: 90, estimated_hours: 7.3, issues: [] }],
    },
    route: {
      route_name: '安阳三日', cities: ['安阳'], warnings: [], transport: [],
      daily_plan: [{
        day: 1, city: '安阳', morning: { name: '殷墟', note: '' }, afternoon: {}, evening: {}, stay: '',
      }],
    },
  });
  const home = app.rHome(guide, '安阳');
  assert.match(home, /可执行性/);
  assert.match(home, /72/);
  assert.match(home, /行程紧凑度提醒/);

  const days = app.rDays(guide);
  assert.match(days, /当天在途约 90 km/);
  assert.match(days, /粗估含在途 7.3 小时/);
});

test('rSpots renders safe sources, ticket leads, and non-embedded image candidates', () => {
  const guide = baseGuide({
    spots: [{
      name: '故宫博物院', city: '北京市', tier: 1, ticket: 188,
      ticket_status: 'reference', photo: '', photo_source: 'none',
    }],
    web_research: {
      status: 'complete', search_count: 1, fetch_count: 1,
      spots: [{
        spot_index: 0, spot_name: '故宫博物院', city: '北京市', status: 'searched',
        evidence: [{
          title: '北京故宫博物院门票', url: 'https://example.com/palace',
          fetched_at: '2026-10-23T01:02:03+00:00',
          snippet: '<script>摘要</script>',
          price_quotes: ['成人票 ¥60，日期待核实。'],
          quotes: ['预约开放时间见页面。'],
          image_candidates: [{
            url: 'https://images.example/palace.jpg', alt: '故宫红墙',
            status: 'downloaded', local_url: '/static/photos/web-research/' + 'a'.repeat(64) + '.jpg',
          }],
        }],
      }],
    },
  });
  const html = app.rSpots(guide);
  assert.match(html, /网页票价线索（不计入预算）/);
  assert.match(html, /成人票 ¥60/);
  assert.match(html, /https:\/\/example.com\/palace/);
  assert.match(html, /本机安全缓存图/);
  assert.match(html, /内容、景点关联及使用授权未核验/);
  assert.match(html, /&lt;script&gt;摘要&lt;\/script&gt;/);
  assert.doesNotMatch(html, /src="https:\/\/images\.example\/palace\.jpg"/);
});

test('rSpots explicitly shows the disabled and unsearched state', () => {
  const html = app.rSpots(baseGuide({
    spots: [{ name: '殷墟', city: '安阳市', tier: 1, photo: '', photo_source: 'none' }],
    web_research: { status: 'disabled', spots: [{ spot_index: 0, status: 'disabled', evidence: [] }] },
  }));
  assert.match(html, /联网检索已关闭，本景点未发起 Search\/Fetch/);
});
