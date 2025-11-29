"""
Configuration file for the bot
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "")

    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "rose_bot")

    # Bot Owner Configuration
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    SUDO_USERS = [OWNER_ID] if OWNER_ID else []

    # Premium Configuration
    PREMIUM_CHAT_IDS = [
        int(chat_id.strip())
        for chat_id in os.getenv("PREMIUM_CHAT_IDS", "").split(",")
        if chat_id.strip()
    ]

    # Optional Configuration
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0")) if os.getenv("LOG_CHANNEL_ID", "").strip().lstrip('-').isdigit() else 0
    SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "")
    FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")

    # Validation
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required in .env file")
        if not cls.OWNER_ID:
            raise ValueError("OWNER_ID is required in .env file")
        return True
