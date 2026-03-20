from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai_client import AIClient
from bot.db.repo import get_or_create_user, save_message

router = Router()


@router.message(F.text)
async def handle_message(
    message: Message, session: AsyncSession, ai: AIClient
):
    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    reply_text = await ai.generate_reply(message.text)

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=message.text,
        bot_reply=reply_text,
    )

    await message.answer(reply_text)
