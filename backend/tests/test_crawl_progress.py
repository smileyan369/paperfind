import asyncio
import contextlib
import unittest

from app.routers.crawl import CrawlEventBus


class CrawlProgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_progress_tick_broadcasts_bounded_progress(self):
        bus = CrawlEventBus()
        q = bus.subscribe()
        bus.running = True
        bus.progress = 90
        bus.message = "testing"

        task = asyncio.create_task(bus._tick_progress())
        try:
            event = await asyncio.wait_for(q.get(), timeout=1.5)
        finally:
            bus.running = False
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        self.assertEqual(event["type"], "progress")
        self.assertEqual(event["message"], "testing")
        self.assertGreaterEqual(event["progress"], 90)
        self.assertLessEqual(event["progress"], 92)


if __name__ == "__main__":
    unittest.main()
