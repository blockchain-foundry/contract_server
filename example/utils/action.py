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
from example.utils import api_helper

headers = {'Content-type': 'application/json'}

#
# def accepts(*types):
#     def decorator(f):
#         def new_f(*args, **kwds):
#             newargs = []
#             for (a, t) in zip(args, types):
#                 newargs.append(t(a))
#             return f(*newargs, **kwds)
#         return new_f
#     return decorator


# def apply_deploy_contract(contract_file, contract_name, function_inputs, sender_address, privkey):
#     print('\n[Apply Deploy Contract] {}:{}({})'.format(contract_file, contract_name, function_inputs))
#
#     # 1. Create a contract
#     source_code = loadContract(contract_file)
#
#     print('>>> Get oracle list')
#     oracle_list = getOracleList().get('oracles')
#     print(oracle_list)
#
#     if not oracle_list:
#         raise ValueError('Empty oracle list')
#
#     print('>>> Create a contract')
#     min_successes = 1
#
#     # without oraclize condition
#     oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'
#
#     r_json_createRawContract = prepareRawContract(source_code, sender_address, min_successes, oracle_list, oraclize_data, function_inputs)
#     multisig_address = r_json_createRawContract['multisig_address']
#     print('>>> raw_tx is created')
#     print('>>> Obtain a contract address: ' + multisig_address)
#
#     # 2. Broadcast the transaction
#     raw_tx = r_json_createRawContract['tx']
#     print('>>> Create and broadcast a signed tx')
#
#     tx_id = signAndSendTx(raw_tx, privkey)
#     print('>>> Unconfirmed Tx id: ' + tx_id)
#
#     # 3. Subscribe transaction
#     r_json_subscribeTx = subscribeTx(tx_id)
#     print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
#     print(">>> Mining transaction....")
#
#     # Check whether the contract is deployed or not
#     deployed_list = []
#     if is_contract_deployed(oracle_list, multisig_address, min_successes, deployed_list) is False:
#         raise Exception('Deploy timeout exception')
#     print('>>> Contract {} is deployed @ {}'.format(contract_name, multisig_address))
#
#     return multisig_address

#
# def apply_deploy_sub_contract(contract_file, contract_name, multisig_address, deploy_address, source_code, function_inputs, sender_address, privkey):
#     print('\n[Apply Deploy SubContract] {}:{}({}) @{}/{}'.format(contract_file, contract_name, function_inputs, multisig_address, deploy_address))
#     # 1. Create a contract
#
#     print('>>> Create a contract')
#     min_successes = 1
#
#     # without oraclize condition
#     oraclize_data = '{"conditions": [], "name": "' + contract_name + '"}'
#     r_json_createRawContract = prepareRawSubContract(multisig_address, source_code, sender_address, deploy_address, oraclize_data, function_inputs)
#     print('>>> raw_tx is created')
#
#     # 2. Broadcast the transaction
#     raw_tx = r_json_createRawContract['raw_tx']
#     print('>>> Create and broadcast a signed tx')
#     tx_id = signAndSendTx(raw_tx, privkey)
#     print('>>> Unconfirmed Tx id: ' + tx_id)
#
#     # 3. Subscribe transaction
#     r_json_subscribeTx = subscribeTx(tx_id)
#     print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
#     print(">>> Mining transaction....")
#     return


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

