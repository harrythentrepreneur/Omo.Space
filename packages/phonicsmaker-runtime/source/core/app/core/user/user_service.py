# app/core/user/user_service.py

from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config.logger import logger
from app.db.models.basic import Subscription, User, UserPreference

load_dotenv()


class UserService:
    def __init__(self, db: Session):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> Dict:
        """Fetch user details from the database."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User not found for {user_id}")
                raise ValueError(f"User not found for {user_id}")

            return {
                "full_name": user.full_name,
                "email": user.email,
                "user_id": str(user.id),
                "clerk_id": user.clerk_id,
            }
        except Exception as e:
            logger.error(f"Error fetching user details for user_id {user_id}: {str(e)}")
            raise e

    async def get_user_details(self, email: str) -> Dict:
        """Fetch user details from the database."""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                logger.error(f"User not found for {email}")
                raise ValueError(f"User not found for {email}")

            return {
                "full_name": user.full_name,
                "email": user.email,
                "user_id": str(user.id),
            }
        except Exception as e:
            logger.error(f"Error fetching user details for email {email}: {str(e)}")
            raise e

    async def get_user_prefs(self, phone_number: str) -> Optional[Dict]:
        try:
            user_pref = (
                self.db.query(UserPreference)
                .filter(UserPreference.phone == phone_number)
                .first()
            )

            if not user_pref:
                logger.info(
                    f"No user preferences found for phone number: {phone_number}"
                )
                return None

            return {
                "user_id": str(user_pref.user_id),
                "phone": user_pref.phone,
                "email": user_pref.email,
                "description": user_pref.description,
            }
        except Exception as e:
            logger.error(f"Error checking user phone number: {str(e)}")
            raise

    async def get_user_subscriptions(self, email: str) -> List[Dict[Any, Any]]:
        """Fetch user subscriptions from the database."""
        try:
            subscriptions = (
                self.db.query(Subscription)
                .filter(
                    Subscription.email == email,
                    or_(Subscription.status.in_(["trialing", "active"])),
                )
                .all()
            )

            return [subscription.__dict__ for subscription in subscriptions]
        except Exception as e:
            logger.error(f"Error fetching subscriptions for user {email}: {str(e)}")
            return []

    async def verify_premium_status(self, email: str) -> bool:
        """Verify if user has premium access."""
        subscriptions = await self.get_user_subscriptions(email)

        # Raising because we expect all users to have a subscription
        if not subscriptions:
            raise ValueError("Not Subscribed to any premium plans")
        return True

    async def get_user_id_by_email(self, email: str) -> str:
        """Get user_id from email"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise ValueError(f"User with email {email} not found")
            return str(user.id)
        except Exception as e:
            logger.error(f"Error getting user_id for email {email}: {str(e)}")
            raise
