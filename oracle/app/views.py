import ast
import base58
import binascii
import hashlib
import json
import re

from gcoin import (multisign, deserialize, pubtoaddr,
                   privtopub, sha256, ripemd)

from django.http import HttpResponse, JsonResponse
from django.utils.crypto import get_random_string
from django.views.generic.edit import BaseFormView, ProcessFormView
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from app.models import Proposal, Keystore, OraclizeContract, ProposalOraclizeLink
from app.serializers import ProposalSerializer
from evm_manager import deploy_contract_utils
from evm_manager.utils import wallet_address_to_evm
from .forms import MultisigAddrFrom, ProposeForm, SignForm, NotifyForm
from oracle.mixins import CsrfExemptMixin
from gcoinbackend import core as gcoincore
from app import response_utils

import threading

pubkey_hash_re = re.compile(r'^76a914[a-f0-9]{40}88ac$')
pubkey_re = re.compile(r'^21[a-f0-9]{66}ac$')
script_hash_re = re.compile(r'^a914[a-f0-9]{40}87$')

try:
    import http.client as httplib
except ImportError:
    import httplib

EVM_PATH = '../oracle/states/{multisig_address}'


def addressFromScriptPubKey(script_pub_key):
    script_pub_key = script_pub_key.lower()
    version_prefix = b'\x00'
    # pay to pubkey hash
    if pubkey_hash_re.match(script_pub_key):
        pubkey_hash = binascii.unhexlify(script_pub_key[6:-4])
    # pay to pubkey
    elif pubkey_re.match(script_pub_key):
        hash1 = hashlib.sha256(binascii.unhexlify(script_pub_key[2:-2]))
        pubkey_hash = ripemd.RIPEMD160(hash1.digest()).digest()
    # pay to script hash
    elif script_hash_re.match(script_pub_key):
        pubkey_hash = binascii.unhexlify(script_pub_key[4:-2])
        version_prefix = b'\x05'
    else:
        return ''

    padded = version_prefix + pubkey_hash
    hash2 = hashlib.sha256(padded)
    hash3 = hashlib.sha256(hash2.digest())
    padded += hash3.digest()[:4]
    return base58.b58encode(padded)


def get_callback_url(request, multisig_address):
    callback_url = settings.ORACLE_API_URL + \
        '/addressnotify/' + multisig_address
    callback_url = ''.join(callback_url.split())
    return callback_url


def evm_deploy(tx_hash):
    print('Deploy tx_hash ' + tx_hash)
    completed = deploy_contract_utils.deploy_contracts(tx_hash)
    if completed:
        print('Deployed Success')
    else:
        print('Deployed Failed')


