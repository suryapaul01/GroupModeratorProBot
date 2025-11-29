"""
Force subscription feature
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ChatMemberStatus, ParseMode
from utils import admin_only
from database import Database
from config import Config
import logging

logger = logging.getLogger(__name__)


async def check_subscription(bot, user_id: int, channel_username: str) -> bool:
    """Check if user is subscribed to the channel"""
    try:
        # Handle both @username and -100xxxxx formats
        channel_id = channel_username
        if not channel_username.startswith('-'):
            # It's a username
            if not channel_username.startswith('@'):
                channel_id = f"@{channel_username}"

        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        ]
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return True  # Allow if check fails


async def force_sub_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is subscribed before allowing to use the bot"""
    if not update.message:
        return

    # Only work in groups/supergroups
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Skip for admins
    from utils import is_user_admin, is_owner
    if is_owner(user_id) or await is_user_admin(update, context, user_id, chat_id):
        return

    db: Database = context.bot_data['db']
    settings = db.get_settings(chat_id)

    # Check if force sub is enabled
    if not settings.get("force_sub_enabled", False):
        return

    force_sub_channel = settings.get("force_sub_channel") or Config.FORCE_SUB_CHANNEL

    if not force_sub_channel:
        return

    # Check subscription
    is_subscribed = await check_subscription(context.bot, user_id, force_sub_channel)

    if not is_subscribed:
        # Delete the message
        try:
            await update.message.delete()
        except Exception:
            pass

        # Create subscription button
        # Get channel link
        try:
            if force_sub_channel.startswith('@'):
                channel_link = f"https://t.me/{force_sub_channel[1:]}"
            elif force_sub_channel.startswith('-100'):
                # Try to get channel info
                try:
                    chat_info = await context.bot.get_chat(force_sub_channel)
                    if chat_info.username:
                        channel_link = f"https://t.me/{chat_info.username}"
                    else:
                        # For private channels without username, can't create a link
                        channel_link = None
                except:
                    channel_link = None
            else:
                channel_link = f"https://t.me/{force_sub_channel}"

            # Only send message if we have a valid link
            if channel_link:
                keyboard = [[InlineKeyboardButton("Join Channel", url=channel_link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                warning_msg = await update.message.chat.send_message(
                    f"⚠️ {update.effective_user.first_name}, you must join our channel to participate in this group!\n\n"
                    f"Click the button below to join:",
                    reply_markup=reply_markup
                )

                # Auto-delete warning after 30 seconds
                context.job_queue.run_once(
                    lambda _: warning_msg.delete(),
                    30,
                    name=f"delete_force_sub_warning_{warning_msg.message_id}"
                )

        except Exception as e:
            logger.error(f"Error sending force sub message: {e}")


@admin_only
async def set_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set force subscription channel"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        settings = db.get_settings(chat_id)
        current_channel = settings.get("force_sub_channel") or Config.FORCE_SUB_CHANNEL
        is_enabled = settings.get("force_sub_enabled", False)

        message = "🔐 Force Subscription Settings:\n\n"
        message += f"Status: {'Enabled' if is_enabled else 'Disabled'}\n"
        message += f"Channel: {current_channel if current_channel else 'Not set'}\n\n"
        message += "Usage:\n"
        message += "/forcesub <on/off> - Toggle force subscription\n"
        message += "/setchannel <@username or channel_id> - Set channel\n\n"
        message += "Example:\n"
        message += "/setchannel @your_channel\n"
        message += "/forcesub on"

        await update.message.reply_text(message)
        return

    action = args[0].lower()

    if action not in ["on", "off"]:
        await update.message.reply_text("Use 'on' or 'off' to enable/disable force subscription.")
        return

    settings = db.get_settings(chat_id)
    settings["force_sub_enabled"] = (action == "on")

    if db.update_settings(chat_id, settings):
        status = "enabled" if action == "on" else "disabled"
        msg = await update.message.reply_text(f"✅ Force subscription {status}!")

        # Auto-delete after 5 seconds
        context.job_queue.run_once(
            lambda _: delete_messages(update.message, msg),
            5,
            name=f"delete_{msg.message_id}"
        )
    else:
        await update.message.reply_text("Failed to update force subscription settings.")


@admin_only
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the channel for force subscription"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /setchannel <@username or channel_id>\n\n"
            "Examples:\n"
            "/setchannel @your_channel\n"
            "/setchannel -1001234567890"
        )
        return

    channel = args[0]

    # Validate channel
    try:
        # Try to get channel info
        chat_info = await context.bot.get_chat(channel)

        settings = db.get_settings(chat_id)
        settings["force_sub_channel"] = channel

        if db.update_settings(chat_id, settings):
            msg = await update.message.reply_text(
                f"✅ Force subscription channel set to: {chat_info.title or channel}"
            )

            # Auto-delete after 5 seconds
            context.job_queue.run_once(
                lambda _: delete_messages(update.message, msg),
                5,
                name=f"delete_{msg.message_id}"
            )
        else:
            await update.message.reply_text("Failed to set channel.")

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: Unable to access that channel.\n\n"
            f"Make sure:\n"
            f"1. The bot is added to the channel as admin\n"
            f"2. The channel ID/username is correct\n\n"
            f"Error: {str(e)}"
        )


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


def register_handlers(application):
    """Register force subscription handlers"""
    application.add_handler(CommandHandler("forcesub", set_force_sub))
    application.add_handler(CommandHandler("setchannel", set_channel))

    # Message handler for force subscription check (should be in early group)
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, force_sub_check),
        group=1
    )