#
# def apply_transaction_call_contract(multisig_address, function_name, function_inputs, sender_address, privkey):
#     print('\n[Call Contract Transaction Function] {}({}) @{}'.format(function_name, function_inputs, multisig_address))
#
#     data = {
#         'function_name': function_name,
#         'function_inputs': function_inputs,
#         'sender_address': sender_address,
#         'amount': '0',
#         'color': '0',
#     }
#     r_json_apply_transaction_call_contract = callContractFunction(multisig_address, data)
#     raw_tx = r_json_apply_transaction_call_contract['raw_tx']
#     print('>>> Create and broadcast a signed tx')
#     tx_id = signAndSendTx(raw_tx, privkey)
#     print('>>> Unconfirmed Tx id: ' + tx_id)
#
#     r_json_subscribeTx = subscribeTx(tx_id)
#     print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
#     print(">>> Mining transaction....")
#     return
#
#
# def apply_transaction_call_sub_contract(multisig_address, deploy_address, function_name, function_inputs, sender_address, privkey):
#     print('\n[Call SubContract Transaction Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, deploy_address))
#     data = {
#         'sender_address': sender_address,
#         'amount': '0',
#         'color': '0',
#         'function_name': function_name,
#         'function_inputs':function_inputs
#     }
#     r_json_apply_transaction_call_contract = callSubContractFunction(multisig_address, deploy_address, data)
#     raw_tx = r_json_apply_transaction_call_contract['raw_tx']
#     print('>>> raw_tx is created')
#
#     print('>>> Create and broadcast a signed tx')
#     tx_id = signAndSendTx(raw_tx, privkey)
#     print('>>> Unconfirmed Tx id: ' + tx_id)
#
#     r_json_subscribeTx = subscribeTx(tx_id)
#     print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
#
#
# def apply_call_constant_contract(multisig_address, function_name, function_inputs, sender_address):
#     """Return constant output (function_outputs)
#     """
#     print('\n[Call Contract Constant Function] {}({}) @{}'.format(function_name, function_inputs, multisig_address))
#
#     data = {
#         'function_name': function_name,
#         'function_inputs': function_inputs,
#         'sender_address': sender_address,
#         'amount': '0',
#         'color': '0',
#     }
#     r_json_apply_call_constant_contract = callContractFunction(multisig_address, data)
#     function_outputs = r_json_apply_call_constant_contract['function_outputs']
#     return function_outputs

#
# def apply_call_constant_sub_contract(multisig_address, deploy_address, function_name, function_inputs, sender_address):
#     """Return constant output (function_outputs)
#     """
#     print('\n[Call SubContract Constant Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, deploy_address))
#
#     data = {
#         'function_name': function_name,
#         'function_inputs': function_inputs,
#         'sender_address': sender_address,
#         'amount': '0',
#         'color': '0',
#     }
#     r_json_apply_call_constant_contract = callSubContractFunction(multisig_address, deploy_address, data)
#     function_outputs = r_json_apply_call_constant_contract['function_outputs']
#     return function_outputs


# @accepts(str, str, str)
def apply_watch_event(multisig_address, contract_address, event_name, conditions=""):
    """Apply watching event

    Args:
        multisig_address
        contract_address
        event_name

    Returns:
        event
    """
    print('\n[Watching Event] name:{} @ {} / {} ; conditions: {}'.format(event_name, multisig_address, contract_address, conditions))
    data = {
        'multisig_address': multisig_address,
        'event_name': event_name,
        'contract_address': contract_address,
        'conditions': conditions
    }

    response_data = api_helper.watch_event(data)
    return response_data


def apply_create_multisig_address(sender_address, min_successes):
    """Create MultisigAddress

    Args:
        sender_address
        min_successes
        oracles

    Returns:
        multisig_address
    """
    print("api_helper.getOracleList():{}".format(api_helper.getOracleList()))
    oracles = api_helper.getOracleList()["data"].get('oracles')
    print('\n[Create MultisigAddress] sender_address:{}, min_successes:{}, oracles:{}'.format(
        sender_address, min_successes, oracles))
    data = {
        "sender_address": sender_address,
        "m": str(min_successes),
        "oracles": str(oracles)
    }
    response_data = api_helper.create_multisig_address(data)
    print('>>> Response: {}'.format(response_data))
    return response_data['multisig_address']


