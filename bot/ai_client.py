import base64
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

# Text model for chat, vision model for images
TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "llama-3.2-90b-vision-preview"


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
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Add chat history for context
            if chat_history:
                messages.extend(chat_history)

            # Build current message
            if image_base64:
                # Vision request with image
                content = []
                if user_message:
                    content.append({"type": "text", "text": user_message})
                else:
                    content.append({"type": "text", "text": "Что изображено на этой картинке? Опиши подробно."})
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                })
                messages.append({"role": "user", "content": content})
                model = VISION_MODEL
            else:
                messages.append({"role": "user", "content": user_message})
                model = TEXT_MODEL

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
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
