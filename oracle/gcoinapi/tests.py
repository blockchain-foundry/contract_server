import json
import re
import unittest

import httpretty
import requests

from .client import GcoinAPIClient
from . import error

base_url = 'http://api.test'

class GcoinAPIClientTest(unittest.TestCase):

    def setUp(self):
        self.client = GcoinAPIClient(base_url)

    @httpretty.activate
    def test_request(self):
        """
        Test GcoinAPIClient's request method will return the requests.Response object when status code is 200
        """
        httpretty.register_uri(
            httpretty.GET,
            re.compile('.*'),
            body='response body',
            status=200
        )

        response = self.client.request('test', 'GET')
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.content, 'response body')

    @httpretty.activate
    def test_handle_api_error(self):
        """
        Test GcoinAPIClient's request method will handle error when status code is not 200
        """
        end_point = '/base/v1/test_endpoint'
        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            responses=[
                httpretty.Response(body='500 response', status=500),
                httpretty.Response(body='404 response', status=404),
                httpretty.Response(body='400 response', status=400),
                httpretty.Response(body='other response', status=409),
            ]
        )

        with self.assertRaises(error.ServerError):
            self.client.request(end_point, 'GET')

        with self.assertRaises(error.NotFoundError):
            self.client.request(end_point, 'GET')

        with self.assertRaises(error.InvalidParameterError):
            self.client.request(end_point, 'GET')

        with self.assertRaises(error.GcoinAPIError):
            self.client.request(end_point, 'GET')

        with self.assertRaises(error.ConnectionError):
            self.client.request('http://notexist.com', 'GET')

    @httpretty.activate
    def test_get_address_balance(self):
        test_address = '1GFRiMpuoruPoEjCHV1cjabXe91VMkRKv2'
        end_point = '/base/v1/balance/{address}'.format(address=test_address)
        fake_get_address_balance_response = {'1': 123.456}

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_get_address_balance_response),
            content_type='application/json',
            status=200
        )

        balance = self.client.get_address_balance(test_address)
        self.assertEqual(balance, fake_get_address_balance_response)

    @httpretty.activate
    def test_get_license_info(self):
        test_color_id = 1
        end_point = '/base/v1/license/{color_id}'.format(color_id=test_color_id)
        fake_get_license_info_response = {
            "member_control": "false",
            "metadata_hash": "0000000000000000000000000000000000000000000000000000000000000123",
            "divisibility": "true",
            "name": "DiQi",
            "mint_schedule": "free",
            "description": "DiQi official",
            "metadata_link": "www.diqi.us",
            "fee_type": "fixed",
            "version": 1,
            "upper_limit": 100000000,
            "fee_collector": "1JwpnfXWxKEQHVDFDuBR3gGkNxEwFwChoP",
            "fee_rate": "0E-8",
            "issuer": "1JwpnfXWxKEQHVDFDuBR3gGkNxEwFwChoP"
        }

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_get_license_info_response),
            content_type='application/json',
            status=200
        )

        license_info = self.client.get_license_info(test_color_id)
        self.assertEqual(license_info, fake_get_license_info_response)

    @httpretty.activate
    def test_prepare_license_tx(self):
        test_alliance_member_address = '1GFRiMpuoruPoEjCHV1cjabXe91VMkRKv2'
        test_to_address = '1JwpnfXWxKEQHVDFDuBR3gGkNxEwFwChoP'
        test_color_id = 1
        test_license_info = {
            'name': 'test license',
            'description': 'This is a test license',
            'color_id': test_color_id,
            'upper_limit': 1000,
            'member_control': False,
            'metadata_link': 'http://test.license.com'
        }
        end_point = '/base/v1/license/prepare'
        fake_prepare_license_tx_response = {
            'raw_tx': 'fake raw tx'
        }

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_prepare_license_tx_response),
            content_type='application/json',
            status=200
        )

        tx_hash = self.client.prepare_license_tx(
                           test_alliance_member_address, test_to_address, test_color_id, test_license_info
                      )
        self.assertEqual(tx_hash, fake_prepare_license_tx_response['raw_tx'])

    @httpretty.activate
    def test_send_license_tx(self):
        test_raw_tx = 'test raw tx'
        end_point = '/base/v1/license/send'
        fake_send_license_tx_response = {
            'tx_id': '427ef5210a77c7fcc432cf293c183ca2bdb1bae1066dfe9a0e0f217f4c5c17f8'
        }

        httpretty.register_uri(
            httpretty.POST,
            base_url + end_point,
            body=json.dumps(fake_send_license_tx_response),
            content_type='application/json',
            status=200
        )

        tx_hash = self.client.send_license_tx(test_raw_tx)
        self.assertEqual(tx_hash, fake_send_license_tx_response['tx_id'])

    @httpretty.activate
    def test_prepare_mint_tx(self):
        test_mint_address = '1JwpnfXWxKEQHVDFDuBR3gGkNxEwFwChoP'
        test_color_id = 10
        test_amount = 123.456
        end_point = '/base/v1/mint/prepare'
        fake_prepare_mint_tx_response = {
            'raw_tx': 'fake raw tx'
        }

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_prepare_mint_tx_response),
            content_type='application/json',
            status=200
        )

        raw_tx = self.client.prepare_mint_tx(test_mint_address, test_amount, test_color_id)
        self.assertEqual(raw_tx, fake_prepare_mint_tx_response['raw_tx'])

    @httpretty.activate
    def test_send_mint_tx(self):
        test_raw_tx = 'test raw tx'
        end_point = '/base/v1/mint/send'
        fake_send_mint_tx_response = {
            'tx_id': '427ef5210a77c7fcc432cf293c183ca2bdb1bae1066dfe9a0e0f217f4c5c17f8'
        }

        httpretty.register_uri(
            httpretty.POST,
            base_url + end_point,
            body=json.dumps(fake_send_mint_tx_response),
            content_type='application/json',
            status=200
        )

        tx_hash = self.client.send_mint_tx(test_raw_tx)
        self.assertEqual(tx_hash, fake_send_mint_tx_response['tx_id'])

    @httpretty.activate
    def test_prepare_raw_tx(self):
        test_from_address = '1GFRiMpuoruPoEjCHV1cjabXe91VMkRKv2'
        test_to_address = '1JwpnfXWxKEQHVDFDuBR3gGkNxEwFwChoP'
        test_amount = 123.456
        test_color_id = 10
        end_point = '/base/v1/transaction/prepare'
        fake_prepare_raw_tx_response = {
            'raw_tx': 'fake raw tx'
        }

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_prepare_raw_tx_response),
            content_type='application/json',
            status=200
        )

        raw_tx = self.client.prepare_raw_tx(test_from_address, test_to_address, test_amount, test_color_id)
        self.assertEqual(raw_tx, fake_prepare_raw_tx_response['raw_tx'])

    @httpretty.activate
    def test_send_tx(self):
        test_raw_tx = 'test raw tx'
        end_point = '/base/v1/transaction/send'
        fake_send_raw_tx_response = {
            'tx_id': '427ef5210a77c7fcc432cf293c183ca2bdb1bae1066dfe9a0e0f217f4c5c17f8'
        }

        httpretty.register_uri(
            httpretty.POST,
            base_url + end_point,
            body=json.dumps(fake_send_raw_tx_response),
            content_type='application/json',
            status=200
        )

        tx_hash = self.client.send_tx(test_raw_tx)
        self.assertEqual(tx_hash, fake_send_raw_tx_response['tx_id'])

    @httpretty.activate
    def test_get_block_by_hash(self):
        test_block_hash = '0000075f2770822d4449ed1b713b979d63092cf19a34873f0a1977ec0e369c0b'
        fake_get_block_by_hash_response = {
            "block": {
                "hash": "0000075f2770822d4449ed1b713b979d63092cf19a34873f0a1977ec0e369c0b",
                "height": "363",
                "previous_block_hash": "00000b5f7c9faf0e84e6af52663c947a81be1f6c7a635b81de4bf8a83ea1dc35",
                "next_blocks": [],
                "merkle_root": "09596e072f6ea84fdd847226bb691b09a69b71b0f55cb54574165e8c91af656a",
                "time": "1468553829",
                "bits": "504365040",
                "nonce": "314755",
                "version": "3",
                "branch": "main",
                "size": "331",
                "chain_work": "381687488",
                "transaction_count": "1",
                "transaction_hashes": [
                    "09596e072f6ea84fdd847226bb691b09a69b71b0f55cb54574165e8c91af656a"
                ]
            }
        }
        end_point = '/explorer/v1/blocks/{block_hash}'.format(block_hash=test_block_hash)

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_get_block_by_hash_response),
            content_type='application/json',
            status=200
        )
        block = self.client.get_block_by_hash(test_block_hash)
        self.assertEqual(block, fake_get_block_by_hash_response['block'])

    @httpretty.activate
    def test_get_tx(self):
        test_tx_hash = '0000075f2770822d4449ed1b713b979d63092cf19a34873f0a1977ec0e369c0b'
        fake_get_tx_response = {
            "tx": {
                "hash": "09596e072f6ea84fdd847226bb691b09a69b71b0f55cb54574165e8c91af656a",
                "block_hash": "0000075f2770822d4449ed1b713b979d63092cf19a34873f0a1977ec0e369c0b",
                "version": "1",
                "locktime": "1468553828",
                "type": "NORMAL",
                "time": "1468553829",
                "vins": [
                    {
                        "tx_id": "668b26a613d26be927461e9d5d117e40adc7118ff0201e63366007111f985c30",
                        "vout": 0,
                        "address": "1BqRyqBK1AHQ55EWiqFXqytMc5R1DP2BZV",
                        "scriptSig": "47304402200e5ccc1e5ec92e041b15ded0ed1de1a7c273ea10759ba58092b09dc743[...]",
                        "sequence": "4294967294"
                    }
                ],
                "vouts": [
                    {
                        "n": "0",
                        "address": "1BqRyqBK1AHQ55EWiqFXqytMc5R1DP2BZV",
                        "scriptPubKey": "210357adc9e9ea9b1919045fb02101e5fb1aa7adb35977656c1be841d0dbb5f87f4aac",
                        "color": "0",
                        "amount": "0"
                    }
                ]
            }
        }
        end_point = '/explorer/v1/transactions/{tx_hash}'.format(tx_hash=test_tx_hash)

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_get_tx_response),
            content_type='application/json',
            status=200
        )
        tx = self.client.get_tx(test_tx_hash)
        self.assertEqual(tx, fake_get_tx_response['tx'])

    @httpretty.activate
    def test_get_latest_blocks(self):
        end_point = '/explorer/v1/blocks'
        fake_get_latest_blocks_response = {
            "blocks": [
                {
                    "hash": "0000075f2770822d4449ed1b713b979d63092cf19a34873f0a1977ec0e369c0b",
                    "height": "363",
                    "previous_block_hash": "00000b5f7c9faf0e84e6af52663c947a81be1f6c7a635b81de4bf8a83ea1dc35",
                    "next_blocks": [],
                    "merkle_root": "09596e072f6ea84fdd847226bb691b09a69b71b0f55cb54574165e8c91af656a",
                    "time": "1468553829",
                    "bits": "504365040",
                    "nonce": "314755",
                    "version": "3",
                    "branch": "main",
                    "size": "331",
                    "chain_work": "381687488",
                    "transaction_count": "1",
                    "transaction_hashes": [
                        "09596e072f6ea84fdd847226bb691b09a69b71b0f55cb54574165e8c91af656a"
                    ]
                },
            ]
        }

        httpretty.register_uri(
            httpretty.GET,
            base_url + end_point,
            body=json.dumps(fake_get_latest_blocks_response),
            content_type='application/json',
            status=200
        )
        blocks = self.client.get_latest_blocks()
        self.assertEqual(blocks, fake_get_latest_blocks_response['blocks'])

