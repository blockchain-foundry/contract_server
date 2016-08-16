from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from oracles import views

urlpatterns = [
    url(r'^oracles/$', views.OracleList.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
