"""
Additional useful features
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from utils import admin_only, bot_admin_check
from database import Database
from logger_handler import log_to_channel
import logging
import asyncio

logger = logging.getLogger(__name__)


@admin_only
@bot_admin_check
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Purge messages from replied message to current"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to purge from that point!")
        return

    chat_id = update.effective_chat.id
    from_message_id = update.message.reply_to_message.message_id
    to_message_id = update.message.message_id

    status_msg = await update.message.reply_text("Purging messages...")

    deleted_count = 0
    failed_count = 0

    # Delete messages in batches
    for msg_id in range(from_message_id, to_message_id + 1):
        try:
            await context.bot.delete_message(chat_id, msg_id)
            deleted_count += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flood limits
        except Exception:
            failed_count += 1

    try:
        await status_msg.delete()
    except:
        pass

    # Send result and auto-delete
    result_msg = await context.bot.send_message(
        chat_id,
        f"✅ Purged {deleted_count} messages!\n"
        f"Failed: {failed_count}"
    )

    # Log to channel
    if context.bot_data.get('db'):
        db: Database = context.bot_data['db']
        db.log_analytics(chat_id, "messages_purged", {"count": deleted_count})

    await log_to_channel(
        context.bot,
        f"📊 Purge executed in chat {chat_id}\n"
        f"Deleted: {deleted_count}\n"
        f"By: {update.effective_user.id}",
        "ADMIN"
    )

    # Auto-delete after 5 seconds
    context.job_queue.run_once(
        lambda _: result_msg.delete(),
        5,
        name=f"delete_purge_{result_msg.message_id}"
    )


@admin_only
@bot_admin_check
async def del_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a specific message"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to delete it!")
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"Failed to delete message: {str(e)}")


@admin_only
async def tagall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tag all members (use with caution)"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    # Get message to send with tags
    args = context.args
    message_text = " ".join(args) if args else "Attention everyone!"

    # Get all users
    users = db.get_chat_users(chat_id, limit=50)  # Limit to avoid spam

    if not users:
        await update.message.reply_text("No users found in database.")
        return

    # Create mention list
    mentions = []
    for user in users:
        user_id = user.get("user_id")
        first_name = user.get("first_name", "User")
        mentions.append(f"[{first_name}](tg://user?id={user_id})")

    # Split into chunks of 5 users per message
    chunk_size = 5
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        tag_message = f"{message_text}\n\n" + " ".join(chunk)

        try:
            await context.bot.send_message(
                chat_id,
                tag_message,
                parse_mode=ParseMode.MARKDOWN
            )
            await asyncio.sleep(1)  # Delay to avoid flood
        except Exception as e:
            logger.error(f"Error tagging users: {e}")
            break

    # Delete command
    try:
        await update.message.delete()
    except:
        pass


async def info_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed user information"""
    user_id = None
    user_obj = None

    # Check if replying to someone
    if update.message.reply_to_message:
        user_obj = update.message.reply_to_message.from_user
        user_id = user_obj.id
    else:
        # Get own info
        user_obj = update.effective_user
        user_id = user_obj.id

    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    # Get user data from database
    user_data = db.get_user(user_id, chat_id)

    message = f"👤 *User Information*\n\n"
    message += f"Name: {user_obj.first_name}"
    if user_obj.last_name:
        message += f" {user_obj.last_name}"
    message += f"\nUser ID: `{user_id}`\n"

    if user_obj.username:
        message += f"Username: @{user_obj.username}\n"

    if user_data:
        message += f"\n📊 *Activity:*\n"
        message += f"Messages: {user_data.get('message_count', 0)}\n"

        if user_data.get("joined_at"):
            joined = user_data["joined_at"].strftime("%Y-%m-%d")
            message += f"Joined: {joined}\n"

        if user_data.get("last_seen"):
            last_seen = user_data["last_seen"].strftime("%Y-%m-%d %H:%M")
            message += f"Last seen: {last_seen}\n"

    # Check warnings
    warnings = db.get_warnings(user_id, chat_id)
    if warnings and warnings.get("count", 0) > 0:
        message += f"\n⚠️ Warnings: {warnings['count']}\n"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean up bot messages and commands"""
    chat_id = update.effective_chat.id

    args = context.args
    limit = 100  # Default

    if args and args[0].isdigit():
        limit = min(int(args[0]), 1000)  # Max 1000

    status_msg = await update.message.reply_text(f"Cleaning up last {limit} messages...")

    deleted_count = 0
    current_msg_id = update.message.message_id

    # Go backwards from current message
    for i in range(1, limit + 1):
        msg_id = current_msg_id - i
        if msg_id <= 0:
            break

        try:
            # Try to get message info
            # This is a simplified version - ideally we'd check if it's a bot message
            await context.bot.delete_message(chat_id, msg_id)
            deleted_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            # Message might not exist or can't be deleted
            pass

    try:
        await status_msg.delete()
        await update.message.delete()
    except:
        pass

    result_msg = await context.bot.send_message(
        chat_id,
        f"✅ Cleaned up {deleted_count} messages!"
    )

    # Auto-delete after 5 seconds
    context.job_queue.run_once(
        lambda _: result_msg.delete(),
        5,
        name=f"delete_cleanup_{result_msg.message_id}"
    )


def register_handlers(application):
    """Register extra features handlers"""
    application.add_handler(CommandHandler("purge", purge))
    application.add_handler(CommandHandler("del", del_message))
    application.add_handler(CommandHandler("delete", del_message))
    application.add_handler(CommandHandler("tagall", tagall))
    application.add_handler(CommandHandler("mention", tagall))
    application.add_handler(CommandHandler("userinfo", info_detailed))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
