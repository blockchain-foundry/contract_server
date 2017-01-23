#!/usr/bin/python
# encoding: utf-8


import conf
import base58
import time

from gcoin import signall, hash160
from utils import get, post

from binascii import hexlify
from pprint import pprint

from eth_abi.abi import decode_abi, decode_single
from eth_abi.exceptions import (
    DecodingError,
)


# url setting
oss_url = conf.OSS_URL
contract_url = conf.CONTRACT_URL
oracle_url = conf.ORACLE_URL

owner_address = '14UeDhNQWCprVdFWfUoFNQwJ9fvh4kLvvL'
owner_privkey = 'KyNBNdEzvVHyFVYcTAdBmZTd9dMkpXJPT54mPnWfQedTvRDy4B6Y'
owner_pubkey = '02c37ee4139e22fb6b234f5a1e92d964805c82196fcd895f88553503f742e51e86'

headers = {'Content-type': 'application/json'}


def loadContract(filename):
    """Load solidty code and intergrate to one line
    """
    with open(filename, 'r') as f:
        lines = f.readlines()
    return ''.join([l.strip() for l in lines])


def wallet_address_to_evm(address):
    """Convert gcoin address to EVM address
    """
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address


def prepareRawContract(source_code, owner_address):
    """Prepare raw contract transaction
    """
    url = contract_url + 'contracts/'
    data = {
        "source_code": source_code,
        "address": owner_address,
        "m": 1,
        "oracles": [
            {
                "url": "http://45.33.14.79:7788",
                "name": "gcoin-oracle"
            }
        ]
    }
    return post(url, json=data, headers=headers).json()


def signAndSendTx(raw_tx, from_privkey):
    """User has to sign the contract before sending to the network
    """
    signed_tx = signall(raw_tx, from_privkey)

    url = oss_url + 'base/v1/transaction/send'
    data = {
        'raw_tx': signed_tx,
    }
    r_json = post(url, data).json()
    return r_json['tx_id']


def subscribeTx(tx_id):
    """Subscribe to a Tx
    """
    url = oss_url + 'notification/v1/tx/subscription'
    callback_url = oracle_url + 'notify/' + tx_id
    data = {
        'tx_hash': tx_id,
        'callback_url': callback_url,
        'confirmation_count': 1,
    }
    r_json = post(url, data).json()
    return r_json['callback_url']


def getBalance(tx_id):
    """Get balance by Tx
    """
    url = oracle_url + 'balance/' + tx_id + '/' + tx_id
    return get(url).json()


def getStorage(contract_addr):
    """Get storage by contract address
    """
    url = oracle_url + 'storage/' + contract_addr
    return get(url).json()


def getABI(contract_addr):
    """Get ABI by contract address
    """
    url = contract_url + 'contracts/' + contract_addr
    return get(url).json()


def callContractFunction(data):
    """Call contract function
    """
    url = contract_url + 'contracts/' + contract_addr + '/'
    return post(url, json=data, headers=headers).json()


# Not implemented yet
def callConstantFunction(data):
    """Call constant function
    """
    pass


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
    source_code = loadContract('greeter.sol')

    print('Create a contract')
    r_json_createRawContract = prepareRawContract(source_code, owner_address)

    contract_addr = r_json_createRawContract['multisig_address']
    print('Obtain a contract address: ' + contract_addr)

    # 2. Broadcast the transaction
    raw_tx = r_json_createRawContract['tx']
    print('Create and broadcast a signed tx')
    tx_id = signAndSendTx(raw_tx, owner_privkey)
    print('Unconfirmed Tx id: ' + tx_id)

    # 3. Contract is deployed
    print('Deploy the contract')
    callback_url = subscribeTx(tx_id)
    print('Waiting for 80 seconds..')
    time.sleep(80)
    # Make sure Tx is included in the block
    r_json_callback = post(callback_url).json()
    pprint(r_json_callback)

    # 4. Check contract status, but not necessary
    print('Get balance')
    pprint(getBalance(contract_addr))
    print('Get storage')
    pprint(getStorage(contract_addr))
    print('Get ABI')
    getABI(getABI(contract_addr))

    return contract_addr


def testContract(contract_addr):
    # Get balance
    print('Get balance')
    pprint(getBalance(contract_addr))
    print()

    # Get storage
    print('Get storage')
    pprint(getStorage(contract_addr))
    print()

    # Get ABI
    print('Get ABI')
    pprint(getABI(contract_addr))
    print()

    # Test a non-consant function call
    data = {
        'function_name': 'setGreeting',
        'function_inputs': [{'value': 'gcoin'}],
        'from_address': owner_address,
        'amount': '1',
        'color': '1',
    }
    r_json_callContractFunction = callContractFunction(data)
    raw_tx = r_json_callContractFunction['raw_tx']

    print('Signed & broadcast Tx call')
    tx_id = signAndSendTx(raw_tx, owner_privkey)
    callback_url = subscribeTx(tx_id)

    print('Waiting for 60 seconds..')
    time.sleep(60)

    # Make sure Tx is included in the block
    r_json_callback = post(callback_url).json()
    pprint(r_json_callback)

    # Get balance
    print('Get balance')
    pprint(getBalance(contract_addr))
    print()

    # Get storage
    print('Get storage')
    pprint(getStorage(contract_addr))
    print()

    # # Test a constant function call
    # # Not implemented yet
    # constant_data = {
    #     'function_name': 'greet',
    #     'function_inputs': [],
    #     'from_address': owner_address,
    #     'amount': '1',
    #     'color': '1',
    # }
    # pprint(callConstantFunction(constant_data))


if __name__ == '__main__':
    contract_addr = deployContract()
    contract_addr = '3EtJYwhy4m185sMTSMe4E8wBupxvcBp4A3'
    testContract(contract_addr)
    # decodeStorageExample()
