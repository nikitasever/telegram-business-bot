import base64
import io
import logging

from aiogram import Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai_client import AIClient
from bot.db.repo import get_chat_context, get_or_create_user, save_message

router = Router()
logger = logging.getLogger(__name__)


async def _get_image_base64(message: Message, bot: Bot) -> str | None:
    """Download photo from message and return as base64 string."""
    try:
        photo = None
        if message.photo:
            photo = message.photo[-1]  # largest size
            logger.info("Got photo from message, file_id: %s", photo.file_id)
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
            photo = message.document
            logger.info("Got image document, file_id: %s", photo.file_id)

        if not photo:
            return None

        file = await bot.get_file(photo.file_id)
        logger.info("File path: %s", file.file_path)
        buffer = io.BytesIO()
        await bot.download_file(file.file_path, buffer)
        data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        logger.info("Image downloaded, base64 length: %d", len(data))
        return data
    except Exception as e:
        logger.error("Failed to download image: %s", e, exc_info=True)
        return None


@router.business_message()
async def handle_business_message(
    message: Message, session: AsyncSession, ai: AIClient, bot: Bot
):
    text = message.text or message.caption or ""
    image_base64 = await _get_image_base64(message, bot)

    logger.info(
        "Business message from %s: text=%s, has_image=%s",
        message.from_user.id, bool(text), bool(image_base64),
    )

    # Skip if no text and no image
    if not text and not image_base64:
        return

    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    # Load full chat history for context
    chat_history = await get_chat_context(session, message.from_user.id)

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