class Proposes(CsrfExemptMixin, BaseFormView):
    """
    Give the publicKey when invoked.
    """
    http_method_name = ['post']
    form_class = ProposeForm

    def form_valid(self, form):
        # Return public key to Contract-Server
        source_code = form.cleaned_data.get('source_code')
        conditions_string = form.cleaned_data.get('conditions')

        private_key = sha256(get_random_string(64, '0123456789abcdef'))
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)
        p = Proposal(source_code=source_code, public_key=public_key, address=address)
        k = Keystore(public_key=public_key, private_key=private_key)
        p.save()
        k.save()

        if conditions_string:
            conditions = ast.literal_eval(conditions_string)
            for condition in conditions:
                if condition['condition_type'] == 'specifies_balance' or condition['condition_type'] == 'issuance_of_asset_transfer':
                    o = OraclizeContract.objects.get(name=condition['condition_type'])
                    l = ProposalOraclizeLink.objects.create(receiver=condition['receiver_addr'], color=condition[
                                                            'color'], oraclize_contract=o)
                    p.links.add(l)
                else:
                    o = OraclizeContract.objects.get(name=condition['condition_type'])
                    l = ProposalOraclizeLink.objects.create(
                        receiver='0', color='0', oraclize_contract=o)
                    p.links.add(l)

        response = {'public_key': public_key}
        return JsonResponse(response, status=httplib.OK)

    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class NewProposes(CsrfExemptMixin, BaseFormView):
    """
    Give the publicKey when invoked.
    """
    http_method_name = ['post']
    form_class = ProposeForm

    def form_valid(self, form):
        # Return public key to Contract-Server
        # source_code = form.cleaned_data.get('source_code')
        # conditions_string = form.cleaned_data.get('conditions')
        source_code = "empty_source_code"
        private_key = sha256(get_random_string(64, '0123456789abcdef'))
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)
        p = Proposal(source_code=source_code, public_key=public_key, address=address)
        k = Keystore(public_key=public_key, private_key=private_key)
        p.save()
        k.save()

        response = {'public_key': public_key}
        return JsonResponse(response, status=httplib.OK)

    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class Multisig_addr(CsrfExemptMixin, BaseFormView):
    http_method_name = ['post']
    form_class = MultisigAddrFrom

    def form_valid(self, form):
        pubkey = form.cleaned_data.get('pubkey')
        multisig_address = form.cleaned_data.get('multisig_address')

        try:
            p = Proposal.objects.get(public_key=pubkey)
            deploy_contract_utils.make_multisig_address_file(multisig_address)
        except Proposal.DoesNotExist:
            return response_utils.error_response(httplib.BAD_REQUEST, "Cannot find proposal with this pubkey.")
        except Exception as e:
            return response_utils.error_response(httplib.INTERNAL_SERVER_ERROR, str(e))

        p.multisig_address = multisig_address
        p.save()

        callback_url = get_callback_url(self.request, multisig_address)
        subscription_id = ""
        created_time = ""

        try:
            subscription_id, created_time = gcoincore.subscribe_address_notification(
                address=multisig_address,
                callback_url=callback_url)
        except Exception as e:
            return response_utils.error_response(httplib.INTERNAL_SERVER_ERROR, str(e))

        response = {
            'status': 'success'
        }
        return JsonResponse(response)

    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class Sign(CsrfExemptMixin, BaseFormView):
    http_method_name = ['post']
    form_class = SignForm

    def form_valid(self, form):
        tx = form.cleaned_data['raw_tx']
        script = form.cleaned_data['script']
        input_index = form.cleaned_data['input_index']
        sender_address = form.cleaned_data['sender_address']
        multisig_address = form.cleaned_data['multisig_address']
        amount = form.cleaned_data['amount']
        color_id = form.cleaned_data['color']

        user_evm_address = wallet_address_to_evm(sender_address)
        # need to check contract result before sign Tx
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][user_evm_address]
                if not account:
                    response = {'error': 'Address not found'}
                    return JsonResponse(response, status=httplib.BAD_REQUEST)
                account_amount = account['balance'][color_id]
        except IOError:
            # Log
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        if int(account_amount) < int(amount):
            response = {'error': 'insufficient funds'}
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        # signature = connection.signrawtransaction(tx)
        p = Proposal.objects.get(multisig_address=multisig_address)
        private_key = Keystore.objects.get(public_key=p.public_key).private_key

        signature = multisign(tx, input_index, script, private_key)
        # return only signature hex
        response = {'signature': signature}

        return JsonResponse(response, status=httplib.OK)

    def form_invalid(self, form):
        response = {'error': form.errors}

        return JsonResponse(response, status=httplib.BAD_REQUEST)


class SignNew(CsrfExemptMixin, BaseFormView):
    http_method_name = ['post']
    form_class = SignForm

    def form_valid(self, form):
        tx = form.cleaned_data['raw_tx']
        script = form.cleaned_data['script']
        input_index = form.cleaned_data['input_index']
        multisig_address = form.cleaned_data['multisig_address']

        decoded_tx = deserialize(tx)
        try:
            old_utxo, all_utxos = self.get_oldest_utxo(multisig_address)
            deploy_contract_utils.deploy_contracts(old_utxo[0])
        except:
            response = {'error': 'Do not contain oldest tx'}
            return JsonResponse(response, status=httplib.NOT_FOUND)
        contained_old = False

        for vin in decoded_tx['ins']:
            vin = (vin['outpoint']['hash'], vin['outpoint']['index'])
            if vin not in all_utxos:
                response = {'error': 'vins contains wrong utxo'}
                return JsonResponse(response, status=httplib.NOT_FOUND)

            if vin == old_utxo:
                contained_old = True
        if not contained_old:
            response = {'error': 'vins do not contain oldest tx'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        # need to check contract result before sign Tx
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                for vout in decoded_tx['outs']:
                    output_address = addressFromScriptPubKey(vout['script'])
                    output_color = vout['color']
                    # convert to diqi
                    output_value = vout['value'] / 100000000
                    if output_address == multisig_address:
                        continue
                    output_evm_address = wallet_address_to_evm(output_address)
                    account = None
                    if output_evm_address in content['accounts']:
                        account = content['accounts'][output_evm_address]
                    if not account:
                        response = {'error': 'Address not found'}
                        return JsonResponse(response, status=httplib.NOT_FOUND)
                    amount = account['balance'].get(str(output_color))
                    if not amount:
                        response = {'error': 'insufficient funds'}
                        return JsonResponse(response, status=httplib.BAD_REQUEST)
                    if int(amount) < int(output_value):
                        response = {'error': 'insufficient funds'}
                        return JsonResponse(response, status=httplib.BAD_REQUEST)
        except IOError:
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)

        # signature = connection.signrawtransaction(tx)
        p = Proposal.objects.get(multisig_address=multisig_address)
        private_key = Keystore.objects.get(public_key=p.public_key).private_key

        signature = multisign(tx, input_index, script, private_key)
        # return only signature hex
        response = {'signature': signature}

        return JsonResponse(response, status=httplib.OK)

    def form_invalid(self, form):
        response = {'error': form.errors}

        return JsonResponse(response, status=httplib.BAD_REQUEST)

    def get_oldest_utxo(self, multisig_address):
        utxos = gcoincore.get_address_utxos(multisig_address)
        block_time = None
        old_utxo = None
        all_utxos = []
        for utxo in utxos:
            all_utxos.append((utxo['txid'], utxo['vout']))
            raw_tx = gcoincore.get_tx(utxo['txid'])
            try:
                block = gcoincore.get_block_by_hash(raw_tx['blockhash'])
                if block_time is None or int(block['time']) < block_time:
                    old_utxo = utxo
                    block_time = int(block['time'])
            except:
                print('unconfirmed')

        old_utxo = (old_utxo['txid'], old_utxo['vout'])
        return old_utxo, all_utxos


