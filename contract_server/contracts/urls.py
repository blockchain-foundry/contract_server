from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from contracts import views

urlpatterns = [
    url(r'^contracts/$', views.Contracts.as_view()),
    url(r'^subcontracts/$', views.SubContracts.as_view()),
    url(r'^subcontracts/(?P<multisig_address>[A-Za-z0-9]+)/(?P<deploy_address>[A-Za-z0-9]+)', views.SubContractFunc.as_view()),
    url(r'^contracts/(?P<multisig_address>[A-Za-z0-9]+)/', views.ContractFunc.as_view()),
    url(r'^contractlist/$', views.ContractList.as_view()),
   # url(r'^functions/$', views.transfer_money_to_account),
    url(r'^execute/$', views.create_multisig_payment),
    url(r'^withdraw/$', views.WithdrawFromContract.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
