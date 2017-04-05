from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from contracts import views

urlpatterns = [
    url(r'^multisig-addresses/(?P<multisig_address>[A-Za-z0-9]+)/bind/$', views.Bind.as_view()),
    url(r'^multisig-addresses/(?P<multisig_address>[A-Za-z0-9]+)/contracts/$', views.DeployContract.as_view()),
    url(r'^multisig-addresses/(?P<multisig_address>[A-Za-z0-9]+)/contracts/(?P<contract_address>[A-Za-z0-9]+)/function/$', views.ContractFunction.as_view()),
    url(r'^contractlist/$', views.ContractList.as_view()),
    url(r'^execute/$', views.create_multisig_payment),
    url(r'^withdraw/$', views.WithdrawFromContract.as_view()),
    url(r'^multisig-addresses/$', views.MultisigAddressesView.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
