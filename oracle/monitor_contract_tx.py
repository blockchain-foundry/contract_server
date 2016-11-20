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

import gcoinrpc
from gcoin import *
CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000

def get_tx_hash_list_from_block(block_hash):

    c = gcoinrpc.connect_to_local()
    result = c.getblock(block_hash)
    return result['tx']

def get_tx_info(tx_hash):
    c = gcoinrpc.connect_to_local()
    result = c.getrawtransaction(tx_hash, 1) # verbose
    return result

def get_sender_addr(txid, vout):
    try:
        c = gcoinrpc.connect_to_local()
        tx = c.getrawtransaction(txid)
        return  tx.vout[vout]['scriptPubKey']['addresses'][0]
    except:
        print("[ERROR] getting sender address")

def get_contracts_info(tx):
    """
    orginal  get_sender_addr_and_multisig_addr_and_bytecode_and_value(tx):
    return (sender_addr, multisig_addr, bytecode, value)
    value is in json type
    """
    sender_addr = None
    multisig_addr = None
    bytecode = None
    sender_addr = get_sender_addr(tx.vin[0]['txid'], tx.vin[0]['vout'])
    value = {}
    is_deploy = True 

    for vout in tx.vout:
        if (vout['scriptPubKey']['type'] == 'scripthash' and
            vout['color'] == CONTRACT_FEE_COLOR and
            vout['value'] == CONTRACT_FEE_AMOUNT):
            
            multisig_addr = vout['scriptPubKey']['addresses'][0]
        if vout['scriptPubKey']['type'] == 'nulldata':
            # 'OP_RETURN 3636......'
            bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
            data = json.loads(bytecode.decode('utf-8'))
            if data.get('source_code'):
                bytecode = data.get('source_code')
            elif data.get('function_inputs_hash'):
                bytecode = data.get('function_inputs_hash')
                is_deploy = False
            else:
                raise ValueError("Contract OP RETURN is not valid")
   
    #In order to collect all value send to the multisig, I have to iterate it twice.   
    try:
        for vout in tx.vout:
            if (vout['scriptPubKey']['type'] == 'scripthash' and
                vout['scriptPubKey']['addresses'][0] == multisig_addr):
                if value.get(vout['color']) == None:
                    value[vout['color']] = int(vout['value'])
                    value[vout['color']] += int(vout['value'])
                    # for color in value:
                    #value[color] = str(value[color])
    except:
        print("ERROR finding address")
    if is_deploy:
        value[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    if multisig_addr is None or bytecode is None or sender_addr is None:
        raise ValueError(
                "Contract tx %s not valid." % tx.txid
        )
    for v in value:
        value[v] = str(value[v])
    return sender_addr, multisig_addr, bytecode, json.dumps(value), is_deploy

def deploy_to_evm(sender_addr, multisig_addr, byte_code, value, is_deploy):
    '''
    sender_addr : who deploy the contract
    multisig_addr : the address to be deploy the contract
    byte_code : contract code
    value : value in json '{[color1]:[value1], [color2]:[value2]}'
    '''
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../go-ethereum/build/bin/evm'
    multisig_hex = base58.b58decode(multisig_addr)
    multisig_hex = hexlify(multisig_hex)
    multisig_hex = "0x" + hash160(multisig_hex)
    sender_hex = base58.b58decode(sender_addr)
    sender_hex = hexlify(sender_hex)
    sender_hex = "0x" + hash160(sender_hex)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/' + multisig_addr

    if is_deploy:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'" + " --deploy " + " --write " + contract_path + " --code " + byte_code +  " --receiver " + multisig_hex
    else:
        command = EVM_PATH + " --sender " + sender_hex + " --fund " + "'" + value + "'" + " --value " + "'" + value + "'"  + " --write " + contract_path + " --input " + byte_code +  " --receiver " + multisig_hex + " --read " + contract_path
    check_call(command, shell=True)

def deploy_contracts(tx_hash_list):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """

    contract_tx_info_list = []
    for tx_hash in tx_hash_list:
        tx = get_tx_info(tx_hash)
        try:
            sender_addr, multisig_addr, bytecode, value, is_deploy = get_contracts_info(tx)
        except:
            continue
        deploy_to_evm(sender_addr, multisig_addr, bytecode, value, is_deploy)

def deploy_block_contracts(block_hash):

    tx_hash_list = get_tx_hash_list_from_block(block_hash)
    deploy_contracts(tx_hash_list)

def main():
    block_hash = sys.argv[1]
    deploy_block_contracts(block_hash)

if __name__ == "__main__":

    main()
