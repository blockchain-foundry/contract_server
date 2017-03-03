import json
import logging
import sha3
import requests
from rest_framework.response import Response
from rest_framework.views import APIView, status
from django.conf import settings
from django.http import JsonResponse

from contract_server.decorators import handle_uncaught_exception
from eth_abi.abi import decode_abi, decode_single
from gcoinapi.client import GcoinAPIClient
from gcoinbackend import core as gcoincore
from evm_manager.deploy_contract_utils import *
from evm_manager.commander import Commander
from .forms import NotifyForm, WatchForm
from contract_server.utils import *
from events.models import Watch
from events.serializers import WatchSerializer
from contracts.views import ContractFunc
from oracles.models import Contract
from contracts.evm_abi_utils import wrap_decoded_data

from contract_server.mixins import CsrfExemptMixin
from .exceptions import *

import threading
import time

# Declare a global list for registering the subscription id
global subscription_id_list
subscription_id_list = []
# Preventing race condition
lock = threading.Lock()

OSSclient = GcoinAPIClient(settings.OSS_API_URL)

try:
    import http.client as httplib
except ImportError:
    import httplib

logger = logging.getLogger(__name__)


class Watches(APIView):

    @handle_uncaught_exception
    def get(self, request, subscription_id):
        """
        Get specific watch object by subscription_id
        """
        try:
            watch = Watch.objects.get(subscription_id=subscription_id)
            serializer = WatchSerializer(watch)

            response = {"watch": serializer.data}
            http_status = status.HTTP_200_OK
        except:
            response = {"error": "watch not found"}
            http_status = status.HTTP_404_NOT_FOUND
        finally:
            return JsonResponse(response, status=http_status)


