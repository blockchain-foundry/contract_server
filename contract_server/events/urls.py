from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from events import views


urlpatterns = [
    url(r'^watches/$', views.Watches.as_view()),
    url(r'^watches/(?P<watch_id>[a-zA-Z0-9-]+)', views.Watches.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
