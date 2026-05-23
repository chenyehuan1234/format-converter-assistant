from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from time import time

from .engines import EngineRegistry
from .history import HistoryStore
from .models import ConversionJob, JobStatus

LOGGER = logging.getLogger(__name__)


class JobQueue:
    def __init__(
        self,
        registry: EngineRegistry | None = None,
        history: HistoryStore | None = None,
        max_workers: int = 2,
    ) -> None:
        self.registry = registry or EngineRegistry()
        self.history = history or HistoryStore()
        self.max_workers = max(1, max_workers)
        self.jobs: list[ConversionJob] = []
        self._executor: ThreadPoolExecutor | None = None

    def add(self, job: ConversionJob) -> None:
        self.jobs.append(job)
        self.history.save_job(job)

    def clear_completed(self) -> None:
        self.jobs = [job for job in self.jobs if job.status not in {JobStatus.SUCCESS, JobStatus.FAILED}]

    def run_all(self, on_update=None) -> list[Future[ConversionJob]]:
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        futures: list[Future[ConversionJob]] = []
        for job in self.jobs:
            if job.status in {JobStatus.PENDING, JobStatus.FAILED}:
                futures.append(self._executor.submit(self._run_one, job, on_update))
        return futures

    def shutdown(self) -> None:
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    def cancel_pending(self) -> None:
        for job in self.jobs:
            if job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELED
                job.progress = 100
                self.history.save_job(job)

    def _run_one(self, job: ConversionJob, on_update=None) -> ConversionJob:
        job.status = JobStatus.RUNNING
        job.started_at = time()
        job.progress = 5
        self._notify(job, on_update)
        try:
            self.registry.convert(job)
            job.progress = 100
            job.status = JobStatus.SUCCESS
        except Exception as exc:
            LOGGER.exception("Conversion failed")
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.progress = 100
        finally:
            job.finished_at = time()
            self.history.save_job(job)
            self._notify(job, on_update)
        return job

    @staticmethod
    def _notify(job: ConversionJob, on_update) -> None:
        if on_update:
            on_update(job)
