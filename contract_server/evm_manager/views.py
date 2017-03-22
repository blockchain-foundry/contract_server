from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from oracles.models import Contract
import requests
try:
    import http.client as httplib
except ImportError:
    import httplib


def error_response(**kwargs):
    response, error, data = {}, [], {}
    for k, v in kwargs.items():
        data[k] = v
    error.append(data)
    response['error'] = error
    return response


def std_response(**kwargs):
    response, data = {}, {}
    for k, v in kwargs.items():
        data[k] = v
    response['data'] = data
    return response


class CheckUpdate(APIView):
    http_method_name = ['get']

    def get(self, request, multisig_address, tx_hash):
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
            m, oracles = contract.least_sign_number, contract.oracles.all()
            counter = 0
            for oracle in oracles:
                try:
                    url = oracle.url + '/states/checkupdate/' + multisig_address + '/' + tx_hash
                    r = requests.get(url, timeout=3)
                    if r.json().get('data').get('completed') is True:
                        counter += 1
                except Exception as e:
                    pass
            response = std_response(completed=counter, total=len(oracles), min_completed_needed=m)
            return JsonResponse(response, status=httplib.OK)
        except ObjectDoesNotExist as e:
            response = error_response(code=httplib.BAD_REQUEST, message='contract not found on server')
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        except Exception as e:
            response = error_response(code=httplib.INTERNAL_SERVER_ERROR, message='server error')
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)
