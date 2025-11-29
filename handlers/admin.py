"""
Admin management commands
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatType, ParseMode
from utils import admin_only, bot_admin_check, extract_user_and_text, mention_user
from database import Database
import logging

logger = logging.getLogger(__name__)


@admin_only
@bot_admin_check
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the chat"""
    chat_id = update.effective_chat.id
    user_id, reason = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to ban by replying to their message or providing their ID."
        )
        return

    if user_id == context.bot.id:
        await update.message.reply_text("I can't ban myself!")
        return

    try:
        # Ban the user
        await context.bot.ban_chat_member(chat_id, user_id)

        # Log to database
        db: Database = context.bot_data['db']
        db.log_analytics(chat_id, "user_banned", {"user_id": user_id, "reason": reason})

        reason_text = f"\nReason: {reason}" if reason else ""
        await update.message.reply_text(
            f"User {user_id} has been banned.{reason_text}"
        )
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await update.message.reply_text(f"Failed to ban user: {str(e)}")


@admin_only
@bot_admin_check
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the chat"""
    chat_id = update.effective_chat.id
    user_id, _ = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to unban by providing their ID."
        )
        return

    try:
        await context.bot.unban_chat_member(chat_id, user_id)
        await update.message.reply_text(f"User {user_id} has been unbanned.")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await update.message.reply_text(f"Failed to unban user: {str(e)}")


@admin_only
@bot_admin_check
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the chat"""
    chat_id = update.effective_chat.id
    user_id, reason = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to kick by replying to their message or providing their ID."
        )
        return

    if user_id == context.bot.id:
        await update.message.reply_text("I can't kick myself!")
        return

    try:
        # Kick (ban and immediately unban)
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)

        # Log to database
        db: Database = context.bot_data['db']
        db.log_analytics(chat_id, "user_kicked", {"user_id": user_id, "reason": reason})

        reason_text = f"\nReason: {reason}" if reason else ""
        await update.message.reply_text(
            f"User {user_id} has been kicked.{reason_text}"
        )
    except Exception as e:
        logger.error(f"Error kicking user: {e}")
        await update.message.reply_text(f"Failed to kick user: {str(e)}")


@admin_only
@bot_admin_check
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user in the chat"""
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    user_id, reason = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to mute by replying to their message or providing their ID."
        )
        return

    if user_id == context.bot.id:
        await update.message.reply_text("I can't mute myself!")
        return

    try:
        # Mute the user (remove all permissions)
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False)
        )

        reason_text = f"\nReason: {reason}" if reason else ""
        await update.message.reply_text(
            f"User {user_id} has been muted.{reason_text}"
        )
    except Exception as e:
        logger.error(f"Error muting user: {e}")
        await update.message.reply_text(f"Failed to mute user: {str(e)}")


@admin_only
@bot_admin_check
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a user in the chat"""
    from telegram import ChatPermissions
    chat_id = update.effective_chat.id
    user_id, _ = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to unmute by replying to their message or providing their ID."
        )
        return

    try:
        # Restore default permissions
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )

        await update.message.reply_text(f"User {user_id} has been unmuted.")
    except Exception as e:
        logger.error(f"Error unmuting user: {e}")
        await update.message.reply_text(f"Failed to unmute user: {str(e)}")


@admin_only
async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin (owner only in most cases)"""
    chat_id = update.effective_chat.id
    user_id, title = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to promote by replying to their message or providing their ID."
        )
        return

    try:
        await context.bot.promote_chat_member(
            chat_id,
            user_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False
        )

        if title:
            try:
                await context.bot.set_chat_administrator_custom_title(chat_id, user_id, title)
            except:
                pass

        await update.message.reply_text(f"User {user_id} has been promoted to admin.")
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        await update.message.reply_text(f"Failed to promote user: {str(e)}")


@admin_only
async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote an admin to regular user"""
    chat_id = update.effective_chat.id
    user_id, _ = extract_user_and_text(update.message)

    if not user_id:
        await update.message.reply_text(
            "Please specify a user to demote by replying to their message or providing their ID."
        )
        return

    try:
        await context.bot.promote_chat_member(
            chat_id,
            user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )

        await update.message.reply_text(f"User {user_id} has been demoted.")
    except Exception as e:
        logger.error(f"Error demoting user: {e}")
        await update.message.reply_text(f"Failed to demote user: {str(e)}")


@admin_only
@bot_admin_check
async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pin a message"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to pin it.")
        return

    try:
        await context.bot.pin_chat_message(
            update.effective_chat.id,
            update.message.reply_to_message.message_id,
            disable_notification=True
        )
        await update.message.reply_text("Message pinned successfully!")
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
        await update.message.reply_text(f"Failed to pin message: {str(e)}")


@admin_only
@bot_admin_check
async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unpin a message"""
    try:
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(
                update.effective_chat.id,
                update.message.reply_to_message.message_id
            )
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)

        await update.message.reply_text("Message unpinned successfully!")
    except Exception as e:
        logger.error(f"Error unpinning message: {e}")
        await update.message.reply_text(f"Failed to unpin message: {str(e)}")


def register_handlers(application):
    """Register admin command handlers"""
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("kick", kick_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("promote", promote_user))
    application.add_handler(CommandHandler("demote", demote_user))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(CommandHandler("unpin", unpin_message))
