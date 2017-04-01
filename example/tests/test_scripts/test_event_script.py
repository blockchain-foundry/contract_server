import time
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.utils import action
from example.utils import api_helper
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)

current_event = ""

def watch_event(multisig_address, contract_address, event_name, conditions):
    global current_event
    response_data = action.apply_watch_event(multisig_address, contract_address, event_name, conditions)
    current_event = response_data['event']

def test_event_script():
    """
    Event
    """
    print('[START] test_event_script')
    # 1. Set contract config
    contract_file = 'tests/test_scripts/test_contracts/event.sol'
    source_code = api_helper.loadContract(contract_file)
    contract_name = 'ClientReceipt'
    function_inputs = '[]'

    # 2. Generate a multisig address
    multisig_address = action.apply_create_multisig_address(
        sender_address=owner_address, min_successes=1)

    # 3. Deploy contract
    tx_hash = action.apply_deploy_contract(
        multisig_address=multisig_address,
        source_code=source_code, contract_name=contract_name,
        function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)
    is_updated, contract_address = action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)
    print()
    print(">>> contract address: {}".format(contract_address))
    '''
    Thread 1: Watch Event before transaction call
    This thread would be responsed after function was executed at Contract Server
    '''
    event_name = 'Deposit'
    t1 = Thread(target=watch_event, args=(multisig_address, contract_address, event_name, ""))
    t1.start()

    ''' Thread 2: Transaction call
    Call deposit function which would trigger Event
    '''
    function_name = 'deposit'
    function_inputs = str([
        {
            "name": "_id",
            "type": "bytes32",
            "value": "0x00000000000000000000000000001234"
        }])
    tx_hash = action.apply_transaction_call_contract(
        multisig_address=multisig_address, contract_address=contract_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=owner_address, privkey=owner_privkey)
    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)
    t1.join()
    global current_event
    print("\n>>>> current_event: {}".format(current_event))
    print('\n[END] test_event_script')


if __name__ == '__main__':
    test_event_script()
