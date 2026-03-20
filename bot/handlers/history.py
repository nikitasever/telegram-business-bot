from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import get_user_history

router = Router()


@router.message(Command("history"))
async def cmd_history(message: Message, session: AsyncSession):
    messages = await get_user_history(session, message.from_user.id)

    if not messages:
        await message.answer("У вас пока нет истории обращений.")
        return

    lines = ["📋 Ваши последние обращения:\n"]
    for i, msg in enumerate(reversed(messages), 1):
        date = msg.created_at.strftime("%d.%m.%Y %H:%M")
        lines.append(f"{i}. [{date}]\n   Вы: {msg.text[:80]}")

    await message.answer("\n".join(lines))
