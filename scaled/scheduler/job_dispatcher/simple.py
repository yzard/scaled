import asyncio
import uuid
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from scaled.protocol.python.objects import TaskStatus, MessageType
from scaled.protocol.python.message import (
    Task,
    GraphJob,
    TaskResult,
)
from scaled.scheduler.mixins import Binder, JobDispatcher, WorkerManager


class SimpleJobDispatcher(JobDispatcher):
    def __init__(self, stop_event: asyncio.Event):
        self._stop_event = stop_event

        self._binder: Optional[Binder] = None
        self._worker_manager: Optional[WorkerManager] = None

        self._function_map: Dict[bytes, bytes] = {}

        self._job_id_to_sub_job_ids: Dict[bytes, List[bytes]] = defaultdict(list)
        self._job_id_to_sub_job_count: Dict[bytes, int] = {}
        self._job_id_to_client: Dict[bytes, bytes] = {}
        self._job_id_func_to_job_result: Dict[Tuple[bytes, bytes], Tuple[bytes, ...]] = {}

        self._sub_job_id_to_job_id: Dict[bytes, bytes] = {}
        self._sub_job_id_to_job: Dict[bytes, Task] = {}
        self._sub_job_id_to_result: Dict[bytes, Tuple[bytes, ...]] = {}

    def hook(self, binder: Binder, worker_manager: WorkerManager):
        self._binder = binder
        self._worker_manager = worker_manager

    async def loop(self):
        while not self._stop_event.is_set():
            if not self._job_id_func_to_job_result:
                await asyncio.sleep(0)
                continue

            (job_id, function_name), results = self._job_id_func_to_job_result.popitem()
            client = self._job_id_to_client.pop(job_id)
            await self._binder.on_send(
                client, MessageType.JobResult, TaskResult(
                    job_id, function_name, TaskStatus.Success,
                    results
                )
            )

    async def on_job(self, client: bytes, job: Task) -> List[Task]:
        sub_jobs = []
        for args in job.function_args:
            sub_jobs.append(self._create_sub_job(job.task_id, job.function_name, args))

        self._job_id_to_sub_job_count[job.task_id] = 0
        self._job_id_to_client[job.task_id] = client
        return sub_jobs

    async def on_new_graph_job(self, client: bytes, job: GraphJob):
        # TODO: implement it later
        pass

    async def on_job_done(self, job_result: TaskResult):
        """job done can be success or failed"""
        if job_result.status == TaskStatus.Success:
            self._on_sub_job_done(job_result)
            return

        job_id = self._sub_job_id_to_job_id[job_result.task_id]
        await self.on_cancel_job(job_id, job_result.result)

    async def on_cancel_job(self, job_id: bytes, message: Tuple[bytes, ...]):
        # TODO: implement it
        #  - cancel all sub jobs belong to a job
        #  - clean memory
        #  - mo
        raise NotImplementedError()

    def _create_sub_job(self, job_id: bytes, function_name: bytes, args: bytes) -> Task:
        sub_job_id = uuid.uuid1().bytes
        sub_job = Task(sub_job_id, function_name, (args,))
        self._sub_job_id_to_job[sub_job_id] = sub_job
        self._sub_job_id_to_job_id[sub_job_id] = job_id
        self._job_id_to_sub_job_ids[job_id].append(sub_job_id)
        return sub_job

    def _on_sub_job_done(self, sub_job_result: TaskResult):
        self._sub_job_id_to_result[sub_job_result.task_id] = sub_job_result.result

        sub_job_id = sub_job_result.task_id
        self._sub_job_id_to_job.pop(sub_job_id)
        job_id = self._sub_job_id_to_job_id.pop(sub_job_id)

        self._job_id_to_sub_job_count[job_id] += 1

        # not all tasks are done
        if self._job_id_to_sub_job_count[job_id] < len(self._job_id_to_sub_job_ids[job_id]):
            return

        self._job_id_to_sub_job_count.pop(job_id)
        self._function_map.pop(_create_function_key(job_id, sub_job_result.function_name))

        self._job_id_func_to_job_result[(job_id, sub_job_result.function_name)] = tuple(
            result
            for sub_job_id in self._job_id_to_sub_job_ids.pop(job_id)
            for results in self._sub_job_id_to_result.pop(sub_job_id)
            for result in results
        )


def _create_function_key(job_id: bytes, function_name: bytes) -> bytes:
    return job_id + b"|" + function_name
