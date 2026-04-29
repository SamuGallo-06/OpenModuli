from flask_mail import Message, Mail

def send_email(mail: Mail, subject: str, recipients: list, body: str):
    msg = Message(subject, recipients=recipients)
    msg.html = body
    mail.send(msg)