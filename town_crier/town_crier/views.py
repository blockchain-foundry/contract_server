from django.views.generic.edit import BaseFormView
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.crypto import get_random_string

from rest_framework import status
from rest_framework.views import APIView

import json
import requests
import http.client as httplib

from gcoinapi.client import GcoinAPIClient
from gcoin import *

from .forms import AskForm, CryForm
from .models import Keystore

OSSclient = GcoinAPIClient(settings.OSS_API_URL)

DIQI_COLOR_ID = 1


class Ask(BaseFormView):

    http_method_names = ['post']
    form_class = AskForm

    def make_fee_tx(self, from_address, to_address, amount, color_id):
        raw_tx = OSSclient.prepare_raw_tx(from_address, to_address, amount, color_id)
        return raw_tx

    def form_valid(self, form):
        url = form.cleaned_data['url']
        contract_address = form.cleaned_data['contract_address']
        sender_address = form.cleaned_data['sender_address']
        
        private_key = sha256(get_random_string(64, '0123456789abcdef'))
        address = privtoaddr(private_key)

        k = Keystore(address=address, private_key=private_key, sender_address=sender_address, contract_address=contract_address, url=url)
        k.save()

        raw_tx = self.make_fee_tx(sender_address, address, 2, DIQI_COLOR_ID)

        response = {
            'raw_tx': raw_tx
        }
        return JsonResponse(response, status=httplib.OK)
        

    def form_invalid(self, form):
        response = {
            'error': form.errors
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class Cry(BaseFormView):

    http_method_names = ['post']
    form_class = CryForm

    def make_cry_tx(self, from_address, to_address, op_return, contract_fee):
        raw_tx = OSSclient.deploy_contract_raw_tx(from_address, to_address, op_return, contract_fee)
        return raw_tx

    def get_tx(self, tx_hash):
        tx = OSSclient.get_tx(tx_hash)
        return tx

    def form_valid(self, form):
        signed_tx = form.cleaned_data['signed_tx']

        try:
            tx_hash = OSSclient.send_tx(signed_tx)
        except:
            response = {
                'error': 'invalid raw transaction'
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        tx = self.get_tx(tx_hash)
        address = tx['vout'][0]['scriptPubKey']['addresses'][0]

        try:
            k = Keystore.objects.get(address=address)
            private_key = k.private_key
            url = k.url
            contract_address = k.contract_address
        except Keystore.DoesNotExist:
            response = {
                'error': 'Wrong address, haven\'t asked yet'
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        try:
            r = requests.get(url)
            result = r.text
            op_return = json.dumps({'url': url, 'result': result})
        except:
            response = {
                'error': 'Url not found',
                'url': url
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        try:
            raw_tx = self.make_cry_tx(address, contract_address, op_return, 1)
            raw_tx = signall(raw_tx, private_key)
            tx_hash = OSSclient.send_tx(raw_tx)

            response = {
                'tx_hash': tx_hash,
                'result': result
            }
            return JsonResponse(response, status=httplib.OK)
        except:
            response = {
                'error': 'error'
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)
