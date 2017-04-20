from contracts.models import Contract
from .utils import wallet_address_to_evm


def set_contract_address(multisig_address, contract_address, sender_address, tx_info):
    op_return_hex, tx_hash = _get_op_return_hex_and_hash(tx_info)
    sender_evm_address = wallet_address_to_evm(sender_address)
    c = Contract.objects.filter(
        multisig_address__address=multisig_address,
        sender_evm_address=sender_evm_address,
        hash_op_return=Contract.make_hash_op_return(op_return_hex),
        is_deployed=False
    )[0]
    c.contract_address = contract_address
    c.tx_hash_init = tx_hash
    c.is_deployed = True
    c.save()


def _get_op_return_hex_and_hash(tx_info):
    return tx_info['op_return']['hex'], tx_info['hash']


def unset_all_contract_addresses(multisig_address):
    contracts = Contract.objects.filter(
        multisig_address__address=multisig_address,
    )
    for c in contracts:
        c.is_deployed = False
        c.save()
