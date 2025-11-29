"""
Allowed links whitelist system
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils import admin_only
from database import Database
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def normalize_domain(url: str) -> str:
    """Normalize domain to handle www and non-www versions"""
    try:
        # Add https if no protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www prefix for comparison
        if domain.startswith('www.'):
            domain = domain[4:]

        return domain
    except Exception:
        return url.lower()


@admin_only
async def add_allowed_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a domain to the allowed links whitelist"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /addallowedlink <domain or URL>\n\n"
            "Examples:\n"
            "/addallowedlink youtube.com\n"
            "/addallowedlink https://www.youtube.com\n"
            "/addallowedlink github.com\n\n"
            "Note: Both www and non-www versions will be treated the same."
        )
        return

    domain = normalize_domain(args[0])

    if not domain:
        await update.message.reply_text("Invalid domain or URL provided.")
        return

    settings = db.get_settings(chat_id)
    allowed_links = settings.get("allowed_links", [])

    if domain in allowed_links:
        await update.message.reply_text(f"Domain '{domain}' is already whitelisted!")
        return

    allowed_links.append(domain)
    settings["allowed_links"] = allowed_links

    if db.update_settings(chat_id, settings):
        msg = await update.message.reply_text(f"✅ Domain '{domain}' added to allowed links!")
        # Auto-delete after 5 seconds
        context.job_queue.run_once(
            lambda _: delete_messages(update.message, msg),
            5,
            name=f"delete_{msg.message_id}"
        )
    else:
        await update.message.reply_text("Failed to add allowed link.")


@admin_only
async def remove_allowed_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a domain from the allowed links whitelist"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removeallowedlink <domain>")
        return

    domain = normalize_domain(args[0])

    settings = db.get_settings(chat_id)
    allowed_links = settings.get("allowed_links", [])

    if domain not in allowed_links:
        await update.message.reply_text(f"Domain '{domain}' is not in the whitelist!")
        return

    allowed_links.remove(domain)
    settings["allowed_links"] = allowed_links

    if db.update_settings(chat_id, settings):
        msg = await update.message.reply_text(f"✅ Domain '{domain}' removed from allowed links!")
        # Auto-delete after 5 seconds
        context.job_queue.run_once(
            lambda _: delete_messages(update.message, msg),
            5,
            name=f"delete_{msg.message_id}"
        )
    else:
        await update.message.reply_text("Failed to remove allowed link.")


async def list_allowed_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all allowed links"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    settings = db.get_settings(chat_id)
    allowed_links = settings.get("allowed_links", [])

    if not allowed_links:
        await update.message.reply_text(
            "No allowed links configured.\n\n"
            "Use /addallowedlink <domain> to add whitelisted domains."
        )
        return

    message = "🔗 Allowed Links:\n\n"
    for i, domain in enumerate(allowed_links, 1):
        message += f"{i}. {domain}\n"

    message += f"\nTotal: {len(allowed_links)} domains"

    await update.message.reply_text(message)


async def delete_messages(command_msg, response_msg):
    """Helper to delete both command and response messages"""
    try:
        await command_msg.delete()
    except Exception:
        pass

    try:
        await response_msg.delete()
    except Exception:
        pass


def is_link_allowed(url: str, allowed_links: list) -> bool:
    """Check if a URL is in the allowed links list"""
    try:
        domain = normalize_domain(url)
        return domain in allowed_links
    except Exception:
        return False


def register_handlers(application):
    """Register allowed links handlers"""
    application.add_handler(CommandHandler("addallowedlink", add_allowed_link))
    application.add_handler(CommandHandler("removeallowedlink", remove_allowed_link))
    application.add_handler(CommandHandler("allowedlinks", list_allowed_links))
