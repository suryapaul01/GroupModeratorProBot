"""
Welcome and goodbye message handlers
"""
from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes, CommandHandler, ChatMemberHandler
from telegram.constants import ParseMode, ChatMemberStatus
from utils import admin_only, format_welcome_message
from database import Database
import logging

logger = logging.getLogger(__name__)


def extract_status_change(chat_member_update: ChatMemberUpdated):
    """Extract status change from ChatMemberUpdated"""
    old_member = chat_member_update.old_chat_member
    new_member = chat_member_update.new_chat_member

    # Member joined
    if old_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED] and \
       new_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return "joined"

    # Member left
    if old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
       new_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.KICKED]:
        return "left"

    return None


async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the chat"""
    chat_member_update = update.chat_member

    if not chat_member_update:
        return

    status_change = extract_status_change(chat_member_update)

    if not status_change:
        return

    chat = chat_member_update.chat
    user = chat_member_update.new_chat_member.user
    db: Database = context.bot_data['db']

    # Add chat to database
    db.add_chat(chat.id, chat.title, chat.type)

    # Add user to database
    db.add_user(
        user.id,
        chat.id,
        user.username,
        user.first_name,
        user.last_name
    )

    # Get chat settings
    settings = db.get_settings(chat.id)

    if status_change == "joined":
        # Send welcome message
        if settings.get("welcome_enabled", True):
            welcome_msg = settings.get(
                "welcome_message",
                "Welcome {mention} to {chatname}!"
            )

            formatted_msg = format_welcome_message(welcome_msg, user, chat)

            try:
                await context.bot.send_message(
                    chat.id,
                    formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")

        # Log analytics
        db.log_analytics(chat.id, "member_joined", {"user_id": user.id})

    elif status_change == "left":
        # Send goodbye message
        if settings.get("goodbye_enabled", False):
            goodbye_msg = settings.get(
                "goodbye_message",
                "Goodbye {mention}!"
            )

            formatted_msg = format_welcome_message(goodbye_msg, user, chat)

            try:
                await context.bot.send_message(
                    chat.id,
                    formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending goodbye message: {e}")

        # Log analytics
        db.log_analytics(chat.id, "member_left", {"user_id": user.id})


@admin_only
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set welcome message"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    # Get message text
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /setwelcome <message>\n\n"
            "Available placeholders:\n"
            "{mention} - Mention the user\n"
            "{first} - User's first name\n"
            "{last} - User's last name\n"
            "{fullname} - User's full name\n"
            "{username} - User's username\n"
            "{id} - User's ID\n"
            "{chatname} - Chat name\n"
            "{chatid} - Chat ID"
        )
        return

    welcome_msg = " ".join(args)
    settings = db.get_settings(chat_id)
    settings["welcome_message"] = welcome_msg
    settings["welcome_enabled"] = True

    if db.update_settings(chat_id, settings):
        await update.message.reply_text("Welcome message updated successfully!")
    else:
        await update.message.reply_text("Failed to update welcome message.")


@admin_only
async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set goodbye message"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /setgoodbye <message>\n\n"
            "Available placeholders are the same as /setwelcome"
        )
        return

    goodbye_msg = " ".join(args)
    settings = db.get_settings(chat_id)
    settings["goodbye_message"] = goodbye_msg
    settings["goodbye_enabled"] = True

    if db.update_settings(chat_id, settings):
        await update.message.reply_text("Goodbye message updated successfully!")
    else:
        await update.message.reply_text("Failed to update goodbye message.")


@admin_only
async def toggle_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle welcome message on/off"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    settings = db.get_settings(chat_id)
    current = settings.get("welcome_enabled", True)
    settings["welcome_enabled"] = not current

    if db.update_settings(chat_id, settings):
        status = "enabled" if not current else "disabled"
        await update.message.reply_text(f"Welcome message {status}!")
    else:
        await update.message.reply_text("Failed to toggle welcome message.")


@admin_only
async def toggle_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle goodbye message on/off"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    settings = db.get_settings(chat_id)
    current = settings.get("goodbye_enabled", False)
    settings["goodbye_enabled"] = not current

    if db.update_settings(chat_id, settings):
        status = "enabled" if not current else "disabled"
        await update.message.reply_text(f"Goodbye message {status}!")
    else:
        await update.message.reply_text("Failed to toggle goodbye message.")


def register_handlers(application):
    """Register welcome/goodbye handlers"""
    application.add_handler(ChatMemberHandler(welcome_handler, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye))
    application.add_handler(CommandHandler("welcome", toggle_welcome))
    application.add_handler(CommandHandler("goodbye", toggle_goodbye))
