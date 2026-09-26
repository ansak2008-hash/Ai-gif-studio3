from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ai_gif_studio.models import VideoSubmission
from ai_gif_studio.services import IntakeError, IntakeService


def create_router(intake_service: IntakeService) -> Router:
    router = Router(name="video_intake")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer("Send a video to register it for GIF processing.")

    @router.message(F.video)
    async def receive_video(message: Message) -> None:
        if message.from_user is None or message.video is None:
            return
        video = message.video
        try:
            job = await intake_service.receive_video(
                VideoSubmission(
                    telegram_file_id=video.file_id,
                    original_filename=video.file_name,
                    content_type=video.mime_type,
                    file_size_bytes=video.file_size or 0,
                    submitted_by=message.from_user.id,
                )
            )
        except IntakeError as error:
            await message.answer(str(error))
            return
        await message.answer(
            f"Video accepted as job `{job.id}`. "
            "Processing is not enabled in this foundation release.",
            parse_mode="Markdown",
        )

    return router
