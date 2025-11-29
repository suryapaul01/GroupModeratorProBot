# DCL Rose Bot - Telegram Group Management Bot

A powerful Telegram bot for managing groups and channels, inspired by the popular Rose bot. Built with Python 3.12+ and MongoDB.

## Features

### Core Features

#### Admin Management
- **Ban/Unban** - Ban or unban users from the group
- **Kick** - Remove users from the group
- **Mute/Unmute** - Restrict or restore user messaging permissions
- **Promote/Demote** - Manage admin permissions
- **Pin/Unpin** - Pin important messages

#### Warnings System
- Warn users for rule violations
- Configurable warning limits (1-10)
- Customizable actions: ban, kick, or mute
- Track warning history
- Reset warnings

#### Welcome & Goodbye Messages
- Customizable welcome messages for new members
- Optional goodbye messages
- Support for placeholders (mention, name, chat name, etc.)
- Toggle on/off functionality

#### Notes System
- Save and retrieve notes
- Support for text, photos, videos, documents, and stickers
- Easy note management with /get and /save commands
- List all saved notes

#### Filters (Custom Triggers)
- Create custom keyword triggers
- Automatic responses to keywords
- Support for media responses
- Easy filter management

#### Locks & Restrictions
- Lock specific message types:
  - All messages
  - Media (photos, videos, documents)
  - Stickers and GIFs
  - Polls
  - Web links
  - Forwarded messages
- Fine-grained control over chat content

#### Anti-Flood Protection
- Configurable message limits
- Time-based flood detection
- Automatic muting of spammers
- Prevent group spam

### Special Features

#### Auto-Delete Join Requests
- Automatically delete "user joined" service messages
- Keep your chat clean and organized
- Toggle on/off per chat

#### Auto-Delete Pin Messages
- Remove pin notification messages
- Optional: Auto-delete pinned messages after a delay
- Configurable delay (0-24 hours)
- Reduce notification spam

#### User Tracking & Analytics
- Track all user activity
- Message count statistics
- Join/leave tracking
- Premium: Advanced analytics and insights

### Premium Features

Premium features provide enhanced functionality for power users:

- **Advanced Analytics** - Detailed event tracking and statistics
- **Priority Support** - Get help faster
- **Extended Limits** - More notes, filters, and storage
- **Custom Features** - Request custom functionality
- **Faster Response Times** - Optimized performance

### Bot Owner Controls

Special commands for bot administrators:

- **Global Statistics** - View bot-wide statistics
- **Broadcast** - Send messages to all chats
- **Premium Management** - Add/remove premium access
- **Chat Information** - Detailed chat insights
- **User Management** - Global user tracking

## Installation

### Prerequisites

- Python 3.12 or higher
- MongoDB (local or cloud instance)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Setup Instructions

