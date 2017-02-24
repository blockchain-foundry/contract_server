from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from events import views


urlpatterns = [
    url(r'^watches/$', views.Events.as_view()),
    url(r'^notify/(?P<multisig_address>[a-zA-Z0-9]+)/(?P<receiver_address>[a-zA-Z0-9-]+)', views.Notify.as_view()),
    url(r'^notify/(?P<multisig_address>[a-zA-Z0-9]+)', views.Notify.as_view()),
    url(r'^watches/(?P<subscription_id>[a-zA-Z0-9-]+)', views.Watches.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
