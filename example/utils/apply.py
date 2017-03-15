#!/usr/bin/python
# encoding: utf-8
import re
import requests
import time
import json
import sys
from gcoin import *

from pprint import pprint
from requests_toolbelt import MultipartEncoder
from threading import Thread
import os
import sys
sys.path.insert(0, os.path.abspath(".."))
from example.conf import (owner_address, owner_privkey, owner_pubkey)
from example.utils.api_helper import *

headers = {'Content-type': 'application/json'}


def apply_deploy_contract(contract_file, contract_name, function_inputs, from_address, privkey):
    print('\n[Apply Deploy Contract] {}:{}({})'.format(contract_file, contract_name, function_inputs))

    # 1. Create a contract
    source_code = loadContract(contract_file)

    print('>>> Get oracle list')
    oracle_list = getOracleList().get('oracles')
    print(oracle_list)

    if not oracle_list:
        raise ValueError('Empty oracle list')

    print('>>> Create a contract')
    min_successes = 1

    # without oraclize condition
    oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'

    r_json_createRawContract = prepareRawContract(source_code, from_address, min_successes, oracle_list, oraclize_data, function_inputs)
    multisig_address = r_json_createRawContract['multisig_address']
    print('>>> raw_tx is created')
    print('>>> Obtain a contract address: ' + multisig_address)

    # 2. Broadcast the transaction
    raw_tx = r_json_createRawContract['tx']
    print('>>> Create and broadcast a signed tx')

    tx_id = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed Tx id: ' + tx_id)

    # 3. Subscribe transaction
    r_json_subscribeTx = subscribeTx(tx_id)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")

    # Check whether the contract is deployed or not
    deployed_list = []
    if is_contract_deployed(oracle_list, multisig_address, min_successes, deployed_list) is False:
        raise Exception('Deploy timeout exception')
    print('>>> Contract {} is deployed @ {}'.format(contract_name, multisig_address))

    return multisig_address


def apply_deploy_sub_contract(contract_file, contract_name, multisig_address, deploy_address, source_code, function_inputs, from_address, privkey):
    print('\n[Apply Deploy SubContract] {}:{}({}) @{}/{}'.format(contract_file, contract_name, function_inputs, multisig_address, deploy_address))
    # 1. Create a contract

    print('>>> Create a contract')
    min_successes = 1

    # without oraclize condition
    oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'
    r_json_createRawContract = prepareRawSubContract(multisig_address, source_code, from_address, deploy_address, oraclize_data, function_inputs)
    print('>>> raw_tx is created')

    # 2. Broadcast the transaction
    raw_tx = r_json_createRawContract['raw_tx']
    print('>>> Create and broadcast a signed tx')
    tx_id = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed Tx id: ' + tx_id)

    # 3. Subscribe transaction
    r_json_subscribeTx = subscribeTx(tx_id)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")
    return


def apply_get_contract_status(multisig_address):
    """ Check contract status, but not necessary
    """
    print('[Check contract status]')
    print('>>> Get balance')
    pprint(getBalance(multisig_address))
    print('>>> Get storage')
    pprint(get_storage(multisig_address))
    print('>>> Get ABI')
    pprint(getABI(multisig_address))
    return


def apply_transaction_call_contract(multisig_address, function_name, function_inputs, from_address, privkey):
    print('\n[Call Contract Transaction Function] {}({}) @{}'.format(function_name, function_inputs, multisig_address))

    data = {
        'function_name': function_name,
        'function_inputs': function_inputs,
        'from_address': from_address,
        'amount': '0',
        'color': '0',
    }
    r_json_apply_transaction_call_contract = callContractFunction(multisig_address, data)
    raw_tx = r_json_apply_transaction_call_contract['raw_tx']
    print('>>> Create and broadcast a signed tx')
    tx_id = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed Tx id: ' + tx_id)

    r_json_subscribeTx = subscribeTx(tx_id)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")
    return


def apply_transaction_call_sub_contract(multisig_address, deploy_address, function_name, function_inputs, from_address, privkey):
    print('\n[Call SubContract Transaction Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, deploy_address))
    data = {
        'from_address': from_address,
        'amount': '0',
        'color': '0',
        'function_name': function_name,
        'function_inputs':function_inputs
    }
    r_json_apply_transaction_call_contract = callSubContractFunction(multisig_address, deploy_address, data)
    raw_tx = r_json_apply_transaction_call_contract['raw_tx']
    print('>>> raw_tx is created')

    print('>>> Create and broadcast a signed tx')
    tx_id = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed Tx id: ' + tx_id)

    r_json_subscribeTx = subscribeTx(tx_id)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))


def apply_call_constant_contract(multisig_address, function_name, function_inputs, from_address):
    """Return constant output (function_outputs)
    """
    print('\n[Call Contract Constant Function] {}({}) @{}'.format(function_name, function_inputs, multisig_address))

    data = {
        'function_name': function_name,
        'function_inputs': function_inputs,
        'from_address': from_address,
        'amount': '0',
        'color': '0',
    }
    r_json_apply_call_constant_contract = callContractFunction(multisig_address, data)
    function_outputs = r_json_apply_call_constant_contract['function_outputs']
    return function_outputs


def apply_call_constant_sub_contract(multisig_address, deploy_address, function_name, function_inputs, from_address):
    """Return constant output (function_outputs)
    """
    print('\n[Call SubContract Constant Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, deploy_address))

    data = {
        'function_name': function_name,
        'function_inputs': function_inputs,
        'from_address': from_address,
        'amount': '0',
        'color': '0',
    }
    r_json_apply_call_constant_contract = callSubContractFunction(multisig_address, deploy_address, data)
    function_outputs = r_json_apply_call_constant_contract['function_outputs']
    return function_outputs


def apply_watch_event(multisig_address, contract_address, event_name):
    """Apply watching event
    """
    print('\n[Watching Event] name:{} @{}/{}'.format(event_name, multisig_address, contract_address))
    data = {
        'multisig_address': multisig_address,
        'event_name': event_name,
        'contract_address': contract_address
    }

    r_json_watchEvent = watchEvent(data)
    print('>>> Event Response: {}'.format(r_json_watchEvent['event']))
    return r_json_watchEvent['event']
