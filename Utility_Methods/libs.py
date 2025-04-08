import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from decouple import config


from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
# Set up logging
def logging_generate(messagetype, message, filelocation):
    log_message = f"{messagetype}: {message} (Logged from {filelocation})"
    logging.info(log_message)

def email_sender(email, subject, text):
    try:
        # Hostinger SMTP configuration
        smtp_host = 'smtp.hostinger.com'
        smtp_port = 465  # Port for SSL
        sender_email = config('HOSTINGER_EMAIL') 
        
        sender_password = config('HOSTINGER_PASS')
        
        
        # Set up the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        
        # Attach the email body text
        msg.attach(MIMEText(text, 'plain'))
        
        # Create the SMTP connection and send the email
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        
        # Log success message
        messagetype = "success"
        message = f"Email sent successfully to {email}"
        filelocation = "emailsender.py"
        logging_generate(messagetype, message, filelocation)
        
        print(f"Email sent successfully to {email}")
    
    except Exception as e:
        # Log error message
        messagetype = "error"
        message = f"Failed to send email and the reason is: {str(e)}"
        filelocation = "emailcreator.py"
        logging_generate(messagetype, message, filelocation)
        
        # Print the error
        print(f"Error sending email to {email}: {e}")
        raise Exception(f"Failed to send email and the reason is: {str(e)}")

# Example usage
# email_sender('recipient@example.com', 'Subject Text', 'Email Body Content')