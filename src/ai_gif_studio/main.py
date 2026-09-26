from __future__ import annotations

import asyncio

from ai_gif_studio.configuration import get_settings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.logging import configure_logging
from ai_gif_studio.services import IntakeService
from ai_gif_studio.telegram import create_bot, create_dispatcher


async def run() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be configured before starting the bot.")
    settings.temp_directory.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_level)
    database = Database(settings.database_url)
    await database.create_schema()
    intake_service = IntakeService(
        SqlAlchemyJobRepository(database.session_factory),
        settings.max_upload_bytes,
        settings.telegram_allowed_user_ids,
    )
    bot = create_bot(settings.telegram_bot_token)
    try:
        await create_dispatcher(intake_service).start_polling(bot)
    finally:
        await bot.session.close()
        await database.dispose()


def main() -> None:
    asyncio.run(run())
