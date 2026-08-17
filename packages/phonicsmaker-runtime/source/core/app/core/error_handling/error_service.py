# core/error_handling/error_service.py

import sentry_sdk
from fastapi import HTTPException
from app.core.config.logger import logger
from typing import Optional


class ErrorService:
    def log_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Log an error and send it to Sentry for tracking.
        """
        try:
            error_message = str(error)
            if context:
                error_message = f"{context}: {error_message}"

            # Log the error
            logger.error(error_message)

            # Capture the error in Sentry
            sentry_sdk.capture_exception(error)
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")

    def handle_http_error(
        self, error: Exception, status_code: int = 500, detail: Optional[str] = None
    ) -> HTTPException:
        """
        Handle an error and return an HTTPException.
        """
        try:
            error_message = str(error)
            if detail:
                error_message = f"{detail}: {error_message}"

            # Log the error
            self.log_error(error, context="HTTP Error")

            # Return an HTTPException
            return HTTPException(status_code=status_code, detail=error_message)
        except Exception as e:
            logger.error(f"Error handling HTTP error: {str(e)}")
            return HTTPException(status_code=500, detail="Internal Server Error")


# Initialize the error service
error_service = ErrorService()
