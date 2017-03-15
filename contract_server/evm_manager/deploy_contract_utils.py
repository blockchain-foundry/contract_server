#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from binascii import unhexlify
from subprocess import check_call
import json
import os
import time
from threading import Lock
from gcoinbackend import core as gcoincore
from .utils import wallet_address_to_evm
from .models import StateInfo
import logging
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_server.settings")

CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000
LOCK_POOL_SIZE = 64
LOCKS = [Lock() for i in range(LOCK_POOL_SIZE)]
logger = logging.getLogger(__name__)


def get_lock(filename):
    index = abs(hash(str(filename))) % LOCK_POOL_SIZE
    return LOCKS[index]


def get_tx_info(tx_hash):
    tx = gcoincore.get_tx(tx_hash)
    return tx


def get_block_info(block_hash):
    block = gcoincore.get_block_by_hash(block_hash)
    return block


def get_latest_blocks():
    blocks = gcoincore.get_latest_blocks()
    return blocks


def get_sender_addr(txid, vout):
    try:
        tx = gcoincore.get_tx(txid)
        return tx['vout'][vout]['scriptPubKey']['addresses'][0]
    except Exception as e:
        print("[ERROR] getting sender address")


def get_address_balance(address, color):
    balance = gcoincore.get_address_balance(address, color)
    return balance


def get_license_info(color):
    info = gcoincore.get_license_info(color)
    return info


def get_multisig_addr(tx_hash):
    try:
        tx = get_tx_info(tx_hash)

        if tx['type'] == 'CONTRACT':
            multisig_addr = None
            for vout in tx['vout']:
                if vout['scriptPubKey']['type'] == 'nulldata':
                    # 'OP_RETURN 3636......'
                    bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
                    data = json.loads(bytecode.decode('utf-8'))
                    multisig_addr = data.get('multisig_addr')
            return multisig_addr
        elif tx['type'] == 'NORMAL':
            sender_address = get_sender_addr(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
            if sender_address[0] == '3':
                return sender_address
            else:
                return None
    except Exception as e:
        return None


def get_unexecuted_txs(multisig_addr, tx_hash, _time):
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_addr)
    latest_tx_time = '0' if state.latest_tx_time == '' else state.latest_tx_time
    latest_tx_hash = state.latest_tx_hash
    if int(_time) < int(latest_tx_time):
        return [], latest_tx_hash
    try:
        txs = gcoincore.get_txs_by_address(multisig_addr, since=latest_tx_time).get('txs')
        tx_found = False
        while tx_found is False:
            txs = gcoincore.get_txs_by_address(multisig_addr, since=latest_tx_time).get('txs')
            for tx in txs:
                if tx.get('hash') == tx_hash:
                    tx_found = True
            time.sleep(1)

        txs = txs[::-1]
        if latest_tx_time == '0':
            return txs, latest_tx_hash
        for i, tx in enumerate(txs):
            if tx.get('hash') == latest_tx_hash:
                return txs[i + 1:], latest_tx_hash
        return [], latest_tx_hash
    except Exception as e:
        raise(e)


