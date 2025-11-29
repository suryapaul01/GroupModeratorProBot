"""
Basic commands handlers
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from database import Database
from utils import get_chat_member_count
import logging

logger = logging.getLogger(__name__)


# Help text for each category
HELP_TEXTS = {
    "help_admin": (
        "👥 *Admin Commands*\n\n"
        "Manage your group with powerful admin tools:\n\n"
        "*Ban/Unban*\n"
        "`/ban` - Ban a user (reply to message or use ID)\n"
        "`/unban <user_id>` - Unban a user\n"
        "Example: `/ban @username spam`\n\n"
        "*Kick*\n"
        "`/kick` - Remove user from group\n"
        "Example: Reply to message and use `/kick`\n\n"
        "*Mute/Unmute*\n"
        "`/mute` - Restrict user from sending messages\n"
        "`/unmute` - Restore user permissions\n\n"
        "*Promote/Demote*\n"
        "`/promote` - Promote user to admin\n"
        "`/demote` - Remove admin rights\n\n"
        "*Pin/Unpin*\n"
        "`/pin` - Pin a message (reply to it)\n"
        "`/unpin` - Unpin message"
    ),
    "help_warnings": (
        "⚠️ *Warning System*\n\n"
        "Manage user warnings for rule violations:\n\n"
        "*Warn User*\n"
        "`/warn [reason]` - Warn a user\n"
        "Example: `/warn Spamming links`\n\n"
        "*Check Warnings*\n"
        "`/warns` - Check user warnings\n"
        "`/warnings` - Same as /warns\n\n"
        "*Remove Warnings*\n"
        "`/removewarn` - Clear user warnings\n"
        "`/resetwarn` - Same as /removewarn\n\n"
        "*Configuration*\n"
        "`/setwarnlimit <1-10>` - Set max warnings\n"
        "Example: `/setwarnlimit 3`\n\n"
        "`/setwarnaction <ban/kick/mute>` - Set action\n"
        "Example: `/setwarnaction ban`"
    ),
    "help_welcome": (
        "💬 *Welcome & Goodbye*\n\n"
        "Greet new members and say goodbye:\n\n"
        "*Set Messages*\n"
        "`/setwelcome <message>` - Set welcome message\n"
        "`/setgoodbye <message>` - Set goodbye message\n\n"
        "*Toggle On/Off*\n"
        "`/welcome` - Toggle welcome messages\n"
        "`/goodbye` - Toggle goodbye messages\n\n"
        "*Available Placeholders:*\n"
        "`{mention}` - Mention the user\n"
        "`{first}` - First name\n"
        "`{last}` - Last name\n"
        "`{fullname}` - Full name\n"
        "`{username}` - Username\n"
        "`{chatname}` - Chat name\n"
        "`{id}` - User ID\n\n"
        "*Example:*\n"
        "`/setwelcome Welcome {mention} to {chatname}! Please read /rules`"
    ),
    "help_notes": (
        "📝 *Notes System*\n\n"
        "Save and retrieve useful information:\n\n"
        "*Save Notes*\n"
        "`/save <name> <content>` - Save a note\n"
        "Or reply to message: `/save <name>`\n"
        "Example: `/save rules Be respectful!`\n\n"
        "*Get Notes*\n"
        "`/get <name>` - Retrieve a note\n"
        "Example: `/get rules`\n\n"
        "*List Notes*\n"
        "`/notes` - Show all saved notes\n"
        "`/saved` - Same as /notes\n\n"
        "*Delete Notes*\n"
        "`/clear <name>` - Delete a note\n"
        "Example: `/clear rules`\n\n"
        "*Supported:* Text, photos, videos, documents, stickers"
    ),
    "help_filters": (
        "🔍 *Custom Filters*\n\n"
        "Auto-respond to keywords:\n\n"
        "*Add Filter*\n"
        "`/filter <keyword> <response>` - Create filter\n"
        "Or reply to message: `/filter <keyword>`\n"
        "Example: `/filter hello Hi there!`\n\n"
        "*List Filters*\n"
        "`/filters` - Show all active filters\n\n"
        "*Remove Filter*\n"
        "`/stop <keyword>` - Delete a filter\n"
        "Example: `/stop hello`\n\n"
        "*How it works:*\n"
        "When users send messages containing the keyword,\n"
        "the bot automatically replies with your response!"
    ),
    "help_locks": (
        "🔒 *Locks & Restrictions*\n\n"
        "Control what users can send:\n\n"
        "*Lock Types*\n"
        "`/lock <type>` - Lock a message type\n"
        "`/unlock <type>` - Unlock a message type\n\n"
        "*Available Types:*\n"
        "• `messages` - All messages\n"
        "• `media` - Photos, videos, documents\n"
        "• `stickers` - Stickers and GIFs\n"
        "• `gifs` - Only GIFs\n"
        "• `polls` - Polls\n"
        "• `links` - Web links\n"
        "• `forwards` - Forwarded messages\n\n"
        "*View Locks*\n"
        "`/locks` - List active locks\n\n"
        "*Anti-Flood*\n"
        "`/antiflood <on/off> [limit] [time]`\n"
        "Example: `/antiflood on 5 10`\n"
        "(Max 5 messages in 10 seconds)"
    ),
    "help_links": (
        "🔗 *Allowed Links*\n\n"
        "Whitelist trusted domains:\n\n"
        "*Add Allowed Link*\n"
        "`/addallowedlink <domain>` - Add to whitelist\n"
        "Example: `/addallowedlink youtube.com`\n"
        "Also works: `/addallowedlink https://www.youtube.com`\n\n"
        "*Remove Allowed Link*\n"
        "`/removeallowedlink <domain>` - Remove from whitelist\n\n"
        "*List Allowed Links*\n"
        "`/allowedlinks` - Show all whitelisted domains\n\n"
        "*How it works:*\n"
        "1. Lock links: `/lock links`\n"
        "2. Add allowed domains: `/addallowedlink youtube.com`\n"
        "3. Users can send YouTube links freely\n"
        "4. Other links get auto-deleted + user receives warning\n"
        "5. After max warnings, user is banned/kicked/muted\n\n"
        "*Note:* www and non-www versions treated the same!"
    ),
    "help_special": (
        "⚙️ *Special Features*\n\n"
        "Advanced group management:\n\n"
        "*Auto-Delete Join Messages*\n"
        "`/autodeletejoins <on/off>` - Toggle auto-delete\n"
        "Removes \"user joined\" service messages\n\n"
        "*Auto-Delete Pin Notifications*\n"
        "`/autodeletepins <on/off> [delay]` - Toggle\n"
        "Example: `/autodeletepins on 300`\n"
        "(Deletes pin after 5 minutes)\n\n"
        "*Rules*\n"
        "`/rules` - Show chat rules\n"
        "`/setrules <text>` - Set chat rules (admin)\n\n"
        "*Information*\n"
        "`/info` - Chat/user information\n"
        "`/id` - Get user/chat ID"
    ),
    "help_premium": (
        "⭐ *Premium Features*\n\n"
        "Unlock advanced functionality:\n\n"
        "*Check Status*\n"
        "`/premium` - View premium status\n\n"
        "*Analytics*\n"
        "`/analytics` - View chat analytics\n"
        "(Premium only)\n\n"
        "*Premium Benefits:*\n"
        "• Advanced analytics & insights\n"
        "• Extended limits for notes/filters\n"
        "• Priority support\n"
        "• Custom features on request\n"
        "• Faster response times\n"
        "• No ads or limitations\n\n"
        "*Get Premium:*\n"
        "Contact the bot owner to upgrade your chat!"
    ),
    "help_owner": (
        "👑 *Owner Commands*\n\n"
        "Bot administration (Owner only):\n\n"
        "*Statistics*\n"
        "`/stats` - Global bot statistics\n\n"
        "*Broadcasting*\n"
        "`/broadcast <message>` - Send to all chats\n\n"
        "*Premium Management*\n"
        "`/addpremium <chat_id> [days]` - Add premium\n"
        "`/removepremium <chat_id>` - Remove premium\n\n"
        "*Chat Management*\n"
        "`/chatinfo [chat_id]` - Chat details\n"
        "`/listchats` - List all bot chats\n\n"
        "*Note:* These commands are restricted\n"
        "to the bot owner only."
    ),
    "help_info": (
        "ℹ️ *Bot Information*\n\n"
        "*About DCL Rose Bot*\n"
        "A powerful group management bot\n"
        "inspired by Rose Bot.\n\n"
        "*Features:*\n"
        "• Admin tools (ban, kick, mute)\n"
        "• Warning system\n"
        "• Welcome/goodbye messages\n"
        "• Notes & filters\n"
        "• Locks & anti-flood\n"
        "• Allowed links whitelist\n"
        "• Auto-delete features\n"
        "• Premium analytics\n\n"
        "*Support:*\n"
        "Use /help to explore all features\n"
        "Contact owner for assistance\n\n"
        "*Version:* 2.0\n"
        "*Built with:* Python 3.12+ & MongoDB"
    ),
    "help_extra": (
        "🎯 *Extra Tools*\n\n"
        "Advanced moderation tools:\n\n"
        "*Purge Messages*\n"
        "`/purge` - Delete messages in bulk\n"
        "Reply to a message and use /purge\n"
        "Deletes all messages from that point to current\n\n"
        "*Delete Message*\n"
        "`/del` or `/delete` - Delete specific message\n"
        "Reply to message and use the command\n\n"
        "*Tag All Members*\n"
        "`/tagall [message]` - Mention all members\n"
        "`/mention [message]` - Same as /tagall\n"
        "Example: `/tagall Important announcement!`\n"
        "Note: Limited to 50 users to prevent spam\n\n"
        "*User Info*\n"
        "`/userinfo` - Detailed user information\n"
        "Shows activity, join date, warnings, etc.\n\n"
        "*Cleanup*\n"
        "`/cleanup [count]` - Clean old messages\n"
        "Example: `/cleanup 100`"
    ),
    "help_forcesub": (
        "🔐 *Force Subscription*\n\n"
        "Require users to join your channel:\n\n"
        "*Setup*\n"
        "1. Add bot to your channel as admin\n"
        "2. Set the channel:\n"
        "`/setchannel @your_channel`\n"
        "Or: `/setchannel -1001234567890`\n\n"
        "*Enable/Disable*\n"
        "`/forcesub on` - Enable force subscription\n"
        "`/forcesub off` - Disable force subscription\n\n"
        "*Check Settings*\n"
        "`/forcesub` - View current settings\n\n"
        "*How it works:*\n"
        "Non-subscribed users' messages are deleted\n"
        "They'll receive a prompt to join the channel\n"
        "Admins are exempt from this restriction\n\n"
        "*Note:* Bot must have delete permissions!"
    )
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    chat_type = update.effective_chat.type

    if chat_type == "private":
        # Private chat welcome message
        message = f"👋 Hello {user.first_name}!\n\n"
        message += "I'm a powerful group management bot inspired by Rose Bot.\n\n"
        message += "🔹 Add me to your group to get started!\n"
        message += "🔹 Make me an admin with appropriate permissions\n"
        message += "🔹 Use /help to see all available commands\n\n"
        message += "💬 For support, contact the bot owner."

        keyboard = [
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
            [InlineKeyboardButton("Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        # Group chat
        db: Database = context.bot_data['db']
        db.add_chat(update.effective_chat.id, update.effective_chat.title, chat_type)

        await update.message.reply_text(
            "👋 Hello! I'm ready to help manage this group.\n"
            "Use /help to see available commands."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler with inline buttons"""
    keyboard = [
        [
            InlineKeyboardButton("👥 Admin", callback_data="help_admin"),
            InlineKeyboardButton("⚠️ Warnings", callback_data="help_warnings")
        ],
        [
            InlineKeyboardButton("💬 Welcome", callback_data="help_welcome"),
            InlineKeyboardButton("📝 Notes", callback_data="help_notes")
        ],
        [
            InlineKeyboardButton("🔍 Filters", callback_data="help_filters"),
            InlineKeyboardButton("🔒 Locks", callback_data="help_locks")
        ],
        [
            InlineKeyboardButton("🔗 Links", callback_data="help_links"),
            InlineKeyboardButton("⚙️ Special", callback_data="help_special")
        ],
        [
            InlineKeyboardButton("🎯 Extra Tools", callback_data="help_extra"),
            InlineKeyboardButton("🔐 Force Sub", callback_data="help_forcesub")
        ],
        [
            InlineKeyboardButton("⭐ Premium", callback_data="help_premium"),
            InlineKeyboardButton("👑 Owner", callback_data="help_owner")
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="help_info")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "📚 *Help Menu*\n\n"
        "Welcome to the DCL Rose Bot help center!\n"
        "Select a category below to view detailed commands and examples.\n\n"
        "💡 Click on any button to explore specific features."
    )

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chat information"""
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        message = f"👤 User Information:\n\n"
        message += f"Name: {user.first_name}"
        if user.last_name:
            message += f" {user.last_name}"
        message += f"\nUser ID: {user.id}\n"
        if user.username:
            message += f"Username: @{user.username}\n"

        await update.message.reply_text(message)
    else:
        # Group info
        db: Database = context.bot_data['db']

        member_count = await get_chat_member_count(context, chat.id)
        is_premium = db.is_premium(chat.id)

        message = f"📊 Chat Information:\n\n"
        message += f"Title: {chat.title}\n"
        message += f"Chat ID: {chat.id}\n"
        message += f"Type: {chat.type}\n"

        if chat.username:
            message += f"Username: @{chat.username}\n"

        message += f"Members: {member_count}\n"
        message += f"Premium: {'Yes ⭐' if is_premium else 'No'}\n"

        await update.message.reply_text(message)


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chat rules"""
    chat_id = update.effective_chat.id
    db: Database = context.bot_data['db']

    settings = db.get_settings(chat_id)
    rules_text = settings.get("rules", "No rules have been set for this chat yet.")

    await update.message.reply_text(
        f"📜 Chat Rules:\n\n{rules_text}",
        parse_mode=ParseMode.MARKDOWN
    )


