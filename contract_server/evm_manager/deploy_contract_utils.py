#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from binascii import hexlify, unhexlify
from subprocess import check_call, PIPE, STDOUT, Popen
import base58
import json
import os
from threading import Lock
from gcoinbackend import core as gcoincore
from .utils import wallet_address_to_evm
from .contract_server_utils import set_contract_address
from .decorators import retry
from .models import StateInfo
import logging
from events import state_log_utils
from gcoin import hash160
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_server.settings")

CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000
LOCK_POOL_SIZE = 64
LOCKS = [Lock() for i in range(LOCK_POOL_SIZE)]
logger = logging.getLogger(__name__)
MAX_RETRY = 10


def get_lock(filename):
    index = abs(hash(str(filename))) % LOCK_POOL_SIZE
    return LOCKS[index]


@retry(MAX_RETRY)
def get_tx(tx_hash):
    tx = gcoincore.get_tx(tx_hash)
    return tx


@retry(MAX_RETRY)
def get_block_info(block_hash):
    block = gcoincore.get_block_by_hash(block_hash)
    return block


@retry(MAX_RETRY)
def get_latest_blocks():
    blocks = gcoincore.get_latest_blocks()
    return blocks


@retry(MAX_RETRY)
def get_sender_address(txid, vout):
    try:
        tx = gcoincore.get_tx(txid)
        return tx['vout'][vout]['scriptPubKey']['addresses'][0]
    except Exception as e:
        print("[ERROR] getting sender address")


@retry(MAX_RETRY)
def get_address_balance(address, color):
    balance = gcoincore.get_address_balance(address, color)
    return balance


@retry(MAX_RETRY)
def get_license_info(color):
    info = gcoincore.get_license_info(color)
    return info


@retry(MAX_RETRY)
def get_txs_by_address(multisig_address, since, included=None):
    txs = gcoincore.get_txs_by_address(multisig_address, since=since).get('txs')
    if included is None:
        return txs
    else:
        for tx in txs:
            if tx.get('hash') == included:
                return txs
        return None


def get_multisig_address(tx_hash):
    tx = get_tx(tx_hash)
    return get_multisig_address_with_tx(tx)


