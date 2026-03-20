from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import get_or_create_user, get_user_history, save_message

router = Router()

BUSINESS_REPLIES = {
    "цена": (
        "Спасибо за интерес к нашим ценам!\n\n"
        "Стоимость наших услуг зависит от выбранного пакета:\n"
        "• Базовый — от 5 000 ₽/мес\n"
        "• Стандарт — от 15 000 ₽/мес\n"
        "• Премиум — от 30 000 ₽/мес\n\n"
        "Для точного расчёта напишите, какие услуги вас интересуют."
    ),
    "услуг": (
        "Мы предоставляем следующие услуги:\n\n"
        "1. Консультации и аудит\n"
        "2. Разработка и внедрение решений\n"
        "3. Техническая поддержка 24/7\n"
        "4. Обучение персонала\n\n"
        "Напишите подробнее, что именно вас интересует, "
        "и мы подготовим индивидуальное предложение."
    ),
    "контакт": (
        "Наши контакты:\n\n"
        "📞 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: info@example.com\n"
        "🕐 Время работы: Пн-Пт 9:00 — 18:00\n\n"
        "Также вы можете оставить заявку прямо здесь, "
        "и мы свяжемся с вами в ближайшее время."
    ),
    "заявк": (
        "Для оформления заявки, пожалуйста, укажите:\n\n"
        "1. Ваше имя\n"
        "2. Название компании\n"
        "3. Описание задачи\n"
        "4. Удобный способ связи\n\n"
        "Мы обработаем вашу заявку в течение 1 рабочего дня."
    ),
}

DEFAULT_REPLY = (
    "Спасибо за ваше сообщение!\n\n"
    "Мы получили ваше обращение и обязательно ответим.\n"
    "Если у вас срочный вопрос — напишите «контакты» для получения "
    "номера телефона.\n\n"
    "Вы также можете спросить про:\n"
    "• Цены\n"
    "• Услуги\n"
    "• Оформление заявки"
)


def get_reply(text: str) -> str:
    text_lower = text.lower()
    for keyword, reply in BUSINESS_REPLIES.items():
        if keyword in text_lower:
            return reply
    return DEFAULT_REPLY


@router.message(F.text)
async def handle_message(message: Message, session: AsyncSession):
    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    reply_text = get_reply(message.text)

    await save_message(
        session=session,
        telegram_id=message.from_user.id,
        text=message.text,
        bot_reply=reply_text,
    )

    await message.answer(reply_text)
