import os
import platform

from django.http import JsonResponse
from rest_framework.views import APIView

from contract_server import error_response, data_response, ERROR_CODE
from oracles.models import Oracle
from .forms import RegisterOracleForm
import logging

try:
    import http.client as httplib
except ImportError:
    import httplib

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

logger = logging.getLogger(__name__)

# modified from stackoverflow
# Returns True if host responds to a ping request


def ping(host, port):
    # Ping parameters as function of OS
    if platform.system().lower() == "windows":
        ping_str = "-n 1 "
    else:
        ping_str = "-c 1 "

    if port is not None:
        ping_str = ping_str + "-p " + str(port)

    # Ping
    return os.system("ping " + ping_str + " " + host) == 0


class OracleList(APIView):

    def get(self, request, format=None):
        response = {}
        oracle_list = []

        oracles = Oracle.objects.all()
        # Have to ping all oracles to check if they are alive
        for oracle in oracles:
            url = oracle.url
            parsed_url = urlparse(url)

            result = ping(parsed_url.hostname, parsed_url.port)

            # If we can ping this oracle, add to data
            if result is True:
                reachable_oracles = {
                    "name": oracle.name,
                    "url": oracle.url}
                oracle_list.append(reachable_oracles)
        response['oracles'] = oracle_list

        return data_response(response)


class RegistereOracle(APIView):
    # Register a new oracle

    def post(self, request):
        response = {}

        # May use latter
        request.META["REMOTE_ADDR"]
        # TODO: may have to check remote ip?

        form = RegisterOracleForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["url"]
            name = form.cleaned_data["name"]
            # check if exist
            if Oracle.objects.filter(url=url).exists():
                response = {"message": "This url already exists."}
                return error_response(httplib.BAD_REQUEST, "This url already exists", ERROR_CODE['repeat_register_error'])
            oracle = Oracle.objects.create(name=name, url=url)
            oracle.save()

            response = {"message": "Add oracle successfully"}
            return data_response(response)
        else:
            response['errors'] = form.errors
            return error_response(httplib.BAD_REQUEST, form.errors, ERROR_CODE['form_invalid_error'])

