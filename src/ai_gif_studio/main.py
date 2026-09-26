from __future__ import annotations
import asyncio
from ai_gif_studio.configuration import get_settings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.infrastructure.queue import ArqQueue
from ai_gif_studio.logging import configure_logging
from ai_gif_studio.services import IntakeService
from ai_gif_studio.telegram import create_bot,create_dispatcher
async def run():
    s=get_settings()
    if not s.telegram_bot_token: raise RuntimeError("TELEGRAM_BOT_TOKEN must be configured.")
    s.temp_directory.mkdir(parents=True,exist_ok=True); s.storage_directory.mkdir(parents=True,exist_ok=True)
    configure_logging(s.log_level); db=Database(s.database_url); await db.create_schema(); queue=await ArqQueue(s.redis_url).connect()
    intake=IntakeService(SqlAlchemyJobRepository(db.session_factory),s.max_upload_bytes,s.telegram_allowed_user_ids)
    bot=create_bot(s.telegram_bot_token)
    try: await create_dispatcher(intake,queue).start_polling(bot)
    finally: await queue.close(); await bot.session.close(); await db.dispose()
def main(): asyncio.run(run())