class Events(APIView):
    """  Events Restful API
    """

    def _get_contract_state_from_oracle(self, multisig_address, oracle_url):
        """
        Get contract state from specific Oracle
        """
        try:
            response = requests.get(oracle_url + '/states/' + multisig_address)
            if response.status_code == requests.codes.ok:
                contract = json.loads(response.text)
            else:
                response.raise_for_status()
        except:
            raise GetStateFromOracle_error

        return contract

    def _subscribe_address_notification(self, multisig_address, callback_url):
        """
        Subscribe address notification via OSS
        OSS will callback to callback_url
        """
        try:
            subscription_id, created_time = OSSclient.subscribe_address_notification(
                multisig_address,
                callback_url)
            return subscription_id, created_time
        except:
            raise SubscribeAddrsssNotification_error

    def _wait_for_notification(self, subscription_id):
        """
        Wait for notification from events/notify API
        """
        print('Waiting for callback of subscription_id: {} ....'.format(subscription_id))

        global subscription_id_list
        # To register the subscription_id
        lock.acquire()
        subscription_id_list.append(subscription_id)
        lock.release()
        tStart = time.time()

        while True:
            time.sleep(5)
            lock.acquire()

            try:
                watch = Watch.objects.get(subscription_id=subscription_id)
                # Check the Timeout
                if time.time() - tStart > 1000 or watch.is_expired:
                    subscription_id_list.remove(subscription_id)

                    watch.is_closed = True
                    watch.save()
                    raise WatchCallbackTimeout_error("Watch callback is timeout")
                    break
                if subscription_id not in subscription_id_list:
                    # The notification is callbacked
                    # print('watch.args:{}'.format(json.loads(watch.args)))

                    event = {
                        "args": json.loads(watch.args),
                        "name": watch.key
                    }
                    watch.is_closed = True
                    watch.save()

                    response = {
                        'subscription_id': subscription_id,
                        'event': event
                    }
                    break
            except Exception as e:
                raise e
            finally:
                lock.release()
        return response

    def _key_exists(self, multisig_address, receiver_address, key):
        """ Check if key exists in multisig_address/receiver_address
        """
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except:
            raise ContractNotFound_error('Contract does not exsit')

        if receiver_address != '' and receiver_address != multisig_address:
            try:
                sub_contract = contract.subcontract.all().filter(deploy_address=receiver_address)[0]
                interface = sub_contract.interface
            except:
                raise SubContractNotFound_error('SubContract does not exsit')
        else:
            interface = contract.interface
        try:
            contract_func = ContractFunc()
            event_json = contract_func._get_event_by_name(interface, key)
            return True if event_json != {} else False
        except:
            return False

    def _process_watch_event(self, multisig_address, key, callback_url, oracle_url, receiver_address):
        response = {'message': 'error'}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            # Check if key exsits
            if not self._key_exists(multisig_address, receiver_address, key):
                raise WatchKeyNotFound_error(
                    "key:[{}] of contract  {}/{} doesn't exsit".format(key, multisig_address, receiver_address))

            # Subscribe address notification by sending request to OSS
            subscription_id, created_time = self._subscribe_address_notification(
                multisig_address, callback_url)

            # Get contract state from oracle
            contract_state = self._get_contract_state_from_oracle(
                multisig_address=multisig_address,
                oracle_url=oracle_url
            )

            # Create Watch object in database
            watch = Watch.objects.create(
                multisig_address=multisig_address,
                key=key,
                subscription_id=subscription_id,
                receiver_address=receiver_address
            )
            watch.save()
            # print('saving watch: receiver_address={}, subscription_id={}'.format(watch.receiver_address, watch.subscription_id))

            # Store contract state in contract server
            contract_path = Commander().getContractPath(subscription_id)
            with open(contract_path, 'w') as f:
                f.write(json.dumps(contract_state))

            # Wait for OSS notification....
            response = self._wait_for_notification(subscription_id)

            http_status = status.HTTP_200_OK

        except ContractNotFound_error as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except SubContractNotFound_error as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except WatchKeyNotFound_error as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except SubscribeAddrsssNotification_error as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except GetStateFromOracle_error as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except WatchCallbackTimeout_error as e:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = {'message': str(e)}
        except (Contract.DoesNotExist, SubContract.DoesNotExist):
            response = {'message': 'contract not found'}
            http_status = status.HTTP_404_NOT_FOUND
            return JsonResponse(response, status=http_status)
        except Exception as e:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = {'messagea': str(e)}
        finally:
            return JsonResponse(response, status=http_status)

    @handle_uncaught_exception
    def post(self, request):
        """ Create new event subscription
        Args:
            multisig_address: the contract's address
            key: event name
            callback_url: callback_url of OSS Address Notification
            oracle_url: the oracle_url for querying last state
            receiver_address: the receiver address for subcontract
        Return:
            event: the new action result in event.args and event.name
            subscription_id: The subscription_id from OSS
        """
        response = {}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        # Form validation
        form = WatchForm(request.POST)

        # Form validation
        if form.is_valid():
            multisig_address = form.cleaned_data['multisig_address']
            key = form.cleaned_data['key']
            oracle_url = form.cleaned_data['oracle_url']
            receiver_address = form.cleaned_data['receiver_address']

            # optional callback_url
            callback_url = form.cleaned_data['callback_url']
            if callback_url == '':
                callback_url = request.build_absolute_uri(
                    '/') + 'events/notify/' + multisig_address + '/' + receiver_address
                callback_url = ''.join(callback_url.split())

            # print('callback_url:{}'.format(callback_url ))
            return self._process_watch_event(
                multisig_address=multisig_address,
                key=key,
                callback_url=callback_url,
                oracle_url=oracle_url,
                receiver_address=receiver_address
            )
        else:
            response = {"error": form.errors}
            http_status = status.HTTP_406_NOT_ACCEPTABLE
            return JsonResponse(response, status=http_status)


