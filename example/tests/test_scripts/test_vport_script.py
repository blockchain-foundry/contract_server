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
from example.utils.apply import *
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)
from example.utils.encode_function_data import encode_function_data

user1_address = owner_address
user1_privkey = owner_privkey
user1_evmAddr = wallet_address_to_evm_address(owner_address)

user2_address = "15QzWKknjaT3m3R2TgpbieEGZVT4R7VjvN"
user2_privkey = "L2CWz4fw6LieNcnhorx63ZtnryBKJaKysaohcacYW6SybPP4FzBL"
user2_evmAddr = "14f896224568dcf07c3034250d942b1a4114a88b"

user3_address = "158tHLs4G5nzwbkDPz4jnUqm9PfECYJ5Zh"
user3_privkey = "KxxoZP52apTUBDjKjZ8Zpn6jzhjacrbsCezcJRJDhaw3dP3GwPXM"
user3_evmAddr = "5a22ff4d00eb319cb1009a4a3c4e6f6baaad0955"


# multisig_address for all contracts
multisig_address = ""

# Contract Address
proxy_address =             "0000000000000000000000000000000000000157"
controller_address =        "0000000000000000000000000000000000000158"
recoveryQuorum_address =    "0000000000000000000000000000000000000159"
registry_address =          "0000000000000000000000000000000000000176"

contract_file = 'tests/test_scripts/test_contracts/proxy.sol'

def deployContract():
    print('\n===============================================')
    print('[START] deployContract')
    print('===============================================')
    #Deploy IdentityFactory
    global multisig_address
    global controller_address
    global proxy_address

    source_code = loadContract(contract_file)

    contract_name = 'Owned'
    function_inputs = '[]'
    print('===============================================')
    print('>>> Deploy Contract {}'.format(contract_name))
    multisig_address = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs, from_address=user1_address, privkey=user1_privkey)
    multisig_address = multisig_address
    print('>>> MultiSig contract_addr:{}'.format(multisig_address))

    contract_name = 'Proxy'
    function_inputs = '[]'
    print('===============================================')
    print('>>> Deploy Subcontract {}'.format(contract_name))
    apply_deploy_sub_contract(contract_file, contract_name, multisig_address, proxy_address, source_code, function_inputs, user1_address, user1_privkey)

    contract_name = 'RecoverableController'
    function_inputs = str([
        {
            "name": "proxyAddress",
            "type": "address",
            "value": proxy_address
        },
        {
            "name": "_userKey",
            "type": "address",
            "value": user1_evmAddr
        },
        {
            "name": "longTimeLock",
            "type": "uint",
            "value": 0
        },
        {
            "name": "shortTimeLock",
            "type": "uint",
            "value": 0
        }])
    print('===============================================')
    print('>>> Deploy Subcontract {}'.format(contract_name))
    print('>>> proxyAddress:{}'.format(proxy_address))
    print('>>> userkey:{}'.format(user1_evmAddr))
    print('>>> long/short time lock:0')
    apply_deploy_sub_contract(contract_file, contract_name, multisig_address, controller_address, source_code, function_inputs, user1_address, user1_privkey)

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('>>> Function Call transfer(controller address:{}) of proxy contract'.format(controller_address))
    function_name = 'transfer'
    function_inputs = str([
        {
            "name": "_owner",
            "type": "address",
            "value": controller_address
        }])
    apply_transaction_call_sub_contract(multisig_address, proxy_address, function_name, function_inputs, user1_address, user1_privkey)

    print('>>> Wait 30s.....')
    time.sleep(30)

    contract_name = 'RecoveryQuorum'
    function_inputs = str([
        {
            "name": "_controller",
            "type": "address",
            "value": controller_address
        },
        {
            "name": "_delegates",
            "type": "address[]",
            "value": [user3_evmAddr]
        }])
    print('===============================================')
    print('>>> Deploy Subcontract {}'.format(contract_name))
    print('>>> controllerAddress:{}'.format(controller_address))
    print('>>> delegateAddress:{}'.format([user3_evmAddr]))
    apply_deploy_sub_contract(contract_file, contract_name, multisig_address, recoveryQuorum_address, source_code, function_inputs, user1_address, user1_privkey)

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('>>> Function Call changeRecoveryFromRecovery(recovery address:{}) of controller contract'.format(recoveryQuorum_address))
    function_name = 'changeRecoveryFromRecovery'
    function_inputs = str([
        {
            "name": "_owner",
            "type": "address",
            "value": recoveryQuorum_address
        }])
    apply_transaction_call_sub_contract(multisig_address, controller_address, function_name, function_inputs, user1_address, user1_privkey)

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('[END] deployContract')
    return multisig_address