async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set chat rules (admin only)"""
    from utils import admin_only

    # Check if user is admin
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    from utils import is_user_admin, is_owner
    if not (is_owner(user_id) or await is_user_admin(update, context, user_id, chat_id)):
        await update.message.reply_text("This command is only available to admins.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /setrules <rules>\n"
            "Or reply to a message with /setrules"
        )
        return

    db: Database = context.bot_data['db']

    if update.message.reply_to_message:
        rules_text = update.message.reply_to_message.text or "No rules set."
    else:
        rules_text = " ".join(args)

    settings = db.get_settings(chat_id)
    settings["rules"] = rules_text

    if db.update_settings(chat_id, settings):
        await update.message.reply_text("Chat rules updated successfully!")
    else:
        await update.message.reply_text("Failed to update rules.")


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user or chat ID"""
    chat = update.effective_chat
    user = update.effective_user

    message = f"💳 ID Information:\n\n"
    message += f"Your ID: `{user.id}`\n"

    if chat.type != "private":
        message += f"Chat ID: `{chat.id}`\n"

    if update.message.reply_to_message:
        replied_user = update.message.reply_to_message.from_user
        message += f"Replied User ID: `{replied_user.id}`\n"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help menu button callbacks"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    # Get help text for the selected category
    help_text = HELP_TEXTS.get(callback_data, "Help text not found.")

    # Back button
    keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def help_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button in help menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("👥 Admin", callback_data="help_admin"),
            InlineKeyboardButton("⚠️ Warnings", callback_data="help_warnings")
        ],
        [
            InlineKeyboardButton("💬 Welcome", callback_data="help_welcome"),
            InlineKeyboardButton("📝 Notes", callback_data="help_notes")
        ],
        [
            InlineKeyboardButton("🔍 Filters", callback_data="help_filters"),
            InlineKeyboardButton("🔒 Locks", callback_data="help_locks")
        ],
        [
            InlineKeyboardButton("🔗 Links", callback_data="help_links"),
            InlineKeyboardButton("⚙️ Special", callback_data="help_special")
        ],
        [
            InlineKeyboardButton("🎯 Extra Tools", callback_data="help_extra"),
            InlineKeyboardButton("🔐 Force Sub", callback_data="help_forcesub")
        ],
        [
            InlineKeyboardButton("⭐ Premium", callback_data="help_premium"),
            InlineKeyboardButton("👑 Owner", callback_data="help_owner")
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="help_info")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "📚 *Help Menu*\n\n"
        "Welcome to the DCL Rose Bot help center!\n"
        "Select a category below to view detailed commands and examples.\n\n"
        "💡 Click on any button to explore specific features."
    )

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


def register_handlers(application):
    """Register basic command handlers"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("setrules", set_rules))
    application.add_handler(CommandHandler("id", id_command))

    # Callback query handlers for help menu
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_(admin|warnings|welcome|notes|filters|locks|links|special|premium|owner|info|extra|forcesub)$"))
    application.add_handler(CallbackQueryHandler(help_back_callback, pattern="^help_back$"))
