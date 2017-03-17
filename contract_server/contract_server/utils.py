import base58

from binascii import hexlify
from gcoin import hash160

from django.conf import settings

def wallet_address_to_evm_address(address):
     address = base58.b58decode(address)
     address = hexlify(address)
     address = hash160(address)
     return address


def prefixed_wallet_address_to_evm_address(address):
     # add 0x prefix
     address = '0x' + wallet_address_to_evm_address(address)
     return address

def error_response(code, message):
    response = {
        "errors": [
            {
                "code": code,
                "message": message,
            }
        ]
    }
    return response
