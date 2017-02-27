from binascii import hexlify
import base58
from gcoin import hash160
import json
from eth_abi.abi import *

def wallet_address_to_evm_address(address):
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address

def prefixed_wallet_address_to_evm_address(address):
    # add 0x prefix
    address = '0x' + wallet_address_to_evm_address(address)
    return address

def decode_evm_output(interface, function_name, out):
    ''' Decode EVM outputs
    interface is string of a list of dictionary containing id, name, type, inputs and outputs
    '''
    if not interface:
        return {}

    # get output_type_list
    interface = json.loads(interface.replace("'", '"'))
    output_type_list = []
    for i in interface:
        name = i.get('name')
        if name == function_name and i['type'] == 'function':
            # only one return value for now
            for item in i['outputs']:
                output_type_list.append(item['type'])
            break

    # decode
    decoded_data = decode_abi(output_type_list, out)

    # wrap to json args
    function_outputs = []
    count = 0
    for output_type in output_type_list:
        item = {
            'type': output_type,
            'value': decoded_data[count]
        }

        # For JSON string
        if item['type'] == 'bool':
            item['value'] = item['value']
        elif item['type'] == 'address':
            item['value'] = item['value']
        elif item['type'] == 'string':
            item['value'] = item['value'].decode("utf-8").replace("\x00", "")
        elif 'int' not in item['type']:
            item['value'] = item['value'].decode("utf-8")

        count += 1
        function_outputs.append(item)

    return function_outputs
