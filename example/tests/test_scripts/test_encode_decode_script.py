import time
from threading import Thread
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.utils.apply import *
from example.conf import (owner_address, owner_privkey, owner_pubkey,
                    OSS_URL, CONTRACT_URL, ORACLE_URL)


def test_encode_decode_script():
    """
    Encode and Decode
    """
    print('[START] test_encode_decode_script')
    # 1. Set contract config
    contract_file = 'tests/test_scripts/test_contracts/encode_decode.sol'
    contract_name = 'encodeAndDecode'
    # string _string,
    # bytes _bytes, bytes2 _bytes2, bytes32 _bytes32,
    # uint bytes32, int _int,
    # bool _bool, address _address
    function_inputs = str([
        { "name": "_string", "type": "string", "value": "hello world"},
        { "name": "_bytes", "type": "bytes", "value": "0x5566000000000000000000000000001255660000000000000000000000000012452544"},
        { "name": "_bytes2", "type": "bytes2", "value": "0x1134"},
        { "name": "_bytes32", "type": "bytes32", "value": "0x5566000000000000000000000000001255660000000000000000000000000012"},

        { "name": "_uint256", "type": "uint256", "value": 12345},
        { "name": "_int256", "type": "int256", "value": -123},

        { "name": "_bool", "type": "bool", "value": True},
        { "name": "_address", "type": "address", "value": "0000000000000000000000000000000000000171"}
    ])


    # 2. Deploy contract
    contract_address = apply_deploy_contract(contract_file=contract_file, contract_name=contract_name, function_inputs=function_inputs, from_address=owner_address, privkey=owner_privkey)
    apply_get_contract_status(contract_address=contract_address)

    # contract_address = "3B1MjrWUxKEvpSvvnQrGycsAswtT9o5yH3"
    print('>>> Wait 10s.....')
    time.sleep(10)

    '''
    Thread 1: Watch Event before transaction call
    This thread would be responsed after function was executed at Contract Server
    '''
    key = 'TestEvent'
    oracle_url = ORACLE_URL
    callback_url = CONTRACT_URL +  '/events/notify/' + contract_address + '/'
    receiver_address = ''

    t1 = Thread(target=apply_watch_event, args=(contract_address, key, oracle_url, callback_url, receiver_address, ))
    t1.start()

    ''' Thread 2: Transaction call
    Call deposit function which would trigger Event
    '''
    function_name = 'testEvent'
    function_inputs = str([])
    from_address = owner_address


    t2 = Thread(target=apply_transaction_call_contract, args=(contract_address, function_name, function_inputs, from_address, owner_privkey))
    t2.start()

    t1.join()


    print('[END] test_encode_decode_script')

if __name__ == '__main__':
    test_encode_decode_script()
