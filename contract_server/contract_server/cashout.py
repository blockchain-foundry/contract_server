import json
import decimal
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from gcoinapi.client import GcoinAPIClient
from gcoinbackend import core as gcoincore
from oracles.models import Oracle, Contract
from evm_manager.utils import get_evm_balance
from gcoin import apply_multisignatures, deserialize

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
        if payouts == []:
            return {'payouts': payouts}
        raw_tx = gcoincore.prepare_general_raw_tx(payouts)
        '''
        before cashout.
        '''
        addresses.append(multisig_address)
        balances = [gcoincore.get_address_balance(addr) for addr in addresses]
        signed_tx = sign(raw_tx, multisig_address)
        tx_id = send_cashout_tx(signed_tx, multisig_address)
        '''
        after cashout.
        '''
        balances1 = [gcoincore.get_address_balance(addr) for addr in addresses]
     
        return {"addresses": addresses, "evm_accounts_of_addresses": accounts, "payouts": payouts, "before_balance": balances, "after_balance": balances1}


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
    if output_is_zero(contract_balance, surplus):
        return payouts
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
 

def output_is_zero(balance, surplus):
    fee_color, fee_amount = process_key_value_type(TX_FEE_COLOR, TX_FEE)
    for key, value in balance.items():
        key, value = process_key_value_type(key, value)
        if surplus[key] != value and key != fee_color:
            return False
        elif surplus[key] != value - fee_amount and key == fee_color:
            return False
    return True


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

def send_cashout_tx(signed_tx, multisig_address):
    try:
        contract = Contract.objects.get(multisig_address=multisig_address)
    except Contract.DoesNotExist as e:
        raise e
    oracles = contract.oracles.all()
    urls = [ora.url for ora in oracles]
    tx_id = gcoincore.send_cashout_tx(signed_tx, urls)
    return tx_id

def sign(raw_tx, multisig_address):
    try:
        contract = Contract.objects.get(multisig_address=multisig_address)
    except Contract.DoesNotExist as e:
        raise e
    oracles = contract.oracles.all()

    # multisig sign
    # calculate counts of inputs
    tx_inputs = deserialize(raw_tx)['ins']
    for i in range(len(tx_inputs)):
        sigs = []
        for oracle in oracles:
            data = {
                'tx': raw_tx,
                'multisig_address': multisig_address,
                'user_address': multisig_address,
                'color_id': "1",
                'amount': "0",
                'script': contract.multisig_script,
                'input_index': i,
            }
            r = requests.post(oracle.url + '/signnew/', data=data)
            signature = r.json().get('signature')
            print('Get ' + oracle.url + '\'s signature.')
            if signature is not None:
                # sign success, update raw_tx
                sigs.append(signature)
        raw_tx = apply_multisignatures(raw_tx, i, contract.multisig_script,
                                       sigs[:contract.least_sign_number])
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