def get_multisig_address_with_tx(tx):
    try:
        if tx['type'] == 'CONTRACT':
            multisig_address = None
            for vout in tx['vout']:
                if vout['scriptPubKey']['type'] == 'nulldata':
                    # 'OP_RETURN 3636......'
                    bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
                    data = json.loads(bytecode.decode('utf-8'))
                    multisig_address = data.get('multisig_address')
            return multisig_address
        elif tx['type'] == 'NORMAL':
            sender_address = get_sender_address(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
            if sender_address[0] == '3':
                return sender_address
            else:
                return None
    except Exception as e:
        logger.debug("Exception:{}".format(str(e)))
        return None


def get_unexecuted_txs(multisig_address, tx_hash, _time):
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
    latest_tx_time = '0' if state.latest_tx_time == '' else state.latest_tx_time
    latest_tx_hash = state.latest_tx_hash
    if int(_time) < int(latest_tx_time):
        return [], latest_tx_hash
    try:
        txs = get_txs_by_address(multisig_address, since=latest_tx_time, included=tx_hash)
        if txs is None:
            raise Exception('txs not found')
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
    return (sender_address, multisig_address, bytecode, value)
    value is in json type
    """
    multisig_address = None
    bytecode = None
    sender_address = get_sender_address(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
    value = {}
    is_deploy = True
    blocktime = tx['blocktime']

    for vout in tx['vout']:
        if vout['scriptPubKey']['type'] == 'nulldata':
            # 'OP_RETURN 3636......'
            bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
            data = json.loads(bytecode.decode('utf-8'))
            multisig_address = data.get('multisig_address')
            if data.get('contract_address'):
                contract_address = data.get('contract_address')
            else:
                contract_address = multisig_address
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
                    vout['scriptPubKey']['addresses'][0] == multisig_address):
                if value.get(vout['color']) is None:
                    value[vout['color']] = int(vout['value'])
                else:
                    value[vout['color']] += int(vout['value'])
                    # for color in value:
                    # value[color] = str(value[color])
    except Exception as e:
        print("ERROR finding address")
    value[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    if multisig_address is None or bytecode is None or sender_address is None:
        raise ValueError(
            "Contract tx %s not valid." % tx['txid']
        )
    for v in value:
        value[v] = str(value[v] / 100000000)
    return sender_address, multisig_address, contract_address, bytecode, json.dumps(value), is_deploy, blocktime


def deploy_to_evm(sender_address, multisig_address, byte_code, value, is_deploy, contract_address, tx_hash, ex_tx_hash):
    '''
    sender_address : who deploy the contract
    multisig_address : the address to be deploy the contract
    byte_code : contract code
    value : value in json '{[color1]:[value1], [color2]:[value2]}'
    '''
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'

    sender_hex = "0x" + wallet_address_to_evm(sender_address)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    log_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address + "_" + tx_hash + "_log"
    print("Contract path: ", contract_path)
    tx = get_tx(tx_hash)
    _time = tx['blocktime']
    if is_deploy:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + \
            " --deploy " + " --write " + contract_path + " --code " + \
            byte_code + " --receiver " + contract_address + " --time " + str(_time) + \
            " --writelog " + log_path + " --read " + contract_path
    else:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + " --write " + \
            contract_path + " --input " + byte_code + " --receiver " + \
            contract_address + " --read " + contract_path + " --time " + str(_time) + \
            " --writelog " + log_path
    lock = get_lock(multisig_address)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
        if state.latest_tx_hash == ex_tx_hash:
            try:
                check_call(command, shell=True)
                if is_deploy:
                    set_contract_address(multisig_address, contract_address, sender_hex, tx)
                inc_nonce(contract_path, wallet_address_to_evm(sender_address))
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
    multisig_address = get_multisig_address(tx_hash)
    if multisig_address is None:
        return False

    tx = get_tx(tx_hash)
    _time = tx['blocktime']

    try:
        txs, latest_tx_hash = get_unexecuted_txs(multisig_address, tx_hash, _time)
    except Exception as e:
        print(e)
        return False

    for tx in txs:
        completed = deploy_single_tx(tx['hash'], latest_tx_hash, multisig_address)
        if completed is False:
            return False
        else:
            state_log_utils.check_watch(tx['hash'], multisig_address)

        latest_tx_hash = tx['hash']


def _log(status, typ, tx_hash, message):
    s = '{:7s}: {:9s}{:65s}- {}'
    logger.debug(s.format(status, typ, tx_hash, message))


def deploy_single_tx(tx_hash, ex_tx_hash, multisig_address):
    tx = get_tx(tx_hash)
    _time = tx['blocktime']
    if tx['type'] == 'CONTRACT':
        try:
            sender_address, multisig_address, to_address, bytecode, value, is_deploy, blocktime = get_contracts_info(
                tx)
        except Exception as e:
            _log('Failed', 'CONTRACT', tx_hash, 'Decode tx error')
            return False
        try:
            completed, status, message = deploy_to_evm(
                sender_address, multisig_address, bytecode, value, is_deploy, to_address, tx_hash, ex_tx_hash)
            _log(status, tx['type'], tx_hash, message)
            return completed
        except Exception as e:
            _log('Failed', 'CONTRACT', tx_hash, 'Call evm error')
            return False

    elif tx['type'] == 'NORMAL':
        try:
            sender_address = get_sender_address(tx['vin'][0]['txid'], tx['vin'][0]['vout'])
            if sender_address[0] == '1':
                lock = get_lock(multisig_address)
                with lock:
                    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
                    if state.latest_tx_hash == ex_tx_hash:
                        state.latest_tx_hash = tx_hash
                        state.latest_tx_time = _time
                        state.save()
                _log('Success', tx['type'], tx_hash, 'Non-cashout type')
                return True

            elif sender_address == multisig_address:
                vouts = tx.get('vout')
            else:
                raise Exception('Unsupported tx spec')
        except Exception as e:
            _log('Failed', tx['type'], tx_hash, 'Decode tx error')
            return False
        try:
            completed, status, message = update_state_after_payment(
                vouts, multisig_address, tx_hash, ex_tx_hash, _time)
            _log(status, tx['type'], tx_hash, message)
            return completed
        except Exception as e:
            _log('Failed', tx['type'], tx_hash, 'Unpredicted exception: ' + str(e))
            return False


def update_state_after_payment(vouts, multisig_address, tx_hash, ex_tx_hash, _time):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address

    lock = get_lock(multisig_address)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
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

        if output_address == multisig_address:
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

    lock = get_lock(multisig_address)
    with lock:
        state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
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


def inc_nonce(contract_path, sender_evm_addr):
    with open(contract_path, 'r') as f:
        content = json.load(f)
        if sender_evm_addr in content['accounts']:
            content['accounts'][sender_evm_addr]['nonce'] += 1

    with open(contract_path, 'w') as f:
        json.dump(content, f, indent=4, separators=(',', ': '))


def make_multisig_address_file(multisig_address):
    try:
        EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
        contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
        if not os.path.exists(contract_path):
            command = EVM_PATH + " --deploy " " --write " + contract_path
            check_call(command, shell=True)
            return True
    except Exception as e:
        logger.debug(e)
        raise(e)


def call_constant_function(sender_addr, multisig_address, byte_code, value, to_addr):
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    if to_addr == multisig_address:
        multisig_hex = base58.b58decode(multisig_address)
        multisig_hex = hexlify(multisig_hex)
        multisig_hex = "0x" + hash160(multisig_hex)
    else:
        multisig_hex = to_addr
    sender_hex = base58.b58decode(sender_addr)
    sender_hex = hexlify(sender_hex)
    sender_hex = "0x" + hash160(sender_hex)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + \
        '/../states/' + multisig_address
    print("Contract path: ", contract_path)

    command = '{EVM_PATH} --sender {sender_hex} --fund {value} --value {value} \
        --write {contract_path} --input {byte_code} --receiver {multisig_hex} --read {contract_path}'.format(
        EVM_PATH=EVM_PATH, sender_hex=sender_hex, value=value, contract_path=contract_path, byte_code=byte_code, multisig_hex=multisig_hex)
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()
    print("stdout: ", stdout)
    print("stderr: ", stderr)

    if p.returncode != 0:
        print(stderr)
        err_msg = "{}. Code: {}".format(stderr, p.returncode)
        raise Exception(err_msg)

    return {'out': stdout.decode().split()[-1]}
