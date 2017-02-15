#!/usr/bin/python
# encoding: utf-8


import time
import re
from utils import (get, post, loadContract, wallet_address_to_evm,
                   prepareRawContract, signAndSendTx, subscribeTx,
                   getBalance, getStorage, getABI, getCurrentStatus,
                   callContractFunction, getOracleList, is_contract_deployed)

from pprint import pprint

from eth_abi.abi import decode_abi, decode_single

contract_file = 'CONTRACT_FILE'
contract_name = 'CONTRACT_NAME'
oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'

owner_address = 'ADDRESS'
owner_privkey = 'PRIVATE_KEY'
owner_pubkey  = 'PUBLIC_KEY'


def decodeStorageExample():
    """Examples for decode storage
    """
    # b87d8ec6e9ae49aa94bf3a041bcdd5d06ca8836e
    input = '000000000000000000000000b87d8ec6e9ae49aa94bf3a041bcdd5d06ca8836e'
    output = decode_single('address', input)
    print('[Type] address: ' + input)
    print('Decode to: ' + output + '\n')

    # gcoin
    input = '67636f696e00000000000000000000000000000000000000000000000000000a'
    output = decode_single('bytes32', input)
    print('[Type] bytes32: ' + input)
    print('Decode to: ' + output.decode('utf-8'))

    # '82a978b3f5962a5b0957d9ee9eef472ee55b42f1'
    # 1
    # b'stupid pink animal\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    # 0
    input = ('0x00000000000000000000000082a978b3f5962a5b0957d9ee9eef472ee55b42f10000000000000'
             '0000000000000000000000000000000000000000000000000017374757069642070696e6b20616e69'
             '6d616c000000000000000000000000000000000000000000000000000000000000000000000000000'
             '00000000000000000')
    output = decode_abi(['address', 'uint32', 'bytes32', 'int32'], input)
    for out in output:
        print(out)


def deployContract():
    # 1. Create a contract
    source_code = loadContract(contract_file)

    print('Get oracle list')
    oracle_list = getOracleList().get('oracles')
    print(oracle_list)

    if not oracle_list:
        raise ValueError('Empty oracle list')

    print('Create a contract')
    min_successes = 1

    # without oraclize condition
    oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'

    r_json_createRawContract = prepareRawContract(source_code, owner_address, min_successes, oracle_list, oraclize_data)
    contract_addr = r_json_createRawContract['multisig_address']
    print('Obtain a contract address: ' + contract_addr)

    # 2. Broadcast the transaction
    raw_tx = r_json_createRawContract['tx']
    print('Create and broadcast a signed tx')
    tx_id = signAndSendTx(raw_tx, owner_privkey)
    print('Unconfirmed Tx id: ' + tx_id)

    # 3. Contract is deployed
    print('Deploy the contract')
    r_json_subscribeTx = subscribeTx(tx_id)

    # Check whether the contract is deployed or not
    deployed_list = []
    if is_contract_deployed(oracle_list, contract_addr, min_successes, deployed_list) == False:
        raise Exception('Deploy timeout exception')

    # 4. Check contract status, but not necessary
    print('Get balance')
    pprint(getBalance(contract_addr))
    print('Get storage')
    pprint(getStorage(contract_addr))
    print('Get ABI')
    pprint(getABI(contract_addr))

    return contract_addr


def testTransactionCall(contract_addr):
    getCurrentStatus(contract_addr)

    # Get ABI
    print('Get ABI')
    pprint(getABI(contract_addr))
    print()

# Before transaction call

    # Test a non-consant function call
    data = {
        'function_name': 'setGreeting',
        'function_inputs': str([{'value': 'gcoin'}]),
        'from_address': owner_address,
        'amount': '0',
        'color': '0',
    }
    r_json_callContractFunction = callContractFunction(contract_addr, data)
    raw_tx = r_json_callContractFunction['raw_tx']

    print('Signed & broadcast Tx call')
    tx_id = signAndSendTx(raw_tx, owner_privkey)
    r_json_subscribeTx = subscribeTx(tx_id)

    print('Waiting for 60 seconds..')
    time.sleep(60)
    print()

    getCurrentStatus(contract_addr)


def testConstantCall(contract_addr):
    getCurrentStatus(contract_addr)

    # Get ABI
    print('Get ABI')
    pprint(getABI(contract_addr))
    print()

    # Test a constant function call
    constant_data = {
        'function_name': 'greet',
        'function_inputs': str([]),
        'from_address': owner_address,
        'amount': '0',
        'color': '0',
    }

    r_json_callContractFunction = callContractFunction(contract_addr, constant_data)
    pprint(r_json_callContractFunction)
    print()

    getCurrentStatus(contract_addr)


if __name__ == '__main__':
    contract_addr = deployContract()
    # contract_addr = '3AytWwkkdre1ByX8zFYyU3yGKdfTqZaVUU'
    testTransactionCall(contract_addr)
    testConstantCall(contract_addr)
    # decodeStorageExample()
