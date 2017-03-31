import os
import sys
import time
sys.path.insert(0, os.path.abspath(".."))

from example.conf import (owner_address, owner_privkey, owner_pubkey, OSS_URL, CONTRACT_URL, ORACLE_URL)
from example.utils import action
from example.utils import api_helper


def test_deploy_multi_contracts_script():
    print('[START] test_multi_contracts')
    """
    Create MultisigAddress
    """
    multisig_address = action.apply_create_multisig_address(
        sender_address=owner_address, min_successes=1)

    """
    Deploy First Contract
    """
    contract_file = 'tests/test_scripts/test_contracts/greeter.sol'
    source_code = api_helper.loadContract(contract_file)
    contract_name = 'mortal'
    function_inputs = str([
        {
            "name": "_test_constractor",
            "type": "int256",
            "value": "1234"
        }])
    tx_hash = action.apply_deploy_contract(
        multisig_address=multisig_address,
        source_code=source_code, contract_name=contract_name,
        function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    is_updated, contract_address = action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    """
    Call First Contract (constant)
    """
    # Constanct function call, call without transaction
    # function getStorage() constant returns (address, int256)
    function_name = 'getStorage'
    function_inputs = str([])
    sender_address = owner_address
    function_outputs = action.apply_call_constant_contract(
        multisig_address=multisig_address, contract_address=contract_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=sender_address)
    print('>>> function_outputs:{}'.format(function_outputs))

    """
    Deploy Second Contract
    """
    contract_file = 'tests/test_scripts/test_contracts/greeter.sol'
    source_code = api_helper.loadContract(contract_file)
    contract_name = 'greeter'
    function_inputs = str([
        {
            "name": "_greeting",
            "type": "string",
            "value": "SubContract constructor"
        }])
    tx_hash = action.apply_deploy_contract(
        multisig_address=multisig_address,
        source_code=source_code, contract_name=contract_name,
        function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    is_updated, contract_address2 = action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    """
    Call Second Contract (constant)
    """
    function_name = 'greet'
    function_inputs = str([])
    function_outputs = action.apply_call_constant_contract(
        multisig_address=multisig_address, contract_address=contract_address2,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=owner_address)
    print('>>> function_outputs:{}'.format(function_outputs))

    """
    Call Second Contract (transaction)
    """
    function_name = "setgreeter"
    function_inputs = '[{"name": "_greeting", "type": "string", "value":"Hello World"}]'
    tx_hash = action.apply_transaction_call_contract(
        multisig_address=multisig_address, contract_address=contract_address2,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    """
    Call Second Contract (constant)
    """
    function_name = 'greet'
    function_inputs = str([])
    function_outputs = action.apply_call_constant_contract(
        multisig_address=multisig_address, contract_address=contract_address2,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=owner_address)
    print('>>> function_outputs:{}'.format(function_outputs))

    """
    Deploy 2 more Contracts
    """
    counter = 0
    while(counter < 5):
        counter += 1

        contract_file = 'tests/test_scripts/test_contracts/greeter.sol'
        source_code = api_helper.loadContract(contract_file)
        contract_name = 'greeter'
        function_inputs = str([
            {
                "name": "_greeting",
                "type": "string",
                "value": "SubContract constructor"
            }])
        tx_hash = action.apply_deploy_contract(
            multisig_address=multisig_address,
            source_code=source_code, contract_name=contract_name,
            function_inputs=function_inputs,
            sender_address=owner_address, privkey=owner_privkey)

        is_updated, contract_address = action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    print('[END] test_multi_contracts')


if __name__ == '__main__':
    test_deploy_multi_contracts_script()
