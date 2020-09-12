from django.urls import path
from api.views import *

app_name = "api"

urlpatterns = [
    path(r'definition/', definition, name='definition'),
    # path(r'', main_page, name="main_page"),
    # path(r'edit_profile/', update_profile, name='update_profile'),
    # path(r'change_password/', change_password, name="change_password"),
    # path(r'create_definition/', create_definition, name='create_definition'),
    # path(r'term/<int:pk>',  TermView.as_view(), name='term'),
    # path(r'activate_user/', activate_user, name='activate_user'),
    # path(r'random_definition', random_definition, name='random_definition'),
    # path(r'personal_definitions/', personal_definitions, name='personal_definitions'),
    # path(r'definition/<int:pk>', definition, name='definition'),
    # path(r'definition/edit/<int:pk>', edit_definition, name='edit_definition'),
    # path(r'definition/check/<int:pk>', request_for_definition, name='request_for_definition'),
    # path(r'page_not_found/', page_not_found, name='page_not_found'),
    # path(r'definition/like', like, name='like'),
    # path(r'definition/dislike', dislike, name='dislike'),
    # path(r'favourite/', favourite, name='favourite'),
    # path(r'favourites/', favourites, name='favourites_list'),
    # path(r'search/', search, name='search'),
    # path(r'requests/', requests_pub, name='requests_pub'),
    # path(r'profile/<int:pk>', UserDetailView.as_view(), name='profile')
]