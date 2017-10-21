try:
    import http.client as httplib
except ImportError:
    import httplib

import requests
import threading

from rest_framework.views import APIView


from contract_server import ERROR_CODE, error_response, data_response
from contracts.models import MultisigAddress, Contract
from smart_contract_utils.ContractStateFileUpdater import ContractStateFileUpdater
from smart_contract_utils.ContractTxInfo import ContractTxInfo
from smart_contract_utils.models import StateInfo
from smart_contract_utils.utils import wallet_address_to_evm
from .decorators import handle_uncaught_exception, handle_apiversion_apiview
from .forms import NotifyForm

# from .cashout import clear_evm_accounts


def evm_deploy(tx_hash):
    print('Deploy tx_hash ' + tx_hash)

    # parse tx
    contract_tx_info = ContractTxInfo(tx_hash)
    state_multisig_address = contract_tx_info.get_state_multisig_address()
    # update tx into corresponding state file
    state_info, _ = StateInfo.objects.get_or_create(multisig_address=state_multisig_address)
    updater = ContractStateFileUpdater(state_info=state_info)
    txs, latest_tx_hash = state_info.get_unexecuted_txs(tx_hash, contract_tx_info.get_time())
    for i, tx in enumerate(txs):
        completed = updater.update_with_single_tx(tx['hash'], latest_tx_hash)
        latest_tx_hash = tx['hash']

        if completed:
            tmp_tx_info = ContractTxInfo(tx['hash'])
            contract_multisig_address = tmp_tx_info.get_contract_multisig_address()
            contract_multisig_script = tmp_tx_info.get_contract_multisig_script()
            contract_address = tmp_tx_info.get_contract_address()
            m = tmp_tx_info.get_least_signed_number()
            pubkey_list = tmp_tx_info.get_pubkey_list()
            sender_evm_address = wallet_address_to_evm(tmp_tx_info.get_sender_address())

            # if new contract
            if contract_tx_info.is_deploy():
                contract_multisig_address_object, _ = MultisigAddress.objects.get_or_create(address=contract_multisig_address,
                                                                                            script=contract_multisig_script, least_sign_number=m, is_state_multisig=False)

                # Init oracles for new contract multisig address object
                oracles = MultisigAddress.objects.get(address=state_multisig_address).oracles.all()

                for oracle in oracles:
                    print('Save contract multisig address.')
                    contract_multisig_address_object.oracles.add(oracle)
                    # Save multisig/public at oracle server
                    url = oracle.url
                    data = {
                        'pubkey_list': str(pubkey_list),
                        'multisig_address': contract_multisig_address,
                        'is_state_multisig': False
                    }
                    requests.post(url + '/multisigaddress/', data=data)

                try:
                    op_return_hex = tmp_tx_info.get_op_return()['hex']
                    if Contract.objects.filter(state_multisig_address__address=state_multisig_address,
                                               contract_address=contract_address,
                                               contract_multisig_address=contract_multisig_address_object,
                                               tx_hash_init=tx_hash,
                                               is_deployed=True).exists():
                        # if this contract already deployed, do nothing
                        print('Contract: {} is already deployed.'.format(contract_multisig_address))
                    elif Contract.objects.filter(state_multisig_address__address=state_multisig_address,
                                                 sender_evm_address=sender_evm_address,
                                                 hash_op_return=Contract.make_hash_op_return(
                                                     op_return_hex),
                                                 is_deployed=False
                                                 ).exists():
                        # if this contract was created, but not deployed
                        c = Contract.objects.filter(state_multisig_address__address=state_multisig_address,
                                                    sender_evm_address=sender_evm_address,
                                                    hash_op_return=Contract.make_hash_op_return(
                                                        op_return_hex),
                                                    is_deployed=False
                                                    )[0]
                        c.contract_address = contract_address
                        c.contract_multisig_address = contract_multisig_address_object
                        c.tx_hash_init = tx_hash
                        c.is_deployed = True
                        c.save()
                        print('Contract: {} update successfully.'.format(contract_multisig_address))
                    else:
                        # if this contract is not in DB, just deploy it. But cannot make any
                        # function call on it.
                        print('Contract: {} not in DB, just deploy it to state file.'.format(
                            contract_multisig_address))
                        pass

                except Exception as e:
                    print('error: ' + str(e))
                    raise(e)

            print('Deployed Success with tx_hash: {}'.format(tx['hash']))
        else:
            print('Deployed Failed with tx_hash: {}'.format(tx['hash']))

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

        form = NotifyForm(request.data)
        tx_hash = ''

        if form.is_valid():
            tx_hash = form.cleaned_data['tx_hash']
        else:
            return error_response(httplib.NOT_ACCEPTABLE, form.errors, ERROR_CODE['invalid_form_error'])

        response = {"message": 'Received notify with address ' +
                    multisig_address + ', tx_hash ' + tx_hash}
        print('Received notify with address ' + multisig_address + ', tx_hash ' + tx_hash)
        t = threading.Thread(target=evm_deploy, args=[tx_hash, ])
        t.start()
        return data_response(response)
