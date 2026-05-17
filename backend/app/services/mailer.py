"""
Mailer service for sending emails via SMTP.
"""

import smtplib
from email.message import EmailMessage
import structlog
from app.config import get_settings

logger = structlog.get_logger()

def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    """Send an email using configured SMTP settings."""
    settings = get_settings()
    
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        logger.warning(
            "SMTP not fully configured, skipping email send.", 
            to_email=to_email, 
            subject=subject
        )
        return False
        
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings.smtp_from_email
    msg['To'] = to_email
    
    if is_html:
        msg.add_alternative(body, subtype='html')
    else:
        msg.set_content(body)
        
    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
            
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent successfully", to_email=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("Failed to send email", to_email=to_email, error=str(e))
        return False

def send_invite_email(to_email: str, org_name: str, role: str, token: str):
    """Send an organization invitation email with the accept link."""
    settings = get_settings()
    invite_url = f"{settings.frontend_url}/invite/{token}"
    
    subject = f"You've been invited to join {org_name} on AI Incubator"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 8px;">
                <h2 style="color: #2563eb;">Invitation to Join {org_name}</h2>
                <p>Hello,</p>
                <p>You have been invited to join the <strong>{org_name}</strong> organization on AI Start-up Incubator Simulator as a <strong>{role.replace('_', ' ').title()}</strong>.</p>
                <div style="margin: 30px 0; text-align: center;">
                    <a href="{invite_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Accept Invitation</a>
                </div>
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666; font-size: 0.9em;">
                    <a href="{invite_url}">{invite_url}</a>
                </p>
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;" />
                <p style="font-size: 0.8em; color: #888;">This invitation link will expire in 7 days. If you did not expect this invitation, you can safely ignore this email.</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body, is_html=True)
