from sqlalchemy import select
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
    session: AsyncSession, telegram_id: int, text: str, bot_reply: str
) -> Message:
    msg = Message(telegram_id=telegram_id, text=text, bot_reply=bot_reply)
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


async def get_chat_context(session: AsyncSession, telegram_id: int, limit: int = 10) -> list[dict]:
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
