from django.http import JsonResponse
from rest_framework.views import APIView
from gcoinbackend import core as gcoincore
from .deploy_contract_utils import get_multisig_address
from .utils import get_tx
from .models import StateInfo
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
            completed = self._check_update(multisig_address, tx_hash)
            response = std_response(completed=completed)
            return JsonResponse(response, status=httplib.OK)
        except Exception as e:
            response = std_response(completed=False)
            return JsonResponse(response, status=httplib.OK)

    def _check_update(self, multisig_address, tx_hash):
        no_data = ''
        try:
            state = StateInfo.objects.get(multisig_address=multisig_address)
            latest_tx_time = state.latest_tx_time
            latest_tx_hash = state.latest_tx_hash

            if latest_tx_hash == tx_hash:
                return True
            if latest_tx_hash == no_data:
                return False

            if multisig_address != get_multisig_address(tx_hash):
                return False

            tx = get_tx(tx_hash)
            _time = tx['time']
            if int(_time) > int(latest_tx_time):
                return False
            elif int(_time) < int(latest_tx_time):
                return True

            txs = gcoincore.get_txs_by_address(multisig_address, starting_after=latest_tx_hash).get('txs')
            for i, tx in enumerate(txs):
                if tx.get('hash') == tx_hash:
                    return True
                if int(tx.get('time')) != int(latest_tx_time):
                    return False
            return False

        except Exception as e:
            raise e
