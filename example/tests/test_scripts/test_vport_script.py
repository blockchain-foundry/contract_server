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

user1_address = "1PKtjyz2dWouk9YpFivNQCaHhcrpVfJmBY"
user1_privkey = "L4BYsGVeAnDyZweUQaVDrD13jUBURgouFeFF5X3f3rwfeYyX24YD"
user1_evmAddr = "19e87f0752f7cf2048cb74fbd54be37db2a8e333"

user2_address = "15QzWKknjaT3m3R2TgpbieEGZVT4R7VjvN"
user2_privkey = "L2CWz4fw6LieNcnhorx63ZtnryBKJaKysaohcacYW6SybPP4FzBL"
user2_evmAddr = "14f896224568dcf07c3034250d942b1a4114a88b"

user3_address = "158tHLs4G5nzwbkDPz4jnUqm9PfECYJ5Zh"
user3_privkey = "KxxoZP52apTUBDjKjZ8Zpn6jzhjacrbsCezcJRJDhaw3dP3GwPXM"
user3_evmAddr = "5a22ff4d00eb319cb1009a4a3c4e6f6baaad0955"

proxy_address = "0000000000000000000000000000000000000157"
controller_address = "0000000000000000000000000000000000000158"
recoveryQuorum_address = "0000000000000000000000000000000000000159"

contract_file = 'tests/test_scripts/test_contracts/proxy.sol'

def deployContract():
    print('[START] deployContract')
    #Deploy IdentityFactory
    source_code = loadContract(contract_file)
    
    contract_name = 'Owned'
    function_inputs = '[]'
    print('===============================================')
    print('>>> Deploy Contract {}'.format(contract_name))
    contract_address = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs, from_address=user1_address, privkey=user1_privkey)
    print('>>> MultiSig contract_addr:{}'.format(contract_address))

    contract_name = 'Proxy' 
    function_inputs = '[]'
    print('===============================================')
    print('>>> Deploy Subcontract {}'.format(contract_name))
    apply_deploy_sub_contract(contract_file, contract_name, contract_address, proxy_address, source_code, function_inputs, user1_address, user1_privkey)  

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
    apply_deploy_sub_contract(contract_file, contract_name, contract_address, controller_address, source_code, function_inputs, user1_address, user1_privkey)    

    print('>>> Wait 60s.....')
    time.sleep(60)
    print('===============================================')
    print('>>> Function Call transfer(controller address:{}) of proxy contract'.format(controller_address))
    function_name = 'transfer'
    function_inputs = str([
        {
            "name": "_owner",
            "type": "address",
            "value": controller_address
        }])
    apply_transaction_call_sub_contract(contract_address, proxy_address, function_name, function_inputs, user1_address, user1_privkey)
    
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
    apply_deploy_sub_contract(contract_file, contract_name, contract_address, recoveryQuorum_address, source_code, function_inputs, user1_address, user1_privkey)

    print('===============================================')
    print('>>> Function Call changeRecoveryFromRecovery(recovery address:{}) of controller contract'.format(recoveryQuorum_address))
    function_name = 'changeRecoveryFromRecovery'
    function_inputs = str([
        {
            "name": "_owner",
            "type": "address",
            "value": recoveryQuorum_address
        }])
    apply_transaction_call_sub_contract(contract_address, controller_address, function_name, function_inputs, user1_address, user1_privkey)
    
    print('[END] deployContract')
    return contract_address

def test_fromProxyToFindDelegates(contract_address):

    # change the address/privkey to user you want to test
    address = user1_address
    delegateAddr = user3_evmAddr

    print('===============================================')
    print('[START] From Proxy To Find Delegates')
    print('===============================================')
    print('Check the owner of proxy')
    print('>>> Delegate evm address we set:{}'.format(delegateAddr))
    print('>>> Proxy @:{}'.format(proxy_address))
    owner_address = apply_call_constant_sub_contract(contract_address, proxy_address, 'getOwner', '[]', address)[0]['value']
    print('>>> Proxy.owner :{}'.format(owner_address))
    print('===============================================')
    print('Check the recovery key')
    print('>>> Controller (Proxy.owner) @:{}'.format(owner_address))
    recovery_key = apply_call_constant_sub_contract(contract_address, owner_address, 'getRecoveryKey', '[]', address)[0]['value']
    print('>>> Controller.recoverykey :{}'.format(recovery_key))
    print('===============================================')
    print('Check the delegateAddress from RecoveryQuorum')
    print('>>> RecoveryQuorum (Controller.recoverykey) @:{}'.format(recovery_key))
    delegateAddress = apply_call_constant_sub_contract(contract_address, recovery_key, 'getAddresses', '[]', address)[0]['value']
    print('>>> Recovery.getAddresses() :{}'.format(delegateAddress))

    print('[END] From Proxy To Find Delegates')

