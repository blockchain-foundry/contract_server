import json
import logging
import time
from rest_framework.views import APIView, status

from contract_server.decorators import handle_uncaught_exception
from contracts import evm_abi_utils
from events.models import Watch
from events.serializers import WatchSerializer
from contracts.models import Contract

from .exceptions import (GetStateFromOracleError, WatchCallbackTimeoutError,
                         WatchKeyNotFoundError, ContractNotFoundError)

from .serializers import CreateWatchSerializer
from contract_server import response_utils

logger = logging.getLogger(__name__)


def wait_for_notification(watch_id):
    """Wait for notification from events/addressnotify API

    Args:
        watch_id: id of Watch object
    Returns:
        event: a dict of args and name (event's name) of the tirggerd event
    """
    logger.debug('Waiting for callback of subscription_id: {} ....'.format(watch_id))

    tStart = time.time()

    while True:
        time.sleep(5)
        try:
            watch = Watch.objects.get(id=watch_id)

            # Check the Timeout
            if time.time() - tStart > 1000 or watch.is_expired:
                watch.is_closed = True
                watch.save()
                raise WatchCallbackTimeoutError("Watch callback is timeout")
                break

            if watch.is_triggered:
                event = {
                    "args": json.loads(watch.args),
                    "name": watch.event_name
                }

                watch.is_closed = True
                watch.save()
                break
        except Exception as e:
            raise e
    return event


class Watches(APIView):
    serializer_class = CreateWatchSerializer

    @handle_uncaught_exception
    def get(self, request, watch_id):
        """Get specific Watch object by id

        Args:
            watch_id: id of Watch object

        Return:
            watch: serialized Watch object
        """
        try:
            watch = Watch.objects.get(id=watch_id)
            serializer = WatchSerializer(watch)
            data = {"watch": serializer.data}
            return response_utils.data_response(data)
        except Exception as e:
            # TODO: ERROR_CODE
            return response_utils.error_response(status.HTTP_404_NOT_FOUND, "watch not found")

    def _event_exists(self, multisig_address, contract_address, event_name):
        """ Check if event_name exists in multisig_address/contract_address

        Args:
            multisig_address: the multisig_address of state
            event_name: event name
            contract_address: the contract_address

        Returns:
            is_matched: check if there's matching event
            contract: matching Contract object
        """
        contract = None

        try:
            contracts = Contract.objects.filter(
                state_multisig_address__address=multisig_address,
                contract_address=contract_address)
            contract = contracts[0]
        except Exception as e:
            raise ContractNotFoundError('Contract does not exsit')

        try:
            event_json = evm_abi_utils.get_event_by_name(contract.interface, event_name)
            if event_json != {}:
                return True, contract
            else:
                raise
        except Exception as e:
            return False, None

    def _process_watch_event(self, multisig_address, event_name, contract_address, conditions=""):
        """Process new event watching subscription and wait for event triggered

        Args:
            multisig_address: the multisig_address of state
            event_name: event name
            contract_address: the receiver address for subcontract
            conditions: event filter conditions
        Returns:
            event: the new action result in event.args and event.name
            watch_id: the id of Watch object
        """
        try:
            # Check if event exsits
            is_matched, contract = self._event_exists(multisig_address, contract_address, event_name)
            if not is_matched:
                raise WatchKeyNotFoundError(
                    "event_name:[{}] of contract  {}/{} doesn't exsit".format(event_name, multisig_address, contract_address))

            # Create Watch object in database
            watch = Watch.objects.create(
                event_name=event_name,
                contract=contract,
                conditions=conditions
            )
            watch.save()
            # logger.debug('saving watch: id={}, event_name={}'.format(watch.id, watch.event_name))

            event = wait_for_notification(watch.id)
            data = {
                'watch_id': watch.id,
                'event': event
            }

            return response_utils.data_response(data)

        except ContractNotFoundError as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e))
        except WatchKeyNotFoundError as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e))
        except GetStateFromOracleError as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e))
        except WatchCallbackTimeoutError as e:
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
        except Exception as e:
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))

    # @handle_uncaught_exception
    def post(self, request):
        """Create new event watching subscription and wait for event triggered

        Args:
            multisig_address: the multisig_address
            event_name: event name
            contract_address: the contract address

        Returns:
            event: the new action result in event.args and event.name
            watch_id: the id of Watch object
        """
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=False):
            data = serializer.data

            multisig_address = data['multisig_address']
            event_name = data['event_name']
            contract_address = data['contract_address']
            if 'conditions' in data:
                conditions = data['conditions']
            else:
                conditions = ""
            return self._process_watch_event(
                multisig_address=multisig_address,
                event_name=event_name,
                contract_address=contract_address,
                conditions=conditions)
        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(serializer.errors))
