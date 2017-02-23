#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from binascii import unhexlify, hexlify
from subprocess import PIPE, STDOUT, CalledProcessError, Popen, check_call
import json
import os
import sys
import requests
import base58
from threading import Thread
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_server.settings")

from gcoinbackend import core as gcoincore

from gcoin import *

from app.models import OraclizeContract, ProposalOraclizeLink, Proposal
from app.oraclize import deployOraclizeContract, set_var_oraclize_contract

CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000


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
    except:
        print("[ERROR] getting sender address")

def get_address_balance(address, color):
    balance = gcoincore.get_address_balance(address, color)
    return balance

def get_license_info(color):
    info = gcoincore.get_license_info(color)
    return info

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

    for vout in tx['vout']:
        if vout['scriptPubKey']['type'] == 'nulldata':
            # 'OP_RETURN 3636......'
            bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
            data = json.loads(bytecode.decode('utf-8'))
            # multisig_address is the filename and to_address is the receiver address
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
                if value.get(vout['color']) == None:
                    value[vout['color']] = int(vout['value'])
                else:
                    value[vout['color']] += int(vout['value'])
                    # for color in value:
                    #value[color] = str(value[color])
    except:
        print("ERROR finding address")
    value[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    if multisig_addr is None or bytecode is None or sender_addr is None:
        raise ValueError(
            "Contract tx %s not valid." % tx['txid']
        )
    for v in value:
        value[v] = str(value[v]/100000000)
    return sender_addr, multisig_addr, to_addr, bytecode, json.dumps(value), is_deploy

def get_oraclize_info(link, tx, sender_addr):
    contract = link.oraclize_contract
    blockhash = tx['blockhash']
    block = get_block_info(blockhash)
    if contract.name == 'start_of_block' or contract.name == 'end_of_block':
        return block['height']
    elif contract.name == 'block_confirm_number':
        blocks = get_latest_blocks()
        latest_block_number = blocks[0]['height']
        block_confirmation_count = str(int(latest_block_number) - int(block['height']))
        return block_confirmation_count
    elif contract.name == 'trand_confirm_number':
        return str(tx['confirmations'])
    elif contract.name == 'specifies_balance':
        balance = get_address_balance(link.receiver, link.color)
        return balance[link.color]
    elif contract.name == 'issuance_of_asset_transfer':
        license_info = get_license_info(link.color)
        if license_info['owner'] == link.receiver:
            return '1'
        else:
            return '0'
    else:
        print('Exception OC')

def deploy_to_evm(sender_addr, multisig_addr, byte_code, value, is_deploy, tx_hash, to_addr):
    '''
    sender_addr : who deploy the contract
    multisig_addr : the address to be deploy the contract
    byte_code : contract code
    value : value in json '{[color1]:[value1], [color2]:[value2]}'
    '''
    is_sub_contract = False
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    if multisig_addr == to_addr:
        multisig_hex = base58.b58decode(multisig_addr)
        multisig_hex = hexlify(multisig_hex)
        multisig_hex = "0x" + hash160(multisig_hex)
    else:
        multisig_hex = to_addr
        is_sub_contract = True

    sender_hex = base58.b58decode(sender_addr)
    sender_hex = hexlify(sender_hex)
    sender_hex = "0x" + hash160(sender_hex)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_addr
    print("Contract path: ", contract_path)
    tx = get_tx_info(tx_hash)
    _time = tx['blocktime']

    p = Proposal.objects.get(multisig_addr=multisig_addr)
    links = p.links.all()
    if is_deploy:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + \
            " --deploy " + " --write " + contract_path + " --code " + \
            byte_code + " --receiver " + multisig_hex + " --time " + str(_time)
        if is_sub_contract:
            command += " --read " + contract_path

        check_call(command, shell=True)

        for link in links:
            contract = link.oraclize_contract
            deployOraclizeContract(multisig_addr, contract.address, contract.byte_code)
    else:
        for link in links:
            info = get_oraclize_info(link, tx, sender_addr)
            set_var_oraclize_contract(multisig_addr, link.oraclize_contract.address, info)

        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + " --write " + \
            contract_path + " --input " + byte_code + " --receiver " + \
            multisig_hex + " --read " + contract_path + " --time " + str(_time)
        check_call(command, shell=True)

def deploy_contracts(tx_hash):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """
    tx = get_tx_info(tx_hash)

    if tx['type'] == 'CONTRACT':
        try:
            sender_addr, multisig_addr, to_addr, bytecode, value, is_deploy = get_contracts_info(tx)
        except:
            print("Not fount tx: " + tx_hash)
            return False
        deploy_to_evm(sender_addr, multisig_addr, bytecode, value, is_deploy, tx_hash, to_addr)
