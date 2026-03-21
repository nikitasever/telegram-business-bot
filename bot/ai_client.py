import logging
import tempfile
from pathlib import Path

from groq import AsyncGroq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — умный личный ассистент, который ведёт переписку от имени владельца аккаунта. "
    "Ты анализируешь диалог в реальном времени и помогаешь в общении.\n\n"
    "Правила:\n"
    "- Отвечай естественно, как живой человек, а не робот\n"
    "- Подстраивайся под тон собеседника: если шутят — шути в ответ, если серьёзно — будь серьёзен\n"
    "- Используй контекст переписки для релевантных ответов\n"
    "- Если уместно — добавь юмор, лёгкую иронию или эмодзи\n"
    "- Если не знаешь ответа — скажи, что владелец свяжется лично\n"
    "- Отвечай на том же языке, на котором написано сообщение\n"
    "- Не используй markdown-разметку\n"
    "- Будь краток, не пиши простыни текста\n\n"
    "ВАЖНО: Если в конце ответа уместен мем — добавь на последней строке тег [MEME:тема], "
    "где тема — короткое описание мема на английском. Например: [MEME:waiting], [MEME:success], "
    "[MEME:confused]. Добавляй мем только когда это реально уместно и смешно, не на каждое сообщение."
)

REACTION_PROMPT = (
    "Выбери ОДНУ самую подходящую реакцию-эмодзи на это сообщение. "
    "Доступные реакции: 👍 👎 ❤ 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 💊 🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡\n\n"
    "Ответь ТОЛЬКО одним эмодзи, без текста."
)

# Fallback chain: if one model hits rate limit, try the next
TEXT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
REACTION_MODEL = "llama-3.1-8b-instant"
WHISPER_MODEL = "whisper-large-v3"


class AIClient:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def generate_reply(
        self,
        user_message: str,
        chat_history: list[dict] | None = None,
        image_base64: str | None = None,
    ) -> tuple[str, str | None]:
        """Returns (reply_text, meme_query_or_none)."""
        try:
            if image_base64:
                raw = await self._vision_reply(user_message, image_base64)
            else:
                raw = await self._text_reply(user_message, chat_history)
            return self._extract_meme(raw)
        except Exception as e:
            logger.error("All AI models failed: %s", e, exc_info=True)
            return (
                "Спасибо за ваше сообщение! "
                "В данный момент я не могу ответить, "
                "но обязательно свяжусь с вами в ближайшее время.",
                None,
            )

    @staticmethod
    def _extract_meme(text: str) -> tuple[str, str | None]:
        """Extract [MEME:topic] tag from AI response."""
        import re
        match = re.search(r'\[MEME:([^\]]+)\]', text)
        if match:
            meme_query = match.group(1).strip()
            clean_text = text[:match.start()].strip()
            return clean_text, meme_query
        return text, None

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=True) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                with open(tmp.name, "rb") as audio_file:
                    transcription = await self.client.audio.transcriptions.create(
                        file=(filename, audio_file.read()),
                        model=WHISPER_MODEL,
                        language="ru",
                    )
            logger.info("Audio transcribed: %s", transcription.text[:100])
            return transcription.text
        except Exception as e:
            logger.error("Whisper transcription error: %s", e, exc_info=True)
            return ""

    async def pick_reaction(self, user_message: str) -> str | None:
        try:
            response = await self.client.chat.completions.create(
                model=REACTION_MODEL,
                messages=[
                    {"role": "system", "content": REACTION_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=10,
                temperature=0.5,
            )
            emoji = response.choices[0].message.content.strip()
            if emoji:
                logger.info("Picked reaction: %s", emoji)
                return emoji
            return None
        except Exception as e:
            logger.error("Reaction pick error: %s", e, exc_info=True)
            return None

    async def _text_reply(
        self, user_message: str, chat_history: list[dict] | None = None
    ) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        last_error = None
        for model in TEXT_MODELS:
            try:
                logger.info("Trying model: %s", model)
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.8,
                )
                logger.info("Success with model: %s", model)
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                logger.warning("Model %s failed: %s", model, e)
                continue

        raise last_error

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
            temperature=0.8,
        )
        return response.choices[0].message.content
