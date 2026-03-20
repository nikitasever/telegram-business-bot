import logging

from groq import AsyncGroq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — личный ассистент, который отвечает на сообщения от имени владельца аккаунта. "
    "Отвечай вежливо, по-деловому и по существу. "
    "Если не знаешь ответа — скажи, что владелец свяжется лично. "
    "Отвечай на том же языке, на котором написано сообщение. "
    "Не используй markdown-разметку, отвечай простым текстом. "
    "Учитывай контекст предыдущих сообщений в разговоре."
)

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


class AIClient:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def generate_reply(
        self,
        user_message: str,
        chat_history: list[dict] | None = None,
        image_base64: str | None = None,
    ) -> str:
        try:
            if image_base64:
                return await self._vision_reply(user_message, image_base64)
            else:
                return await self._text_reply(user_message, chat_history)
        except Exception as e:
            logger.error("Groq API error: %s", e, exc_info=True)
            return (
                "Спасибо за ваше сообщение! "
                "В данный момент я не могу ответить, "
                "но обязательно свяжусь с вами в ближайшее время."
            )

    async def _text_reply(
        self, user_message: str, chat_history: list[dict] | None = None
    ) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        response = await self.client.chat.completions.create(
            model=TEXT_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content

    async def _vision_reply(self, user_message: str, image_base64: str) -> str:
        prompt = user_message if user_message else "Что изображено на этой картинке? Опиши подробно."

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    },
                ],
            }
        ]

        logger.info("Sending vision request, image size: %d bytes", len(image_base64))

        response = await self.client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content
