import requests

from contracts.models import Contract, MultisigAddress

from .models import StateInfo, ContractInfo
from .utils import wallet_address_to_evm, make_contract_multisig_address, get_public_keys


def set_contract_address(state_multisig_address, contract_address, sender_address, tx_info):
    op_return_hex, tx_hash = _get_op_return_hex_and_hash(tx_info)
    sender_evm_address = wallet_address_to_evm(sender_address)

    contract_multisig_address, contract_multisig_script, m = make_contract_multisig_address(
        tx_info['hash'], contract_address)

    try:
        contract_multisig_address_object = MultisigAddress.objects.get(
            address=contract_multisig_address)
    except MultisigAddress.DoesNotExist:
        # New contract
        contract_multisig_address_object = MultisigAddress.objects.create(address=contract_multisig_address,
                                                                          script=contract_multisig_script, least_sign_number=m, is_state_multisig=False)
        state_info = StateInfo.objects.get(multisig_address=state_multisig_address)
        ContractInfo.objects.create(
            state_info=state_info, multisig_address=contract_multisig_address, contract_address=contract_address)

        # Init oracles for new contract multisig address object
        oracles = MultisigAddress.objects.get(address=state_multisig_address).oracles.all()
        pubkey_list = get_public_keys(tx_info['hash'])

        for oracle in oracles:
            contract_multisig_address_object.oracles.add(oracle)
            # Save multisig/public at oracle server
            url = oracle.url
            data = {
                'pubkey_list': pubkey_list,
                'multisig_address': contract_multisig_address,
                'is_state_multisig': False
            }
            requests.post(url + '/multisigaddress/', data=data)

    try:
        c = Contract.objects.filter(
            state_multisig_address__address=state_multisig_address,
            sender_evm_address=sender_evm_address,
            hash_op_return=Contract.make_hash_op_return(op_return_hex),
            is_deployed=False
        )[0]
    except Exception as e:
        print('error: ' + str(e))
        raise(e)

    try:
        c.contract_address = contract_address
        c.contract_multisig_address = contract_multisig_address_object
        c.tx_hash_init = tx_hash
        c.is_deployed = True
        c.save()
    except Exception as e:
        print(str(e))
        raise e


def _get_op_return_hex_and_hash(tx_info):
    return tx_info['op_return']['hex'], tx_info['hash']


def unset_all_contract_addresses(multisig_address):
    contracts = Contract.objects.filter(
        multisig_address__address=multisig_address,
    )
    for c in contracts:
        c.is_deployed = False
        c.save()
