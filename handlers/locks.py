"""
Locks and restrictions handlers
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from utils import admin_only, is_user_admin
from database import Database
import logging

logger = logging.getLogger(__name__)


@admin_only
async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock specific message types"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /lock <type>\n\n"
            "Available lock types:\n"
            "• messages - All messages\n"
            "• media - Photos, videos, audio, documents\n"
            "• stickers - Stickers and GIFs\n"
            "• gifs - Only GIFs\n"
            "• polls - Polls\n"
            "• links - Web links\n"
            "• forwards - Forwarded messages"
        )
        return

    lock_type = args[0].lower()
    valid_types = ["messages", "media", "stickers", "gifs", "polls", "links", "forwards"]

    if lock_type not in valid_types:
        await update.message.reply_text(f"Invalid lock type. Use one of: {', '.join(valid_types)}")
        return

    settings = db.get_settings(chat_id)
    if "locks" not in settings:
        settings["locks"] = {}

    settings["locks"][lock_type] = True

    if db.update_settings(chat_id, settings):
        await update.message.reply_text(f"🔒 Locked: {lock_type}")
    else:
        await update.message.reply_text("Failed to set lock.")


@admin_only
async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock specific message types"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unlock <type>")
        return

    lock_type = args[0].lower()

    settings = db.get_settings(chat_id)
    if "locks" not in settings:
        settings["locks"] = {}

    settings["locks"][lock_type] = False

    if db.update_settings(chat_id, settings):
        await update.message.reply_text(f"🔓 Unlocked: {lock_type}")
    else:
        await update.message.reply_text("Failed to remove lock.")


async def list_locks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active locks"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    settings = db.get_settings(chat_id)
    locks = settings.get("locks", {})

    active_locks = [lock_type for lock_type, is_locked in locks.items() if is_locked]

    if not active_locks:
        await update.message.reply_text("No locks are currently active in this chat.")
        return

    message = "🔒 Active locks:\n\n"
    message += "\n".join([f"• {lock}" for lock in active_locks])

    await update.message.reply_text(message)


async def lock_checker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if message violates any locks"""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Skip check for admins
    if await is_user_admin(update, context, user_id, chat_id):
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)
    locks = settings.get("locks", {})

    message = update.message
    should_delete = False
    violation = None

    # Check various lock types
    if locks.get("messages", False):
        should_delete = True
        violation = "messages"
    elif locks.get("media", False) and (message.photo or message.video or message.audio or message.document):
        should_delete = True
        violation = "media"
    elif locks.get("stickers", False) and (message.sticker or (message.animation and message.animation.file_size)):
        should_delete = True
        violation = "stickers"
    elif locks.get("gifs", False) and message.animation:
        should_delete = True
        violation = "gifs"
    elif locks.get("polls", False) and message.poll:
        should_delete = True
        violation = "polls"
    elif locks.get("links", False) and message.text and ("http://" in message.text.lower() or "https://" in message.text.lower()):
        # Check if link is in allowed list
        from handlers.allowed_links import is_link_allowed
        import re

        # Extract URLs from message
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message.text)

        # Check if any URL is not allowed
        allowed_links = settings.get("allowed_links", [])
        has_disallowed_link = False
        disallowed_url = None

        for url in urls:
            if not is_link_allowed(url, allowed_links):
                has_disallowed_link = True
                disallowed_url = url
                break

        if has_disallowed_link:
            should_delete = True
            violation = "links"

            # Add warning to user for sending disallowed link
            try:
                warn_count = db.add_warning(user_id, chat_id, context.bot.id, f"Sending disallowed link: {disallowed_url}")

                # Get warning settings
                max_warnings = settings.get("max_warnings", 3)
                warn_action = settings.get("warn_action", "ban")

                # Delete the message first
                await message.delete()

                # Send warning notification
                warning_text = (
                    f"⚠️ Warning [{warn_count}/{max_warnings}]\n"
                    f"User: {message.from_user.mention_html()}\n"
                    f"Reason: Sending disallowed links\n\n"
                )

                # Check if max warnings reached
                if warn_count >= max_warnings:
                    if warn_action == "ban":
                        await context.bot.ban_chat_member(chat_id, user_id)
                        warning_text += f"❌ User has been banned for reaching {max_warnings} warnings!"
                    elif warn_action == "kick":
                        await context.bot.ban_chat_member(chat_id, user_id)
                        await context.bot.unban_chat_member(chat_id, user_id)
                        warning_text += f"👢 User has been kicked for reaching {max_warnings} warnings!"
                    elif warn_action == "mute":
                        from telegram import ChatPermissions
                        await context.bot.restrict_chat_member(
                            chat_id,
                            user_id,
                            ChatPermissions(can_send_messages=False)
                        )
                        warning_text += f"🔇 User has been muted for reaching {max_warnings} warnings!"

                    # Reset warnings after action
                    db.reset_warnings(user_id, chat_id)
                else:
                    if allowed_links:
                        warning_text += f"💡 Allowed domains: {', '.join(allowed_links[:3])}"
                        if len(allowed_links) > 3:
                            warning_text += f" and {len(allowed_links) - 3} more"

                warning_msg = await message.chat.send_message(
                    warning_text,
                    parse_mode="HTML"
                )

                # Auto-delete after 10 seconds
                context.job_queue.run_once(
                    lambda _: warning_msg.delete(),
                    10,
                    name=f"delete_link_warning_{warning_msg.message_id}"
                )

                # Skip the default lock handling since we already handled it
                should_delete = False

            except Exception as e:
                logger.error(f"Error warning user for disallowed link: {e}")
                # If warning fails, fall back to default behavior
                should_delete = True
                violation = "links"
    elif locks.get("forwards", False) and message.forward_date:
        should_delete = True
        violation = "forwards"

    if should_delete:
        try:
            await message.delete()
            # Send warning (auto-delete after 10 seconds)
            warning_msg = await message.chat.send_message(
                f"⚠️ {violation.capitalize()} are locked in this chat!",
                reply_to_message_id=None
            )

            # Schedule deletion of warning message
            context.job_queue.run_once(
                lambda _: warning_msg.delete(),
                10,
                name=f"delete_lock_warning_{warning_msg.message_id}"
            )

        except Exception as e:
            logger.error(f"Error enforcing lock: {e}")


