from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ai_gif_studio.models import VideoSubmission
from ai_gif_studio.services import IntakeError, IntakeService


def create_router(intake_service: IntakeService, queue=None) -> Router:
    router = Router(name="video_intake")

    @router.message(CommandStart())
    async def start(message: Message):
        await message.answer("Send a short video to create a 320×320 GIF.")

    @router.message(F.video)
    async def receive_video(message: Message):
        if not message.from_user or not message.video:
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
                    source_message_id=message.message_id,
                )
            )
            if queue is None:
                await message.answer(f"Job {job.id} created.")
                return

            await intake_service.mark_queued(job)
            try:
                queued = await queue.enqueue_job(str(job.id), _job_id=str(job.id))
            except Exception:
                await intake_service.mark_created(job)
                raise
            if queued is None:
                await intake_service.mark_created(job)
                await message.answer("This job is already queued or being processed.")
                return
            await message.answer(f"Job {job.id} queued.")
        except IntakeError as error:
            await message.answer(str(error))
        except Exception:
            await message.answer("The job could not be queued. Please try again.")
            raise

    return router
