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
from .forms import NotifyForm
from contract_server.utils import *
from events.models import Watch
from events.serializers import WatchSerializer
from contracts.views import ContractFunc
from oracles.models import Contract

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
    def _get_contract_from_oracle(self, multisig_address, oracle_url):
        """
        Get contract state from specific Oracle
        """
        response = requests.get(oracle_url + '/states/' + multisig_address)
        if response.status_code == requests.codes.ok:
            contract = json.loads(response.text)
        else:
            response.raise_for_status()

        return contract

    @handle_uncaught_exception
    def post(self, request):
        """ Create new event subscription
        Args:
            multisig_address: the contract's address
            key: event name
            callback_url: callback_url of OSS Address Notification
            oracle_url: the oracle_url for querying last state

        Return:
            event: the new action result in event.args and event.name
            subscription_id: The subscription_id from OSS
        """
        response = {}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        try:
            json_data = json.loads(request.body.decode('utf8'))

            # TODO: form validation
            multisig_address = json_data['multisig_address']
            key = json_data['key']
            callback_url = json_data['callback_url']
            oracle_url = json_data['oracle_url']
        except:
            response = {'error': 'missing input'}
            http_status = status.HTTP_406_NOT_ACCEPTABLE
            return JsonResponse(response, status=http_status)

        # Subscribe address
        try:
            subscription_id, created_time = OSSclient.subscribe_address_notification(
                multisig_address,
                callback_url)
        except:
            response = {'error': 'Failed to subscribe address'}
            http_status = status.HTTP_400_BAD_REQUEST
            return JsonResponse(response, status=http_status)

        # Get contract from database
        try:
            contract = self._get_contract_from_oracle(
                multisig_address=multisig_address,
                oracle_url=oracle_url
            )
        except:
            response = {'error': 'failed to get latest state of contract'}
            http_status = status.HTTP_400_BAD_REQUEST
            return JsonResponse(response, status=http_status)

        # Create Watch object in database
        watch = Watch.objects.create(
            multisig_address=multisig_address,
            key=key,
            subscription_id=subscription_id
        )
        watch.save()

        # Store contract state in contract server
        commander = Commander()
        contract_path = commander.getContractPath(subscription_id)

        with open(contract_path, 'w') as f:
            f.write(json.dumps(contract))

        # Wait for notification....
        global subscription_id_list
        # To register the subscription_id
        lock.acquire()
        subscription_id_list.append(subscription_id)
        lock.release()

        tStart = time.time()
        while True:
            lock.acquire()
            # To check the subscription_id is in the list or not
            if subscription_id not in subscription_id_list:
                # The notification is callbacked
                watch = {}
                try:
                    watch = Watch.objects.get(subscription_id=subscription_id)
                except Watch.DoesNotExist:
                    response = {'error': 'watch not found.'}
                    return JsonResponse(response, status=http_status)

                event = {
                    "args": json.loads(watch.args.replace("'", '"')),
                    "name": watch.key
                }
                watch.is_closed = True
                watch.save()

                response = {
                    'subscription_id': subscription_id,
                    'event': event
                }
                http_status = status.HTTP_200_OK
                break

            # Check the Timeout
            if time.time() - tStart > 1000 or watch.is_expired:
                response = {'error': 'Time Out'}
                http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
                subscription_id_list.remove(subscription_id)

                watch.is_closed = True
                watch.save()
                break
            lock.release()
        lock.release()

        return JsonResponse(response, status=http_status)


