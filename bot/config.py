import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    database_url: str

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN is not set")

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is not set")

        return cls(bot_token=bot_token, database_url=database_url)