def apply_deploy_contract(multisig_address, source_code, contract_name, function_inputs, sender_address, privkey):
    print('\n[Apply Deploy Contract] {}({}) @{}'.format(contract_name, function_inputs, multisig_address))
    # 1. Create a contract

    print('>>> Create a contract')
    min_successes = 1
    # without oraclize condition
    data = {
        "source_code": source_code,
        "sender_address": sender_address,
        "function_inputs": function_inputs,
        "contract_name": contract_name
    }
    data_response = api_helper.create_contract(multisig_address, data)
    print('>>> raw_tx is created')

    # 2. Broadcast the transaction
    raw_tx = data_response['raw_tx']
    print('>>> Sign and broadcast raw_tx')
    tx_hash = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed tx_hash: ' + tx_hash)

    # 3. Subscribe transaction oracle
    r_json_subscribeTx = subscribeTx(tx_hash)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")

    # 4. Subscribe transaction for contract_server
    r_json_subscribeTx = subscribeTx(tx_hash, CONTRACT_URL)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")

    return tx_hash


def apply_transaction_call_contract(multisig_address, contract_address, function_name, function_inputs, sender_address, privkey):
    print('\n[Call Contract Transaction Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, contract_address))
    data = {
        'sender_address': sender_address,
        'amount': '0',
        'color': '0',
        'function_name': function_name,
        'function_inputs': function_inputs
    }

    # 1. Call Contract
    data_response = api_helper.call_contract(multisig_address, contract_address, data)
    raw_tx = data_response['raw_tx']
    print('>>> raw_tx is created')
    print('>>> Sign and broadcast raw_tx')

    # 2. Sign
    tx_hash = signAndSendTx(raw_tx, privkey)
    print('>>> Unconfirmed tx_hash: ' + tx_hash)

    # 3. Subscribe transaction oracle
    r_json_subscribeTx = subscribeTx(tx_hash)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))

    # 4. Subscribe transaction for contract_server
    r_json_subscribeTx = subscribeTx(tx_hash, CONTRACT_URL)
    print('>>> Subscribed transaction, subscription_id: {}'.format(r_json_subscribeTx['id']))
    print(">>> Mining transaction....")

    return tx_hash


def apply_call_constant_contract(multisig_address, contract_address, function_name, function_inputs, sender_address):
    """Return constant output (function_outputs)
    """
    print('\n[Call Contract Constant Function] {}({}) @{}/{}'.format(function_name, function_inputs, multisig_address, contract_address))

    data = {
        'function_name': function_name,
        'function_inputs': function_inputs,
        'sender_address': sender_address,
        'amount': '0',
        'color': '0',
    }
    data_response = api_helper.call_contract(multisig_address, contract_address, data)
    function_outputs = data_response['function_outputs']
    return function_outputs


def apply_check_state(multisig_address, tx_hash):
    """Check if state is updated

    Returns:
        is_updated: is state updated
        contract_address: deployed address
    """
    print('\n[Check state] {} @{}'.format(tx_hash, multisig_address))

    timeout_count = 40
    counter = 0
    while(True):
        data_response = api_helper.check_state(multisig_address, tx_hash)
        completed = data_response['completed']
        total = data_response['total']
        min_completed_needed = data_response['min_completed_needed']
        contract_server_completed = data_response['contract_server_completed']
        print(">>> [{}/{}] {} of {} oracle(s) confirmed and contract_server_completed:{} for {}".format(
            completed, min_completed_needed, completed, total, contract_server_completed, tx_hash))
        if min_completed_needed <= completed and contract_server_completed is True:
            if ("contract_address" in data_response):
                contract_address = data_response["contract_address"]
                return True, contract_address
            else:
                return True, ""
        elif counter > timeout_count:
            return False, ""
        else:
            counter += 1
            time.sleep(5)


def apply_bind_contract(multisig_address, new_contract_address, original_contract_address):
    """Bind new_contract_address to original_contract_address's ABI
    """
    print('\n[Bind Contract] {} to {}'.format(new_contract_address, original_contract_address))

    data = {
        'new_contract_address': new_contract_address,
        'original_contract_address': original_contract_address
    }
    response_data = api_helper.bind_contract(multisig_address, data)
    return response_data["is_success"]
