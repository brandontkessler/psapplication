from main_app import mail
from flask_mail import Message
from main_app.config import Config


def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=Config.MAIL_DEFAULT_SENDER
    )
    mail.send(msg)
