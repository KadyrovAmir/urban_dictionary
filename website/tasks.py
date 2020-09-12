import os

from background_task import background
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.timezone import now
from django_registration.forms import User

from urban_dictionary.settings import EMAIL_HOST_USER

# manage.py process_tasks

@background
def unblock_user(user_id):
    unblocked_user = User.objects.get(pk=user_id)
    blocking = unblocked_user.custom_user.blocking.all().filter(active=True)
    if len(blocking) != 0:
        blocking = blocking[0]
        if blocking.expiration_date <= timezone.now():
            blocking.active = False
            blocking.save()
            unblocked_user.is_active = True
            unblocked_user.save()

            BASE = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(BASE, "unblock_mail.txt"), 'r', encoding="utf-8") as support_mail:
                email_text = support_mail.read() \
                    .replace("user_a93a04d13d4efbf11caf76339de7b435", unblocked_user.username)
                send_mail('Разблокировка на платформе {}'.format(Site.objects.get_current().domain),
                          email_text,
                          EMAIL_HOST_USER,
                          [unblocked_user.email],
                          fail_silently=False)
