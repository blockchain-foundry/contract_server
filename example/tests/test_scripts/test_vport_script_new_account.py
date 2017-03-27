"""

Those 3 users should have coins of color_id = 1
user1 and user2 are both owner's account
user3 is delegate's account

Owner can check the delegate's evm address by test_fromProxyToFindDelegates()

Owner can change userkey from user1 to user2 by test_changeUserKeyByYourself()

Delegate can change userkey from user2 to user1 by test_recoveryByDelegate()

"""
import time
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)
from example.utils.encode_function_data import encode_function_data
from example.utils import action
from example.utils import api_helper

user1_address = owner_address
user1_privkey = owner_privkey
user1_evmAddr = api_helper.wallet_address_to_evm_address(owner_address)

user2_address = "15QzWKknjaT3m3R2TgpbieEGZVT4R7VjvN"
user2_privkey = "L2CWz4fw6LieNcnhorx63ZtnryBKJaKysaohcacYW6SybPP4FzBL"
user2_evmAddr = "14f896224568dcf07c3034250d942b1a4114a88b"

user3_address = "158tHLs4G5nzwbkDPz4jnUqm9PfECYJ5Zh"
user3_privkey = "KxxoZP52apTUBDjKjZ8Zpn6jzhjacrbsCezcJRJDhaw3dP3GwPXM"
user3_evmAddr = "5a22ff4d00eb319cb1009a4a3c4e6f6baaad0955"

current_event = ""


def watch_event(multisig_address, contract_address, event_name):
    global current_event
    response_data = action.apply_watch_event(multisig_address, contract_address, event_name)
    current_event = response_data['event']

def call_identity_factory(
        multisig_address, identity_factory_address,
        userKey, delegates, longTimeLock, shortTimeLock):
    """
    Call IdentityFactory.CreateProxyWithControllerAndRecovery(
        address userKey,
        address[] delegates,
        uint longTimeLock,
        uint shortTimeLock)
    """
    print('[START] call_identity_factory CreateProxyWithControllerAndRecovery({}, {}, {}, {})'.format(userKey, delegates, longTimeLock, shortTimeLock))

    event_name = "IdentityCreated"
    t1 = Thread(target=watch_event, args=(multisig_address, identity_factory_address, event_name, ))
    t1.start()

    function_name = "CreateProxyWithControllerAndRecovery"
    function_inputs = str(
        [
            {"name": "userKey", "type": "address", "value": userKey},
            {"name": "delegates", "type": "delegates", "value": delegates},
            {"name": "longTimeLock", "type": "uint", "value": longTimeLock},
            {"name": "shortTimeLock", "type": "uint", "value": shortTimeLock},
        ]
    )
    tx_hash = action.apply_transaction_call_contract(
        multisig_address=multisig_address, contract_address=identity_factory_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    t1.join()
    event = current_event
    for item in event['args']:
        if item['name'] == 'controller':
            controller_address = item['value']
        elif item['name'] == 'proxy':
            proxy_address = item['value']
        elif item['name'] == 'recoveryQuorum':
            recovery_address = item['value']
    print('[END] call_identity_factory CreateProxyWithControllerAndRecovery({}, {}, {}, {})'.format(userKey, delegates, longTimeLock, shortTimeLock))

    return controller_address, proxy_address, recovery_address


if __name__ == '__main__':
    print("[START] Creat vPort account")
    multisig_address = '3AzSoAKnekjmWox74FrzRH5tiWjAo29Jem'
    registry_address = 'ce444cb8ee20e79030e48175331bb8dd2dcb7249'
    controller_address = '823a859e21671074fe844bf44399985e8b8be99f'
    proxy_address = 'bdbc27691db039e665148dedce85b8d1c162ecd7'
    recovery_address = '50cd8a99e2557b30046bfa8160843d9e4ccb3bc8'
    identity_factory_address = '3300f5d521dc76f8a5e99d848bc4ae91a209f7c5'

    userKey = user1_evmAddr
    delegates = [user2_evmAddr]
    longTimeLock = 0
    shortTimeLock = 0

    new_controller_address, new_proxy_address, new_recovery_address = call_identity_factory(
        multisig_address, identity_factory_address,
        userKey, delegates, longTimeLock, shortTimeLock)
    is_success = action.apply_bind_contract(multisig_address, new_controller_address, controller_address)
    if is_success is False:
        raise
    is_success = action.apply_bind_contract(multisig_address, new_proxy_address, proxy_address)
    if is_success is False:
        raise
    is_success = action.apply_bind_contract(multisig_address, new_recovery_address, recovery_address)
    if is_success is False:
        raise
    print('------------ created -----------')
    print("    multisig_address = '{}'".format(multisig_address))
    print("    registry_address = '{}'".format(registry_address))
    print("    controller_address = '{}'".format(new_controller_address))
    print("    proxy_address = '{}'".format(new_proxy_address))
    print("    recovery_address = '{}'".format(new_recovery_address))
    print("    identity_factory_address = '{}'".format(identity_factory_address))

    print("[END] vPort account is created!")
