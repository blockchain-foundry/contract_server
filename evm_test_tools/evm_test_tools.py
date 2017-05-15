import ast
import base58
import json
import os
import re
import sha3  # keccak_256
import sys

from binascii import unhexlify, hexlify
from eth_abi.abi import *
from gcoin import *
from subprocess import PIPE, STDOUT, CalledProcessError, Popen, check_call

SOLIDITY_PATH = "../solidity/solc/solc"

def _get_function_by_name(interface, function_name):
    '''
    interface is string of a list of dictionary containing id, name, type, inputs and outputs
    '''
    if not interface:
        return {}

    interface = json.loads(interface.replace("'", '"'))
    for i in interface:
        name = i.get('name')
        if name == function_name and i['type'] == 'function':
            return i
    return {}


def _evm_input_code(function, args):
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


def _compile_code_and_interface(source_code):
    print(SOLIDITY_PATH)
    command = [SOLIDITY_PATH, "--abi", "--bin"]
    try:
        p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    except Exception as e:
        print(e)
    r = str(p.communicate(input=bytes(source_code, "utf8"))[0], "utf8")
    r = r.strip()
    if p.returncode != 0:
        raise Compiled_error(str(r))

    str1 = r.split('Binary:')
    str2 = str1[1].split('\n')
    compiled_code_in_hex = str2[1]
    abi = str2[3]
    abi = json.loads(abi)
    interface = []
    ids = 1
    for func in abi:
        try:
            func["id"] = ids
            interface.append(func)
            ids = ids + 1
        except:
            pass
    interface = json.dumps(interface)
    return compiled_code_in_hex, interface


def loadContract(filename):
    """Load solidty code and intergrate to one line
    """
    with open(filename, 'r') as f:
        codes = remove_comments(f.read())
    return ''.join(l.strip() for l in codes.split('\n'))


def remove_comments(string):
    pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
    # first group captures quoted strings (double or single)
    # second group captures comments (//single-line or /* multi-line */)
    regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return ""  # so we will return empty to remove the comment
        else:  # otherwise, we will return the 1st group
            return match.group(1)  # captured quoted-string
    return regex.sub(_replacer, string)


def deploy_to_evm(sender_addr, receiver_addr, byte_code, value, is_deploy, contract_path):
    '''
    sender_addr : who deploy the contract, or who calls the function
    receiver_addr : receiver address
    byte_code : contract code
    value : value in json '{[color1]:[value1], [color2]:[value2]}'
    '''
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../go-ethereum/build/bin/evm'
    receiver_hex = base58.b58decode(receiver_addr)
    receiver_hex = hexlify(receiver_hex)
    receiver_hex = "0x" + hash160(receiver_hex)
    sender_hex = base58.b58decode(sender_addr)
    sender_hex = hexlify(sender_hex)
    sender_hex = "0x" + hash160(sender_hex)

    print("Contract path: ", contract_path)

    print("value: ", value)

    if is_deploy:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + \
            " --deploy " + " --write " + contract_path + " --code " + \
            byte_code + " --receiver " + receiver_hex
    else:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + \
            " --write " + contract_path + " --input " + byte_code + " --receiver " + \
            receiver_hex + " --read " + contract_path
    check_call(command, shell=True)

if __name__ == '__main__':
    is_deploy = False
    state_file = ''
    interface_file = ''
    source_code_file = ''
    function_name = ''
    sender = ''
    receiver = ''
    value = ''
    function_inputs = []

    for i in range(1, len(sys.argv), 2):
        if sys.argv[i] == '--deploy':
            is_deploy = True
            source_code_file = sys.argv[i + 1]
        elif sys.argv[i] == '--function':
            function_name = sys.argv[i + 1]
        elif sys.argv[i] == '--function-input':
            function_inputs = ast.literal_eval(sys.argv[i + 1])
        elif sys.argv[i] == '--contract-name':
            state_file = os.path.dirname(os.path.abspath(__file__)) + '/state/' + sys.argv[i + 1]
            interface_file = os.path.dirname(os.path.abspath(
                __file__)) + "/interface/" + sys.argv[i + 1]
        elif sys.argv[i] == '--sender':
            sender = sys.argv[i + 1]
        elif sys.argv[i] == '--receiver':
            receiver = sys.argv[i + 1]
        elif sys.argv[i] == '--value':
            value = sys.argv[i + 1]
        else:
            raise Exception('invalid flag' + sys.argv[i])

    if state_file == '':
        raise Exception('--contract-name is required.')

    if sender == '':
        raise Exception('--sender is required.')

    if receiver == '':
        raise Exception('--receiver is required.')

    if is_deploy:
        source_code = loadContract(source_code_file)
        compiled_code, interface = _compile_code_and_interface(source_code)
        # print(compiled_code, interface)
        if not os.path.exists(os.path.dirname(interface_file)):
            os.makedirs(os.path.dirname(interface_file))
        if not os.path.exists(os.path.dirname(state_file)):
            os.makedirs(os.path.dirname(state_file))

        deploy_to_evm(sender, receiver, compiled_code, value, is_deploy, state_file)
        with open(interface_file, "w") as f:
            f.write(interface)
            f.close()
    else:
        try:
            with open(interface_file, "r") as f:
                interface = f.read()
        except Exception as e:
            raise e

        function = _get_function_by_name(interface, function_name)
        if not function:
            raise Exception('Function ' + function_name + ' does not exist.')

        input_value = []
        for i in function_inputs:
            input_value.append(i['value'])
        evm_input_code = _evm_input_code(function, input_value)

        deploy_to_evm(sender, receiver, evm_input_code, value, is_deploy, state_file)

    print("")
