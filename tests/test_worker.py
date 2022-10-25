import asyncio
import multiprocessing
import unittest

from scaled.system.worker import Worker
from scaled.system.io.binder import Binder
from scaled.system.config import ZMQConfig, ZMQType
from scaled.system.objects import HeartbeatInfo


class TestWorker(unittest.TestCase):
    def test_worker(self):
        async def callback(frames):
            print(HeartbeatInfo.from_bytes(frames[3]))

        config = ZMQConfig(type=ZMQType.tcp, host="127.0.0.1", port=12346)

        stop_event = multiprocessing.get_context("spawn").Event()

        worker = Worker(address=config, stop_event=stop_event)
        worker.start()

        async_stop_event = asyncio.Event()
        driver = Binder("Backend", address=config, stop_event=async_stop_event)
        driver.register(callback)
        asyncio.run(driver.start())