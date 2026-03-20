import logging

from google import genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — личный ассистент, который отвечает на сообщения от имени владельца аккаунта. "
    "Отвечай вежливо, по-деловому и по существу. "
    "Если не знаешь ответа — скажи, что владелец свяжется лично. "
    "Отвечай на том же языке, на котором написано сообщение. "
    "Не используй markdown-разметку, отвечай простым текстом."
)


class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate_reply(self, user_message: str) -> str:
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=500,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return (
                "Спасибо за ваше сообщение! "
                "В данный момент я не могу ответить, "
                "но обязательно свяжусь с вами в ближайшее время."
            )
