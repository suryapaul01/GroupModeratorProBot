"""
Notes and filters system handlers
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from utils import admin_only
from database import Database
import logging
import re

logger = logging.getLogger(__name__)


@admin_only
async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a note"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    # Parse command: /save <name> <content>
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /save <name> <content>\n"
            "Or reply to a message with /save <name>"
        )
        return

    note_name = args[0].lower()

    # Check if replying to a message
    if update.message.reply_to_message:
        replied_msg = update.message.reply_to_message
        content = replied_msg.text or replied_msg.caption or ""
        file_id = None
        note_type = "text"

        # Check for media
        if replied_msg.photo:
            file_id = replied_msg.photo[-1].file_id
            note_type = "photo"
        elif replied_msg.document:
            file_id = replied_msg.document.file_id
            note_type = "document"
        elif replied_msg.video:
            file_id = replied_msg.video.file_id
            note_type = "video"
        elif replied_msg.audio:
            file_id = replied_msg.audio.file_id
            note_type = "audio"
        elif replied_msg.sticker:
            file_id = replied_msg.sticker.file_id
            note_type = "sticker"

        if db.add_note(chat_id, note_name, content, file_id, note_type):
            await update.message.reply_text(f"Note '{note_name}' saved!")
        else:
            await update.message.reply_text("Failed to save note.")
    else:
        # Content from command args
        if len(args) < 2:
            await update.message.reply_text("Please provide content for the note.")
            return

        content = " ".join(args[1:])
        if db.add_note(chat_id, note_name, content):
            await update.message.reply_text(f"Note '{note_name}' saved!")
        else:
            await update.message.reply_text("Failed to save note.")


async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a note"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /get <name>")
        return

    note_name = args[0].lower()
    note = db.get_note(chat_id, note_name)

    if not note:
        await update.message.reply_text(f"Note '{note_name}' not found.")
        return

    # Send note based on type
    note_type = note.get("type", "text")
    content = note.get("content", "")
    file_id = note.get("file_id")

    try:
        if note_type == "text":
            await update.message.reply_text(content, parse_mode=ParseMode.MARKDOWN)
        elif note_type == "photo":
            await update.message.reply_photo(file_id, caption=content, parse_mode=ParseMode.MARKDOWN)
        elif note_type == "document":
            await update.message.reply_document(file_id, caption=content, parse_mode=ParseMode.MARKDOWN)
        elif note_type == "video":
            await update.message.reply_video(file_id, caption=content, parse_mode=ParseMode.MARKDOWN)
        elif note_type == "audio":
            await update.message.reply_audio(file_id, caption=content, parse_mode=ParseMode.MARKDOWN)
        elif note_type == "sticker":
            await update.message.reply_sticker(file_id)
    except Exception as e:
        logger.error(f"Error sending note: {e}")
        await update.message.reply_text(f"Error sending note: {str(e)}")


async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notes in the chat"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    notes = db.get_all_notes(chat_id)

    if not notes:
        await update.message.reply_text("No notes saved in this chat.")
        return

    message = "📝 Saved notes:\n\n"
    for note in notes:
        name = note.get("name", "")
        note_type = note.get("type", "text")
        message += f"• {name} ({note_type})\n"

    message += f"\nTotal: {len(notes)} notes\nUse /get <name> to retrieve a note."

    await update.message.reply_text(message)


@admin_only
async def clear_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a note"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /clear <name>")
        return

    note_name = args[0].lower()

    if db.delete_note(chat_id, note_name):
        await update.message.reply_text(f"Note '{note_name}' deleted.")
    else:
        await update.message.reply_text(f"Note '{note_name}' not found.")


# Filters System

@admin_only
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a custom filter"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /filter <keyword> <response>\n"
            "Or reply to a message with /filter <keyword>"
        )
        return

    keyword = args[0].lower()

    # Check if replying to a message
    if update.message.reply_to_message:
        replied_msg = update.message.reply_to_message
        response = replied_msg.text or replied_msg.caption or ""
        file_id = None
        filter_type = "text"

        # Check for media
        if replied_msg.photo:
            file_id = replied_msg.photo[-1].file_id
            filter_type = "photo"
        elif replied_msg.document:
            file_id = replied_msg.document.file_id
            filter_type = "document"
        elif replied_msg.video:
            file_id = replied_msg.video.file_id
            filter_type = "video"
        elif replied_msg.sticker:
            file_id = replied_msg.sticker.file_id
            filter_type = "sticker"

        if db.add_filter(chat_id, keyword, response, file_id, filter_type):
            await update.message.reply_text(f"Filter '{keyword}' added!")
        else:
            await update.message.reply_text("Failed to add filter.")
    else:
        # Response from command args
        if len(args) < 2:
            await update.message.reply_text("Please provide a response for the filter.")
            return

        response = " ".join(args[1:])
        if db.add_filter(chat_id, keyword, response):
            await update.message.reply_text(f"Filter '{keyword}' added!")
        else:
            await update.message.reply_text("Failed to add filter.")


async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all filters in the chat"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    filters_list = db.get_all_filters(chat_id)

    if not filters_list:
        await update.message.reply_text("No filters set in this chat.")
        return

    message = "🔍 Active filters:\n\n"
    for f in filters_list:
        keyword = f.get("keyword", "")
        filter_type = f.get("type", "text")
        message += f"• {keyword} ({filter_type})\n"

    message += f"\nTotal: {len(filters_list)} filters"

    await update.message.reply_text(message)


@admin_only
async def remove_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a filter"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /stop <keyword>")
        return

    keyword = args[0].lower()

    if db.delete_filter(chat_id, keyword):
        await update.message.reply_text(f"Filter '{keyword}' removed.")
    else:
        await update.message.reply_text(f"Filter '{keyword}' not found.")


async def filter_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check messages for filters"""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    message_text = update.message.text.lower()

    db: Database = context.bot_data['db']
    filters_list = db.get_all_filters(chat_id)

    for f in filters_list:
        keyword = f.get("keyword", "").lower()

        # Check if keyword is in message
        if keyword in message_text:
            response = f.get("response", "")
            file_id = f.get("file_id")
            filter_type = f.get("type", "text")

            try:
                if filter_type == "text":
                    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                elif filter_type == "photo":
                    await update.message.reply_photo(file_id, caption=response, parse_mode=ParseMode.MARKDOWN)
                elif filter_type == "document":
                    await update.message.reply_document(file_id, caption=response, parse_mode=ParseMode.MARKDOWN)
                elif filter_type == "video":
                    await update.message.reply_video(file_id, caption=response, parse_mode=ParseMode.MARKDOWN)
                elif filter_type == "sticker":
                    await update.message.reply_sticker(file_id)
            except Exception as e:
                logger.error(f"Error sending filter response: {e}")

            break  # Only trigger first matching filter


def register_handlers(application):
    """Register notes and filters handlers"""
    # Notes
    application.add_handler(CommandHandler("save", save_note))
    application.add_handler(CommandHandler("get", get_note))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("saved", list_notes))
    application.add_handler(CommandHandler("clear", clear_note))

    # Filters
    application.add_handler(CommandHandler("filter", add_filter))
    application.add_handler(CommandHandler("filters", list_filters))
    application.add_handler(CommandHandler("stop", remove_filter))

    # Filter message handler (should be added last)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        filter_message_handler
    ), group=10)
