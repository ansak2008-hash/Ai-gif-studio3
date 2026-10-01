import asyncio
import pytest

from ai_gif_studio.worker import _cleanup_resources


class _Session:
    def __init__(self, error=None):
        self.error = error
        self.closed = 0

    async def close(self):
        self.closed += 1
        if self.error is not None:
            raise self.error


class _Bot:
    def __init__(self, error=None):
        self.session = _Session(error)


class _Db:
    def __init__(self, error=None):
        self.error = error
        self.disposed = 0

    async def dispose(self):
        self.disposed += 1
        if self.error is not None:
            raise self.error


class _Path:
    def __init__(self, error=None):
        self.error = error
        self.unlink_calls = 0

    def unlink(self, *, missing_ok=False):
        self.unlink_calls += 1
        if self.error is not None:
            raise self.error


pytestmark = pytest.mark.unit


async def test_cleanup_attempts_every_resource_and_reports_all_failures() -> None:
    source = _Path(RuntimeError("source cleanup"))
    bot = _Bot(RuntimeError("telegram cleanup"))
    db = _Db(RuntimeError("database cleanup"))

    errors = await _cleanup_resources(source=source, bot=bot, db=db)

    assert source.unlink_calls == 1
    assert bot.session.closed == 1
    assert db.disposed == 1
    assert [str(error) for error in errors] == [
        "source cleanup",
        "telegram cleanup",
        "database cleanup",
    ]


async def test_cleanup_is_successful_for_all_acquired_resources() -> None:
    source = _Path()
    bot = _Bot()
    db = _Db()

    errors = await _cleanup_resources(source=source, bot=bot, db=db)

    assert errors == []
    assert source.unlink_calls == 1
    assert bot.session.closed == 1
    assert db.disposed == 1


async def test_cleanup_does_not_touch_unacquired_source() -> None:
    bot = _Bot()
    db = _Db()

    errors = await _cleanup_resources(source=None, bot=bot, db=db)

    assert errors == []
    assert bot.session.closed == 1
    assert db.disposed == 1


async def test_cleanup_captures_cancellation_from_cleanup_without_losing_the_error() -> None:
    source = _Path(asyncio.CancelledError("cleanup cancelled"))
    bot = _Bot()
    db = _Db()

    errors = await _cleanup_resources(source=source, bot=bot, db=db)

    assert len(errors) == 1
    assert isinstance(errors[0], asyncio.CancelledError)
    assert bot.session.closed == 1
    assert db.disposed == 1

async def test_process_job_preserves_primary_error_when_cleanup_also_fails(
    monkeypatch,
) -> None:
    import ai_gif_studio.worker as worker

    class _Settings:
        database_url = "unused"
        telegram_bot_token = "token"

    class _FailingDb(_Db):
        pass

    class _FailingBot(_Bot):
        pass

    class _Repo:
        def __init__(self, _session_factory):
            pass

        async def get(self, _job_id):
            raise RuntimeError("primary processing failure")

    db = _FailingDb(RuntimeError("database cleanup failure"))
    bot = _FailingBot(RuntimeError("telegram cleanup failure"))

    monkeypatch.setattr(worker, "get_settings", lambda: _Settings())
    monkeypatch.setattr(worker, "Database", lambda _url: db)
    monkeypatch.setattr(worker, "Bot", lambda _token: bot)
    monkeypatch.setattr(worker, "SqlAlchemyJobRepository", _Repo)

    with pytest.raises(RuntimeError, match="primary processing failure"):
        await worker.process_job(None, "00000000-0000-0000-0000-000000000001")
