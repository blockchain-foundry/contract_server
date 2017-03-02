import os, sys
import time
sys.path.insert(0, os.path.abspath(".."))
from example.utils.apply import *
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)



def test_deploy_multi_contracts_script():
    """
    Deploy First Contract
    """
    contract_file = 'tests/test_scripts/test_contracts/greeter.sol'
    contract_name = 'mortal'
    function_inputs = str([
        {
            "name": "_test_constractor",
            "type": "int256",
            "value": "1234"
        }])
    contract_address = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs)
    apply_get_contract_status(contract_address=contract_address)

    getCurrentStatus(contract_address)
    pprint(getABI(contract_address))

    """
    Call First Contract
    """
    # Constanct function call, call without transaction
    # function getStorage() constant returns (address, int256)
    function_name = 'getStorage'
    function_inputs = str([])
    from_address = owner_address
    function_outputs = apply_call_constant_contract(contract_address, function_name, function_inputs, from_address)
    print('>>> function_outputs:{}'.format(function_outputs))

    # Call with transaction
    # function setOwner(address _address) { owner = _address; }
    function_name = 'setOwner'
    function_inputs = str([
        {
            "name": "_address",
            "type": "address",
            "value": "0000000000000000000000000000000000005566"
        }])
    from_address = owner_address
    apply_transaction_call_contract(contract_address, function_name, function_inputs, from_address)
    print('>>> Wait 60s.....')
    time.sleep(60)

    """
    Deploy SubContract
    """
    contract_file = 'tests/test_scripts/test_contracts/greeter.sol'
    contract_name = 'greeter'
    source_code = loadContract(contract_file)
    second_contract_address = '0000000000000000000000000000000000000158'
    function_inputs = str([
        {
            "name": "_greeting",
            "type": "string",
            "value": "SubContract constructor"
        }])

    apply_deploy_sub_contract(
        contract_file=contract_file,
        contract_name=contract_name,
        multisig_address = contract_address,
        deploy_address = second_contract_address,
        source_code=source_code,
        function_inputs=function_inputs)
    print('>>> Wait 60s.....')
    time.sleep(60)

    """
    Get Storage
    """
    # [TODO]: Use constant function call instead
    global_state = get_states(contract_address)
    print('>>> Glabal state of {}: {}'.format(contract_address, global_state))

    """
    Call SubContract
    """
    # Constant Function Call
    function_name = 'greet'
    function_inputs = str([])
    from_address = owner_address
    deploy_address = second_contract_address
    function_outputs = apply_call_constant_sub_contract(contract_address, deploy_address, function_name, function_inputs, from_address)
    print('>>> function_outputs:{}'.format(function_outputs))

    # Transaciton Call
    apply_call_sub_contract(
        contract_address = contract_address,
        deploy_address = second_contract_address,
        function_name = 'setgreeter',
        function_inputs = '[{"name": "_greeting", "type": "string", "value":"Hello World"}]')
    print('>>> Wait 60s.....')
    time.sleep(60)


if __name__ == '__main__':
    test_deploy_multi_contracts_script()
