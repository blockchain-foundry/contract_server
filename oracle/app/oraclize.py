import os
import locale

from subprocess import check_call


def deployOraclizeContract(multisig_address, oraclize_address, byte_code):
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    CONTRACT_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    command = EVM_PATH + ' --code ' + byte_code + ' --deploy ' + ' --read ' + \
        CONTRACT_PATH + ' --receiver ' + oraclize_address + ' --write ' + CONTRACT_PATH
    check_call(command, shell=True)


def set_var_oraclize_contract(multisig_address, oraclize_address, variable):
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    CONTRACT_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    variable = locale.atof(variable)
    variable = hex(int(variable))[2:]
    INPUT = '76cafced' + (64 - len(variable)) * '0' + variable
    command = EVM_PATH + ' --read ' + CONTRACT_PATH + ' --input ' + INPUT + \
        ' --receiver ' + oraclize_address + ' --write ' + CONTRACT_PATH
    check_call(command, shell=True)
