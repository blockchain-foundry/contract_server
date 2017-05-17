try:
    import http.client as httplib
except ImportError:
    import httplib
from rest_framework.views import APIView

from evm_manager import deploy_contract_utils

from contract_server import ERROR_CODE, error_response, data_response
from .decorators import handle_uncaught_exception, handle_apiversion_apiview
from .forms import NotifyForm

# from .cashout import clear_evm_accounts
import threading


def evm_deploy(tx_hash):
    print('Deploy tx_hash ' + tx_hash)
    completed = deploy_contract_utils.deploy_contracts(tx_hash)
    if completed:
        print('Deployed Success')
    else:
        print('Deployed Failed')
    #
    # Cash out function
    # Modified in future
    # multisig_address = deploy_contract_utils.get_multisig_address(tx_hash)
    # response = clear_evm_accounts(multisig_address)


class NewTxNotified(APIView):
    @handle_uncaught_exception
    def post(self, request, tx_hash):
        """ Receive Transaction Notification From OSS

        Args:
            tx_hash: the latest tx_hash of multisig_address
            subscription_id: subscription_id of OSS
            notification_id: notification_id of subscription_id

        Returns:
            status: State-Update is failed or completed
        """
        response = {"message": 'Received notify with tx_hash ' + tx_hash}
        print('Received notify with tx_hash ' + tx_hash)

        t = threading.Thread(target=evm_deploy, args=[tx_hash, ])
        t.start()
        return data_response(response)


class AddressNotified(APIView):
    @handle_apiversion_apiview
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
            return error_response(httplib.NOT_ACCEPTABLE, form.errors, ERROR_CODE['invalid_form_error'])

        response = {"message": 'Received notify with address ' + multisig_address + ', tx_hash ' + tx_hash}
        print('Received notify with address ' + multisig_address + ', tx_hash ' + tx_hash)
        t = threading.Thread(target=evm_deploy, args=[tx_hash, ])
        t.start()
        return data_response(response)
