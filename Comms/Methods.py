import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config
from Comms.Templates import email_templates

# Load environment variables
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_USER = config("EMAIL_USER")
EMAIL_PASSWORD = config("EMAIL_PASSWORD")


async def send_email(to_email: str, subject: str, body: str) -> bool:
    try:
        # Set up the server
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        # Construct the message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send the email
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


async def get_email_content(template_name: str, **kwargs) -> dict:
    """
    Generates the subject and body for an email by substituting placeholders.

    Args:
    - template_name (str): The key name of the template in the email_templates dictionary.
    - kwargs: Key-value pairs matching placeholders in the template.

    Returns:
    - dict: A dictionary with 'subject' and 'body' containing the populated content.
    """
    template = email_templates.get(template_name)
    if not template:
        raise ValueError("Template not found.")

    subject = template["subject"].format(**kwargs)
    body = template["body"].format(**kwargs)

    return {"subject": subject, "body": body}
