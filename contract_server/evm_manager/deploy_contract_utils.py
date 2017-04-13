#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from binascii import hexlify
from subprocess import check_call, PIPE, STDOUT, Popen
import base58
import json
import os
from gcoinbackend import core as gcoincore
from .utils import wallet_address_to_evm, get_tx_info, get_sender_address, get_multisig_address, make_contract_address
from .contract_server_utils import set_contract_address, unset_all_contract_addresses
from .decorators import retry, write_lock, handle_exception
from .models import StateInfo
import logging
from events import state_log_utils
from gcoin import hash160
from .exceptions import TxNotFoundError, DoubleSpendingError, UnsupportedTxTypeError
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_server.settings")

CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000
logger = logging.getLogger(__name__)
MAX_RETRY = 10


@handle_exception
def deploy_contracts(tx_hash):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """

    logger.info('---------- Start  updating ----------')
    logger.info('/notify/' + tx_hash)

    tx = get_tx(tx_hash)
    multisig_address = get_multisig_address(tx)

    if tx['type'] == 'NORMAL' and multisig_address is None:
        raise UnsupportedTxTypeError

    txs, latest_tx_hash = get_unexecuted_txs(multisig_address, tx_hash, tx['time'])

    logger.info('Start : The latest updated tx of ' + multisig_address + ' is ' + (latest_tx_hash or 'None'))
    logger.info(str(len(txs)) + ' non-updated txs are found')

    for i, tx in enumerate(txs):
        logger.info(str(i+1) + '/' + str(len(txs)) + ' updating tx: ' + tx['type'] + ' ' + tx['hash'])
        deploy_single_tx(tx, latest_tx_hash, multisig_address)
        if tx['type'] == 'CONTRACT':
            state_log_utils.check_watch(tx['hash'], multisig_address)
        latest_tx_hash = tx['hash']

    logger.info('Finish: The latest updated tx is ' + (latest_tx_hash or 'None'))
    logger.info('---------- Finish updating ----------')
    return True


def deploy_single_tx(tx, ex_tx_hash, multisig_address):
    tx_info = get_tx_info(tx)
    sender_address = get_sender_address(tx)
    if tx['type'] == 'CONTRACT':
        update_contract_type(tx_info, ex_tx_hash, multisig_address, sender_address)
    elif tx['type'] == 'NORMAL' and sender_address == multisig_address:
        update_cashout_type(tx_info, ex_tx_hash, multisig_address)
    else:
        update_other_type(tx_info, ex_tx_hash, multisig_address)


def update_contract_type(tx_info, ex_tx_hash, multisig_address, sender_address):
    command, contract_address, is_deploy = get_command(tx_info, sender_address)
    write_state_contract_type(tx_info, ex_tx_hash, multisig_address, sender_address, command, contract_address, is_deploy)


def update_cashout_type(tx_info, ex_tx_hash, multisig_address):
    write_state_cashout_type(tx_info, ex_tx_hash, multisig_address)


def update_other_type(tx_info, ex_tx_hash, multisig_address):
    write_state_other_type(tx_info, ex_tx_hash, multisig_address)


@write_lock
def write_state_contract_type(tx_info, ex_tx_hash, multisig_address, sender_address, command, contract_address, is_deploy):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    check_call(command, shell=True)
    sender_evm_address = wallet_address_to_evm(sender_address)
    inc_nonce(contract_path, sender_evm_address)
    if is_deploy:
        set_contract_address(multisig_address, contract_address, sender_evm_address, tx_info)


@write_lock
def write_state_cashout_type(tx_info, ex_tx_hash, multisig_address):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    with open(contract_path, 'r') as f:
        content = json.load(f)
    content = get_remaining_money(content, tx_info, multisig_address)
    with open(contract_path, 'w') as f:
        json.dump(content, f, sort_keys=True, indent=4, separators=(',', ': '))


@write_lock
def write_state_other_type(tx_info, ex_tx_hash, multisig_address):
    logger.info('Ignored: non-contract & non-cashout type ' + tx_info['hash'])


@retry(MAX_RETRY)
def get_tx(tx_hash):
    tx = gcoincore.get_tx(tx_hash)
    if tx is None:
        raise TxNotFoundError
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
    if txs is None:
        raise TxNotFoundError
    if included is None:
        return txs
    else:
        for tx in txs:
            if tx.get('hash') == included:
                return txs
        raise TxNotFoundError


def get_unexecuted_txs(multisig_address, tx_hash, _time):
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
    latest_tx_time = int(state.latest_tx_time or 0)
    latest_tx_hash = state.latest_tx_hash

    if int(_time) < int(latest_tx_time):
        return [], latest_tx_hash
    txs = get_txs_by_address(multisig_address, since=latest_tx_time, included=tx_hash)
    txs = txs[::-1]
    if latest_tx_time == 0:
        return txs, latest_tx_hash
    for i, tx in enumerate(txs):
        if tx.get('hash') == latest_tx_hash:
            return txs[i + 1:], latest_tx_hash


def get_command(tx_info, sender_address):
    _time = tx_info['time']
    tx_hash = tx_info['hash']
    bytecode = tx_info['op_return']['bytecode']
    is_deploy = tx_info['op_return']['is_deploy']
    multisig_address = tx_info['op_return']['multisig_address']
    contract_address = tx_info['op_return']['contract_address']
    amount = get_amount(tx_info, multisig_address)
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    sender_hex = "0x" + wallet_address_to_evm(sender_address)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    log_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address + "_" + tx_hash + "_log"
    command = EVM_PATH + \
        " --sender " + sender_hex + \
        " --fund " + "'" + amount + "'" + \
        " --value " + "'" + amount + "'" + \
        " --write " + contract_path + \
        " --read " + contract_path + \
        " --time " + str(_time) + \
        " --writelog " + log_path
    if is_deploy:
        contract_address = make_contract_address(multisig_address, sender_address)
        command = command + \
            " --receiver " + contract_address + \
            " --code " + bytecode + \
            " --deploy "
    else:
        command = command + \
            " --receiver " + contract_address + \
            " --input " + bytecode
    return command, contract_address, is_deploy


def get_remaining_money(content, tx_info, multisig_address):
    for vout in tx_info['vouts']:
        output_address = vout['address']
        output_color = vout['color']
        # convert to diqi
        output_amount = vout['amount'] / 100000000

        if output_address == multisig_address:
            continue
        output_evm_address = wallet_address_to_evm(output_address)
        account = content['accounts'][output_evm_address]

        if not account:
            raise DoubleSpendingError
        amount = account['balance'][str(output_color)]
        if not amount:
            raise DoubleSpendingError
        if int(amount) < int(output_amount):
            raise DoubleSpendingError

        amount = str(int(amount) - int(output_amount))
        content['accounts'][output_evm_address]['balance'][str(output_color)] = amount
    return content


def get_amount(tx_info, multisig_address):
    amount = {}
    for vout in tx_info['vouts']:
        if(vout['address'] == multisig_address):
            amount[vout['color']] = amount.get(vout['color'], 0) + int(vout['amount'])
    amount[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    for v in amount:
        amount[v] = str(amount[v] / 100000000)
    return json.dumps(amount)


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


def rebuild_state_file(multisig_address):
    make_multisig_address_file(multisig_address)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
    os.remove(contract_path)
    make_multisig_address_file(multisig_address)
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
    state.latest_tx_hash = ''
    state.latest_tx_time = ''
    state.save()
    unset_all_contract_addresses(multisig_address)
