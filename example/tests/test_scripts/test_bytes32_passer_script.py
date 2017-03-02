import time
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.utils.apply import *
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)


def test_bytes32_passer_script():
    print('[START] test_bytes32_passer')

    """
    Deploy Descriptor
    """
    contract_file = 'tests/test_scripts/test_contracts/bytes32_passer_Descriptor.sol'
    contract_name = 'Descriptor'
    function_inputs = '[]'

    contract_address_descriptor = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs, from_address=owner_address, privkey=owner_privkey)
    print('>>> Descriptor contract_addr:{}'.format(contract_address_descriptor))
    # Applyed contract_address_bytes32passer: '3DubYuqy3ja2UziDoGC6376ZyV67JzyMse'

    """
    Deploy Bytes32Passer
    """
    contract_file = 'tests/test_scripts/test_contracts/bytes32_passer_Bytes32Passer.sol'
    contract_name = 'Bytes32Passer'

    source_code = loadContract(contract_file)
    source_code = source_code.replace('DESCRIPTOR_ADDRESS', prefixed_wallet_address_to_evm_address(contract_address_descriptor))
    print('source_code:{}'.format(source_code))
    second_contract_receiver = '0000000000000000000000000000000000000111'
    function_inputs = '[]'

    apply_deploy_sub_contract(
        contract_file=contract_file,
        contract_name=contract_name,
        multisig_address = contract_address_descriptor,
        deploy_address = second_contract_receiver,
        source_code=source_code,
        function_inputs=function_inputs,
        from_address=owner_address,
        privkey=owner_privkey)

    print('>>> Wait 60s.....')
    time.sleep(60)

    """
    Watch Event and Call Function
    """
    '''
    Thread 1: Watch Event before transaction call
    This thread would be responsed after function was executed at Contract Server
    '''
    contract_address = contract_address_descriptor
    key = 'TestEvent'
    oracle_url = ORACLE_URL
    callback_url = CONTRACT_URL + '/events/notify/' + contract_address + '/' + second_contract_receiver
    receiver_address = second_contract_receiver

    t1 = Thread(target=apply_watch_event, args=(contract_address, key, oracle_url, callback_url, receiver_address, ))
    t1.start()
    print('>>> Watching event......')


    ''' Thread 2: Transaction call
    Call getDescription function which would trigger Event
    '''
    contract_address = contract_address_descriptor
    deploy_address = second_contract_receiver
    function_name = 'getDescription'
    function_inputs = '[]'

    t2 = Thread(target=apply_transaction_call_sub_contract, args=(contract_address, deploy_address, function_name, function_inputs, owner_address, owner_privkey))
    t2.start()

    t1.join()
    print('[END] test_bytes32_passer')

if __name__ == '__main__':
    test_bytes32_passer_script()
