const assert = require('node:assert/strict');
const test = require('node:test');
const { readGenerationStream } = require('../frontend/js/generation_stream.js');

function fakeAbortController() {
  return {
    signal: { aborted: false },
    abort() { this.signal.aborted = true; },
  };
}

test('invalid NDJSON aborts the request and cancels the reader', { timeout: 1000 }, async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode('{bad json\n')); },
    cancel() { cancelled = true; },
  });
  const abortController = fakeAbortController();

  await assert.rejects(
    readGenerationStream(stream, abortController, () => {}),
    /无法解析的流式数据/
  );

  assert.equal(abortController.signal.aborted, true);
  assert.equal(cancelled, true);
});

test('UTF-8 split chunks and a final line without newline produce a guide', { timeout: 1000 }, async () => {
  const events = [
    JSON.stringify({ type: 'progress', progress: 30, stage: 'route', message: '路线规划中' }),
    JSON.stringify({ type: 'guide', guide: { title: '安阳漫游' } }),
  ];
  const bytes = new TextEncoder().encode(events.join('\n'));
  const splitAt = bytes.findIndex(value => value >= 0xe0) + 1;
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(bytes.slice(0, splitAt));
      controller.enqueue(bytes.slice(splitAt, splitAt + 2));
      controller.enqueue(bytes.slice(splitAt + 2));
      controller.close();
    },
  });
  const abortController = fakeAbortController();
  const progress = [];

  const result = await readGenerationStream(stream, abortController,
    (pct, stage, message) => progress.push({ pct, stage, message }));

  assert.equal(result.terminal, 'guide');
  assert.equal(result.guide.title, '安阳漫游');
  assert.deepEqual(progress, [{ pct: 30, stage: 'route', message: '路线规划中' }]);
  assert.equal(abortController.signal.aborted, false);
});

test('events after a terminal guide are rejected and cancel the open stream', { timeout: 1000 }, async () => {
  let cancelled = false;
  const payload = [
    JSON.stringify({ type: 'guide', guide: { title: '安阳漫游' } }),
    JSON.stringify({ type: 'progress', progress: 100, stage: 'done', message: '完成' }),
  ].join('\n') + '\n';
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode(payload)); },
    cancel() { cancelled = true; },
  });
  const abortController = fakeAbortController();

  await assert.rejects(
    readGenerationStream(stream, abortController, () => {}),
    /终止事件后仍发送了数据/
  );
  assert.equal(abortController.signal.aborted, true);
  assert.equal(cancelled, true);
});
