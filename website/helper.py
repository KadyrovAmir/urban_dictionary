from datetime import datetime
from django.shortcuts import get_object_or_404
from website.models import Definition, Notification, Rating
from website.enums import *


def like_and_dislike(request, is_like):
    main_value = 1 if is_like else 0
    second_value = 0 if is_like else 1

    user = request.user.custom_user
    definition_id = request.POST.get('def_id', None)
    defin = get_object_or_404(Definition, pk=definition_id)

    if defin.estimates.filter(user=user, estimate=main_value).exists():
        # user has already liked this definition
        # remove like/user
        defin.estimates.get(user=user).delete()
    elif defin.estimates.filter(user=user, estimate=second_value).exists():
        defin.estimates.get(user=user).delete()
        Rating(definition=defin, user=user, estimate=main_value).save()
        if defin.author.id != user.id:
            Notification(date_creation=datetime.now(), action_type=ACTION_TYPES[main_value][0], user=defin.author,
                         models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()
    else:
        # add a new like for a company
        Rating(definition=defin, user=user, estimate=main_value).save()
        if defin.author.id != user.id:
            Notification(date_creation=datetime.now(), action_type=ACTION_TYPES[main_value][0], user=defin.author,
                         models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()

    return {'likes_count': defin.get_likes(), 'dislikes_count': defin.get_dislikes(), 'is_liked': is_like}
