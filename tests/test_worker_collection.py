import unittest

from scaled.protocol.python.message import Task
from scaled.scheduler.worker_manager.worker_collection import WorkerCollection


class TestWorkerCollection(unittest.TestCase):
    def test_worker_collection(self):
        collection = WorkerCollection()
        self.assertEqual(collection.size(), 0)
        self.assertEqual(collection.capacity(), 0)

        collection[b"a"] = None
        self.assertEqual(collection.size(), 1)
        self.assertEqual(collection.capacity(), 1)

        collection[b"b"] = None
        self.assertEqual(collection.size(), 2)
        self.assertEqual(collection.capacity(), 2)

        collection[b"c"] = None
        self.assertEqual(collection.size(), 3)
        self.assertEqual(collection.capacity(), 3)

        collection[b"a"] = Task(b"1", b"", (b"",))
        self.assertEqual(collection.size(), 3)
        self.assertEqual(collection.capacity(), 2)

        collection[b"b"] = Task(b"2", b"", (b"",))
        self.assertEqual(collection.size(), 3)
        self.assertEqual(collection.capacity(), 1)

        collection[b"d"] = None
        self.assertEqual(collection.size(), 4)
        self.assertEqual(collection.capacity(), 2)

        collection[b"a"] = None
        self.assertEqual(collection.size(), 4)
        self.assertEqual(collection.capacity(), 3)

        collection.pop(b"d")
        self.assertEqual(collection.size(), 3)
        self.assertEqual(collection.capacity(), 2)

        collection.pop(b"b")
        self.assertEqual(collection.size(), 2)
        self.assertEqual(collection.capacity(), 2)
