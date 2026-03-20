import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import Config
from bot.db.engine import create_db_engine
from bot.db.models import Base
from bot.gemini import GeminiClient
from bot.handlers import business, history, messages, start
from bot.middlewares.db import DbSessionMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    config = Config.from_env()
    engine, session_factory = create_db_engine(config.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    gemini = GeminiClient(api_key=config.gemini_api_key)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher(gemini=gemini)

    dp.message.middleware(DbSessionMiddleware(session_factory))
    dp.business_message.middleware(DbSessionMiddleware(session_factory))

    dp.include_router(business.router)
    dp.include_router(start.router)
    dp.include_router(history.router)
    dp.include_router(messages.router)

    logger.info("Bot started")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "business_connection",
                "business_message",
                "edited_business_message",
            ],
        )
    finally:
        await engine.dispose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
