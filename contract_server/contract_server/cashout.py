import json
import decimal
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from gcoinapi.client import GcoinAPIClient
from gcoinbackend import core as gcoincore
from oracles.models import Oracle, Contract
from evm_manager.utils import get_evm_balance

OSS = GcoinAPIClient(settings.OSS_API_URL)
MAX_DIGITS = 20
SCALE = 8	
TX_FEE_COLOR = 1
TX_FEE = 1
RETRY = 1

def clear_evm_accouts(multisig_address):
    for i in range(RETRY):
        contract_balance = gcoincore.get_address_balance(multisig_address)
        addresses = get_participants(multisig_address)
        accounts = [get_evm_balance(multisig_address, addr) for addr in addresses]
        payouts = get_payouts_from_accounts(multisig_address, contract_balance, accounts, addresses)
        raw_tx = gcoincore.prepare_general_raw_tx(payouts)
        signed_tx = sign(raw_tx, multisig_address)
        tx_id = gcoincore.send_tx(signed_tx)
     
        return {"signed_tx":signed_tx, "address": addresses, "accounts": accounts, "payouts": payouts, "balance": contract_balance}

def get_surplus(contract_balance, accounts):
    surplus = process_dict_type(contract_balance)
    for acc in accounts:
        for key, value in acc.items():
            key, value = process_key_value_type(key, value)
            surplus[key] = surplus.get(key, process_value_type(0)) - value
    fee_color, fee_amount = process_key_value_type(TX_FEE_COLOR, TX_FEE)
    surplus[fee_color] -= fee_amount
    return surplus

def get_payouts_from_accounts(multisig_address, contract_balance, accounts, addresses):
    surplus = get_surplus(contract_balance, accounts)
    payouts = []
    for i, acc in enumerate(accounts):
        payouts.extend(get_payouts_from_single_account(acc, multisig_address, addresses[i]))
    payouts.extend(get_payouts_from_single_account(surplus, multisig_address, multisig_address))
    return payouts

def get_payouts_from_single_account(account, from_address, to_address):
    payouts = []
    for key, value in account.items():
        key, value = process_key_value_type(key, value)
        if (value != process_value_type(0)):
            pay = {
                "from_address" : from_address,
                "to_address" : to_address,
                "color_id" : str(key),
                "amount" : str(round(value, SCALE))
            }
            payouts.append(pay) 
    return payouts
 
def process_value_type(value):
    decimal.getcontext().prec = MAX_DIGITS
    return decimal.Decimal(str(value))

def process_key_value_type(key, value):
    return str(key), process_value_type(value)

def process_dict_type(dic):
    ret = {}
    for key, value in dic.items():
        key, value = process_key_value_type(key, value)
        ret[key] = value
    return ret


def sign(raw_tx, multisig_address):
    contract = Contract.objects.get(multisig_address=multisig_address)
    oracles = contract.oracles.all()
    for oracle in oracles:
        data = {
            'transaction': raw_tx,
            'multisig_address': multisig_address,
            'script': contract.multisig_script
        }
        r = requests.post(oracle.url + '/sign/', data=data)
        print (r.content)
        signature = r.json().get('signature')
        if signature is not None:
            raw_tx = signature
    return raw_tx


def get_participants(multisig_address):
    contract = Contract.objects.get(multisig_address=multisig_address)
    txs = gcoincore.get_txs_by_address(multisig_address).get('txs')
    address = []
    for tx in txs:
        vins = tx.get('vins')
        vouts = tx.get('vouts')
        for data in vins:
            if(data.get('address') != multisig_address and data.get('address')!=''):
                address.append(data.get('address'))
        for data in vouts:
            if(data.get('address') != multisig_address and data.get('address')!=''):
                address.append(data.get('address'))
    return list(set(address))
