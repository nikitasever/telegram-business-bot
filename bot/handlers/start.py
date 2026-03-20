from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import get_or_create_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    await message.answer(
        f"Здравствуйте, {message.from_user.full_name}!\n\n"
        "Я бизнес-бот. Напишите мне любое сообщение, "
        "и я отвечу вам развёрнуто.\n\n"
        "Команды:\n"
        "/start — приветствие\n"
        "/history — история ваших обращений"
    )
