from enum import Enum

# FOR UPDATE STATUS

# DEF_AMOUNT = 50
# PERCENTAGE_OF_LIKES = 85
# ALL_ESTIMATES = 10000

DEF_AMOUNT = 2
PERCENTAGE_OF_LIKES = 60
ALL_ESTIMATES = 5

AMOUNT_NOTIF_DISPLAY = 10

DEF = "DEF"
SUPPORT = "SUPPORT"
USER = "USER"
RFP = "RFP"
RUPS = "RUPS"
SUP = "SUP"


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

ACTION_TYPES = (
    (0, "Dislike"),  # user_id def_id [DONE]
    (1, "Like"),  # user_id def_id [DONE]
    (2, "Notify update status"),  # NOT IMPLEMENT
    (3, "Status has updated"),  # rups_id [DONE]
    (4, "Def was checked by admin"),  # def_id [DONE]
    (5, "Def was rejected by admin"),  # def_id [DONE]
    (6, "Def was published"),  # def_id [DONE]
    (7, "Block"),  # NOT IMPLEMENT, SEND EMAIL [DONE]
    (8, "Unblock by admin"),  # NOT IMPLEMENT, SEND EMAIL [DONE]
    (9, "Unblock (time)"),  # NOT IMPLEMENT, SEND EMAIL [DONE]
    (10, "Def was added in favorites by smb"),  # user_id  def_id [DONE]
    (11, "Support respond on the email"),  # SUP_ID [DONE]
    (12, "Request for publication"),  # user_id rfp_io [DONE]
    (13, "Request for update status"),  # rups_id [DONE]
    (14, "New question in support"),  # SUP_ID [DONE]
)
