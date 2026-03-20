import logging

from groq import AsyncGroq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — личный ассистент, который отвечает на сообщения от имени владельца аккаунта. "
    "Отвечай вежливо, по-деловому и по существу. "
    "Если не знаешь ответа — скажи, что владелец свяжется лично. "
    "Отвечай на том же языке, на котором написано сообщение. "
    "Не используй markdown-разметку, отвечай простым текстом."
)


class AIClient:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def generate_reply(self, user_message: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Groq API error: %s", e)
            return (
                "Спасибо за ваше сообщение! "
                "В данный момент я не могу ответить, "
                "но обязательно свяжусь с вами в ближайшее время."
            )
