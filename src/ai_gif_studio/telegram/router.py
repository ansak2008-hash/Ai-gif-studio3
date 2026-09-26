from aiogram import F,Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from ai_gif_studio.models import VideoSubmission
from ai_gif_studio.services import IntakeError,IntakeService
def create_router(intake_service:IntakeService,queue=None)->Router:
    router=Router(name="video_intake")
    @router.message(CommandStart())
    async def start(message:Message): await message.answer("Send a short video to create a 320×320 GIF.")
    @router.message(F.video)
    async def receive_video(message:Message):
        if not message.from_user or not message.video: return
        v=message.video
        try:
            job=await intake_service.receive_video(VideoSubmission(telegram_file_id=v.file_id,original_filename=v.file_name,content_type=v.mime_type,file_size_bytes=v.file_size or 0,submitted_by=message.from_user.id))
        except IntakeError as error:
            await message.answer(str(error)); return
        if queue is not None:
            await queue.enqueue_job(str(job.id),_job_id=str(job.id))
            await intake_service.mark_queued(job)
            await message.answer(f"Job {job.id} queued.")
        else:
            await message.answer(f"Job {job.id} created.")
    return router
