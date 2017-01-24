#!/usr/bin/python
# encoding: utf-8

import base58

from pprint import pprint

import requests

from binascii import hexlify
from gcoin import signall, hash160

import conf

# url setting
oss_url = conf.OSS_URL
contract_url = conf.CONTRACT_URL
oracle_url = conf.ORACLE_URL

headers = {'Content-type': 'application/json'}


# GET
def get(url, payload={}):
    r = requests.get(url, params=payload)
    if r.status_code == requests.codes.ok:
        return r
    else:
        print(r.raise_for_status())


#  POST
def post(url, data={}, headers={}, json={}):
    r = requests.post(url, data=data, headers=headers, json=json)
    if r.status_code == requests.codes.ok:
        return r
    else:
        print(r.raise_for_status())


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


def prepareRawContract(source_code, owner_address, oracle_list):
    """Prepare raw contract transaction
    """
    url = contract_url + 'contracts/'

    data = {
        "source_code": source_code,
        "address": owner_address,
        "m": 1,
        "oracles": oracle_list,
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


def getCurrentStatus(contract_addr):
    # Get balance
    print('Get balance')
    pprint(getBalance(contract_addr))
    print()

    # Get storage
    print('Get storage')
    pprint(getStorage(contract_addr))
    print()


def callContractFunction(contract_addr, data):
    """Call contract function
    """
    url = contract_url + 'contracts/' + contract_addr + '/'
    return post(url, json=data, headers=headers).json()
