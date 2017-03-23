import json
import logging
import time
from rest_framework.views import APIView, status
from django.http import JsonResponse

from contract_server.decorators import handle_uncaught_exception
from contracts import evm_abi_utils
from events.models import Watch
from events.serializers import WatchSerializer
from contracts.models import Contract

from .exceptions import (GetStateFromOracleError, WatchCallbackTimeoutError,
                         WatchKeyNotFoundError, ContractNotFoundError)

from .forms import WatchForm

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

            response = {"watch": serializer.data}
            http_status = status.HTTP_200_OK
        except Exception as e:
            response = {"error": "watch not found"}
            http_status = status.HTTP_404_NOT_FOUND
        finally:
            return JsonResponse(response, status=http_status)

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
                multisig_address__address=multisig_address,
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

    def _process_watch_event(self, multisig_address, event_name, contract_address):
        """Process new event watching subscription and wait for event triggered

        Args:
            multisig_address: the multisig_address of state
            event_name: event name
            contract_address: the receiver address for subcontract

        Returns:
            event: the new action result in event.args and event.name
            watch_id: the id of Watch object
        """
        response = {'message': 'error'}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
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
            )
            watch.save()
            # logger.debug('saving watch: id={}, event_name={}'.format(watch.id, watch.event_name))

            event = wait_for_notification(watch.id)
            response = {
                'watch_id': watch.id,
                'event': event
            }
            http_status = status.HTTP_200_OK

        except ContractNotFoundError as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except WatchKeyNotFoundError as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except GetStateFromOracleError as e:
            http_status = status.HTTP_400_BAD_REQUEST
            response = {'message': str(e)}
        except WatchCallbackTimeoutError as e:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = {'message': str(e)}
        except (Contract.DoesNotExist):
            response = {'message': 'contract not found'}
            http_status = status.HTTP_404_NOT_FOUND
            return JsonResponse(response, status=http_status)
        except Exception as e:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = {'message': str(e)}
        finally:
            return JsonResponse(response, status=http_status)

    @handle_uncaught_exception
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
        response = {}
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        # Form validation
        form = WatchForm(request.POST)

        # Form validation
        if form.is_valid():
            multisig_address = form.cleaned_data['multisig_address']
            event_name = form.cleaned_data['event_name']
            contract_address = form.cleaned_data['contract_address']

            return self._process_watch_event(
                multisig_address=multisig_address,
                event_name=event_name,
                contract_address=contract_address
            )
        else:
            response = {"error": form.errors}
            http_status = status.HTTP_400_BAD_REQUEST
            return JsonResponse(response, status=http_status)
