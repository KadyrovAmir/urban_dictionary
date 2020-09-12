from datetime import datetime, timedelta, date

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import truncatechars, truncatewords
from django.utils import timezone

from website.enums import *


class CustomUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="custom_user")
    description = models.TextField(verbose_name="О себе")
    status = models.IntegerField(choices=Status.choices(), blank=False, null=False, default=Status.not_activated.value,
                                 verbose_name="Статус")
    photo = models.ImageField(upload_to='profile_pics', default='profile_pics/default.jpg')

    def get_rating(self):
        return sum(map(lambda x: x.get_likes() - x.get_dislikes(), self.definitions.all()))

    def __str__(self):
        return self.user.username

    def is_moderator(self):
        return self.role == ROLE_CHOICES[1][0]

    def is_admin(self):
        return self.role == ROLE_CHOICES[2][0]

    def get_new_notification(self):
        return len(self.notifications.filter(new=True))

    def get_ratio_lik_to_dis(self):
        likes = sum(map(lambda x: x.get_likes(), self.definitions.all()))
        dislikes = sum(map(lambda x: x.get_dislikes(), self.definitions.all()))
        return likes * 100 / (likes + dislikes)

    def is_ready_to_update(self):
        return len(self.definitions.all().exclude(
            date__isnull=True)) > DEF_AMOUNT and self.get_rating() >= ALL_ESTIMATES and self.get_ratio_lik_to_dis() >= PERCENTAGE_OF_LIKES

    def is_block(self):
        block = self.blocking.all().filter(active=True)
        if len(block) == 0:
            return False
        block = block[0]
        if block.expiration_date <= timezone.now():
            block.active = False
            block.save()
            block.user.is_active = True
            block.user.save()
            return False
        return True


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        CustomUser.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.custom_user.save()


class Term(models.Model):
    name = models.CharField(max_length=200, verbose_name="Термин", unique=True)

    def __str__(self):
        return self.name


class Definition(models.Model):
    term = models.ForeignKey(Term, related_name='definitions', on_delete=models.CASCADE,
                             blank=False, null=False, verbose_name='Термин')
    description = models.TextField(verbose_name="Описание термина")
    date = models.DateTimeField(blank=True, verbose_name="Дата публикации", null=True)
    author = models.ForeignKey(CustomUser, related_name='definitions', on_delete=models.CASCADE,
                               blank=False, null=False, verbose_name='Автор')
    source = models.TextField(verbose_name="Ссылка на источник/первоисточник", default=None, blank=True, null=True)

    def __str__(self):
        return "Определение %s - автор %s" % (self.term, self.author)

    def get_likes(self):
        return self.estimates.filter(estimate=1).count()

    def get_dislikes(self):
        return self.estimates.filter(estimate=0).count()

    def get_primary_example(self):
        return self.examples.get(primary=True).example

    def is_publish(self):
        if self.date is None:
            return False
        return True

    def get_cur_status(self):
        reqs = self.requests.all()
        if len(reqs) == 0:
            return -1
        return reqs.first().status

    @property
    def short_description(self):
        return truncatewords(self.description, 80)

    @classmethod
    def get_top_for_week(cls):
        result = []
        for i in range(7):
            day = date.today() - timedelta(i)
            defs = Definition.objects.filter(date__day=day.day, date__month=day.month, date__year=day.year)
            x = {}
            for d in defs:
                # TODO - temporary change
                if d.get_dislikes() + d.get_likes() >= 5:
                    try:
                        x[d] = d.get_likes() / d.get_dislikes()
                    except ZeroDivisionError:
                        x[d] = d.get_likes()
            m = 0
            top_def = None
            for d, proportion in x.items():
                if proportion > m:
                    top_def = d
            if top_def:
                result.append(top_def)
        return result


