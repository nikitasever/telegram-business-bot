from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Message, User


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None, full_name: str
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()

    return user


async def save_message(
    session: AsyncSession,
    telegram_id: int,
    text: str,
    bot_reply: str,
    media_type: str | None = None,
    file_id: str | None = None,
    file_name: str | None = None,
) -> Message:
    msg = Message(
        telegram_id=telegram_id,
        text=text,
        bot_reply=bot_reply,
        media_type=media_type,
        file_id=file_id,
        file_name=file_name,
    )
    session.add(msg)
    await session.commit()
    return msg


async def get_user_history(session: AsyncSession, telegram_id: int, limit: int = 10):
    result = await session.execute(
        select(Message)
        .where(Message.telegram_id == telegram_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_chat_context(session: AsyncSession, telegram_id: int, limit: int = 30) -> list[dict]:
    """Get recent messages formatted as chat history for AI context."""
    result = await session.execute(
        select(Message)
        .where(Message.telegram_id == telegram_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))

    chat_history = []
    for msg in messages:
        chat_history.append({"role": "user", "content": msg.text})
        chat_history.append({"role": "assistant", "content": msg.bot_reply})

    return chat_history


# ---- Search functions ----

async def search_messages(session: AsyncSession, query: str, limit: int = 20) -> list[tuple[Message, User | None]]:
    """Search messages by text across all users."""
    result = await session.execute(
        select(Message, User)
        .outerjoin(User, Message.telegram_id == User.telegram_id)
        .where(
            or_(
                Message.text.ilike(f"%{query}%"),
                Message.bot_reply.ilike(f"%{query}%"),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.all()


async def search_media(session: AsyncSession, media_type: str, limit: int = 20) -> list[tuple[Message, User | None]]:
    """Search messages by media type (photo, video, voice, audio, document)."""
    result = await session.execute(
        select(Message, User)
        .outerjoin(User, Message.telegram_id == User.telegram_id)
        .where(Message.media_type == media_type)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.all()


async def search_by_user(session: AsyncSession, username: str, limit: int = 20) -> list[Message]:
    """Search messages by username."""
    result = await session.execute(
        select(Message)
        .join(User, Message.telegram_id == User.telegram_id)
        .where(
            or_(
                User.username.ilike(f"%{username}%"),
                User.full_name.ilike(f"%{username}%"),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_users(session: AsyncSession) -> list[User]:
    """Get all users who have contacted the bot."""
    result = await session.execute(
        select(User).order_by(User.created_at.desc())
    )
    return result.scalars().all()


async def get_stats(session: AsyncSession) -> dict:
    """Get message statistics."""
    from sqlalchemy import func as sqla_func

    total_msgs = await session.execute(select(sqla_func.count(Message.id)))
    total_users = await session.execute(select(sqla_func.count(User.id)))

    media_counts = await session.execute(
        select(Message.media_type, sqla_func.count(Message.id))
        .where(Message.media_type.isnot(None))
        .group_by(Message.media_type)
    )

    return {
        "total_messages": total_msgs.scalar() or 0,
        "total_users": total_users.scalar() or 0,
        "media_counts": {row[0]: row[1] for row in media_counts.all()},
    }
