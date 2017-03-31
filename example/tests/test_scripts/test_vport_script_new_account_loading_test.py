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
import gcoin

user2_address = "15QzWKknjaT3m3R2TgpbieEGZVT4R7VjvN"
user2_privkey = "L2CWz4fw6LieNcnhorx63ZtnryBKJaKysaohcacYW6SybPP4FzBL"
user2_evmAddr = api_helper.wallet_address_to_evm_address(user2_address)

users = []
current_event = ""


def generate_users():
    for x in range(1, 11):
        priv = gcoin.sha256("user" + str(x))
        addr = gcoin.pubtoaddr(gcoin.privtopub(priv))
        evm_address = api_helper.wallet_address_to_evm_address(addr)
        user = {
            "gcoin_address": addr,
            "privkey": priv,
            "evm_address": evm_address
        }
        users.append(user)


def watch_event(multisig_address, contract_address, event_name, conditions):
    global current_event
    response_data = action.apply_watch_event(multisig_address, contract_address, event_name, conditions)
    current_event = response_data['event']

def call_identity_factory(
        multisig_address, identity_factory_address,
        delegates, longTimeLock, shortTimeLock,
        user):
    """
    Call IdentityFactory.CreateProxyWithControllerAndRecovery(
        address userKey,
        address[] delegates,
        uint longTimeLock,
        uint shortTimeLock)
    """
    userKey = user['evm_address']
    print('[START] call_identity_factory CreateProxyWithControllerAndRecovery({}, {}, {}, {})'.format(userKey, delegates, longTimeLock, shortTimeLock))

    event_name = "IdentityCreated"
    conditions = str([{
        "name": "userKey",
        "type": "address",
        "value": userKey
    }])
    t1 = Thread(target=watch_event, args=(multisig_address, identity_factory_address, event_name, conditions,))
    t1.start()

    function_name = "CreateProxyWithControllerAndRecovery"
    function_inputs = str(
        [
            {"name": "userKey", "type": "address", "value": userKey},
            {"name": "delegates", "type": "delegates", "value": delegates},
            {"name": "longTimeLock", "type": "uint", "value": longTimeLock},
            {"name": "shortTimeLock", "type": "uint", "value": shortTimeLock},
        ]
    )
    tx_hash = action.apply_transaction_call_contract(
        multisig_address=multisig_address, contract_address=identity_factory_address,
        function_name=function_name, function_inputs=function_inputs,
        sender_address=user["gcoin_address"], privkey=user["privkey"])

    action.apply_check_state(multisig_address=multisig_address, tx_hash=tx_hash)

    t1.join()
    event = current_event
    for item in event['args']:
        if item['name'] == 'controller':
            controller_address = item['value']
        elif item['name'] == 'proxy':
            proxy_address = item['value']
        elif item['name'] == 'recoveryQuorum':
            recovery_address = item['value']
    print('[END] call_identity_factory CreateProxyWithControllerAndRecovery({}, {}, {}, {})'.format(userKey, delegates, longTimeLock, shortTimeLock))

    return controller_address, proxy_address, recovery_address


def new_account(user):

    print("[START] Creat vPort account")
    multisig_address = '3J2fJondfkDa9eVYN4m7HUr2vs3NusNdWv'
    registry_address = 'c6ecb4ce7ddd2acf03eaf8f85b884de95e5be4f0'
    controller_address = '718f770a52ac1926302f42d99637cc96634fcf6c'
    proxy_address = '5c96b5a9cdd080d009a5f9b39233bb852a1d0604'
    recovery_address = '2f5816810f255cb57e3a9e5ef92a5a5deda15ea5'
    identity_factory_address = '4f8c35f1ca068863047fcdb4a3c4f82f565aadb8'

    # userKey = user['evm_address']
    delegates = [user2_evmAddr]
    longTimeLock = 0
    shortTimeLock = 0

    new_controller_address, new_proxy_address, new_recovery_address = call_identity_factory(
        multisig_address, identity_factory_address,
        delegates, longTimeLock, shortTimeLock,
        user)
    is_success = action.apply_bind_contract(multisig_address, new_controller_address, controller_address)
    if is_success is False:
        raise
    is_success = action.apply_bind_contract(multisig_address, new_proxy_address, proxy_address)
    if is_success is False:
        raise
    is_success = action.apply_bind_contract(multisig_address, new_recovery_address, recovery_address)
    if is_success is False:
        raise
    print('------------ created -----------')
    print("    multisig_address = '{}'".format(multisig_address))
    print("    registry_address = '{}'".format(registry_address))
    print("    controller_address = '{}'".format(new_controller_address))
    print("    proxy_address = '{}'".format(new_proxy_address))
    print("    recovery_address = '{}'".format(new_recovery_address))
    print("    identity_factory_address = '{}'".format(identity_factory_address))

    print("[END] vPort account is created!")

    return new_controller_address, new_proxy_address, new_recovery_address


def maxtime(self, ts):
    global MAXTIME
    if ts > MAXTIME:
        MAXTIME = ts


def mintime(self, ts):
    global MINTIME
    if ts < MINTIME:
        MINTIME = ts


def main():
    print("User " + sys.argv[1])
    user_id = int(sys.argv[1])

    generate_users()
    print(users[user_id])

    counter = 1
    testing_times = 10
    testing_logs = []
    time_spans = []

    while(counter <= testing_times):
        print("========= Round {} ========".format(counter))

        start_time = time.time()
        new_controller_address, new_proxy_address, new_recovery_address = new_account(users[user_id])
        time_span = time.time() - start_time

        testing_log = {
            "new_controller_address": new_controller_address,
            "new_proxy_address": new_proxy_address,
            "new_recovery_address": new_recovery_address,
            "time_span": time_span
        }
        time_spans.append(time_span)
        testing_logs.append(testing_log)
        counter += 1
        print("time_span: {}".format(time_span))

    time_total = 0
    for x in range(0, testing_times):
        time_total += time_spans[x]

    print("testing_logs: {}".format(testing_logs))
    print("time_spans: {}".format(time_spans))

    print("\ntotal time: {}".format(time_total))
    print("average time span: %0.3f" % (time_total / testing_times))


if __name__ == '__main__':
    main()
