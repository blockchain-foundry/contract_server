try:
    import http.client as httplib
except ImportError:
    import httplib
from django.http import JsonResponse
from rest_framework.views import APIView

from evm_manager.deploy_contract_utils import deploy_contracts, get_multisig_addr
from .cashout import clear_evm_accouts
from .decorators import handle_uncaught_exception


class NewTxNotified(APIView):

    @handle_uncaught_exception
    def get(self, request, tx_id):
        response = {}
        print('ok, received notify with tx_id ' + tx_id)

        completed = deploy_contracts(tx_id)
        if completed is False:
            response['status'] = "State-Update failed: tx_id = " + tx_id
            return JsonResponse(response, status=httplib.OK)

        multisig_address = get_multisig_addr(tx_id)
        response = clear_evm_accouts(multisig_address)
        response['status'] = 'State-Update completed: tx_id = ' + tx_id

        return JsonResponse(response, status=httplib.OK)
