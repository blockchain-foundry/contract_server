from binascii import hexlify

import base58
from gcoin import *

def wallet_address_to_evm(address):


    address = base58.b58decode(address)
    address = hexlify(address)
    address = '0x' + hash160(address)
    return address
