import json
import logging
import requests

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from contracts.exceptions import Multisig_error, SubscribeAddrsssNotificationError
from contracts.models import MultisigAddress
from evm_manager import deploy_contract_utils
from gcoin import scriptaddr, mk_multisig_script
from gcoinapi.client import GcoinAPIClient
from oracles.models import Oracle


logger = logging.getLogger(__name__)
OSSclient = GcoinAPIClient(settings.OSS_API_URL)


class CsrfExemptMixin(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)


class MultisigAddressCreateMixin():

    def get_pubkey_from_oracle(self, oracle, multisig_address=''):
        """Get public keys from an oracle
        """
        url = oracle['url']
        r = requests.get(url + '/proposals/' + multisig_address)
        pubkey = json.loads(r.text)['public_key']
        logger.debug('get ' + url + '\'s pubkey.')
        print('get ' + url + '\'s pubkey.')

        return pubkey

    def _get_multisig_address(self, oracle_list, m, message=''):
        """Get public keys and create multisig_address
        """
        if len(oracle_list) < m:
            raise Multisig_error("The m in 'm of n' is bigger than n.")

        pubkeys = []

        for oracle in oracle_list:
            pubkeys.append(self.get_pubkey_from_oracle(oracle))

        if len(pubkeys) != len(oracle_list):
            raise Multisig_error('there are some oracles that did not response')

        multisig_script = mk_multisig_script(pubkeys, m, message)
        multisig_address = scriptaddr(multisig_script)

        return multisig_address, multisig_script, pubkeys

    def get_oracle_list(self, oracle_list):
        """Check oracle_list is matching oracles in database
        """
        if len(oracle_list) == 0:
            oracle_list = []
            for i in Oracle.objects.all():
                oracle_list.append(
                    {
                        'name': i.name,
                        'url': i.url
                    }
                )
        return oracle_list

    def get_or_create_multisig_address_object(self, oracle_list, m):

        multisig_address, multisig_script, pubkeys = self._get_multisig_address(oracle_list, m)

        try:
            multisig_address_object = MultisigAddress.objects.get(address=multisig_address)
        except MultisigAddress.DoesNotExist:
            # if new multisig address
            multisig_address_object = MultisigAddress.objects.create(
                address=multisig_address, script=multisig_script, least_sign_number=m, is_state_multisig=True)

            for i in oracle_list:
                multisig_address_object.oracles.add(Oracle.objects.get(url=i["url"]))
            multisig_address_object.save()

            deploy_contract_utils.make_multisig_address_file(multisig_address)

            # save multisig address at oracle server
            url_map_pubkeys = []
            for oracle in oracle_list:
                url_map_pubkeys.append({
                    'public_key': self.get_pubkey_from_oracle(oracle),
                    'url': oracle['url']
                })
            self._save_multisig_address(multisig_address, url_map_pubkeys, is_state_multisig=True)

        return multisig_address_object

    def get_multisig_address_object(self, multisig_address):
        multisig_address_object = MultisigAddress.objects.get(address=multisig_address)
        return multisig_address_object

    def _save_multisig_address(self, multisig_address, url_map_pubkeys, is_state_multisig=False):
        """Save multisig_address at Oracle
        """
        for url_map_pubkey in url_map_pubkeys:
            url = url_map_pubkey['url']
            data = {
                'pubkey': url_map_pubkey["public_key"],
                'multisig_address': multisig_address,
                'is_state_multisig': is_state_multisig
            }
            response = requests.post(url + '/multisigaddress/', data=data)

    def _get_callback_url(self, address):
        callback_url = settings.CONTRACT_SERVER_API_URL + \
            '/addressnotify/' + address
        callback_url = ''.join(callback_url.split())
        return callback_url
