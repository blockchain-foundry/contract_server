try:
    import http.client as httplib
except ImportError:
    import httplib
from django.http import JsonResponse
from rest_framework.views import APIView

from evm_manager.deploy_contract_utils import deploy_contracts, get_multisig_addr
from .cashout import clear_evm_accouts
from .decorators import handle_uncaught_exception
from .forms import NotifyForm
from events import state_log_utils


class NewTxNotified(APIView):
    @handle_uncaught_exception
    def get(self, request, tx_hash):
        """ Receive Transaction Notification From OSS

        Args:
            tx_hash: the latest tx_hash of multisig_address
            subscription_id: subscription_id of OSS
            notification_id: notification_id of subscription_id

        Returns:
            status: State-Update is failed or completed
        """
        response = {}
        print('Received notify with tx_hash ' + tx_hash)

        completed = deploy_contracts(tx_hash)
        if completed is False:
            response['status'] = 'State-Update failed: tx_hash = ' + tx_hash
            return JsonResponse(response, status=httplib.OK)

        multisig_address = get_multisig_addr(tx_hash)
        response = clear_evm_accouts(multisig_address)
        response['status'] = 'State-Update completed: tx_hash = ' + tx_hash
        return JsonResponse(response, status=httplib.OK)


class AddressNotified(APIView):
    def post(self, request, multisig_address):
        """ Receive Address Notification From OSS

        Args:
            multisig_address: multisig_address for contracts
            tx_hash: the latest tx_hash of multisig_address
            subscription_id: subscription_id of OSS
            notification_id: notification_id of subscription_id

        Returns:
            status: State-Update is failed or completed
        """

        form = NotifyForm(request.POST)
        tx_hash = ""

        if form.is_valid():
            tx_hash = form.cleaned_data['tx_hash']
        else:
            response = {"error": form.errors}
            return JsonResponse(response, status=httplib.NOT_ACCEPTABLE)

        response = {}
        print('Received notify with tx_hash ' + tx_hash)
        completed = deploy_contracts(tx_hash)
        if completed is False:
            response['status'] = 'State-Update failed: tx_hash = ' + tx_hash
            return JsonResponse(response, status=httplib.OK)
        else:
            try:
                state_log_utils.check_watch(tx_hash, multisig_address)
            except Exception as e:
                print(e)

        response = clear_evm_accouts(multisig_address)
        response['status'] = 'State-Update completed: tx_hash = ' + tx_hash
        return JsonResponse(response, status=httplib.OK)