def test_fromProxyToFindDelegates(multisig_address):

    # change the address/privkey to user you want to test
    address = user1_address
    delegateAddr = user3_evmAddr

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('[START] From Proxy To Find Delegates')
    print('===============================================')
    print('Check the owner of proxy')
    print('>>> Delegate evm address we set:{}'.format(delegateAddr))
    print('>>> Proxy @:{}'.format(proxy_address))
    owner_address = apply_call_constant_sub_contract(multisig_address, proxy_address, 'getOwner', '[]', address)[0]['value']
    print('>>> Proxy.owner :{}'.format(owner_address))
    print('===============================================')
    print('Check the recovery key')
    print('>>> Controller (Proxy.owner) @:{}'.format(owner_address))
    recovery_key = apply_call_constant_sub_contract(multisig_address, owner_address, 'getRecoveryKey', '[]', address)[0]['value']
    print('>>> Controller.recoverykey :{}'.format(recovery_key))
    print('===============================================')
    print('Check the delegateAddress from RecoveryQuorum')
    print('>>> RecoveryQuorum (Controller.recoverykey) @:{}'.format(recovery_key))
    delegateAddress = apply_call_constant_sub_contract(multisig_address, recovery_key, 'getAddresses', '[]', address)[0]['value']
    print('>>> Recovery.getAddresses() :{}'.format(delegateAddress))

    print('[END] From Proxy To Find Delegates')

