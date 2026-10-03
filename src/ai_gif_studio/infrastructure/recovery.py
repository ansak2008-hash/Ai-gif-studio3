from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from redis.exceptions import RedisError

from ai_gif_studio.configuration import AppSettings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.domain.job_queue import QueueConfig
from ai_gif_studio.domain.recovery_contract import (
    RecoveryConfig,
    RecoveryDispatchError,
    RecoveryLockPort,
    RecoveryReport,
    RecoverySchedulerPort,
)
from ai_gif_studio.infrastructure.queue import ArqQueue

logger = logging.getLogger(__name__)


class RedisRecoveryLock(RecoveryLockPort):
    def __init__(self, redis, key: str = "ai-gif-studio:recovery-lock") -> None:
        self._redis = redis
        self._key = key

    async def try_acquire(self, ttl: timedelta) -> str | None:
        token = str(uuid4())
        acquired = await self._redis.set(
            self._key,
            token,
            nx=True,
            ex=max(1, int(ttl.total_seconds())),
        )
        return token if acquired else None

    async def release(self, token: str) -> None:
        await self._redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            self._key,
            token,
        )


class ArqRecoveryDispatcher:
    def __init__(self, queue: ArqQueue) -> None:
        self._queue = queue

    async def __call__(self, job_id: str) -> None:
        try:
            await self._queue.enqueue_job(job_id)
        except RedisError as error:
            raise RecoveryDispatchError(f"dispatch failed for job {job_id}") from error


class RecoveryScheduler(RecoverySchedulerPort):
    def __init__(
        self,
        repository: SqlAlchemyJobRepository,
        dispatcher,
        lock: RecoveryLockPort,
        config: RecoveryConfig | None = None,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher
        self._lock = lock
        self._config = config or RecoveryConfig()

    async def run_once(self, now: datetime) -> RecoveryReport:
        ttl = max(self._config.interval * 2, timedelta(seconds=60))
        token = await self._lock.try_acquire(ttl)
        if token is None:
            return RecoveryReport(0, 0, 0, False)

        recovered = 0
        redispatched = 0
        failures = 0
        try:
            recovered_ids = await self._repository.recover_expired_processing(
                now, max_attempts=QueueConfig().max_attempts
            )
            recovered = len(recovered_ids)
            snapshots = await self._repository.get_stale_queued(
                now - self._config.redispatch_grace,
                self._config.batch_size,
            )
            for job_id, _updated_at in snapshots:
                try:
                    await self._dispatcher(str(job_id))
                except RecoveryDispatchError:
                    failures += 1
                    continue
                redispatched += 1
            return RecoveryReport(recovered, redispatched, failures, True)
        finally:
            await self._lock.release(token)


async def recover_jobs(ctx) -> None:
    settings = AppSettings()
    db = Database(settings.database_url)
    queue = ArqQueue(settings.redis_url)
    await queue.connect()
    try:
        scheduler = RecoveryScheduler(
            SqlAlchemyJobRepository(db.session_factory),
            ArqRecoveryDispatcher(queue),
            RedisRecoveryLock(ctx["redis"]),
        )
        report = await scheduler.run_once(datetime.now(UTC))
        failure_key = "ai-gif-studio:recovery:consecutive-dispatch-failures"
        if report.dispatch_failures and not report.redispatched:
            failures = await ctx["redis"].incr(failure_key)
            if failures >= RecoveryConfig().max_consecutive_dispatch_failures:
                logger.warning("recovery dispatch failures reached threshold: %s", failures)
        elif report.redispatched:
            await ctx["redis"].delete(failure_key)
    finally:
        await queue.close()
        await db.dispose()


def cron_settings():
    from arq import cron

    return cron(
        recover_jobs,
        second={0, 30},
        unique=True,
        run_at_startup=True,
        timeout=20,
        max_tries=1,
    )