1. **Clone or download the repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB**
   - Install MongoDB locally, or
   - Use MongoDB Atlas (cloud) - [Get started here](https://www.mongodb.com/cloud/atlas)

4. **Configure the bot**
   - Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and fill in your details:

   ```env
   # Bot Configuration
   BOT_TOKEN=your_bot_token_here
   BOT_USERNAME=your_bot_username

   # MongoDB Configuration
   MONGO_URI=mongodb://localhost:27017/
   DATABASE_NAME=rose_bot

   # Bot Owner Configuration
   OWNER_ID=your_telegram_user_id

   # Premium Configuration (optional)
   PREMIUM_CHAT_IDS=123456789,987654321

   # Optional Configuration
   LOG_CHANNEL_ID=
   SUPPORT_CHAT=
   ```

5. **Get your User ID**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram to get your user ID
   - Add this ID to the `OWNER_ID` field in `.env`

6. **Run the bot**
   ```bash
   python bot.py
   ```

## Usage

### Getting Started

1. **Add the bot to your group**
   - Click on "Add to Group" button when you start the bot in private
   - Or manually add the bot to your group

2. **Make the bot an admin**
   - Give the bot admin permissions
   - Required permissions:
     - Delete messages
     - Ban users
     - Invite users
     - Pin messages
     - Manage chat

3. **Start using commands**
   - Use `/help` to see all available commands
   - Configure welcome messages, warnings, locks, etc.

### Command List

#### Basic Commands
- `/start` - Start the bot
- `/help` - Show all commands
- `/info` - Chat/user information
- `/id` - Get user or chat ID
- `/rules` - Show chat rules
- `/setrules` - Set chat rules (admin)

#### Admin Commands
- `/ban` - Ban a user
- `/unban` - Unban a user
- `/kick` - Kick a user
- `/mute` - Mute a user
- `/unmute` - Unmute a user
- `/promote` - Promote to admin
- `/demote` - Demote admin
- `/pin` - Pin a message
- `/unpin` - Unpin message

#### Warning Commands
- `/warn` - Warn a user
- `/removewarn` - Remove warnings
- `/warns` - Check warnings
- `/setwarnlimit <number>` - Set max warnings (1-10)
- `/setwarnaction <ban/kick/mute>` - Set action when limit reached

#### Welcome Commands
- `/setwelcome <message>` - Set welcome message
- `/setgoodbye <message>` - Set goodbye message
- `/welcome` - Toggle welcome on/off
- `/goodbye` - Toggle goodbye on/off

**Available placeholders:**
- `{mention}` - Mention the user
- `{first}` - User's first name
- `{last}` - User's last name
- `{fullname}` - Full name
- `{username}` - Username
- `{id}` - User ID
- `{chatname}` - Chat name
- `{chatid}` - Chat ID

#### Notes Commands
- `/save <name> <content>` - Save a note
- `/get <name>` - Get a note
- `/notes` - List all notes
- `/clear <name>` - Delete a note

#### Filter Commands
- `/filter <keyword> <response>` - Add filter
- `/filters` - List all filters
- `/stop <keyword>` - Remove filter

#### Lock Commands
- `/lock <type>` - Lock message type
- `/unlock <type>` - Unlock message type
- `/locks` - List active locks
- `/antiflood <on/off> [limit] [time]` - Configure antiflood

**Available lock types:**
- `messages` - All messages
- `media` - Photos, videos, documents
- `stickers` - Stickers and GIFs
- `gifs` - Only GIFs
- `polls` - Polls
- `links` - Web links
- `forwards` - Forwarded messages

#### Special Feature Commands
- `/autodeletejoins <on/off>` - Toggle auto-delete join messages
- `/autodeletepins <on/off> [delay]` - Toggle auto-delete pin messages

#### Premium Commands
- `/premium` - Check premium status
- `/analytics` - View chat analytics (premium only)

#### Owner Commands (Owner Only)
- `/stats` - Global bot statistics
- `/broadcast <message>` - Broadcast to all chats
- `/addpremium <chat_id> [days]` - Add premium to chat
- `/removepremium <chat_id>` - Remove premium
- `/chatinfo [chat_id]` - Chat information
- `/listchats` - List all bot chats

## Examples

### Setting up Welcome Messages

```
/setwelcome Welcome {mention} to {chatname}! Please read the /rules
```

### Warning System

```
# Set 3 warnings before ban
/setwarnlimit 3
/setwarnaction ban

# Warn a user (reply to their message)
/warn Spamming the chat

# Check warnings
/warns
```

### Locks Example

```
# Lock links and media
/lock links
/lock media

# Enable antiflood: max 5 messages in 10 seconds
/antiflood on 5 10
```

### Auto-Delete Features

```
# Auto-delete join messages
/autodeletejoins on

# Auto-delete pin notifications and remove pins after 5 minutes
/autodeletepins on 300
```

## Project Structure

```
DCL_RoseBot/
├── bot.py                          # Main bot file
├── config.py                       # Configuration management
├── database.py                     # MongoDB operations
├── utils.py                        # Utility functions
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables
├── README.md                       # Documentation
└── handlers/                       # Command handlers
    ├── __init__.py
    ├── basic.py                    # Basic commands
    ├── admin.py                    # Admin commands
    ├── welcome.py                  # Welcome/goodbye
    ├── warnings.py                 # Warning system
    ├── notes.py                    # Notes and filters
    ├── locks.py                    # Locks and antiflood
    ├── special_features.py         # Auto-delete features
    └── owner.py                    # Owner commands
```

## Database Collections

- **chats** - Store chat information
- **users** - Track user activity
- **warnings** - Warning records
- **notes** - Saved notes
- **filters** - Custom filters
- **settings** - Chat-specific settings
- **premium** - Premium subscriptions
- **analytics** - Event tracking

## Contributing

Contributions are welcome! Feel free to:

- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## Support

For support:
- Check the `/help` command in the bot
- Review this documentation
- Contact the bot owner

## License

This project is created for educational and group management purposes.

## Credits

Inspired by the popular Rose Bot for Telegram.

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [pymongo](https://github.com/mongodb/mongo-python-driver)
- Python 3.12+

---

Made with ❤️ for the Telegram community
