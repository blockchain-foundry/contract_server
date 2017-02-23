#!/usr/bin/python
# encoding: utf-8

import base58
import re
import requests
import time

from pprint import pprint
from requests_toolbelt import MultipartEncoder
from threading import Thread

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
    try:
        r = requests.get(url, params=payload)

        if 400 <= r.status_code < 500:
            return "Bad request, raw response body: {0}".format(r.text)
        elif r.status_code >= 500:
            return "Server error, raw response body: {0}".format(r.text)
        elif not r.status_code // 100 == 2:
            return "Error: Unexpected response {}".format(r)
        return r
    except ConnectionError as e:
        return "Error: {}".format(e)
    except requests.exceptions.RequestException as e:
        return "Ensure that the backend is working properly"


#  POST
def post(url, data={}, headers={}, json={}):
    try:
        r = requests.post(url, data=data, headers=headers, json=json)

        if 400 <= r.status_code < 500:
            return "Bad request, raw response body: {0}".format(r.text)
        elif r.status_code >= 500:
            return "Server error, raw response body: {0}".format(r.text)
        elif not r.status_code // 100 == 2:
            return "Error: Unexpected response {}".format(r)
        return r
    except ConnectionError as e:
        return "Error: {}".format(e)
    except requests.exceptions.RequestException as e:
        return "Ensure that the backend is working properly"


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
    regex = re.compile(pattern, re.MULTILINE|re.DOTALL)
    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return "" # so we will return empty to remove the comment
        else: # otherwise, we will return the 1st group
            return match.group(1) # captured quoted-string
    return regex.sub(_replacer, string)


def wallet_address_to_evm(address):
    """Convert gcoin address to EVM address
    """
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address


def prepareRawContract(source_code, owner_address, min_successes, oracle_list, oraclize_data):
    """Prepare raw contract transaction
    """
    url = contract_url + 'contracts/'

    data = {
        "source_code": source_code,
        "address": owner_address,
        "m": str(min_successes),
        "oracles": str(oracle_list),
        "data": str(oraclize_data),
    }

    data = MultipartEncoder(data)
    return post(url, data=data, headers={'Content-Type': data.content_type}).json()

def prepareRawSubContract(multisig_addr, source_code, owner_address, deploy_address, oraclize_data):
    """Prepare raw contract transaction
    """
    url = contract_url + 'subcontracts/'+ multisig_addr + '/'

    data = {
        "source_code": source_code,
        "from_address": owner_address,
        "deploy_address": deploy_address,
        "data": str(oraclize_data),
    }

    data = MultipartEncoder(data)
    #print(post(url, data=data, headers={'Content-Type': data.content_type}))
    return post(url, data=data, headers={'Content-Type': data.content_type}).json()

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
    return post(url, data).json()


def is_contract_deployed(oracle_list, multisig_address, min_successes, deployed_list):
    time.sleep(18)
    threads = []
    for oracle in oracle_list:
        t = Thread(target=get_deployed_status_from_oracle,
                   args=(oracle['url'], multisig_address, deployed_list))
        t.setDaemon(True)
        t.start()

    while(True):
        time.sleep(3)
        if len(deployed_list) >= min_successes:
            return True
    return False


def get_deployed_status_from_oracle(url, multisig_address, deployed_list):
    while(True):
        time.sleep(2)
        r = get(url + '/getcontract/' + multisig_address)
        if r.status_code == requests.codes.ok:
            deployed_list.append(url)
            break


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

def callSubContractFunction(contract_addr, data):
    """Call contract function
    """
    data = MultipartEncoder(data)

    url = contract_url + 'subcontracts/' + contract_addr + '/function'
    return post(url, data=data, headers={'Content-Type': data.content_type}).json()

def callContractFunction(contract_addr, data):
    """Call contract function
    """
    data = MultipartEncoder(data)

    url = contract_url + 'contracts/' + contract_addr + '/'
    return post(url, data=data, headers={'Content-Type': data.content_type}).json()


def getOracleList():
    """Get oracle list registered from contract server
    """
    url = contract_url + 'oracles/'
    return get(url).json()
