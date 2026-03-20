import base64
import io

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai_client import AIClient
from bot.db.repo import get_chat_context, get_or_create_user, save_message

router = Router()


async def _get_image_base64(message: Message, bot: Bot) -> str | None:
    """Download photo from message and return as base64 string."""
    photo = None
    if message.photo:
        photo = message.photo[-1]
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        photo = message.document

    if not photo:
        return None

    file = await bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@router.message(F.text | F.photo | F.document)
async def handle_message(
    message: Message, session: AsyncSession, ai: AIClient, bot: Bot
):
    text = message.text or message.caption or ""
    image_base64 = await _get_image_base64(message, bot)

    if not text and not image_base64:
        return

    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    chat_history = await get_chat_context(session, message.from_user.id, limit=10)

    reply_text = await ai.generate_reply(
        user_message=text,
        chat_history=chat_history,
        image_base64=image_base64,
    )

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=text or "(изображение)",
        bot_reply=reply_text,
    )

    await message.answer(reply_text)
