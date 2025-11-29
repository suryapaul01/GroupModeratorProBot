"""
Bot owner and premium features handlers
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from utils import owner_only
from database import Database
import logging

logger = logging.getLogger(__name__)


@owner_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get global bot statistics (owner only)"""
    db: Database = context.bot_data['db']

    try:
        stats_data = db.get_global_stats()

        message = "📊 Bot Statistics:\n\n"
        message += f"Total Chats: {stats_data['total_chats']}\n"
        message += f"Total Users: {stats_data['total_users']}\n"
        message += f"Total Notes: {stats_data['total_notes']}\n"
        message += f"Total Filters: {stats_data['total_filters']}\n"
        message += f"Premium Chats: {stats_data['premium_chats']}\n"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(f"Error getting stats: {str(e)}")


@owner_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to all chats (owner only)"""
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /broadcast <message>\n"
            "Or reply to a message with /broadcast"
        )
        return

    # Get message to broadcast
    if update.message.reply_to_message:
        broadcast_msg = update.message.reply_to_message
    else:
        broadcast_text = " ".join(args)
        broadcast_msg = None

    # Get all chats
    try:
        chats = list(db.chats.find({}))
        success = 0
        failed = 0

        status_msg = await update.message.reply_text(
            f"Broadcasting to {len(chats)} chats..."
        )

        for chat in chats:
            chat_id = chat.get("chat_id")
            try:
                if broadcast_msg:
                    await broadcast_msg.copy(chat_id)
                else:
                    await context.bot.send_message(
                        chat_id,
                        broadcast_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                success += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {chat_id}: {e}")
                failed += 1

        await status_msg.edit_text(
            f"Broadcast complete!\n"
            f"Success: {success}\n"
            f"Failed: {failed}"
        )

    except Exception as e:
        logger.error(f"Error broadcasting: {e}")
        await update.message.reply_text(f"Error broadcasting: {str(e)}")


@owner_only
async def add_premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add premium to a chat (owner only)"""
    db: Database = context.bot_data['db']

    args = context.args
    if not args or not args[0].lstrip('-').isdigit():
        await update.message.reply_text(
            "Usage: /addpremium <chat_id> [duration_days]\n"
            "Example: /addpremium -1001234567890 30"
        )
        return

    chat_id = int(args[0])
    duration = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30

    if db.add_premium(chat_id, duration):
        await update.message.reply_text(
            f"Premium added to chat {chat_id} for {duration} days!"
        )
    else:
        await update.message.reply_text("Failed to add premium.")


@owner_only
async def remove_premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove premium from a chat (owner only)"""
    db: Database = context.bot_data['db']

    args = context.args
    if not args or not args[0].lstrip('-').isdigit():
        await update.message.reply_text(
            "Usage: /removepremium <chat_id>\n"
            "Example: /removepremium -1001234567890"
        )
        return

    chat_id = int(args[0])

    if db.remove_premium(chat_id):
        await update.message.reply_text(f"Premium removed from chat {chat_id}!")
    else:
        await update.message.reply_text("Failed to remove premium.")


@owner_only
async def chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get information about a chat (owner only)"""
    db: Database = context.bot_data['db']

    args = context.args
    if not args or not args[0].lstrip('-').isdigit():
        # Use current chat if no chat_id provided
        chat_id = update.effective_chat.id
    else:
        chat_id = int(args[0])

    try:
        # Get chat info from Telegram
        chat = await context.bot.get_chat(chat_id)

        # Get stats from database
        chat_data = db.get_chat(chat_id)
        user_count = len(db.get_chat_users(chat_id, limit=10000))
        notes_count = len(db.get_all_notes(chat_id))
        filters_count = len(db.get_all_filters(chat_id))
        is_premium = db.is_premium(chat_id)

        message = f"📝 Chat Information:\n\n"
        message += f"Title: {chat.title}\n"
        message += f"Chat ID: {chat_id}\n"
        message += f"Type: {chat.type}\n"
        message += f"Username: @{chat.username}\n" if chat.username else ""
        message += f"\n📊 Statistics:\n"
        message += f"Users tracked: {user_count}\n"
        message += f"Notes: {notes_count}\n"
        message += f"Filters: {filters_count}\n"
        message += f"Premium: {'Yes ⭐' if is_premium else 'No'}\n"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error getting chat info: {e}")
        await update.message.reply_text(f"Error getting chat info: {str(e)}")


@owner_only
async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all chats the bot is in (owner only)"""
    db: Database = context.bot_data['db']

    try:
        chats = list(db.chats.find({}).limit(50))

        if not chats:
            await update.message.reply_text("No chats found.")
            return

        message = "📋 Bot Chats (Max 50):\n\n"

        for i, chat in enumerate(chats, 1):
            chat_title = chat.get("chat_title", "Unknown")
            chat_id = chat.get("chat_id", "Unknown")
            chat_type = chat.get("chat_type", "Unknown")

            message += f"{i}. {chat_title}\n"
            message += f"   ID: {chat_id} | Type: {chat_type}\n\n"

        # Split if too long
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        await update.message.reply_text(f"Error listing chats: {str(e)}")


# Premium Features

async def check_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if current chat has premium"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    is_premium = db.is_premium(chat_id)

    if is_premium:
        premium_data = db.premium.find_one({"chat_id": chat_id})
        expires_at = premium_data.get("expires_at", "Unknown")

        if expires_at != "Unknown":
            expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC")
        else:
            expires_str = "Never"

        message = "⭐ This chat has Premium access!\n\n"
        message += f"Expires: {expires_str}\n\n"
        message += "Premium Features:\n"
        message += "• Priority support\n"
        message += "• Advanced filters with regex\n"
        message += "• Custom welcome images\n"
        message += "• Extended analytics\n"
        message += "• Higher limits for notes and filters\n"
        message += "• Faster response times"
    else:
        message = "This chat does not have Premium access.\n\n"
        message += "Contact the bot owner to learn more about Premium features!"

    await update.message.reply_text(message)


async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get chat analytics (premium feature)"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    # Check premium status
    if not db.is_premium(chat_id):
        await update.message.reply_text(
            "⭐ Analytics is a Premium feature!\n"
            "Contact the bot owner to upgrade."
        )
        return

    try:
        # Get analytics data
        analytics_data = db.get_analytics(chat_id, limit=100)
        user_count = len(db.get_chat_users(chat_id, limit=10000))

        # Count events
        event_counts = {}
        for event in analytics_data:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        message = "📊 Chat Analytics (Last 100 events):\n\n"
        message += f"Total Users Tracked: {user_count}\n\n"
        message += "Event Breakdown:\n"

        for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
            message += f"• {event_type}: {count}\n"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        await update.message.reply_text(f"Error getting analytics: {str(e)}")


def register_handlers(application):
    """Register owner and premium command handlers"""
    # Owner commands
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addpremium", add_premium_cmd))
    application.add_handler(CommandHandler("removepremium", remove_premium_cmd))
    application.add_handler(CommandHandler("chatinfo", chat_info))
    application.add_handler(CommandHandler("listchats", list_chats))

    # Premium features
    application.add_handler(CommandHandler("premium", check_premium))
    application.add_handler(CommandHandler("analytics", analytics))
