"""
Custom logger handler for sending logs to Telegram channel
"""
import logging
from datetime import datetime
from telegram import Bot
from config import Config
import asyncio


class TelegramLogHandler(logging.Handler):
    """Custom logging handler to send logs to Telegram channel"""

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.log_channel_id = Config.LOG_CHANNEL_ID
        self.pending_logs = []
        self.batch_size = 10
        self.last_send_time = datetime.now()

    def emit(self, record):
        """Send log to Telegram channel"""
        if not self.log_channel_id:
            return

        try:
            log_entry = self.format(record)

            # Only send important logs (WARNING and above)
            if record.levelno >= logging.WARNING:
                # Use asyncio to send message
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._send_log(log_entry))
                    else:
                        loop.run_until_complete(self._send_log(log_entry))
                except RuntimeError:
                    # If no event loop is running, skip
                    pass

        except Exception:
            # Silently fail to avoid infinite loops
            pass

    async def _send_log(self, log_entry: str):
        """Async method to send log to channel"""
        try:
            await self.bot.send_message(
                chat_id=self.log_channel_id,
                text=f"🔍 Log Entry:\n\n{log_entry[:4000]}"  # Truncate if too long
            )
        except Exception:
            pass


async def log_to_channel(bot: Bot, message: str, log_type: str = "INFO"):
    """Helper function to send custom logs to channel"""
    if not Config.LOG_CHANNEL_ID:
        return

    try:
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "ADMIN": "👑",
            "USER": "👤",
            "GROUP": "👥"
        }.get(log_type, "📝")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"{emoji} {log_type}\n{timestamp}\n\n{message}"

        # Send with shorter timeout to prevent blocking
        await asyncio.wait_for(
            bot.send_message(
                chat_id=Config.LOG_CHANNEL_ID,
                text=formatted_message[:4000]
            ),
            timeout=5.0  # 5 second timeout
        )
    except asyncio.TimeoutError:
        # Silently ignore timeout
        pass
    except Exception:
        # Silently fail
        pass
