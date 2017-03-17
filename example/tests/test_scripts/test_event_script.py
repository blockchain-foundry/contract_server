import time
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.utils.apply import *
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)


def test_event_script():
    """
    Event
    """
    print('[START] test_event_script')
    # 1. Set contract config
    contract_file = 'tests/test_scripts/test_contracts/event.sol'
    contract_name = 'ClientReceipt'
    function_inputs = '[]'

    # 2. Deploy contract
    multisig_address = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs, from_address=owner_address, privkey=owner_privkey)
    apply_get_contract_status(multisig_address=multisig_address)

    '''
    Thread 1: Watch Event before transaction call
    This thread would be responsed after function was executed at Contract Server
    '''
    receiver_address = ''
    event_name = 'Deposit'

    t1 = Thread(target=apply_watch_event, args=(multisig_address, receiver_address, event_name,))
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
    from_address = owner_address


    t2 = Thread(target=apply_transaction_call_contract, args=(multisig_address, function_name, function_inputs, from_address, owner_privkey))
    t2.start()

    t1.join()

    print('[END] test_event_script')

if __name__ == '__main__':
    test_event_script()
