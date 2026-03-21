import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import get_all_users, get_stats, search_by_user, search_media, search_messages

router = Router()
logger = logging.getLogger(__name__)

MEDIA_EMOJI = {
    "photo": "🖼",
    "video": "🎥",
    "voice": "🎤",
    "audio": "🎵",
    "document": "📄",
}


@router.message(Command("search"))
async def cmd_search(message: Message, session: AsyncSession):
    """Search messages by text: /search <query>"""
    query = message.text.replace("/search", "", 1).strip()
    if not query:
        await message.answer(
            "🔍 Как искать:\n\n"
            "/search <текст> — поиск по сообщениям\n"
            "/find photo — найти фото\n"
            "/find video — найти видео\n"
            "/find voice — найти голосовые\n"
            "/find audio — найти аудио\n"
            "/find document — найти документы\n"
            "/user <имя> — сообщения от пользователя\n"
            "/users — все пользователи\n"
            "/stats — статистика"
        )
        return

    results = await search_messages(session, query)

    if not results:
        await message.answer(f"🔍 По запросу «{query}» ничего не найдено.")
        return

    lines = [f"🔍 Результаты по «{query}» ({len(results)}):\n"]
    for msg, user in results:
        date = msg.created_at.strftime("%d.%m.%Y %H:%M")
        name = user.full_name if user else "Неизвестный"
        media_icon = MEDIA_EMOJI.get(msg.media_type, "") if msg.media_type else ""
        text_preview = msg.text[:60].replace("\n", " ")
        lines.append(f"{media_icon} [{date}] {name}:\n   {text_preview}")

    text = "\n".join(lines)
    # Telegram message limit
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (показаны не все результаты)"
    await message.answer(text)


@router.message(Command("find"))
async def cmd_find(message: Message, session: AsyncSession, bot: Bot):
    """Find media by type: /find photo|video|voice|audio|document"""
    media_type = message.text.replace("/find", "", 1).strip().lower()

    valid_types = {"photo": "фото", "video": "видео", "voice": "голосовые", "audio": "аудио", "document": "документы"}

    if media_type not in valid_types:
        await message.answer(
            "📎 Укажите тип медиа:\n\n"
            "/find photo — фото\n"
            "/find video — видео\n"
            "/find voice — голосовые\n"
            "/find audio — аудио\n"
            "/find document — документы"
        )
        return

    results = await search_media(session, media_type)

    if not results:
        await message.answer(f"📎 {valid_types[media_type].capitalize()} не найдены.")
        return

    lines = [f"{MEDIA_EMOJI.get(media_type, '📎')} Найдено {valid_types[media_type]}: {len(results)}\n"]
    for msg, user in results:
        date = msg.created_at.strftime("%d.%m.%Y %H:%M")
        name = user.full_name if user else "Неизвестный"
        text_preview = msg.text[:60].replace("\n", " ")
        file_info = f" [{msg.file_name}]" if msg.file_name else ""
        lines.append(f"[{date}] {name}{file_info}:\n   {text_preview}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (показаны не все результаты)"
    await message.answer(text)

    # Send the actual media files (last 5)
    sent = 0
    for msg, user in results[:5]:
        if msg.file_id:
            try:
                if media_type == "photo":
                    await message.answer_photo(msg.file_id)
                elif media_type == "video":
                    await message.answer_video(msg.file_id)
                elif media_type == "voice":
                    await message.answer_voice(msg.file_id)
                elif media_type == "audio":
                    await message.answer_audio(msg.file_id)
                elif media_type == "document":
                    await message.answer_document(msg.file_id)
                sent += 1
            except Exception as e:
                logger.warning("Failed to send media %s: %s", msg.file_id, e)

    if sent > 0:
        logger.info("Sent %d media files for /find %s", sent, media_type)


@router.message(Command("user"))
async def cmd_user(message: Message, session: AsyncSession):
    """Search messages by user: /user <name>"""
    username = message.text.replace("/user", "", 1).strip()
    if not username:
        await message.answer("👤 Укажите имя пользователя:\n/user <имя или username>")
        return

    results = await search_by_user(session, username)

    if not results:
        await message.answer(f"👤 Сообщения от «{username}» не найдены.")
        return

    lines = [f"👤 Сообщения от «{username}» ({len(results)}):\n"]
    for msg in results:
        date = msg.created_at.strftime("%d.%m.%Y %H:%M")
        media_icon = MEDIA_EMOJI.get(msg.media_type, "") if msg.media_type else ""
        text_preview = msg.text[:60].replace("\n", " ")
        lines.append(f"{media_icon} [{date}]: {text_preview}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (показаны не все результаты)"
    await message.answer(text)


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession):
    """List all users: /users"""
    users = await get_all_users(session)

    if not users:
        await message.answer("👥 Пока нет пользователей.")
        return

    lines = [f"👥 Все пользователи ({len(users)}):\n"]
    for u in users:
        date = u.created_at.strftime("%d.%m.%Y")
        username = f" @{u.username}" if u.username else ""
        lines.append(f"• {u.full_name}{username} (с {date})")

    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Show stats: /stats"""
    stats = await get_stats(session)

    lines = [
        "📊 Статистика бота:\n",
        f"👥 Пользователей: {stats['total_users']}",
        f"💬 Сообщений: {stats['total_messages']}",
    ]

    if stats["media_counts"]:
        lines.append("\n📎 Медиа:")
        for mtype, count in stats["media_counts"].items():
            emoji = MEDIA_EMOJI.get(mtype, "📎")
            lines.append(f"   {emoji} {mtype}: {count}")

    await message.answer("\n".join(lines))
