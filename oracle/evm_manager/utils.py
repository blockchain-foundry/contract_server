import os
import json
import base58
from binascii import hexlify
from gcoin import hash160


def wallet_address_to_evm(address):
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address


def get_evm_balance(multisig_address, address):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address

    user_evm_address = wallet_address_to_evm(address)
    try:
        with open(contract_path.format(multisig_address=multisig_address), 'r') as f:
            content = json.load(f)
            account = content['accounts'][user_evm_address]
            amount = account['balance']
            return amount
    except Exception as e:
        print(e)
        return {}
