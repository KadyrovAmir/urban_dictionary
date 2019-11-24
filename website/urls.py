from django.conf.urls import url
from website.views import *

app_name = "website"

urlpatterns = [
    url(r'^(?P<pk>\d+)$', TermView.as_view(), name='term_page'),
    url(r'^$', main_page, name="main_page"),
    url('edit_profile/', update_profile, name='update_profile'),
    url('create_definition/', page_create_definition, name='page_create_definition'),
    url('definition/', page_create_definition, name='create_definition'),
    url(r'^definition/(?P<id>\d+)$', definition, name='definition')
    url('activate_user/', activate_user, name='activate_user'),
]
