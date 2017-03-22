from django.conf.urls import url

from .views import CheckUpdate

urlpatterns = [
    url(r'^checkupdate/(?P<multisig_address>[a-zA-Z0-9]+)/(?P<tx_hash>[a-zA-Z0-9]+)', CheckUpdate.as_view()),
]