class Notify(APIView):

    def _hash_key(self, key):
        """
        Hash key by Keccak-256
        """
        k = sha3.keccak_256()
        k.update(key.encode())
        return k.hexdigest()

    def _get_event_key(self, multisig_address, receiver_address, event_name):
        """
        Get event key string via multisig_address and event_name
        """

        # Get contract by multisig_address
        try:
            interface = ''
            contract = Contract.objects.get(multisig_address=multisig_address)
            if receiver_address == multisig_address:
                interface = contract.interface
            else:
                sub_contract = contract.subcontract.all().filter(deploy_address=receiver_address)[0]
                interface = sub_contract.interface
        except (Contract.DoesNotExist, SubContract.DoesNotExist):
            return 'contract not found'
            response = {'error': 'contract not found'}
            http_status = status.HTTP_404_NOT_FOUND
            return JsonResponse(response, status=http_status)

        # Get event JSON
        contract_func = ContractFunc()
        event_json = contract_func._get_event_by_name(interface, event_name)
        types = []
        event_args = []
        order = 0
        for i in event_json['inputs']:
            arg = {
                "type": i.get("type"),
                "name": i.get("name"),
                "indexed": i.get("indexed"),
                "order": order
            }
            order += 1
            event_args.append(arg)
            types.append(i.get('type'))
        key = event_name + '(' + ','.join(types) + ')'
        return key, event_args

    def _run_contract(self, tx_hash, subscription_id):
        '''
        Run the contract function call of tx_hash
        '''

        raw_tx = gcoincore.get_tx(tx_hash)
        logger.debug('raw_tx:{}'.format(raw_tx))

        tx = get_tx_info(tx_hash)

        sender_address, multisig_address, to_addr, bytecode, value, is_deploy, blocktime = get_contracts_info(
            tx)
        value = "\'" + str(value) + "\'"
        blocktime = "\'" + str(blocktime) + "\'"
        logger.debug('[Transaction Info] tx_hash:{}, blocktime:{}'.format(tx_hash, blocktime))

        logger.debug(
            '[Contract Info] sender_addr:{}, multisig_address:{}, bytecode:{}'.format(
                sender_address, multisig_address, bytecode))
        # print('[Contract Info] sender_addr:{}, multisig_address:{}, bytecode:{}, to_addr:{}'.format(sender_address, multisig_address, bytecode, to_addr))
        commander = Commander()
        command_string = commander.buildCommand(
            sender_address=sender_address,
            multisig_address=multisig_address,
            bytecode=bytecode, value=value,
            blocktime=blocktime, is_deploy=is_deploy,
            subscription_id=subscription_id,
            to_addr=to_addr)

        # print('command_string:' + command_string)
        commander.execute(command_string)

    def _decode_event_from_logs(self, logs, evm_address, event_hex, event_args, receiver_address):
        '''
        Decode event content from log file
        '''
        # Initialize
        event = {}

        # Arrange args
        indexed_args = []
        non_indexed_args = []
        for arg in event_args:
            if arg['indexed']:
                indexed_args.append(arg)
            else:
                non_indexed_args.append(arg)
        non_indexed_types = []
        for arg in non_indexed_args:
            non_indexed_types.append(arg['type'])

        # Get corresponding logs
        current_log = None
        for log in logs:
            is_matched_address = (receiver_address != '' and log['address'] == receiver_address) or log[
                'address'] == evm_address

            # print('is_matched_address:{}'.format(is_matched_address))
            if is_matched_address and log['topics'][0] == '0x' + event_hex:
                current_log = log
                break
        # print('logs:{} \ncurrent_log: {}'.format(logs, current_log))

        if current_log is not None:
            array = []
            data = log['data']

            decoded_data = decode_abi(non_indexed_types, data)
            indexed_count = 1
            non_indexed_count = 0

            for arg in event_args:
                item = {
                    "name": arg["name"],
                    "type": arg["type"],
                    "indexed": str(arg["indexed"])
                }
                if arg["indexed"]:
                    value = decode_single(
                        arg["type"],
                        current_log["topics"][indexed_count])
                    indexed_count += 1
                else:
                    value = decoded_data[non_indexed_count]
                    non_indexed_count += 1

                item['value'] = value
                item = wrap_decoded_data(item)
                array.append(item)
            event = array
        else:
            event = None

        return event

    def _get_alive_watch(self, subscription_id):
        '''
        Check if watch is alive
        '''
        watch = Watch.objects.get(subscription_id=subscription_id)
        if watch.is_closed or watch.is_expired:
            if watch.is_closed:
                raise WatchIsClosed_error('watch is closed')
            elif watch.is_expired:
                raise WatchIsExpired_error('watch is expired')
        return watch

    def _callback_to_watch(self, subscription_id):
        # [TODO]: unittest

        global subscription_id_list
        lock.acquire()
        try:
            if subscription_id in subscription_id_list:
                subscription_id_list.remove(subscription_id)
            else:
                raise GlobalSubscriptionIdNotFound_error
        except Exception as e:
            raise e
        finally:
            lock.release()

    def _unsubscribe_address_notification(self, subscription_id):
        """
        Unsubscribe subscription via OSS
        """
        try:
            deleted, deleted_id = OSSclient.unsubscribe_address_notification(subscription_id)
            return deleted, deleted_id
        except:
            raise UnsubscribeAddrsssNotification_error

    def _process_accept_notification(self, tx_hash, subscription_id, multisig_address, receiver_address):
        """ Process accepting notification
        """
        response = {'message': 'error'}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            # Get event_name from subscription_id
            watch = self._get_alive_watch(subscription_id)
            # print('find watch subscription_id:{}, key:{}'.format(watch.subscription_id, watch.key))

            # Get hashed key

            key, event_args = self._get_event_key(multisig_address, receiver_address, watch.key)
            event_hex = self._hash_key(key)
            # print('event_hex:{}'.format(event_hex))

            # Run EVM
            self._run_contract(tx_hash, subscription_id)

            # Open [:subscription_id]_log file
            contract_path = Commander().getContractPath(subscription_id)
            log_path = contract_path + '_log'
            logger.debug("Current Log file path: {}".format(log_path))

            contract_evm_address = wallet_address_to_evm_address(multisig_address)
            # print('contract_evm_address:{}'.format(contract_evm_address))

            # Save log into watch object
            logs = ''
            with open(log_path, 'r') as f:
                content_str = f.read().replace('\n', '')
                logger.debug('[Log content]:{}'.format(content_str))
                content = json.loads(content_str)
                logs = content['logs']
                # print('logs:{}'.format(logs))

            event = self._decode_event_from_logs(
                logs=logs,
                evm_address=contract_evm_address,
                event_hex=event_hex,
                event_args=event_args,
                receiver_address=receiver_address
            )

            if event is None:
                raise LogDecodeFailed_error('Log decoding failed')
            else:
                watch.args = json.dumps(event)
                # print('watch.args after decoding:{}'.format(watch.args))
                watch.save()

            # Callback
            self._callback_to_watch(subscription_id)

            http_status = status.HTTP_200_OK
            response = {'message': 'Notified:' + subscription_id}

        except WatchIsClosed_error as e:
            response = {'message': str(e)}
            http_status = status.HTTP_200_OK
        except WatchIsExpired_error as e:
            response = {'message': str(e)}
            http_status = status.HTTP_200_OK
        except IOError:
            response = {'message': 'contract log not found'}
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
        except LogDecodeFailed_error as e:
            response = {'message': str(e)}
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
        except Exception as e:
            response = {'message': str(e)}
            print(str(e))
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
        finally:
            logger.debug("[Event]/[Notify]/:[response:{}]".format(response))
            return JsonResponse(response, status=http_status)

    @handle_uncaught_exception
    def post(self, request, multisig_address, receiver_address=''):
        """ Receive Address Notification from OSS Server
        The Address Notification related to [:multisig_address] was subscribed from [events/watches/] API.
        Args:
            multisig_address: The address that deployed contract, or main contract
            receiver_address: The receiver address. If it's empty, then set receiver_address = multisig_address.
            tx_hash: A new transaction hash related to [:multisig_address]
            subscription_id: The subscription_id from OSS
            notification_id: The notification_id from OSS
        Returns:
            error: If there's error, return error message.
            message: If it's successful, return messge.
        """

        # Form validation
        form = NotifyForm(request.POST)

        if form.is_valid():
            tx_hash = form.cleaned_data['tx_hash']
            subscription_id = form.cleaned_data['subscription_id']
            notification_id = form.cleaned_data['notification_id']
            if receiver_address == '':
                receiver_address = multisig_address
            # print('[Received notification]: multisig_address:{}, tx_hash:{}, subscription_id:{}, notification_id:{}, receiver_address:{}'.format(multisig_address, tx_hash, subscription_id, notification_id, receiver_address))

            # Use thread to callback to events/watches
            t = threading.Thread(target=self._process_accept_notification, args=(
                tx_hash, subscription_id, multisig_address, receiver_address))
            t.setDaemon(False)
            t.start()

            # Unsubscribe the subscription_id
            self._unsubscribe_address_notification(subscription_id)

            response = {"message": "Received subscription_id:{}".format(subscription_id)}
            http_status = status.HTTP_200_OK
            return JsonResponse(response, status=http_status)

        else:
            response = {"error": form.errors}
            http_status = status.HTTP_406_NOT_ACCEPTABLE
            return JsonResponse(response, status=http_status)
