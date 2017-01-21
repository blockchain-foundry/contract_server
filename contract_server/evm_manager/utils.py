import base58
from binascii import hexlify
from gcoin import hash160

def wallet_address_to_evm(address):

    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address
