"""Disconnecting from the NDJSON response must cancel its generation task."""

import asyncio
import json
import unittest
from unittest.mock import patch

import app


class StreamCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_disconnect_cancels_backend_generation(self):
        generation_started = asyncio.Event()
        generation_cancelled = asyncio.Event()

        class HangingOrchestrator:
            async def generate(self, query, on_progress=None, request_overrides=None):
                try:
                    generation_started.set()
                    if on_progress:
                        on_progress(5, "intent", "正在理解需求")
                    await asyncio.Event().wait()
                finally:
                    generation_cancelled.set()

        class RequestStub:
            disconnected = False

            async def is_disconnected(self):
                return self.disconnected

        request = RequestStub()
        with patch.object(app, "_request_orchestrator", return_value=HangingOrchestrator()):
            response = await app.api_generate_stream(app.GenReq(query="安阳玩3天"), request)
            events = response.body_iterator
            first_event = await asyncio.wait_for(anext(events), timeout=1)
            self.assertIn('"type": "progress"', first_event)
            self.assertTrue(generation_started.is_set())
            request.disconnected = True
            with self.assertRaises(StopAsyncIteration):
                await asyncio.wait_for(anext(events), timeout=1)

        self.assertTrue(generation_cancelled.is_set(), "disconnect should cancel the backend task")

    async def test_full_asgi_disconnect_waits_for_async_generation_cleanup(self):
        generation_started = asyncio.Event()
        cleanup_started = asyncio.Event()
        cleanup_finished = asyncio.Event()

        class SlowCleanupOrchestrator:
            async def generate(self, query, on_progress=None, request_overrides=None):
                try:
                    generation_started.set()
                    if on_progress:
                        on_progress(5, "intent", "离线取消测试")
                    await asyncio.Event().wait()
                finally:
                    cleanup_started.set()
                    await asyncio.sleep(0.1)
                    cleanup_finished.set()

        first_receive = True

        async def receive():
            nonlocal first_receive
            if first_receive:
                first_receive = False
                return {
                    "type": "http.request",
                    "body": json.dumps({"query": "安阳玩3天"}).encode(),
                    "more_body": False,
                }
            await generation_started.wait()
            return {"type": "http.disconnect"}

        async def send(_message):
            return None

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/generate/stream",
            "raw_path": b"/api/generate/stream",
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"127.0.0.1"),
                (b"content-type", b"application/json"),
            ],
            "server": ("127.0.0.1", 18003),
            "client": ("127.0.0.1", 12345),
        }

        with patch.object(app, "_request_orchestrator", return_value=SlowCleanupOrchestrator()):
            await asyncio.wait_for(app.app(scope, receive, send), timeout=3)

        self.assertTrue(cleanup_started.is_set())
        self.assertTrue(
            cleanup_finished.is_set(),
            "the full ASGI disconnect path must await async generation cleanup",
        )


if __name__ == "__main__":
    unittest.main()
