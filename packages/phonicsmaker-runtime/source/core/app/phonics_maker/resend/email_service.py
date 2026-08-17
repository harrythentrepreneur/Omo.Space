# email_service.py

from app.core.config.config import settings
from app.core.config.logger import logger
import resend


class EmailService:
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        if not self.api_key:
            raise ValueError("Resend API key not found")
        self.from_email = settings.FROM_EMAIL

        # Set the API key globally
        resend.api_key = self.api_key

    async def send_email(
        self, email_subject: str, email: str, html_content: str
    ) -> bool:
        try:
            response = resend.Emails.send(
                {
                    "from": self.from_email,
                    "to": [email],
                    "subject": email_subject,
                    "html": html_content,
                }
            )

            if response.get("id"):
                logger.info(f"Email sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send email to {email}: {response}")
                return False

        except Exception as e:
            logger.error(f"Exception while sending email to {email}: {str(e)}")
            return False


email_service = EmailService()
