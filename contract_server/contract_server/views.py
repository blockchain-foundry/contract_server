try:
    import http.client as httplib
except ImportError:
    import httplib
import json
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView, status

from gcoinbackend import core as gcoincore
from oracles.models import Oracle, Contract
from evm_manager.deploy_contract_utils import deploy_contracts, get_contracts_info, get_tx_info



class NewTxNotified(APIView):

    def get(self, request, tx_id):
        response = {}
        print('ok, received notify with tx_id ' + tx_id)
        try:
            tx = get_tx_info(tx_id)
            if tx.get('type') != 'CONTRACT':
                response['data'] = 'tx_id ' + tx_id + ' is not CONTRACT type' 
                return JsonResponse(response, status=httplib.OK)
           
            sender_address, multisig_address, bytecode, value, is_deploy = get_contracts_info(tx)
        except Exception as e:
            print (e)
            response['data'] = 'Not found: tx_id =' + tx_id 
            return JsonResponse(response, status=httplib.OK)

        try:
            txs = gcoincore.get_txs_by_address(multisig_address).get('txs')
            for tx in reversed(txs):
                deploy_contracts(tx.get('hash'))
 
        except Exception as e:
            print (e)
            response['data'] = "State-Update failed: tx_id = " + tx_id + " multisig_address = " + multisig_address
            return JsonResponse(response, status=httplib.OK)

        response['data'] = "State-Update completed: tx_id = " + tx_id + " multisig_address = " + multisig_address
        return JsonResponse(response, status=httplib.OK)

