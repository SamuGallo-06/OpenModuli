import os
from flask_mail import Message, Mail
from extensions import mail

def send_email(mail: Mail, subject: str, recipients: list, body: str):
    msg = Message(subject, recipients=recipients)
    msg.html = body
    mail.send(msg)

def send_email_with_attachment(mail: Mail, subject: str, recipients: list, body: str, attachment_path: str|None = None):
    msg = Message(subject, recipients=recipients)
    msg.html = body
    if attachment_path:
        with open(attachment_path, 'rb') as f:
            msg.attach(filename=os.path.basename(attachment_path), content_type='application/pdf', data=f.read())
    mail.send(msg)