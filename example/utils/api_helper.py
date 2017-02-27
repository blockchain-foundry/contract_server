#!/usr/bin/python
# encoding: utf-8

import re
import requests
import time
import json
import sys
from binascii import hexlify
import base58
from gcoin import *

from pprint import pprint
from requests_toolbelt import MultipartEncoder
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)


headers = {'Content-type': 'application/json'}

'''
API Call
'''
# GET
def get_helper(url, payload={}):
    json_string = ''
    code = 500
    try:
        r = requests.get(url, params=payload)
        if r.status_code == 200:
            json_string = r.text
        if 400 <= r.status_code < 500:
            message = "Bad request, raw response body: {0}".format(r.text)
            json_string = json.dumps({ 'message': message })
        elif r.status_code >= 500:
            message = "Server error, raw response body: {0}".format(r.text)
            json_string = json.dumps({ 'message': message })
        elif not r.status_code // 100 == 2:
            message = "Error: Unexpected response {}".format(r)
            json_string = json.dumps({ 'message': message })
        code = r.status_code
    except ConnectionError as e:
        message = "Error: {}".format(e)
        json_string = json.dumps({ 'message': message })
        code = 500
    except requests.exceptions.RequestException as e:
        message =  "Ensure that the backend is working properly"
        json_string = json.dumps({ 'message': message })
        code = 500
    finally:
        return { 'data': json.loads(json_string), 'code': code }

#  POST
def post_helper(url, data={}, headers={}, json_input={}):
    """
    Return handled json data
    """
    json_string = ''
    code = 500
    try:
        r = requests.post(url, data=data, headers=headers, json=json_input)
        if r.status_code == 200:
            json_string = r.text
        if 400 <= r.status_code < 500:
            message = "Bad request, raw response body: {0}".format(r.text)
            json_string = json.dumps({ 'message': message })
        elif r.status_code >= 500:
            message = "Server error, raw response body: {0}".format(r.text)
            json_string = json.dumps({ 'message': message })
        elif not r.status_code // 100 == 2:
            message = "Error: Unexpected response {}".format(r)
            json_string = json.dumps({ 'message': message })

        code = r.status_code
    except ConnectionError as e:
        message = "Error: {}".format(e)
        json_string = json.dumps({ 'message': message })
        code = 500
    except requests.exceptions.RequestException as e:
        message =  "Ensure that the backend is working properly"
        json_string = json.dumps({ 'message': message })
        code = 500
    finally:
        return { 'data': json.loads(json_string), 'code': code }

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


def wallet_address_to_evm_address(address):
    """Convert gcoin address to EVM address
    """
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address

def prefixed_wallet_address_to_evm_address(address):
    # add 0x prefix
    address = '0x' + wallet_address_to_evm_address(address)
    return address


def prepareRawContract(source_code, owner_address, min_successes, oracle_list, oraclize_data, function_inputs):
    """Prepare raw contract transaction
    """
    url = CONTRACT_URL + '/contracts/'

    data = {
        "source_code": source_code,
        "address": owner_address,
        "m": str(min_successes),
        "oracles": str(oracle_list),
        "data": str(oraclize_data),
        "function_inputs": function_inputs
    }
    print('data:{}'.format(data))

    data = MultipartEncoder(data)
    response = post_helper(url, data=data, headers={'Content-Type': data.content_type})
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        print(sys.exc_info())
        sys.exit(1)

def prepareRawSubContract(multisig_addr, source_code, owner_address, deploy_address, oraclize_data, function_inputs):
    """Prepare raw contract transaction
    """
    url = CONTRACT_URL + '/subcontracts/'+ multisig_addr + '/'

    data = {
        "source_code": source_code,
        "from_address": owner_address,
        "deploy_address": deploy_address,
        "data": str(oraclize_data),
        "function_inputs": function_inputs
    }

    data = MultipartEncoder(data)
    #print(post(url, data=data, headers={'Content-Type': data.content_type}))
    # return post(url, data=data, headers={'Content-Type': data.content_type}).json()
    response = post_helper(url, data=data, headers={'Content-Type': data.content_type})
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise

