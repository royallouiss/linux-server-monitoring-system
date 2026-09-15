from django.conf import settings
from django.core.mail import send_mail


class EmailNotificationService:
    def __init__(self, recipient_list=None):
        self.recipient_list = recipient_list or getattr(
            settings,
            "ALERT_NOTIFICATION_RECIPIENTS",
            [],
        )

    def notify(self, alert):
        if not self.recipient_list:
            return False

        return bool(
            send_mail(
                subject=alert.title,
                message=alert.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self.recipient_list,
                fail_silently=True,
            ),
        )


class NotificationService:
    def __init__(self, backend=None):
        self.backend = backend or EmailNotificationService()

    def notify(self, alert):
        return self.backend.notify(alert)
