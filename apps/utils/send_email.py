from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from threading import Thread


def async_send(subject, text_content, html, manage):
    from_email = settings.DEFAULT_FROM_EMAIL
    email = EmailMultiAlternatives(subject, text_content, from_email, manage)
    email.attach_alternative(html, "text/html")
    email.send()


def send_email(subject, text_content, html, manage):
    if settings.SEND_EMAIL:
        email_task = Thread(target=async_send, args=(subject, text_content, html, manage))
        email_task.start()
        return