def signAndSendTx(raw_tx, from_privkey):
    """User has to sign the contract before sending to the network
    """
    signed_tx = signall(raw_tx, from_privkey)

    url = OSS_URL + '/base/v1/transaction/send'
    data = {
        'raw_tx': signed_tx,
    }
    # r_json = post(url, data).json()
    # return r_json['tx_id']

    response = post_helper(url, data=data)
    if response['code'] == 200:
        return response['data']['tx_id']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise


def subscribeTx(tx_id):
    """Subscribe to a Tx
    """
    url = OSS_URL + '/notification/v1/tx/subscription'
    callback_url = ORACLE_URL + '/notify/' + tx_id
    data = {
        'tx_hash': tx_id,
        'callback_url': callback_url,
        'confirmation_count': 1,
    }
    # return post(url, data).json()
    response = post_helper(url, data=data)
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise


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
        r = get_helper(url + '/getcontract/' + multisig_address)
        if r['code'] == 200:
            deployed_list.append(url)
            break


def getBalance(tx_id):
    """Get balance by Tx
    """
    url = ORACLE_URL + '/balance/' + tx_id + '/' + tx_id
    r =  get_helper(url)
    if r['code'] == 200:
        return r['data']
    else:
        print(r['data'])
        # [TODO] raise?


def get_storage(contract_address):
    """Get storage by contract address
    """
    url = ORACLE_URL + '/storage/' + contract_address
    r =  get_helper(url)
    if r['code'] == 200:
        return r['data']
    else:
        print(r['data'])
        # [TODO] raise?



def getABI(contract_address):
    """Get ABI by contract address
    """
    url = CONTRACT_URL + '/contracts/' + contract_address
    r =  get_helper(url)
    if r['code'] == 200:
        return r['data']
    else:
        print(r['data'])
        # [TODO] raise?



def getCurrentStatus(contract_address):
    # Get balance
    print('Get balance')
    pprint(getBalance(contract_address))
    print()

    # Get storage
    print('Get storage')
    pprint(get_storage(contract_address))
    print()

def get_states(contract_address):
    """Get ABI by contract address
    """
    url = ORACLE_URL + '/states/' + contract_address
    r =  get_helper(url)
    if r['code'] == 200:
        return r['data']
    else:
        print(r['data'])
        # [TODO] raise?

def callSubContractFunction(contract_address, deploy_address, data):
    """Call contract function
    """
    data = MultipartEncoder(data)

    url = CONTRACT_URL + '/subcontracts/' + contract_address + '/' + deploy_address + '/'
    # return post(url, data=data, headers={'Content-Type': data.content_type}).json()
    response = post_helper(url, data=data, headers={'Content-Type': data.content_type})
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise

def callContractFunction(contract_address, data):
    """Call contract function
    """
    data = MultipartEncoder(data)

    url = CONTRACT_URL + '/contracts/' + contract_address + '/'
    # return post(url, data=data, headers={'Content-Type': data.content_type}).json()
    response = post_helper(url, data=data, headers={'Content-Type': data.content_type})
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise


def getOracleList():
    """Get oracle list registered from contract server
    """
    url = CONTRACT_URL + '/oracles/'
    # return get(url).json()
    r =  get_helper(url)
    if r['code'] == 200:
        return r['data']
    else:
        print(r['data'])
        # [TODO] raise?


def watchEvent(data):
    """Watch a certain event of multisig_address
    """

    url = CONTRACT_URL + '/events/watches/'

    response = post_helper(url, data=data)
    if response['code'] == 200:
        return response['data']
    else:
        print('[ResponseCode]:{} [Message]:{}'.format(response['code'], response['data']))
        raise
