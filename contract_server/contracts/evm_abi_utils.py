import json
import sha3  # keccak_256
import binascii
from eth_abi.abi import *

def get_abi_list(interface):
    if not interface:
        return [], []

    # The outermost quote must be ', otherwise json.loads will fail
    interface = json.loads(interface.replace("'", '"'))
    function_list = []
    event_list = []
    for i in interface:
        if i['type'] == 'function':
            function_list.append({
                'name': i['name'],
                'inputs': i['inputs']
            })
        elif i['type'] == 'event':
            event_list.append({
                'name': i['name'],
                'inputs': i['inputs']
            })
    return function_list, event_list

def get_event_by_name(interface, event_name):
    '''
    interface is string of a list of dictionary containing id, name, type, inputs and outputs
    '''
    if not interface:
        return {}

    interface = json.loads(interface.replace("'", '"'))
    for i in interface:
        name = i.get('name')
        if name == event_name and i['type'] == 'event':
            return i
    return {}

def get_constructor_function(interface):
    if not interface:
        return {}

    interface = json.loads(interface.replace("'", '"'))
    for i in interface:
        if  i['type'] == 'constructor':
            return i
    return {}

def get_function_by_name(interface, function_name):
    '''
    interface is string of a list of dictionary containing id, name, type, inputs and outputs
    '''
    if not interface:
        return {}

    interface = json.loads(interface.replace("'", '"'))
    for i in interface:
        name = i.get('name')
        if name == function_name and i['type'] == 'function':
            return i, i['constant']
    return {}

def wrap_decoded_data(item):
    """
    Wrap eth_abi decoded data for JSON format output
    """
    if  item['type'] == 'bytes':
        item['value'] = binascii.b2a_hex(item['value']).decode()
    elif 'byte' in item['type']:
        # bytes2, bytes32....
        item['value'] = item['value'].decode('utf-8')
    elif item['type'] == 'string':
        item['value'] = item['value'].decode("utf-8")

    return item

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

        item = wrap_decoded_data(item)

        count += 1
        function_outputs.append(item)

    return function_outputs

def make_evm_constructor_code(function, args):
    if not function:
        return ""
    types = [_process_type(i['type']) for i in function['inputs']]
    bytes_evm_args = encode_abi(types, args)
    evm_args = ''.join(format(x, '02x') for x in bytes_evm_args)
    return evm_args

def make_evm_input_code(function, args):
    types = [_process_type(i['type']) for i in function['inputs']]
    func = function['name'] + '(' + ','.join(types) + ')'
    func = func.encode()
    k = sha3.keccak_256()
    k.update(func)
    evm_func = k.hexdigest()[:8]

    # evm_args = bytes_evm_args.hex() in python 3.5
    args = [_process_arg(arg, typ) for arg, typ in zip(args, types)]
    bytes_evm_args = encode_abi(types, args)
    evm_args = ''.join(format(x, '02x') for x in bytes_evm_args)
    return evm_func + evm_args

def _process_type(typ):
    if(len(typ) == 3 and typ[:3] == "int"):
        return "int256"
    if(len(typ) == 4 and typ[:4] == "uint"):
        return "uint256"
    if(len(typ) > 4 and typ[:4] == "int["):
        return "int256[" + typ[4:]
    if(len(typ) > 5 and typ[:5] == "uint["):
        return "uint256[" + typ[5:]
    return typ

def _process_arg(arg, typ):
    if (arg[:2] == "0x" and typ[:4] == "byte"):
        return bytes.fromhex(arg[2:])

