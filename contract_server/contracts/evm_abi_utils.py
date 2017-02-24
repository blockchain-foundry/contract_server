import json
import sha3  # keccak_256
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
