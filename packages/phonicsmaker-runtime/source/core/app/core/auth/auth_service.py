# app/core/auth/auth_service.py

from typing import Optional

from clerk_backend_api import Clerk

from app.core.config.config import settings
from app.core.config.logger import logger


async def get_user_token(clerk_id: str, provider: str) -> Optional[str]:
    logger.info(f"Getting OAuth token for user {clerk_id} from provider {provider}")
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            # Get OAuth tokens for the user
            # Unlike supabase, clerk automatically handles the OAuth token refresh and returns the latest valid token
            oauth_tokens = await clerk.users.get_o_auth_access_token_async(
                user_id=clerk_id, provider=provider
            )

            # Extract and return the access token
            if len(oauth_tokens) > 0:
                providerToken = oauth_tokens[0].token

                logger.info(
                    f"Got OAuth token for user {clerk_id} from provider {provider}"
                )
                return providerToken
            else:
                raise Exception(
                    f"OAuth token not found for user {clerk_id} from provider {provider}"
                )

    except Exception as e:
        print(f"Error getting OAuth token: {str(e)}")
        raise e
