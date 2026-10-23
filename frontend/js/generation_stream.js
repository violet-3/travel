/* Strict NDJSON parsing and reader cleanup for the generation endpoint. */
(function(root) {
  function parseEvent(line, state, onProgress) {
    line = line.trim();
    if (!line) return;
    if (state.terminal) throw new Error('服务端在终止事件后仍发送了数据');

    var event;
    try {
      event = JSON.parse(line);
    } catch (error) {
      throw new Error('服务端返回了无法解析的流式数据');
    }
    if (!event || typeof event !== 'object' || Array.isArray(event)) {
      throw new Error('服务端返回了无效的流式事件');
    }
    if (event.type === 'progress') {
      var progress = Number(event.progress);
      if (!Number.isFinite(progress) || progress < 0 || progress > 100 ||
          typeof event.stage !== 'string' || typeof event.message !== 'string') {
        throw new Error('服务端返回了无效的进度事件');
      }
      onProgress(progress, event.stage, event.message);
      return;
    }
    if (event.type === 'guide') {
      if (!event.guide || typeof event.guide !== 'object' || Array.isArray(event.guide)) {
        throw new Error('服务端返回的攻略内容无效');
      }
      state.terminal = 'guide';
      state.guide = event.guide;
      return;
    }
    if (event.type === 'error') {
      state.terminal = 'error';
      state.error = typeof event.message === 'string' && event.message
        ? event.message : '生成失败';
      state.metrics = event.metrics && typeof event.metrics === 'object' ? event.metrics : null;
      return;
    }
    throw new Error('服务端返回了未知的流式事件');
  }

  async function readGenerationStream(body, abortController, onProgress) {
    var reader = body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';
    var streamEnded = false;
    var state = { terminal: null, guide: null, error: null, metrics: null };
    try {
      for (;;) {
        var chunk = await reader.read();
        if (chunk.done) {
          buffer += decoder.decode();
          if (buffer.trim()) parseEvent(buffer, state, onProgress);
          streamEnded = true;
          break;
        }
        buffer += decoder.decode(chunk.value, { stream: true });
        var lines = buffer.split('\n');
        buffer = lines.pop();
        for (var index = 0; index < lines.length; index++) {
          parseEvent(lines[index], state, onProgress);
        }
      }
      if (!state.terminal) throw new Error('服务端流结束前未发送终止事件');
      return state;
    } finally {
      if (!streamEnded && abortController && abortController.signal &&
          !abortController.signal.aborted) {
        abortController.abort();
      }
      try { await reader.cancel(); } catch (error) {}
      try { reader.releaseLock(); } catch (error) {}
    }
  }

  var api = { readGenerationStream: readGenerationStream };
  root.TravelGenerationStream = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