def test_changeUserKeyByYourself(multisig_address):
    global controller_address
    # change the address/privkey to what you want to change
    address = user1_address
    privkey = user1_privkey
    to_evmAddr = user2_evmAddr

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('[START] Change User Key By Yourself')
    print('===============================================')
    print('Get your userkey from controller')
    print('>>> Controller @:{}'.format(controller_address))
    userKey = apply_call_constant_sub_contract(multisig_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('===============================================')
    print('Use controller to proposed a new key:{}'.format(to_evmAddr))
    print('>>> Controller.signUserKeyChange')
    function_name = "signUserKeyChange"
    function_inputs = str([
        {
            "name": "_proposedUserKey",
            "type": "address",
            "value": to_evmAddr
        }])
    apply_transaction_call_sub_contract(multisig_address, controller_address, function_name, function_inputs, address, privkey)

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('Get the proposed user key from controller')
    print('>>> Controller.getProposedUserKey')
    function_name = "getProposedUserKey"
    function_inputs = '[]'
    ProposedUserKey = apply_call_constant_sub_contract(multisig_address, controller_address, function_name, function_inputs, address)
    print('>>> Controller.proposedUserKey :{}'.format(ProposedUserKey))

    print('===============================================')
    print('Change the the user key if time lock is over')
    print('>>> Controller.changeUserKey')
    function_name = "changeUserKey"
    function_inputs = '[]'
    apply_transaction_call_sub_contract(multisig_address, controller_address, function_name, function_inputs, address, privkey)
    print('>>> Changing Key from ProposedUserKey')
    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('Check the new user key')
    userKey = apply_call_constant_sub_contract(multisig_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('[END] Change User Key By Yourself')

def test_recoveryByDelegate(multisig_address):

    print('>>> Wait 30s.....')
    time.sleep(30)

    address = user1_address
    new_evmaddr = user1_evmAddr
    delegate_address = user3_address
    delegate_privkey = user3_privkey
    print('===============================================')
    print('[START] Recovery by Delegate')
    print('===============================================')
    print('Get your userkey from controller')
    print('>>> Controller @:{}'.format(controller_address))
    userKey = apply_call_constant_sub_contract(multisig_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('===============================================')
    print('Get the delegateAddress')
    print('>>> RecoveryQuorum @:{}'.format(recoveryQuorum_address))
    delegateAddress = apply_call_constant_sub_contract(multisig_address, recoveryQuorum_address, 'getAddresses', '[]', address)[0]['value']
    print('>>> Recovery.getAddresses() :{}'.format(delegateAddress))
    print('===============================================')
    print('>>> change key from userKey:{} to {}'.format(userKey, new_evmaddr))
    function_inputs = str([
        {
            "name": "proposedUserKey",
            "type": "address",
            "value": new_evmaddr
        }])
    apply_transaction_call_sub_contract(multisig_address, recoveryQuorum_address, 'signUserChange', function_inputs, delegate_address, delegate_privkey)
    print('>>> delegate sign user change')

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('===============================================')
    print('Check the new user key')
    userKey = apply_call_constant_sub_contract(multisig_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))

    print('>>> Wait 30s.....')
    time.sleep(30)

    print('[END] Recovery by Delegate')

"""
Proxy_Forward
"""
def watch_ForwardedEvent(multisig_address, receiver_address, event_name):
    global current_event
    current_event = apply_watch_event(multisig_address, receiver_address, event_name)


def call_forward(destination, value, data):
    global multisig_address
    global controller_address
    global proxy_address

    print('\n>>> call_forward({}, {}, {})'.format(destination, value, data))
    multisig_address = multisig_address

    """
    Watch Proxy's Forwarded event
    """
    receiver_address = proxy_address
    event_name = 'Forwarded'

    t1 = Thread(target=watch_ForwardedEvent, args=(multisig_address, receiver_address, event_name, ))
    t1.start()

    """
    Call Controller's forward function
    """
    receiver_address = controller_address
    print('\n>>> Function Call forward(data:{}) of Controller contract'.format(data))
    function_name = "forward"
    # address destination, uint value, bytes data
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
    apply_transaction_call_sub_contract(multisig_address, receiver_address, function_name, function_inputs, user1_address, user1_privkey)

    t1.join()
    event = current_event
    data = ''
    print('>>> event:{}'.format(event))
    for item in event['args']:
        print('item:{}'.format(item))
        if(item['name'] == 'data'):
            data = item['value']
    print('>>> data:{}'.format(data))

def test_deploy_registry_v3():
    global multisig_address
    global registry_address
    print('\n===============================================')
    print('[Start] test_deploy_registry_v3')
    print('===============================================')
    contract_file = 'tests/test_scripts/test_contracts/UportRegistry_v3.sol'
    source_code = loadContract(contract_file)
    contract_name = 'UportRegistry'
    multisig_address = multisig_address
    receiver_address = registry_address
    function_inputs = str([
        {
            "name": "_previousPublishedVersion",
            "type": "address",
            "value": "0000000000000000000000000000000000000001"
        }])

    print('>>> Deploy Subcontract {}'.format(contract_name))
    print('>>> Source_code: {}'.format(source_code))
    apply_deploy_sub_contract(
        contract_file=contract_file, contract_name=contract_name, multisig_address=multisig_address,
        deploy_address=receiver_address, source_code=source_code, function_inputs=function_inputs, from_address=user1_address, privkey=user1_privkey)

    ## [TODO] check SubContract is deployed
    print('>>> Wait 30s.....')
    time.sleep(30)

    print('\n[End] test_deploy_registry_v3')


def test_forwardToRegistry_v3(registrationIdentifier, subject, value):
    global registry_address
    print('\n===============================================')
    print('[Start] test_forwardToRegistry_v3')
    print('===============================================')

    """
    Call forward
    """
    # set(bytes32 registrationIdentifier, address subject, bytes32 value)
    types = ['bytes32', 'address', 'bytes32']
    values = [
        registrationIdentifier,
        subject,
        value
    ]
    # d79d8e6c516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b780000000000000000000000000000000000000000000000000000000000000157516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78
    data = '0x' + encode_function_data('set', types, values)
    print(">>> forward data:{}".format(data))

    call_forward(destination=registry_address, value=0, data=data)


    print('\n[End] test_forwardToRegistry_v3')

def test_getRegistryAttribute_v3(registrationIdentifier, subject):
    global multisig_address
    global registry_address
    global proxy_address

    print('>>> Wait 60s.....')
    time.sleep(60)

    print('\n===============================================')
    print('[Start] test_getRegistryAttribute_v3')
    print('===============================================')
    multisig_address = multisig_address
    receiver_address = registry_address

    # get(bytes32 registrationIdentifier, address issuer, address subject)
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

    # [{"name": "registrationIdentifier", "value": "516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78", "type": "bytes32"}, {"name": "issuer", "value": "0000000000000000000000000000000000000157", "type": "address"}, {"name": "subject", "value": "0000000000000000000000000000000000000157", "type": "address"}]
    result = apply_call_constant_sub_contract(
        multisig_address=multisig_address, deploy_address=receiver_address,
        function_name=function_name, function_inputs=function_inputs, from_address=user1_address)

    print('>>> result:{}'.format(result))
    print('\n[End] test_getRegistryAttribute_v3')


if __name__ == '__main__':

    global multisig_address

    # Deploy Controller, Proxy and RecoveryQuorum contract
    multisig_address = deployContract()

    # Test Recovery functions
    test_fromProxyToFindDelegates(multisig_address)
    test_changeUserKeyByYourself(multisig_address)
    test_recoveryByDelegate(multisig_address)

    # Deploy Registry contract
    test_deploy_registry_v3()

    # Test Forward functions
    test_forwardToRegistry_v3(registrationIdentifier="0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78", subject="0x" + proxy_address, value="0x55555a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78")
    test_getRegistryAttribute_v3(registrationIdentifier="0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78", subject="0x" + proxy_address)
