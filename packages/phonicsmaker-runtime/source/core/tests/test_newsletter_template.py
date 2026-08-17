# tests/test_newsletter_template.py

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

LOGO_URL = "https://app.inboxclarity.io/images/logo.png"


def get_template_path():
    """Get the absolute path to the templates directory"""
    current_dir = Path(__file__).parent
    template_dir = current_dir.parent / "templates"
    return template_dir


def test_newsletter_template_renders():
    # Setup template environment
    env = Environment(loader=FileSystemLoader(get_template_path()))
    template = env.get_template("newsletter.html")

    # Prepare test data
    test_data = {
        "title": "Daily Executive Summary",
        "timestamp": datetime.now().strftime("%B %d, %Y"),
        "logo_data": LOGO_URL,
        "day_of_week": "Monday",
        "date": "January 10, 2025",
        "summary": """
            <div class="text">
            <span class="bold">Executive Summary:</span>
            <div class="text-content">FocusGate has reached MVP status with key functionalities working, though there's a potential concurrency issue under specific high-load scenarios. Billing and pricing infrastructure is being implemented. A significant development is the commencement of InboxClarity, an email summarization tool, spurred by immediate client demand. Kavishka has been hired as a Software Engineer Intern. The team is actively addressing technical challenges related to Stripe integration, Google OAuth, and multi-workspace support. The successful launch of Lightstone is driving this rapid pace of development.</div>
        </div>

        <div class="text">
            <span class="bold">Email Deadlines:</span>
            <div class="text-content">Respond to DigitalOcean non-payment notice by Monday, January 27th to avoid resource deletion.</div>
            <div class="text-content">AWS invoices are due, with charges attempted in two days. Update payment method if necessary.</div>
        </div>

        <div class="text">
            <span class="bold">Action Items:</span>
            <div class="text-content">Set up Sentry for Enzi products (<span>Rukshan</span>).</div>
            <div class="text-content">Finalize FocusGate billing/pricing fixes (<span>Rukshan</span>).</div>
        </div>
        """,
        "is_premium": False,
        "prep_for": "Harry Edwards",
        "prep_by": "Inbox Clarity",
    }

    # Render template
    rendered_html = template.render(**test_data)

    # Optional: Save rendered HTML for manual inspection
    output_path = Path(__file__).parent / "test_output"
    output_path.mkdir(exist_ok=True)

    with open(output_path / "test_newsletter.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)


def test_premium_newsletter_template():
    """Test rendering for premium users"""
    env = Environment(loader=FileSystemLoader(get_template_path()))
    template = env.get_template("newsletter.html")

    test_data = {
        "title": "Daily Executive Summary",
        "timestamp": datetime.now().strftime("%B %d, %Y"),
        "logo_data": LOGO_URL,
        "day_of_week": "Monday",
        "date": "January 10, 2025",
        "summary": """
            <p>Premium Executive Summary:</p>
            <p>1. Detailed Market Analysis: In-depth review of sector performance...</p>
            <p>2. Strategic Planning: Complete breakdown of Q1 2025 initiatives...</p>
            <p>3. Advanced Metrics: Comprehensive dashboard of all KPIs...</p>
        """,
        "is_premium": True,
    }

    rendered_html = template.render(**test_data)

    output_path = Path(__file__).parent / "test_output"
    output_path.mkdir(exist_ok=True)

    with open(output_path / "test_premium_newsletter.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
