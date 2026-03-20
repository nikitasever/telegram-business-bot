from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import get_or_create_user, save_message

router = Router()

AUTO_REPLY = (
    "Здравствуйте! Спасибо за ваше сообщение.\n\n"
    "В данный момент я не могу ответить лично, "
    "но обязательно прочитаю ваше обращение и свяжусь с вами "
    "в ближайшее время.\n\n"
    "Если вопрос срочный — пожалуйста, уточните это в сообщении, "
    "и я постараюсь ответить как можно скорее."
)


@router.business_message()
async def handle_business_message(message: Message, session: AsyncSession):
    # Ignore messages sent by the account owner (you)
    if message.from_user.id == message.business_connection_id:
        return

    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=message.text or "(медиа/стикер)",
        bot_reply=AUTO_REPLY,
    )

    await message.answer(AUTO_REPLY)