# Antiflood System

# Store message tracking: {chat_id: {user_id: [timestamps]}}
message_tracker = {}


async def antiflood_checker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check for spam/flood"""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Skip check for admins
    if await is_user_admin(update, context, user_id, chat_id):
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)

    if not settings.get("antiflood_enabled", False):
        return

    from datetime import datetime, timedelta

    flood_limit = settings.get("antiflood_limit", 5)
    flood_time = settings.get("antiflood_time", 10)  # seconds

    # Initialize tracking
    if chat_id not in message_tracker:
        message_tracker[chat_id] = {}
    if user_id not in message_tracker[chat_id]:
        message_tracker[chat_id][user_id] = []

    # Add current message timestamp
    now = datetime.now()
    message_tracker[chat_id][user_id].append(now)

    # Remove old timestamps
    cutoff_time = now - timedelta(seconds=flood_time)
    message_tracker[chat_id][user_id] = [
        ts for ts in message_tracker[chat_id][user_id]
        if ts > cutoff_time
    ]

    # Check if flooding
    message_count = len(message_tracker[chat_id][user_id])

    if message_count > flood_limit:
        try:
            from telegram import ChatPermissions

            # Mute user for 5 minutes
            await context.bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=5)
            )

            # Delete the message
            await update.message.delete()

            # Send warning
            warning_msg = await update.message.chat.send_message(
                f"⚠️ User {user_id} has been muted for 5 minutes due to flooding!"
            )

            # Clear user's message tracker
            message_tracker[chat_id][user_id] = []

            # Log analytics
            db.log_analytics(chat_id, "user_muted_flood", {"user_id": user_id})

        except Exception as e:
            logger.error(f"Error handling flood: {e}")


@admin_only
async def antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure antiflood settings"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        settings = db.get_settings(chat_id)
        enabled = settings.get("antiflood_enabled", False)
        limit = settings.get("antiflood_limit", 5)
        time_window = settings.get("antiflood_time", 10)

        status = "enabled" if enabled else "disabled"
        await update.message.reply_text(
            f"Antiflood is currently {status}.\n"
            f"Limit: {limit} messages in {time_window} seconds\n\n"
            f"Usage: /antiflood <on/off> [limit] [time]\n"
            f"Example: /antiflood on 5 10"
        )
        return

    action = args[0].lower()

    if action not in ["on", "off"]:
        await update.message.reply_text("Use 'on' or 'off' to enable/disable antiflood.")
        return

    settings = db.get_settings(chat_id)
    settings["antiflood_enabled"] = (action == "on")

    # Update limit and time if provided
    if len(args) >= 2 and args[1].isdigit():
        settings["antiflood_limit"] = int(args[1])
    if len(args) >= 3 and args[2].isdigit():
        settings["antiflood_time"] = int(args[2])

    if db.update_settings(chat_id, settings):
        status = "enabled" if action == "on" else "disabled"
        await update.message.reply_text(f"Antiflood {status}!")
    else:
        await update.message.reply_text("Failed to update antiflood settings.")


def register_handlers(application):
    """Register locks and antiflood handlers"""
    application.add_handler(CommandHandler("lock", lock))
    application.add_handler(CommandHandler("unlock", unlock))
    application.add_handler(CommandHandler("locks", list_locks))
    application.add_handler(CommandHandler("antiflood", antiflood))

    # Message checkers (should be in a group to run after other handlers)
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        lock_checker
    ), group=5)

    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        antiflood_checker
    ), group=5)
