# import utils
from eth_abi.abi import (
    decode_single,
    decode_abi,
    encode_single,
    encode_abi,
)

import binascii
import sha3

def encode_function_data(function_name, types, values):
    func = function_name + '(' + ','.join(types) + ')'
    func = func.encode()
    k = sha3.keccak_256()
    k.update(func)
    signature = k.hexdigest()[:8]

    data = []
    for t, v in zip(types, values):
        if t == 'bytes32' and v.startswith('0x'):
            data.append(bytes.fromhex(v.strip('0x')))
        else:
            data.append(v)

    encode_data = encode_abi(types, data)
    dataHex = signature + binascii.hexlify(encode_data).decode()
    return dataHex


# TEST_CASE
# funcName: set
# funcType: [ 'bytes32', 'address', 'bytes32' ]
# funcParams: [ 'cepave',
#               '0xec37d2a9cacd01ad72cfcdb5a729c833075513e8',
#               '0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78' ]
# data: 0xd79d8e6c6365706176650000000000000000000000000000000000000000000000000000000000000000000000000000ec37d2a9cacd01ad72cfcdb5a729c833075513e8516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78

types = ['bytes32', 'address', 'bytes32']
values = [
    'cepave',
    '0xec37d2a9cacd01ad72cfcdb5a729c833075513e8',
    '0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78'
]
print(encode_function_data('set', types, values))
