import logging

from aiogram import Bot, Router
from aiogram.types import BufferedInputFile, Message, ReactionTypeEmoji
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai_client import AIClient
from bot.db.repo import get_chat_context, get_or_create_user, save_message
from bot.media import get_audio_bytes, get_document_text, get_image_base64, get_video_frames_base64
from bot.memes import download_meme, fetch_meme_url
from bot.tts import text_to_speech

router = Router()
logger = logging.getLogger(__name__)


def _detect_media(message: Message) -> tuple[str | None, str | None, str | None]:
    if message.photo:
        return "photo", message.photo[-1].file_id, None
    if message.video:
        return "video", message.video.file_id, message.video.file_name
    if message.voice:
        return "voice", message.voice.file_id, None
    if message.audio:
        return "audio", message.audio.file_id, message.audio.file_name
    if message.video_note:
        return "video", message.video_note.file_id, None
    if message.document:
        return "document", message.document.file_id, message.document.file_name
    return None, None, None


@router.message()
async def handle_message(
    message: Message, session: AsyncSession, ai: AIClient, bot: Bot
):
    text = message.text or message.caption or ""
    image_base64 = None
    extra_context = ""
    media_type, file_id, file_name = _detect_media(message)

    image_base64 = await get_image_base64(message, bot)

    if message.voice or message.audio:
        audio_data, filename = await get_audio_bytes(message, bot)
        if audio_data:
            transcription = await ai.transcribe_audio(audio_data, filename)
            if transcription:
                extra_context += f"[Голосовое сообщение]: {transcription}\n"

    if message.video or (
        message.document and message.document.mime_type and message.document.mime_type.startswith("video/")
    ):
        frames = await get_video_frames_base64(message, bot)
        if frames:
            image_base64 = frames[0]
            extra_context += f"[Видео: извлечено {len(frames)} кадров для анализа]\n"

    if message.video_note:
        audio_data, filename = await get_audio_bytes(message, bot)
        if audio_data:
            transcription = await ai.transcribe_audio(audio_data, filename)
            if transcription:
                extra_context += f"[Речь из видеосообщения]: {transcription}\n"
        frames = await get_video_frames_base64(message, bot)
        if frames:
            image_base64 = frames[0]

    if message.document and not image_base64:
        doc_text = await get_document_text(message, bot)
        if doc_text:
            extra_context += f"[Содержимое документа]:\n{doc_text}\n"

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

    chat_history = await get_chat_context(session, message.from_user.id, limit=30)

    reply_text, meme_query = await ai.generate_reply(
        user_message=full_message,
        chat_history=chat_history,
        image_base64=image_base64,
    )

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=full_message or "(медиа)",
        bot_reply=reply_text,
        media_type=media_type,
        file_id=file_id,
        file_name=file_name,
    )

    # Set reaction
    try:
        reaction_emoji = await ai.pick_reaction(full_message or "медиа")
        if reaction_emoji:
            await message.react([ReactionTypeEmoji(emoji=reaction_emoji)])
    except Exception as e:
        logger.warning("Failed to set reaction: %s", e)

    await message.answer(reply_text)

    # Send meme if AI suggested one
    if meme_query:
        try:
            meme_url = await fetch_meme_url(meme_query)
            if meme_url:
                meme_bytes = await download_meme(meme_url)
                if meme_bytes:
                    meme_file = BufferedInputFile(meme_bytes, filename="meme.jpg")
                    await message.answer_photo(meme_file)
        except Exception as e:
            logger.warning("Failed to send meme: %s", e)

    # Send voice version
    voice_bytes = await text_to_speech(reply_text)
    if voice_bytes:
        voice_file = BufferedInputFile(voice_bytes, filename="reply.ogg")
        await message.answer_voice(voice_file)
