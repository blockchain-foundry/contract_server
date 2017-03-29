from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from contracts.models import MultisigAddress
from evm_manager.models import StateInfo
from evm_manager import deploy_contract_utils
from gcoinbackend import core as gcoincore

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
    response['errors'] = error
    return response


def std_response(**kwargs):
    response, data = {}, {}
    for k, v in kwargs.items():
        data[k] = v
    response['data'] = data
    return response


def check_state(multisig_address, tx_hash):
    no_data = ''
    try:
        state = StateInfo.objects.get(multisig_address=multisig_address)
    except Exception as e:
        return False
    latest_tx_time = state.latest_tx_time
    latest_tx_hash = state.latest_tx_hash

    if latest_tx_hash == tx_hash:
        return True
    if latest_tx_hash == no_data:
        return False

    if multisig_address != deploy_contract_utils.get_multisig_addr(tx_hash):
        return False

    try:
        tx = deploy_contract_utils.get_tx_info(tx_hash)
        _time = tx['blocktime']
    except Exception as e:
        print("error: " + str(e))
        return False
    if int(_time) > int(latest_tx_time):
        return False
    elif int(_time) < int(latest_tx_time):
        return True
    try:
        txs = gcoincore.get_txs_by_address(multisig_address, starting_after=latest_tx_hash).get('txs')
    except Exception as e:
        print("error: " + str(e))
        return False

    for i, tx in enumerate(txs):
        if tx.get('hash') == tx_hash:
            return True
        if int(tx.get('time')) != int(latest_tx_time):
            return False
    return False


class CheckUpdate(APIView):
    http_method_name = ['get']

    def get(self, request, multisig_address, tx_hash):
        contract_server_completed = False
        try:
            contract_server_completed = check_state(multisig_address, tx_hash)
        except Exception as e:
            response = error_response(code=httplib.INTERNAL_SERVER_ERROR, message=str(e))
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)

        try:
            multisig_address_object = MultisigAddress.objects.get(address=multisig_address)
            m, oracles = multisig_address_object.least_sign_number, multisig_address_object.oracles.all()
            counter = 0
            for oracle in oracles:
                try:
                    url = oracle.url + '/states/checkupdate/' + multisig_address + '/' + tx_hash
                    r = requests.get(url, timeout=3)
                    if r.json().get('data').get('completed') is True:
                        counter += 1
                except Exception as e:
                    pass
            response = std_response(completed=counter, total=len(oracles), min_completed_needed=m, contract_server_completed=contract_server_completed)
            return JsonResponse(response, status=httplib.OK)
        except ObjectDoesNotExist as e:
            response = error_response(code=httplib.BAD_REQUEST, message='multisig address not found on server')
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        except Exception as e:
            response = error_response(code=httplib.INTERNAL_SERVER_ERROR, message=str(e))
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)
