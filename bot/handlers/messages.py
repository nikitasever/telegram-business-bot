import logging

from aiogram import Bot, Router
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai_client import AIClient
from bot.db.repo import get_chat_context, get_or_create_user, save_message
from bot.media import get_audio_bytes, get_document_text, get_image_base64, get_video_frames_base64
from bot.tts import text_to_speech

router = Router()
logger = logging.getLogger(__name__)


@router.message()
async def handle_message(
    message: Message, session: AsyncSession, ai: AIClient, bot: Bot
):
    text = message.text or message.caption or ""
    image_base64 = None
    extra_context = ""

    # --- Image ---
    image_base64 = await get_image_base64(message, bot)

    # --- Voice / Audio ---
    if message.voice or message.audio:
        audio_data, filename = await get_audio_bytes(message, bot)
        if audio_data:
            transcription = await ai.transcribe_audio(audio_data, filename)
            if transcription:
                extra_context += f"[Голосовое сообщение]: {transcription}\n"

    # --- Video ---
    if message.video or (
        message.document and message.document.mime_type and message.document.mime_type.startswith("video/")
    ):
        frames = await get_video_frames_base64(message, bot)
        if frames:
            image_base64 = frames[0]
            extra_context += f"[Видео: извлечено {len(frames)} кадров для анализа]\n"

    # --- Video note (circle video) ---
    if message.video_note:
        audio_data, filename = await get_audio_bytes(message, bot)
        if audio_data:
            transcription = await ai.transcribe_audio(audio_data, filename)
            if transcription:
                extra_context += f"[Речь из видеосообщения]: {transcription}\n"
        frames = await get_video_frames_base64(message, bot)
        if frames:
            image_base64 = frames[0]

    # --- Documents ---
    if message.document and not image_base64:
        doc_text = await get_document_text(message, bot)
        if doc_text:
            extra_context += f"[Содержимое документа]:\n{doc_text}\n"

    # Build final message
    full_message = ""
    if extra_context:
        full_message += extra_context.strip() + "\n\n"
    if text:
        full_message += text

    full_message = full_message.strip()

    if not full_message and not image_base64:
        return

    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    chat_history = await get_chat_context(session, message.from_user.id)

    reply_text = await ai.generate_reply(
        user_message=full_message,
        chat_history=chat_history,
        image_base64=image_base64,
    )

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=full_message or "(медиа)",
        bot_reply=reply_text,
    )

    await message.answer(reply_text)

    # Send voice version too
    voice_bytes = await text_to_speech(reply_text)
    if voice_bytes:
        voice_file = BufferedInputFile(voice_bytes, filename="reply.ogg")
        await message.answer_voice(voice_file)
