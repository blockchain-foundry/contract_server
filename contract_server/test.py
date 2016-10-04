#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
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

def get_contract_txs(tx_hash_list):
    """
        May be slow when one block contains seas of transactions.
        Using thread doesn't help due to the fact that rpc getrawtransaction
        locks cs_main, which blocks other operations requiring cs_main lock.
    """

    contract_tx_list = []
    for tx_hash in tx_hash_list:
        tx = get_tx_info(tx_hash)
        if tx.type == 'CONTRACT':
            contract_tx_list.append(tx)
    return contract_tx_list

def get_multisig_addr_from_contract_tx(tx):

    for vout in tx.vout:
        if (vout['color'] == CONTRACT_FEE_COLOR and
                vout['value'] == CONTRACT_FEE_AMOUNT and
                vout['scriptPubKey']['type'] == 'scripthash'):
            return vout['scriptPubKey']['addresses'][0]
    raise ValueError(
            "Multisig address doesn't show up in contract tx %s" % tx.txid
    )

def get_related_oracles(multisig_addr_list):
    '''
        @return: list of Contract objects
    '''

    return Contract.objects.filter(multisig_address__in=multisig_addr_list)

def notify_oracle(host, multisig_addr):

    '''
    url = host + '/notify'
    data = {
            'multisig_addr': multisig_addr
    }
    r = requests.post(url, data=json.dumps(data))
    return r.json()['interface']
    '''
    print(host, ': ', multisig_addr)
    return 'interface for fake'

def main():

    block_hash = sys.argv[1]
    tx_hash_list = get_tx_hash_list_from_block(block_hash)
    contract_txs = get_contract_txs(tx_hash_list)
    multisig_addr_list = [
            get_multisig_addr_from_contract_tx(tx) for tx in contract_txs
    ]
    print(get_related_oracles(multisig_addr_list))
    '''
    for i in Oracle.objects.all():
        print(i.url)
    '''

if __name__ == "__main__":

    main()
