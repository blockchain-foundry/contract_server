#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from binascii import unhexlify
import json
import os
import sys
from threading import Thread
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contract_server.settings")

import requests

import gcoinrpc
from gcoin import *
from oracles.models import Contract, Oracle


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

def get_multisig_addr_and_bytecode(tx):

    multisig_addr = None
    bytecode = None
    for vout in tx.vout:
        if (vout['scriptPubKey']['type'] == 'scripthash' and
                vout['color'] == CONTRACT_FEE_COLOR and
                vout['value'] == CONTRACT_FEE_AMOUNT):
            multisig_addr = vout['scriptPubKey']['addresses'][0]
        if vout['scriptPubKey']['type'] == 'nulldata':
            # 'OP_RETURN 3636......'
            bytecode = unhexlify(vout['scriptPubKey']['asm'][10:])
            bytecode = bytecode.decode('utf-8')
    if multisig_addr is None or bytecode is None:
        raise ValueError(
                "Contract tx %s not valid." % tx.txid
        )
    return multisig_addr, bytecode

def get_contracts_info(tx_hash_list):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """

    contract_tx_info_list = []
    for tx_hash in tx_hash_list:
        tx = get_tx_info(tx_hash)
        if tx.type == 'CONTRACT':
            multisig_addr, bytecode = get_multisig_addr_and_bytecode(tx)
            oracles = get_related_oracles(multisig_addr)
            contract_tx_info_list.append(
                    {
                        'multisig_addr': multisig_addr,
                        'bytecode': bytecode,
                        'oracles': oracles
                    }
            )
    return contract_tx_info_list

def get_related_oracles(multisig_addr):

    DELIMETER = ','
    contract = Contract.objects.get(multisig_address=multisig_addr)
    oracles = contract.oracles.split(DELIMETER)
    # contract.oracles should be in the form of
    # 'http://localhost:8000,http://localhost:8080,...'
    try:
        # this deal with the case like 'http:localhost:8080,'
        oracles.remove('')
    except:
        pass
    return oracles

def oracle_deploy(multisig_addr, bytecode, host):

    url = host + '/deploy/'
    data = {
            'multisig_addr': multisig_addr,
            'compiled_code': bytecode
    }
    r = requests.post(url, data=json.dumps(data))

def deploy_contracts(contract_txs):

    threads = []
    for contract in contract_txs:
        multisig_addr = contract['multisig_addr']
        bytecode = contract['bytecode']
        oracles = contract['oracles']
        for oracle in oracles:
            t = Thread(
                    target=oracle_deploy,
                    args=(multisig_addr, bytecode, oracle)
            )
            t.start()
            threads.append(t)
    for t in threads:
        t.join()

def deploy_block_contracts(block_hash):

    tx_hash_list = get_tx_hash_list_from_block(block_hash)
    contracts_info = get_contracts_info(tx_hash_list)
    deploy_contracts(contracts_info)

def main():

    block_hash = sys.argv[1]
    deploy_block_contracts(block_hash)

if __name__ == "__main__":

    main()
