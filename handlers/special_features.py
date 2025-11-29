"""
Special features: Auto-delete join requests and pin messages
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from utils import admin_only
from database import Database
import logging

logger = logging.getLogger(__name__)


# Auto-delete join request messages
async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle and auto-delete join request approval messages"""
    if not update.message:
        return

    message = update.message
    chat_id = message.chat.id

    # Check if this is a service message about new members
    if not message.new_chat_members:
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)

    if settings.get("auto_delete_join_requests", False):
        try:
            # Delete the service message
            await message.delete()
            logger.info(f"Auto-deleted join request message in chat {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting join request message: {e}")


# Auto-delete pin messages
async def pin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle and auto-delete pin notification messages"""
    if not update.message:
        return

    message = update.message
    chat_id = message.chat.id

    # Check if this is a pinned message service notification
    if not message.pinned_message:
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)

    if settings.get("auto_delete_pin_messages", False):
        try:
            # Delete the pin notification
            await message.delete()
            logger.info(f"Auto-deleted pin notification in chat {chat_id}")

            # Optionally schedule deletion of the pinned message itself after delay
            pin_delete_delay = settings.get("pin_delete_delay", 0)
            if pin_delete_delay > 0:
                context.job_queue.run_once(
                    delete_pinned_message,
                    pin_delete_delay,
                    data={
                        "chat_id": chat_id,
                        "message_id": message.pinned_message.message_id
                    },
                    name=f"delete_pin_{chat_id}_{message.pinned_message.message_id}"
                )
        except Exception as e:
            logger.error(f"Error handling pin message: {e}")


async def delete_pinned_message(context: ContextTypes.DEFAULT_TYPE):
    """Callback to delete pinned message after delay"""
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]

    try:
        await context.bot.delete_message(chat_id, message_id)
        await context.bot.unpin_chat_message(chat_id, message_id)
        logger.info(f"Auto-deleted pinned message {message_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error deleting pinned message: {e}")


# Configuration commands

@admin_only
async def auto_delete_joins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle auto-delete join request messages"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    settings = db.get_settings(chat_id)

    if not args:
        current = settings.get("auto_delete_join_requests", False)
        status = "enabled" if current else "disabled"
        await update.message.reply_text(
            f"Auto-delete join requests is currently {status}.\n"
            f"Usage: /autodeletejoins <on/off>"
        )
        return

    action = args[0].lower()

    if action not in ["on", "off"]:
        await update.message.reply_text("Use 'on' or 'off'.")
        return

    settings["auto_delete_join_requests"] = (action == "on")

    if db.update_settings(chat_id, settings):
        status = "enabled" if action == "on" else "disabled"
        await update.message.reply_text(f"Auto-delete join requests {status}!")
    else:
        await update.message.reply_text("Failed to update setting.")


@admin_only
async def auto_delete_pins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle auto-delete pin notification messages"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    settings = db.get_settings(chat_id)

    if not args:
        current = settings.get("auto_delete_pin_messages", False)
        delay = settings.get("pin_delete_delay", 0)
        status = "enabled" if current else "disabled"

        message = f"Auto-delete pin messages is currently {status}.\n"
        if delay > 0:
            message += f"Pinned messages will be deleted after {delay} seconds.\n"
        message += "\nUsage: /autodeletepins <on/off> [delay_in_seconds]\n"
        message += "Example: /autodeletepins on 300 (deletes after 5 minutes)"

        await update.message.reply_text(message)
        return

    action = args[0].lower()

    if action not in ["on", "off"]:
        await update.message.reply_text("Use 'on' or 'off'.")
        return

    settings["auto_delete_pin_messages"] = (action == "on")

    # Set delay if provided
    if len(args) >= 2 and args[1].isdigit():
        delay = int(args[1])
        if delay < 0 or delay > 86400:  # Max 24 hours
            await update.message.reply_text("Delay must be between 0 and 86400 seconds (24 hours).")
            return
        settings["pin_delete_delay"] = delay

    if db.update_settings(chat_id, settings):
        status = "enabled" if action == "on" else "disabled"
        response = f"Auto-delete pin messages {status}!"

        if action == "on" and settings.get("pin_delete_delay", 0) > 0:
            response += f"\nPinned messages will be deleted after {settings['pin_delete_delay']} seconds."

        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Failed to update setting.")


def register_handlers(application):
    """Register special features handlers"""
    # Join request auto-delete
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        join_request_handler
    ), group=1)

    # Pin message auto-delete
    application.add_handler(MessageHandler(
        filters.StatusUpdate.PINNED_MESSAGE,
        pin_message_handler
    ), group=1)

    # Configuration commands
    application.add_handler(CommandHandler("autodeletejoins", auto_delete_joins))
    application.add_handler(CommandHandler("autodeletepins", auto_delete_pins))