class Example(models.Model):
    definition = models.ForeignKey(Definition, related_name='examples', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    example = models.TextField(verbose_name="Пример использования")
    primary = models.BooleanField(default=False, blank=False, null=False, verbose_name="Основной пример")

    def __str__(self):
        return "Пример %s - %s" % (self.example, self.primary)


class UploadData(models.Model):
    definition = models.ForeignKey(Definition, related_name='files', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    header_for_file = models.CharField(max_length=100, null=True, blank=True)
    image = models.ImageField()

    def __str__(self):
        return '%s - %s - %s' % (
            self.definition, self.header_for_file, self.image.url)


class RequestForPublication(models.Model):
    definition = models.ForeignKey(Definition, related_name='requests', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    status = models.IntegerField(choices=STATUSES_FOR_REQUESTS, blank=False, null=False,
                                 default=STATUSES_FOR_REQUESTS[0][0],
                                 verbose_name="Статус публикации")
    reason = models.TextField(verbose_name="Причина отклонения", blank=False, null=False)

    old_request = models.ForeignKey("self", blank=True, null=True, verbose_name="Старый запрос на публикацию",
                                    on_delete=models.SET_NULL)

    date_creation = models.DateTimeField(blank=False, null=False, verbose_name="Дата создания запроса")

    def __str__(self):
        return "Запрос на публикацию определения %s" % self.definition

    def is_new(self):
        return self.status == STATUSES_FOR_REQUESTS[0][0]


class Comment(models.Model):
    definition = models.ForeignKey(Definition, related_name='comments', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    other_comment = models.ForeignKey("self", blank=True, null=True, verbose_name="Корневой комментарий",
                                      on_delete=models.CASCADE)

    text = models.TextField(verbose_name="Комментарий", blank=False)

    date_creation = models.DateTimeField(auto_now_add=True, blank=False, verbose_name="Дата")

    author = models.ForeignKey(CustomUser, related_name='comments', on_delete=models.CASCADE,
                               blank=False, null=False, verbose_name='Автор комментария')

    def __str__(self):
        return "Комментарий %s от %s " % (self.text, self.author)


class Rating(models.Model):
    definition = models.ForeignKey(Definition, related_name='estimates', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    user = models.ForeignKey(CustomUser, related_name='estimates', on_delete=models.CASCADE,
                             blank=False, null=False, verbose_name='Пользователь')
    estimate = models.IntegerField(choices=RATING_VALUES, blank=False, null=False,
                                   default=RATING_VALUES[0][0],
                                   verbose_name="Оценка")

    def __str__(self):
        return "%s определения %s от %s " % (self.estimate, self.definition, self.user)


class Blocking(models.Model):
    user = models.ForeignKey(CustomUser, related_name='blocking', on_delete=models.CASCADE,
                             blank=False, null=False, verbose_name='Пользователь')
    reason = models.TextField(verbose_name="Причина блокировки", blank=False)
    date_creation = models.DateTimeField(auto_now_add=True, blank=False, verbose_name="Дата создания блокировки")
    expiration_date = models.DateTimeField(blank=True, null=True, verbose_name="Дата истекания блокировки")
    active = models.BooleanField(blank=False, null=False, default=True, verbose_name="Активная ")

    def __str__(self):
        return "Блокировка пользователя %s" % self.user


class Favorites(models.Model):
    definition = models.ForeignKey(Definition, related_name='favorites', on_delete=models.CASCADE,
                                   blank=False, null=False, verbose_name='Ссылка на определение')
    user = models.ForeignKey(CustomUser, related_name='favorites', on_delete=models.CASCADE,
                             blank=False, null=False, verbose_name='Ссылка на пользователя')

    def __str__(self):
        return "Избранное пользователя %s - %s " % (self.user, self.definition)


class Notification(models.Model):
    date_creation = models.DateTimeField(blank=False, null=False, verbose_name="Дата уведомления")
    action_type = models.IntegerField(choices=ACTION_TYPES, blank=False, null=False,
                                      default=ACTION_TYPES[0][0],
                                      verbose_name="Тип события")
    user = models.ForeignKey(CustomUser, related_name='notifications', on_delete=models.CASCADE,
                             blank=False, null=False, verbose_name='Ссылка на пользователя')
    models_id = models.CharField(max_length=50, verbose_name="Почта", default="", blank=True, null=True)
    new = models.BooleanField(blank=False, null=False, default=True, verbose_name="Новое уведомление")

    def __str__(self):
        return "Уведомление %s пользователя %s" % (self.action_type, self.user)

    def get_def(self):
        return Definition.objects.get(pk=self.get_id(DEF))

    def get_support(self):
        return Support.objects.get(pk=self.get_id(SUP))

    def get_user(self):
        return CustomUser.objects.get(pk=self.get_id(USER))

    def get_rfp(self):
        return RequestForPublication.objects.get(pk=self.get_id(RFP))

    def get_rups(self):
        return RequestUpdateStatus.objects.get(pk=self.get_id(RUPS))

    # TODO change return object
    def get_request_support(self):
        return self.get_id(SUPPORT)

    def get_id(self, pref):
        elems = str(self.models_id).split(" ")
        for e in elems:
            if pref in e:
                return e[len(pref):]
        return None


class RequestUpdateStatus(models.Model):
    status = models.IntegerField(choices=STATUSES_FOR_REQUESTS, blank=False, null=False,
                                 default=STATUSES_FOR_REQUESTS[0][0],
                                 verbose_name="Статус обновления уровня профиля")
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="update_status")
    date_creation = models.DateTimeField(blank=False, null=False, verbose_name="Дата создания запроса")

    def __str__(self):
        return "Запрос на обновление статуса до модератора для пользователя %s" % self.user


class Support(models.Model):
    question = models.TextField(verbose_name="Ваш вопрос", blank=False)
    name = models.TextField(verbose_name="Ваше имя", blank=False, default="Аноним")
    email = models.CharField(max_length=50, verbose_name="Почта")
    date_creation = models.DateTimeField(blank=False, null=False, verbose_name="Дата")
    answer = models.TextField(verbose_name="Ответ", blank=False, null=True)
    user = models.ForeignKey(CustomUser, related_name='support', on_delete=models.CASCADE,
                             blank=True, null=True, default=None,
                             verbose_name='Ссылка на пользователя')

    def __str__(self):
        return "Вопрос %s от пользователя %s" % (self.question, self.email)
