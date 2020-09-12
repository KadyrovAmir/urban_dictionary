from django import template

from website.models import Favorites, Rating

register = template.Library()


@register.simple_tag
def is_favoured(definition, user):
    if Favorites.objects.filter(user=user.custom_user, definition=definition).exists():
        return "favoritesadded"
    else:
        return "favorites"


@register.simple_tag
def is_liked(definition, user):
    if user.is_authenticated and Rating.objects.filter(user=user.custom_user, definition=definition,
                                                       estimate=1).exists():
        return "btn-success"
    else:
        return "btn-outline-success"


@register.simple_tag
def is_disliked(definition, user):
    if user.is_authenticated and Rating.objects.filter(user=user.custom_user, definition=definition,
                                                       estimate=0).exists():
        return "btn-danger"
    else:
        return "btn-outline-danger"
