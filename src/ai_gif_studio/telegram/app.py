from aiogram import Bot, Dispatcher

from ai_gif_studio.services import IntakeService

from .router import create_router


def create_bot(token: str) -> Bot:
    return Bot(token=token)


def create_dispatcher(intake_service: IntakeService) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(create_router(intake_service))
    return dispatcher
