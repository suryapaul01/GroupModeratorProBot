"""
Warnings system handlers
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from utils import admin_only, bot_admin_check, extract_user_and_text
from database import Database
import logging

logger = logging.getLogger(__name__)


@admin_only
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user"""
    chat_id = update.effective_chat.id
    user_id, reason = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to warn by replying to their message or providing their ID."
        )
        return

    db: Database = context.bot_data['db']
    warned_by = update.effective_user.id

    # Add warning
    warn_count = db.add_warning(user_id, chat_id, warned_by, reason)

    # Get settings
    settings = db.get_settings(chat_id)
    max_warnings = settings.get("max_warnings", 3)
    warn_action = settings.get("warn_action", "ban")

    reason_text = f"\nReason: {reason}" if reason else ""
    message = f"User {user_id} has been warned ({warn_count}/{max_warnings}).{reason_text}"

    # Check if max warnings reached
    if warn_count >= max_warnings:
        try:
            if warn_action == "ban":
                await context.bot.ban_chat_member(chat_id, user_id)
                message += f"\n\nUser has reached {max_warnings} warnings and has been banned!"
            elif warn_action == "kick":
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                message += f"\n\nUser has reached {max_warnings} warnings and has been kicked!"
            elif warn_action == "mute":
                from telegram import ChatPermissions
                await context.bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(can_send_messages=False)
                )
                message += f"\n\nUser has reached {max_warnings} warnings and has been muted!"

            # Reset warnings after action
            db.reset_warnings(user_id, chat_id)

        except Exception as e:
            logger.error(f"Error executing warn action: {e}")
            message += f"\n\nFailed to execute action: {str(e)}"

    await update.message.reply_text(message)


@admin_only
async def remove_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove warnings from a user"""
    chat_id = update.effective_chat.id
    user_id, _ = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user by replying to their message or providing their ID."
        )
        return

    db: Database = context.bot_data['db']

    if db.reset_warnings(user_id, chat_id):
        await update.message.reply_text(f"Warnings reset for user {user_id}.")
    else:
        await update.message.reply_text("Failed to reset warnings.")


async def check_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check warnings for a user"""
    chat_id = update.effective_chat.id
    user_id, _ = extract_user_and_text(update.message)

    # If no user specified, check own warnings
    if not user_id:
        user_id = update.effective_user.id

    db: Database = context.bot_data['db']
    warnings = db.get_warnings(user_id, chat_id)

    if not warnings or warnings.get("count", 0) == 0:
        await update.message.reply_text(f"User {user_id} has no warnings.")
        return

    settings = db.get_settings(chat_id)
    max_warnings = settings.get("max_warnings", 3)
    warn_count = warnings.get("count", 0)

    message = f"User {user_id} has {warn_count}/{max_warnings} warnings.\n\n"

    # List recent warnings
    recent_warnings = warnings.get("warnings", [])[-5:]  # Last 5 warnings
    for i, warn in enumerate(recent_warnings, 1):
        reason = warn.get("reason", "No reason provided")
        timestamp = warn.get("timestamp", "").strftime("%Y-%m-%d %H:%M") if warn.get("timestamp") else "Unknown"
        message += f"{i}. {reason} (on {timestamp})\n"

    await update.message.reply_text(message)


@admin_only
async def set_warn_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set maximum warnings before action"""
    chat_id = update.effective_chat.id
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: /setwarnlimit <number>\n"
            "Example: /setwarnlimit 3"
        )
        return

    limit = int(args[0])
    if limit < 1 or limit > 10:
        await update.message.reply_text("Limit must be between 1 and 10.")
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)
    settings["max_warnings"] = limit

    if db.update_settings(chat_id, settings):
        await update.message.reply_text(f"Warning limit set to {limit}.")
    else:
        await update.message.reply_text("Failed to update warning limit.")


@admin_only
async def set_warn_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set action to take when max warnings reached"""
    chat_id = update.effective_chat.id
    args = context.args

    if not args or args[0].lower() not in ["ban", "kick", "mute"]:
        await update.message.reply_text(
            "Usage: /setwarnaction <action>\n"
            "Available actions: ban, kick, mute\n"
            "Example: /setwarnaction ban"
        )
        return

    action = args[0].lower()
    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)
    settings["warn_action"] = action

    if db.update_settings(chat_id, settings):
        await update.message.reply_text(f"Warning action set to {action}.")
    else:
        await update.message.reply_text("Failed to update warning action.")


def register_handlers(application):
    """Register warning command handlers"""
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("removewarn", remove_warn))
    application.add_handler(CommandHandler("resetwarn", remove_warn))
    application.add_handler(CommandHandler("warns", check_warns))
    application.add_handler(CommandHandler("warnings", check_warns))
    application.add_handler(CommandHandler("setwarnlimit", set_warn_limit))
    application.add_handler(CommandHandler("setwarnaction", set_warn_action))
