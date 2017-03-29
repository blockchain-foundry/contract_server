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


def call_forward(
        multisig_address,
        controller_address, proxy_address,
        destination, value, data,
        sender_address, privkey):

    print('\n>>> call_forward({}, {}, {})'.format(destination, value, data))
    # """
    # Watch Proxy's Forwarded event
    # """
    # event_name = 'Forwarded'
    # t1 = Thread(target=watch_event, args=(multisig_address, proxy_address, event_name, ))
    # t1.start()

    """
    Call Controller's forward function
    """
    print('\n>>> Function Call forward(data:{}) of Controller contract'.format(data))

    function_name = "forward"
    function_inputs = str([
        {
            "name": "destination",
            "type": "address",
            "value": destination
        },
        {
            "name": "value",
            "type": "uint256",
            "value": value
        },
        {
            "name": "data",
            "type": "bytes",
            "value": data
        }])
    print(">>> function_inputs:{}".format(function_inputs))
    tx_hash = action.apply_transaction_call_contract(
        multisig_address=multisig_address, contract_address=controller_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=sender_address, privkey=privkey)

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    # t1.join()
    # event = current_event
    #
    # for item in event['args']:
    #     print('item: {}'.format(item))
    #     if(item['name'] == 'data'):
    #         data = item['value']
    #         break
    # print('>>> forwarded data: {}'.format(data))


def update_profile(
        multisig_address, registry_address, controller_address,
        registrationIdentifier, subject, value,
        sender_address, privkey):
    """
    Update profile
    """
    print('[START]  forward({}, {}, {})'.format(registrationIdentifier, subject, value))
    types = ['bytes32', 'address', 'bytes32']
    values = [
        registrationIdentifier,
        subject,
        value
    ]

    data = '0x' + encode_function_data('set', types, values)
    print(">>> forward data:{}".format(data))

    call_forward(
        multisig_address=multisig_address,
        controller_address=controller_address, proxy_address=proxy_address,
        destination=registry_address, value=0, data=data,
        sender_address=sender_address, privkey=privkey)


def get_profile(
        multisig_address, registry_address, proxy_address,
        registrationIdentifier, subject):

    function_name = 'get'
    function_inputs = str([
        {
            "name": "registrationIdentifier",
            "type": "bytes32",
            "value": registrationIdentifier
        },
        {
            "name": "issuer",
            "type": "address",
            "value": proxy_address
        },
        {
            "name": "subject",
            "type": "address",
            "value": subject
        }
    ])
    sender_address = owner_address
    result = action.apply_call_constant_contract(
        multisig_address=multisig_address, contract_address=registry_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=sender_address)
    print("result: {}".format(result))


if __name__ == '__main__':
    print("[START] Update vPort profile")
    multisig_address = '3AzSoAKnekjmWox74FrzRH5tiWjAo29Jem'
    registry_address = 'ce444cb8ee20e79030e48175331bb8dd2dcb7249'
    controller_address = '0d27551e6e84097eaa6b1f0ebdbba8d55bf6d128'
    proxy_address = 'b733387634001ddc2d5ec65b8fc010405b08cccc'
    recovery_address = '3f0d4a5641ffcb1f9d04e0e62fd0c4d9b0393dc6'
    identity_factory_address = '3300f5d521dc76f8a5e99d848bc4ae91a209f7c5'

    registrationIdentifier = "0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78"
    subject = proxy_address
    value = "0x55555a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78"

    update_profile(
        multisig_address=multisig_address, registry_address=registry_address, controller_address=controller_address,
        registrationIdentifier=registrationIdentifier, subject=subject, value=value,
        sender_address=owner_address, privkey=owner_privkey)

    get_profile(
        multisig_address=multisig_address, registry_address=registry_address, proxy_address=proxy_address,
        registrationIdentifier=registrationIdentifier, subject=subject)
    print("[END]")
