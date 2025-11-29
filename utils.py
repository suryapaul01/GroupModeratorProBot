"""
Utility functions for the bot
"""
from telegram import Update, User, Chat, ChatMember
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from typing import Optional, List
from functools import wraps
from config import Config
import logging

logger = logging.getLogger(__name__)


def mention_user(user: User) -> str:
    """Create a mention for a user"""
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"


def get_user_display_name(user: User) -> str:
    """Get user's display name"""
    name = user.first_name
    if user.last_name:
        name += f" {user.last_name}"
    return name


def format_welcome_message(message: str, user: User, chat: Chat) -> str:
    """Format welcome message with placeholders"""
    replacements = {
        "{mention}": mention_user(user),
        "{first}": user.first_name,
        "{last}": user.last_name or "",
        "{fullname}": get_user_display_name(user),
        "{username}": f"@{user.username}" if user.username else user.first_name,
        "{id}": str(user.id),
        "{chatname}": chat.title or "this chat",
        "{chatid}": str(chat.id)
    }

    for placeholder, value in replacements.items():
        message = message.replace(placeholder, value)

    return message


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       user_id: int, chat_id: int) -> bool:
    """Check if user is an admin in the chat"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


async def is_bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      chat_id: int) -> bool:
    """Check if bot is an admin in the chat"""
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        return bot_member.status == ChatMemberStatus.ADMINISTRATOR
    except Exception as e:
        logger.error(f"Error checking bot admin status: {e}")
        return False


def is_owner(user_id: int) -> bool:
    """Check if user is the bot owner"""
    return user_id == Config.OWNER_ID


def is_sudo_user(user_id: int) -> bool:
    """Check if user is a sudo user"""
    return user_id in Config.SUDO_USERS


def owner_only(func):
    """Decorator to restrict command to bot owner only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            await update.message.reply_text("This command is only available to the bot owner.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def admin_only(func):
    """Decorator to restrict command to chat admins only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Owner can use all commands
        if is_owner(user_id):
            return await func(update, context, *args, **kwargs)

        # Check if user is admin
        if not await is_user_admin(update, context, user_id, chat_id):
            await update.message.reply_text("This command is only available to admins.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapper


def bot_admin_check(func):
    """Decorator to check if bot is admin before executing command"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id

        if not await is_bot_admin(update, context, chat_id):
            await update.message.reply_text(
                "I need to be an admin with appropriate permissions to use this feature!"
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper


def extract_user_and_text(message):
    """Extract user and text from a message (for commands like warn, ban, etc.)"""
    entities = message.entities or []
    text = message.text or message.caption or ""
    user_id = None
    reason = None

    # Check if replying to a message
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        # Text after command is the reason
        args = text.split(maxsplit=1)
        if len(args) > 1:
            reason = args[1]
        return user_id, reason

    # Check for mentions in entities
    for entity in entities:
        if entity.type == "text_mention":
            user_id = entity.user.id
            break
        elif entity.type == "mention":
            # Extract username
            offset = entity.offset
            length = entity.length
            username = text[offset:offset + length].replace("@", "")
            # We can't get user_id from username directly
            # This needs to be handled differently
            continue

    # Extract user ID and reason from text
    args = text.split()
    if len(args) > 1:
        try:
            user_id = int(args[1])
            if len(args) > 2:
                reason = " ".join(args[2:])
        except ValueError:
            pass

    return user_id, reason


async def get_chat_member_count(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int:
    """Get the number of members in a chat"""
    try:
        count = await context.bot.get_chat_member_count(chat_id)
        return count
    except Exception as e:
        logger.error(f"Error getting member count: {e}")
        return 0


def split_message(text: str, max_length: int = 4096) -> List[str]:
    """Split long message into chunks"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        # Find last newline within limit
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts


async def auto_delete_message(message, delay: int = 5):
    """Auto-delete a message after delay"""
    import asyncio
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def delete_command_and_response(command_msg, response_msg, delay: int = 5):
    """Delete both command and response after delay"""
    import asyncio
    await asyncio.sleep(delay)

    try:
        await command_msg.delete()
    except Exception:
        pass

    try:
        await response_msg.delete()
    except Exception:
        pass
