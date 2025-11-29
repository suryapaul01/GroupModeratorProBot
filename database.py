"""
Database handler for MongoDB operations
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from typing import Optional, Dict, List, Any
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, mongo_uri: str, database_name: str):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[database_name]

            # Test connection
            self.client.admin.command('ping')
            logger.info("MongoDB connection successful")

            # Initialize collections
            self.chats = self.db.chats
            self.users = self.db.users
            self.warnings = self.db.warnings
            self.notes = self.db.notes
            self.filters = self.db.filters
            self.settings = self.db.settings
            self.premium = self.db.premium
            self.analytics = self.db.analytics

            # Create indexes
            self._create_indexes()

        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    def _create_indexes(self):
        """Create necessary indexes for better query performance"""
        self.chats.create_index("chat_id", unique=True)
        self.users.create_index([("user_id", ASCENDING), ("chat_id", ASCENDING)])
        self.warnings.create_index([("user_id", ASCENDING), ("chat_id", ASCENDING)])
        self.notes.create_index([("chat_id", ASCENDING), ("name", ASCENDING)])
        self.filters.create_index([("chat_id", ASCENDING), ("keyword", ASCENDING)])
        self.settings.create_index("chat_id", unique=True)
        self.premium.create_index("chat_id", unique=True)
        self.analytics.create_index([("chat_id", ASCENDING), ("date", DESCENDING)])

    # Chat Management
    def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Get chat information"""
        return self.chats.find_one({"chat_id": chat_id})

    def add_chat(self, chat_id: int, chat_title: str, chat_type: str) -> bool:
        """Add or update chat information"""
        try:
            self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_title": chat_title,
                        "chat_type": chat_type,
                        "joined_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding chat: {e}")
            return False

    # User Management
    def add_user(self, user_id: int, chat_id: int, username: str = None,
                 first_name: str = None, last_name: str = None) -> bool:
        """Add or update user information"""
        try:
            self.users.update_one(
                {"user_id": user_id, "chat_id": chat_id},
                {
                    "$set": {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "last_seen": datetime.utcnow()
                    },
                    "$setOnInsert": {"joined_at": datetime.utcnow()},
                    "$inc": {"message_count": 1}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_user(self, user_id: int, chat_id: int) -> Optional[Dict]:
        """Get user information"""
        return self.users.find_one({"user_id": user_id, "chat_id": chat_id})

    def get_chat_users(self, chat_id: int, limit: int = 100) -> List[Dict]:
        """Get all users in a chat"""
        return list(self.users.find({"chat_id": chat_id}).limit(limit))

    # Warnings System
    def add_warning(self, user_id: int, chat_id: int, warned_by: int,
                    reason: str = None) -> int:
        """Add warning to user and return current warning count"""
        try:
            result = self.warnings.update_one(
                {"user_id": user_id, "chat_id": chat_id},
                {
                    "$push": {
                        "warnings": {
                            "warned_by": warned_by,
                            "reason": reason,
                            "timestamp": datetime.utcnow()
                        }
                    },
                    "$inc": {"count": 1}
                },
                upsert=True
            )

            # Get updated count
            user_warnings = self.warnings.find_one({"user_id": user_id, "chat_id": chat_id})
            return user_warnings.get("count", 1) if user_warnings else 1
        except Exception as e:
            logger.error(f"Error adding warning: {e}")
            return 0

    def get_warnings(self, user_id: int, chat_id: int) -> Optional[Dict]:
        """Get user warnings"""
        return self.warnings.find_one({"user_id": user_id, "chat_id": chat_id})

    def reset_warnings(self, user_id: int, chat_id: int) -> bool:
        """Reset user warnings"""
        try:
            self.warnings.delete_one({"user_id": user_id, "chat_id": chat_id})
            return True
        except Exception as e:
            logger.error(f"Error resetting warnings: {e}")
            return False

    # Notes System
    def add_note(self, chat_id: int, name: str, content: str,
                 file_id: str = None, note_type: str = "text") -> bool:
        """Add or update a note"""
        try:
            self.notes.update_one(
                {"chat_id": chat_id, "name": name.lower()},
                {
                    "$set": {
                        "content": content,
                        "file_id": file_id,
                        "type": note_type,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return False

    def get_note(self, chat_id: int, name: str) -> Optional[Dict]:
        """Get a specific note"""
        return self.notes.find_one({"chat_id": chat_id, "name": name.lower()})

    def get_all_notes(self, chat_id: int) -> List[Dict]:
        """Get all notes for a chat"""
        return list(self.notes.find({"chat_id": chat_id}))

    def delete_note(self, chat_id: int, name: str) -> bool:
        """Delete a note"""
        try:
            result = self.notes.delete_one({"chat_id": chat_id, "name": name.lower()})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            return False

    # Filters System
    def add_filter(self, chat_id: int, keyword: str, response: str,
                   file_id: str = None, filter_type: str = "text") -> bool:
        """Add or update a filter"""
        try:
            self.filters.update_one(
                {"chat_id": chat_id, "keyword": keyword.lower()},
                {
                    "$set": {
                        "response": response,
                        "file_id": file_id,
                        "type": filter_type,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding filter: {e}")
            return False

    def get_all_filters(self, chat_id: int) -> List[Dict]:
        """Get all filters for a chat"""
        return list(self.filters.find({"chat_id": chat_id}))

    def delete_filter(self, chat_id: int, keyword: str) -> bool:
        """Delete a filter"""
        try:
            result = self.filters.delete_one({"chat_id": chat_id, "keyword": keyword.lower()})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting filter: {e}")
            return False

    # Settings Management
    def get_settings(self, chat_id: int) -> Dict:
        """Get chat settings with defaults"""
        settings = self.settings.find_one({"chat_id": chat_id})
        if not settings:
            # Return default settings
            return {
                "chat_id": chat_id,
                "welcome_enabled": True,
                "goodbye_enabled": False,
                "welcome_message": "Welcome {mention} to {chatname}!",
                "goodbye_message": "Goodbye {mention}!",
                "antiflood_enabled": False,
                "antiflood_limit": 5,
                "antiflood_time": 10,
                "max_warnings": 3,
                "warn_action": "ban",
                "locks": {
                    "messages": False,
                    "media": False,
                    "stickers": False,
                    "gifs": False,
                    "polls": False,
                    "links": False,
                    "forwards": False
                },
                "auto_delete_join_requests": False,
                "auto_delete_pin_messages": False,
                "pin_delete_delay": 300,  # 5 minutes default
                "allowed_links": [],  # Whitelisted domains
                "force_sub_enabled": False,
                "force_sub_channel": None
            }
        return settings

    def update_settings(self, chat_id: int, settings: Dict) -> bool:
        """Update chat settings"""
        try:
            self.settings.update_one(
                {"chat_id": chat_id},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    # Premium Management
    def is_premium(self, chat_id: int) -> bool:
        """Check if chat has premium access"""
        premium = self.premium.find_one({"chat_id": chat_id})
        if not premium:
            return False

        # Check if premium is still valid
        if "expires_at" in premium:
            if premium["expires_at"] < datetime.utcnow():
                return False

        return premium.get("active", False)

    def add_premium(self, chat_id: int, duration_days: int = 30) -> bool:
        """Add premium access to a chat"""
        try:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(days=duration_days)

            self.premium.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "active": True,
                        "expires_at": expires_at,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding premium: {e}")
            return False

    def remove_premium(self, chat_id: int) -> bool:
        """Remove premium access"""
        try:
            self.premium.update_one(
                {"chat_id": chat_id},
                {"$set": {"active": False}}
            )
            return True
        except Exception as e:
            logger.error(f"Error removing premium: {e}")
            return False

    # Analytics
    def log_analytics(self, chat_id: int, event_type: str, data: Dict = None) -> bool:
        """Log analytics event"""
        try:
            self.analytics.insert_one({
                "chat_id": chat_id,
                "event_type": event_type,
                "data": data or {},
                "date": datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Error logging analytics: {e}")
            return False

    def get_analytics(self, chat_id: int, limit: int = 100) -> List[Dict]:
        """Get analytics for a chat"""
        return list(self.analytics.find({"chat_id": chat_id})
                   .sort("date", DESCENDING)
                   .limit(limit))

    def get_global_stats(self) -> Dict:
        """Get global bot statistics"""
        return {
            "total_chats": self.chats.count_documents({}),
            "total_users": self.users.count_documents({}),
            "total_notes": self.notes.count_documents({}),
            "total_filters": self.filters.count_documents({}),
            "premium_chats": self.premium.count_documents({"active": True})
        }
