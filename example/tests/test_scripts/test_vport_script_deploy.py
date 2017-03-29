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


def create_multisig_address():
    print('[START] create_multisig_address')
    """
    Create MultisigAddress
    """
    multisig_address = action.apply_create_multisig_address(
        sender_address=owner_address, min_successes=1)
    print('[END] create_multisig_address')

    return multisig_address


def deploy_registry_contract(multisig_address):
    """
    Deploy vPortRegistry Contract
    """
    print('[START] deploy_registry_contract')
    contract_file = 'tests/test_scripts/test_contracts/UportRegistry_v3.sol'
    source_code = api_helper.loadContract(contract_file)
    contract_name = 'UportRegistry'
    function_inputs = str([
        {
            "name": "_previousPublishedVersion",
            "type": "address",
            "value": "0000000000000000000000000000000000000001"
        }])
    contract_address, tx_hash = action.apply_deploy_contract(
        multisig_address=multisig_address,
        source_code=source_code, contract_name=contract_name,
        function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)
    print('[END] deploy_registry_contract')
    return contract_address


def deploy_proxy_contract(multisig_address, contract_name):
    """
    Deploy vPortProxy Contract
    """
    print('[START] deploy_proxy_contract: {}'.format(contract_name))
    contract_file = 'tests/test_scripts/test_contracts/UportProxy.sol'
    source_code = api_helper.loadContract(contract_file)
    contract_name = contract_name
    function_inputs = str([])
    contract_address, tx_hash = action.apply_deploy_contract(
        multisig_address=multisig_address,
        source_code=source_code, contract_name=contract_name,
        function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)
    print('[END] deploy_proxy_contract: {}'.format(contract_name))
    return contract_address


if __name__ == '__main__':
    multisig_address = create_multisig_address()
    registry_address = deploy_registry_contract(multisig_address)

    controller_address = deploy_proxy_contract(multisig_address, "RecoverableController")
    proxy_address = deploy_proxy_contract(multisig_address, "Proxy")
    recovery_address = deploy_proxy_contract(multisig_address, "RecoveryQuorum")
    identity_factory_address = deploy_proxy_contract(multisig_address, "IdentityFactory")

    print("----------")
    print("    multisig_address = '{}'".format(multisig_address))
    print("    registry_address = '{}'".format(registry_address))
    print("    controller_address = '{}'".format(controller_address))
    print("    proxy_address = '{}'".format(proxy_address))
    print("    recovery_address = '{}'".format(recovery_address))
    print("    identity_factory_address = '{}'".format(identity_factory_address))