def get_contracts_info(tx):
    """
    orginal  get_sender_addr_and_multisig_addr_and_bytecode_and_value(tx):
    return (sender_addr, multisig_addr, bytecode, value)
    value is in json type
    """
    sender_addr = None
    multisig_addr = None
    bytecode = None
    sender_addr = get_sender_addr(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
    value = {}
    is_deploy = True
    blocktime = tx['blocktime']

    for vout in tx['vout']:
        if vout['scriptPubKey']['type'] == 'nulldata':
            # 'OP_RETURN 3636......'
            bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
            data = json.loads(bytecode.decode('utf-8'))
            multisig_addr = data.get('multisig_addr')
            if data.get('to_addr'):
                to_addr = data.get('to_addr')
            else:
                to_addr = multisig_addr
            if data.get('source_code'):
                bytecode = data.get('source_code')
            elif data.get('function_inputs_hash'):
                bytecode = data.get('function_inputs_hash')
                is_deploy = False
            else:
                raise ValueError("Contract OP RETURN is not valid")

    # In order to collect all value send to the multisig, I have to iterate it twice.
    try:
        for vout in tx['vout']:
            if (vout['scriptPubKey']['type'] == 'scripthash' and
                    vout['scriptPubKey']['addresses'][0] == multisig_addr):
                if value.get(vout['color']) is None:
                    value[vout['color']] = int(vout['value'])
                else:
                    value[vout['color']] += int(vout['value'])
                    # for color in value:
                    # value[color] = str(value[color])
    except Exception as e:
        print("ERROR finding address")
    value[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    if multisig_addr is None or bytecode is None or sender_addr is None:
        raise ValueError(
            "Contract tx %s not valid." % tx['txid']
        )
    for v in value:
        value[v] = str(value[v] / 100000000)
    return sender_addr, multisig_addr, to_addr, bytecode, json.dumps(value), is_deploy, blocktime


def deploy_to_evm(sender_addr, multisig_addr, byte_code, value, is_deploy, to_addr, tx_hash, ex_tx_hash):
    '''
    sender_addr : who deploy the contract
    multisig_addr : the address to be deploy the contract
    byte_code : contract code
    value : value in json '{[color1]:[value1], [color2]:[value2]}'
    '''
    is_sub_contract = False
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    if multisig_addr == to_addr:
        multisig_hex = "0x" + wallet_address_to_evm(multisig_addr)
    else:
        multisig_hex = to_addr
        is_sub_contract = True

    sender_hex = "0x" + wallet_address_to_evm(sender_addr)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_addr
    log_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_addr + "_" + tx_hash + "_log"
    print("Contract path: ", contract_path)
    tx = get_tx_info(tx_hash)
    _time = tx['blocktime']
    if is_deploy:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + \
            " --deploy " + " --write " + contract_path + " --code " + \
            byte_code + " --receiver " + multisig_hex + " --time " + str(_time) + \
            " --writelog " + log_path
        if is_sub_contract:
            command += " --read " + contract_path
    else:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + " --write " + \
            contract_path + " --input " + byte_code + " --receiver " + \
            multisig_hex + " --read " + contract_path + " --time " + str(_time) + \
            " --writelog " + log_path
    lock = get_lock(multisig_addr)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_addr)
        if state.latest_tx_hash == ex_tx_hash:
            try:
                check_call(command, shell=True)
                state.latest_tx_hash = tx_hash
                state.latest_tx_time = _time
                state.save()
                completed, status, message = True, 'Success', ''
                return completed, status, message
            except Exception as e:
                completed, status, message = False, 'Failed', 'Unpredicted exception: ' + str(e)
                return completed, status, message
        else:
            completed, status, message = True, 'Ignored', 'Wrong sequential order'
            return completed, status, message


def deploy_contracts(tx_hash):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """
    multisig_addr = get_multisig_addr(tx_hash)

    if multisig_addr is None:
        print("Non-contract tx & Non-cashout tx: " + tx_hash)
        return False

    tx = get_tx_info(tx_hash)
    _time = tx['blocktime']

    try:
        txs, latest_tx_hash = get_unexecuted_txs(multisig_addr, tx_hash, _time)
    except Exception as e:
        print(e)
        return False
    for tx in txs:
        completed = deploy_single_tx(tx['hash'], latest_tx_hash, multisig_addr)
        if completed is False:
            return False
        latest_tx_hash = tx['hash']


def _log(status, typ, tx_hash, message):
    s = '{:7s}: {:9s}{:65s}- {}'
    print(s.format(status, typ, tx_hash, message))


def deploy_single_tx(tx_hash, ex_tx_hash, multisig_addr):
    tx = get_tx_info(tx_hash)
    _time = tx['blocktime']
    if tx['type'] == 'CONTRACT':
        try:
            sender_addr, multisig_addr, to_addr, bytecode, value, is_deploy, blocktime = get_contracts_info(
                tx)
        except Exception as e:
            _log('Failed', 'CONTRACT', tx_hash, 'Decode tx error')
            return False
        try:
            completed, status, message = deploy_to_evm(
                sender_addr, multisig_addr, bytecode, value, is_deploy, to_addr, tx_hash, ex_tx_hash)
            _log(status, tx['type'], tx_hash, message)
            return completed
        except Exception as e:
            _log('Failed', 'CONTRACT', tx_hash, 'Call evm error')
            return False

    elif tx['type'] == 'NORMAL':
        try:
            sender_address = get_sender_addr(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
            if sender_address[0] == '1':
                lock = get_lock(multisig_addr)
                with lock:
                    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_addr)
                    if state.latest_tx_hash == ex_tx_hash:
                        state.latest_tx_hash = tx_hash
                        state.latest_tx_time = _time
                        state.save()
                _log('Success', tx['type'], tx_hash, 'Non-cashout type')
                return True

            elif sender_address == multisig_addr:
                vouts = tx.get('vout')
            else:
                raise Exception('Unsupported tx spec')
        except Exception as e:
            _log('Failed', tx['type'], tx_hash, 'Decode tx error')
            return False
        try:
            completed, status, message = update_state_after_payment(
                vouts, multisig_addr, tx_hash, ex_tx_hash, _time)
            _log(status, tx['type'], tx_hash, message)
            return completed
        except Exception as e:
            _log('Failed', tx['type'], tx_hash, 'Unpredicted exception: ' + str(e))
            return False


def update_state_after_payment(vouts, multisig_addr, tx_hash, ex_tx_hash, _time):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_addr

    lock = get_lock(multisig_addr)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_addr)
        if state.latest_tx_hash == ex_tx_hash:
            with open(contract_path, 'r') as f:
                content = json.load(f)
        else:
            completed, status, message = True, 'Ignored', 'Wrong sequential order'
            return completed, status, message

    for vout in vouts:
        output_address = vout['scriptPubKey']['addresses'][0]
        output_color = vout['color']
        # convert to diqi
        output_value = vout['value'] / 100000000

        if output_address == multisig_addr:
            continue
        output_evm_address = wallet_address_to_evm(output_address)
        account = content['accounts'][output_evm_address]

        if not account:
            completed, status, message = False, 'Failed', 'Double spending'
            return completed, status, message
        amount = account['balance'][str(output_color)]
        if not amount:
            completed, status, message = False, 'Failed', 'Double spending'
            return completed, status, message
        if int(amount) < int(output_value):
            completed, status, message = False, 'Failed', 'Double spending'
            return completed, status, message

        amount = str(int(amount) - int(output_value))
        content['accounts'][output_evm_address]['balance'][str(output_color)] = amount

    lock = get_lock(multisig_addr)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_addr)
        if state.latest_tx_hash == ex_tx_hash:
            with open(contract_path, 'w') as f:
                json.dump(content, f, sort_keys=True, indent=2, separators=(',', ': '))
            state.latest_tx_hash = tx_hash
            state.latest_tx_time = _time
            state.save()
            completed, status, message = True, 'Success', ''
            return completed, status, message
        else:
            completed, status, message = True, 'Ignored', 'Wrong sequential order'
            return completed, status, message
