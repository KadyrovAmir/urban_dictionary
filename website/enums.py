from enum import Enum


class Role(Enum):
    user = 1
    moderator = 2
    admin = 3

    @staticmethod
    def get_role(user):
        if user.is_superuser:
            return Role.admin
        if user.is_staff:
            return Role.moderator
        return Role.user

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

    def __str__(self):
        if self is Role.admin:
            return 'Администратор'
        if self is Role.moderator:
            return 'Модератор'
        return 'Пользователь'


class Status(Enum):
    active = 1
    blocked = 2
    not_activated = 3

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

    def __str__(self):
        if self.value == Status.active:
            return 'Активный'
        if self.value == Status.blocked:
            return 'Заблокированный'
        return 'Неподтвержденная регистрация'

STATUSES_FOR_REQUESTS = (
    (1, "Новый"),
    (2, "Отклонен"),
    (3, "Опубликован"),
    (4, "Навсегда отклонен")
)

RATING_VALUES = (
    (0, "Dislike"),
    (1, "Like"),
)