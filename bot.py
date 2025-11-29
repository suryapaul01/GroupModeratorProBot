"""
Main bot file
DCL Rose Bot - Telegram Group Management Bot
"""
import logging
from telegram.ext import Application, MessageHandler, filters
from telegram import Update
from config import Config
from database import Database
from logger_handler import log_to_channel

# Import handlers
from handlers import (
    basic,
    admin,
    welcome,
    warnings,
    notes,
    locks,
    special_features,
    owner,
    allowed_links,
    force_sub,
    extra_features
)

# Configure logging - Only errors to console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR  # Only show errors in console
)
logger = logging.getLogger(__name__)


async def track_messages(update: Update, context):
    """Track all messages for user analytics and log to channel"""
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        db: Database = context.bot_data['db']

        # Ensure chat is in database
        db.add_chat(chat.id, chat.title, chat.type)

        # Track user activity
        db.add_user(
            user.id,
            chat.id,
            user.username,
            user.first_name,
            user.last_name
        )


async def error_handler(update: Update, context):
    """Handle errors and log to channel"""
    import traceback
    from telegram.error import TimedOut, NetworkError, RetryAfter

    error = context.error

    # Handle specific error types - silently ignore these
    if isinstance(error, TimedOut):
        return
    elif isinstance(error, NetworkError):
        return
    elif isinstance(error, RetryAfter):
        return

    # Log other errors to console only
    error_msg = f"Update {update} caused error {context.error}"
    logger.error(error_msg)

    # Get detailed traceback
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = ''.join(tb_list)

    # Log critical errors to channel (but not timeouts or common errors)
    if Config.LOG_CHANNEL_ID and update and update.effective_chat:
        try:
            error_info = f"❌ Error occurred:\n\n{str(error)[:400]}\n\nUpdate: {str(update)[:200] if update else 'None'}"
            await log_to_channel(
                context.bot,
                error_info,
                "ERROR"
            )
        except Exception:
            # Silently ignore logging errors
            pass


async def post_init(application: Application):
    """Post initialization tasks"""
    # Send startup message to log channel
    if Config.LOG_CHANNEL_ID:
        try:
            await log_to_channel(
                application.bot,
                "Bot started successfully!",
                "SUCCESS"
            )
        except Exception as e:
            logger.warning(f"Failed to send startup log (non-critical): {e}")


async def post_shutdown(application: Application):
    """Post shutdown tasks"""
    # Send shutdown message to log channel
    if Config.LOG_CHANNEL_ID:
        try:
            await log_to_channel(
                application.bot,
                "Bot stopped.",
                "WARNING"
            )
        except Exception:
            pass


def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()

        # Initialize database
        db = Database(Config.MONGO_URI, Config.DATABASE_NAME)
        print("✅ Database initialized successfully")

        # Create application with connection settings
        application = (
            Application.builder()
            .token(Config.BOT_TOKEN)
            .connect_timeout(10.0)
            .read_timeout(10.0)
            .write_timeout(10.0)
            .pool_timeout(10.0)
            .get_updates_connect_timeout(30.0)
            .get_updates_read_timeout(30.0)
            .build()
        )

        # Store database in bot_data
        application.bot_data['db'] = db

        # Register handlers
        print("📝 Registering handlers...")

        # Force subscription (must be early)
        force_sub.register_handlers(application)

        # Basic commands
        basic.register_handlers(application)

        # Admin commands
        admin.register_handlers(application)

        # Welcome/goodbye
        welcome.register_handlers(application)

        # Warnings
        warnings.register_handlers(application)

        # Notes and filters
        notes.register_handlers(application)

        # Locks and antiflood
        locks.register_handlers(application)

        # Allowed links
        allowed_links.register_handlers(application)

        # Special features
        special_features.register_handlers(application)

        # Extra features (purge, tagall, etc.)
        extra_features.register_handlers(application)

        # Owner commands
        owner.register_handlers(application)

        # Message tracker (should be last)
        application.add_handler(
            MessageHandler(filters.ALL, track_messages),
            group=99
        )

        # Error handler
        application.add_error_handler(error_handler)

        # Post init and shutdown hooks
        application.post_init = post_init
        application.post_shutdown = post_shutdown

        print("✅ All handlers registered successfully")

        # Start the bot
        print("=" * 50)
        print("🤖 DCL Rose Bot v2.0 is running!")
        print("=" * 50)
        if Config.LOG_CHANNEL_ID:
            print(f"📡 Logging to channel: {Config.LOG_CHANNEL_ID}")
        print("=" * 50)
        print("⚡ Bot is now polling for updates...")
        print("💡 Press Ctrl+C to stop the bot")
        print("=" * 50)

        # Run polling with error handling
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
            close_loop=False
        )

    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("🛑 Bot stopped by user")
        print("=" * 50)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"\n❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
