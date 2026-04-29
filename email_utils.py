import logging
import os

from flask_mail import Mail, Message

from extensions import mail


def _normalize_recipients(recipients: list) -> list:
    return [recipient for recipient in recipients if recipient]


def send_email(mail: Mail, subject: str, recipients: list, body: str):
    msg = Message(subject, recipients=_normalize_recipients(recipients))
    msg.html = body
    try:
        mail.send(msg)
        return True, None
    except Exception as exc:
        print("[ERROR]: Failed to send email")
        return False, str(exc)

def send_email_with_attachment(mail: Mail, subject: str, recipients: list, body: str, attachment_path: str|None = None):
    
    normalized_recipients = _normalize_recipients(recipients)
    if not normalized_recipients:
        return False, "Nessun destinatario email disponibile"

    msg = Message(subject, recipients=normalized_recipients)
    msg.html = body
    try:
        if attachment_path:
            with open(attachment_path, 'rb') as f:
                msg.attach(filename=os.path.basename(attachment_path), content_type='application/pdf', data=f.read())
        mail.send(msg)
        return True, None
    except Exception as exc:
        print("[ERROR]: Failed to send email with attachment")
        return False, str(exc)
    
def build_email_body(submitter_name, submitter_surname, form_name, entity_name):
    return f"""
    <p>Gentile {submitter_name} {submitter_surname},</p>
    <p>La informiamo che il modulo <strong>{form_name}</strong> è stato ricevuto con successo da {entity_name}.</p>
    <p>In allegato trova una copia del modulo compilato.</p>
    <br>
    <p>Cordiali saluti,<br><strong>{entity_name}</strong></p>
    <hr>
    <p style="font-size: 0.8em; color: gray;">
        Questa email è stata inviata automaticamente tramite 
        <a href="https://github.com/SamuGallo-06/OpenModuli">OpenModuli</a>. 
        Si prega di non rispondere a questa email.
    </p>
    """