class ProposalList(APIView):

    def get(self, request):
        proposals = Proposal.objects.all()
        serializer = ProposalSerializer(proposals, many=True)
        response = {'proposal': serializer.data}
        return HttpResponse(json.dumps(response), content_type="application/json")


class GetBalance(ProcessFormView):
    http_method_name = ['get']

    def get(self, request, multisig_address, address):
        user_evm_address = wallet_address_to_evm(address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][user_evm_address]
                amount = account['balance']
                response = amount
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {}
            return JsonResponse(response, status=httplib.OK)


class GetStorage(APIView):

    def get(self, request, multisig_address):
        contract_evm_address = wallet_address_to_evm(multisig_address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][contract_evm_address]
                storage = account['storage']
                response = storage
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {}
            return JsonResponse(response, status=httplib.OK)


class DumpContractState(APIView):
    """
    Get contract state file
    """

    def get(self, request, multisig_address):
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                response = content
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {}
            return JsonResponse(response, status=httplib.OK)


class CheckContractCode(APIView):
    http_method_name = ['get']

    def get(self, request, multisig_address):
        contract_evm_address = wallet_address_to_evm(multisig_address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][contract_evm_address]
                code = account['code']
                response = {'code': code}
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {'status': 'Contract code not found'}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)


class NewTxNotified(CsrfExemptMixin, ProcessFormView):
    http_method_name = ['post']

    def post(self, request, *args, **kwargs):
        tx_hash = self.kwargs['tx_hash']
        response = {"message":'Received notify with tx_hash ' + tx_hash}
        print('Received notify with tx_hash ' + tx_hash)

        t = threading.Thread(target = evm_deploy, args=[tx_hash,])
        t.start()
        return JsonResponse(response, status=httplib.OK)


class AddressNotified(APIView):
    def post(self, request, *args, **kwargs):
        """ Receive Address Notification From OSS

        Args:
            multisig_address: multisig_address for contracts
            tx_hash: the latest tx_hash of multisig_address
            subscription_id: subscription_id of OSS
            notification_id: notification_id of subscription_id

        Returns:
            status: State-Update is failed or completed
        """
        multisig_address = self.kwargs['multisig_address']
        form = NotifyForm(request.POST)
        tx_hash = ""

        if form.is_valid():
            tx_hash = form.cleaned_data['tx_hash']
        else:
            return response_utils.error_response(httplib.NOT_ACCEPTABLE, form.errors)

        response = {"message":'Received notify with address ' + multisig_address +', tx_hash '+ tx_hash}
        print('Received notify with address ' + multisig_address +', tx_hash '+ tx_hash)
        t = threading.Thread(target = evm_deploy, args=[tx_hash,])
        t.start()
        return JsonResponse(response, status=httplib.OK)


class OraclizeContractInterface(APIView):

    def get(self, request, contract_name):
        response = {}

        obj = OraclizeContract.objects.get(name=contract_name)
        response = {
            'address': obj.address,
            'interface': obj.interface,
        }
        return JsonResponse(response, status=httplib.OK)
