"""contract_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import patterns, include, url
from .views import NewTxNotified, AddressNotified

urlpatterns = [
    url(r'^events/', include('events.urls')),
    url(r'^oracles/', include('oracles.urls')),
    url(r'^smart-contract/', include('contracts.urls')),
    url(r'^', include('contracts.urls')),
    url(r'^states/', include('evm_manager.urls')),
]

urlpatterns += patterns(
    '',
    url(r'^notify/(?P<tx_hash>[a-zA-Z0-9]+)\W', NewTxNotified.as_view()),
    url(r'^addressnotify/(?P<multisig_address>[a-zA-Z0-9]+)', AddressNotified.as_view()),
)