class Notify(APIView):
    def _hash_key(self, key):
        """
        Hash key by Keccak-256
        """
        k = sha3.keccak_256()
        k.update(key.encode())
        return k.hexdigest()

    def _get_event_key(self, multisig_address, event_name):
        """
        Get event key string via multisig_address and event_name
        """

        # Get contract by multisig_address
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            return 'contract not found'
            response = {'error': 'contract not found'}
            http_status = status.HTTP_404_NOT_FOUND
            return JsonResponse(response, status=http_status)

        # Get event JSON
        contract_func = ContractFunc()
        event_json = contract_func._get_event_by_name(contract.interface, event_name)
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
        raw_tx = gcoincore.get_tx(tx_hash)
        logger.debug('raw_tx:{}'.format(raw_tx))

        tx = get_tx_info(tx_hash)

        sender_address, multisig_address, bytecode, value, is_deploy, blocktime = get_contracts_info(tx)
        value = "\'" + str(value) + "\'"
        blocktime = "\'" + str(blocktime) + "\'"
        logger.debug('[Transaction Info] tx_hash:{}, blocktime:{}'.format(tx_hash, blocktime))

        logger.debug(
            '[Contract Info] sender_addr:{}, multisig_address:{}, bytecode:{}'.format(
                sender_address, multisig_address, bytecode))
        commander = Commander()
        command_string = commander.buildCommand(
            sender_address=sender_address,
            multisig_address=multisig_address,
            bytecode=bytecode, value=value,
            blocktime=blocktime, is_deploy=is_deploy,
            subscription_id=subscription_id)

        print('command_string:' + command_string)
        commander.execute(command_string)

    def _get_event_from_logs(self, logs, evm_address, event_hex, event_args):
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
            if log['address'] == evm_address and log['topics'][0] == '0x' + event_hex:
                current_log = log
                break

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

                # For JSON string
                if arg['type'] == 'bool':
                    value = str(value)
                elif arg['type'] == 'address':
                    value = value
                elif 'int' not in arg['type']:
                    value = value.decode("utf-8")

                item['value'] = value
                array.append(item)
            event["args"] = array

        return event

    @handle_uncaught_exception
    def post(self, request, multisig_address):
        """ Receive Address Notification from OSS Server

        The Address Notification related to [:multisig_address] was subscribed from [events/watch/] API.

        Args:
            tx_hash: A new transaction hash related to [:multisig_address]
            subscription_id: The subscription_id from OSS
            notification_id: The notification_id from OSS

        Returns:
            error: If there's error, return error message.
            message: If it's successful, return messge.
        """

        response = {"error": "error"}

        # Form validation
        form = NotifyForm(request.POST)
        tx_hash = ''
        subscription_id = ''

        if form.is_valid():
            tx_hash = form.cleaned_data['tx_hash']
            subscription_id = form.cleaned_data['subscription_id']
        else:
            errors = ', '.join(reduce(lambda x, y: x + y, form.errors.values()))
            response = {"error": errors}
            http_status = status.HTTP_406_NOT_ACCEPTABLE
            return JsonResponse(response, status=http_status)

        # Get event_name from subscription_id
        watch = None
        try:
            watch = Watch.objects.get(subscription_id=subscription_id)
        except Watch.DoesNotExist:
            response = {'error': 'watch is not found'}
            http_status = status.HTTP_404_NOT_FOUND
            return JsonResponse(response, status=http_status)
        if watch.is_closed or watch.is_expired:
            if watch.is_closed:
                response = {'message': 'watch is closed'}
            elif watch.is_expired:
                response = {'message': 'watch is expired'}
            return JsonResponse(response, status=status.HTTP_200_OK)

        # Get hashed key
        key, event_args = self._get_event_key(multisig_address, watch.key)
        event_hex = self._hash_key(key)

        # Run EVM
        evm_result = self._run_contract(tx_hash, subscription_id)
        print(evm_result)

        # Open [:subscription_id]_log file
        commander = Commander()
        contract_path = commander.getContractPath(subscription_id)
        log_path = contract_path + '_log'
        logger.debug("Current Log file path: {}".format(log_path))

        contract_evm_address = wallet_address_to_evm_address(multisig_address)

        try:
            with open(log_path, 'r') as f:
                content_str = f.read().replace('\n', '')
                logger.debug('[Log content]:{}'.format(content_str))
                content = json.loads(content_str)
                logs = content['logs']

                event = self._get_event_from_logs(
                    logs=logs,
                    evm_address=contract_evm_address,
                    event_hex=event_hex,
                    event_args=event_args
                )
                logger.debug("event:{}".format(event))

                if event is None:
                    response = {'error': 'event not found'}
                    http_status = status.HTTP_404_NOT_FOUND
                    return JsonResponse(response, status=http_status)
                watch.args = event["args"]
                watch.save()
        except IOError:
            response = {'error': 'contract log not found'}
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
            return JsonResponse(response, status=http_status)

        # Callback
        global subscription_id_list
        lock.acquire()
        try:
            subscription_id_list.remove(subscription_id)
            response = {'Event Notify': subscription_id}
            http_status = status.HTTP_200_OK
        except:
            response = {'No subscription_id': subscription_id}
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        finally:
            lock.release()
            return JsonResponse(response, status=http_status)