def test_changeUserKeyByYourself(contract_address):

    # change the address/privkey to what you want to change
    address = user1_address
    privkey = user1_privkey
    to_evmAddr = user2_evmAddr
    print('===============================================')
    print('[START] Change User Key By Yourself')
    print('===============================================')
    print('Get your userkey from controller')
    print('>>> Controller @:{}'.format(controller_address))
    userKey = apply_call_constant_sub_contract(contract_address, controller_address, 'getUserkey', '[]', address)[0]['value']
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
    apply_transaction_call_sub_contract(contract_address, controller_address, function_name, function_inputs, address, privkey)
    
    print('>>> Wait 60s.....')
    time.sleep(60)

    print('===============================================')
    print('Get the proposed user key from controller')
    print('>>> Controller.getProposedUserKey')
    function_name = "getProposedUserKey"
    function_inputs = '[]'
    ProposedUserKey = apply_call_constant_sub_contract(contract_address, controller_address, function_name, function_inputs, address)
    print('>>> Controller.proposedUserKey :{}'.format(ProposedUserKey))

    print('===============================================')
    print('Change the the user key if time lock is over')
    print('>>> Controller.changeUserKey')
    function_name = "changeUserKey"
    function_inputs = '[]'
    apply_transaction_call_sub_contract(contract_address, controller_address, function_name, function_inputs, address, privkey)
    print('>>> Changing Key from ProposedUserKey')
    print('>>> Wait 60s.....')
    time.sleep(60)
    print('===============================================')
    print('Check the new user key')
    userKey = apply_call_constant_sub_contract(contract_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('[END] Change User Key By Yourself')

def test_recoveryByDelegate(contract_address):

    address = user1_address
    new_evmaddr = user1_evmAddr
    delegate_address = user3_address
    delegate_privkey = user3_privkey
    print('===============================================')
    print('[START] Recovery by Delegate')
    print('===============================================')
    print('Get your userkey from controller')
    print('>>> Controller @:{}'.format(controller_address))
    userKey = apply_call_constant_sub_contract(contract_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('===============================================')
    print('Get the delegateAddress')
    print('>>> RecoveryQuorum @:{}'.format(recoveryQuorum_address))
    delegateAddress = apply_call_constant_sub_contract(contract_address, recoveryQuorum_address, 'getAddresses', '[]', address)[0]['value']
    print('>>> Recovery.getAddresses() :{}'.format(delegateAddress))
    print('===============================================')
    print('>>> change key from userKey:{} to {}'.format(userKey, new_evmaddr))
    function_inputs = str([
        {
            "name": "proposedUserKey",
            "type": "address",
            "value": new_evmaddr
        }])
    apply_transaction_call_sub_contract(contract_address, recoveryQuorum_address, 'signUserChange', function_inputs, delegate_address, delegate_privkey)
    print('>>> delegate sign user change')
    print('>>> Wait 60s.....')
    time.sleep(60)
    
    print('===============================================')
    print('Check the new user key')
    userKey = apply_call_constant_sub_contract(contract_address, controller_address, 'getUserkey', '[]', address)[0]['value']
    print('>>> Controller.userKey :{}'.format(userKey))
    print('[END] Recovery by Delegate')

if __name__ == '__main__':
    multisig_address = deployContract()
    #multisig_address = '3M43atCq8UdyyNCRru1HD4pvCrSN15Xfdv'
    test_fromProxyToFindDelegates(multisig_address)
    test_changeUserKeyByYourself(multisig_address)
    test_recoveryByDelegate(multisig_address)