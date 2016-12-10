import requests

from . import error


class GcoinAPIClient(object):

    def __init__(self, base_url, verify=False, timeout=5):
        self.base_url = base_url
        self.verify = verify
        self.timeout = timeout

    def request(self, end_point, method, params=None, data=None, headers=None):
        url = self.base_url + end_point
        try:
            response = requests.request(
                           method=method,
                           url=url,
                           params=params,
                           data=data,
                           headers=headers,
                           verify=self.verify,
                           timeout=self.timeout,
                       )
        except requests.exceptions.Timeout as e:
            raise error.TimeoutError
        except requests.exceptions.ConnectionError as e:
            raise error.ConnectionError

        if response.ok:
            return response
        else:
            self.handle_api_error(response)

    def handle_api_error(self, response):
        print(response.content)
        if response.status_code >= 500:
            raise error.ServerError
        elif response.status_code == 400:
            raise error.InvalidParameterError(response.json()['error'])
        elif response.status_code == 404:
            raise error.NotFoundError
        else:
            raise error.GcoinAPIError

    def get_address_balance(self, address):
        end_point = '/base/v1/balance/{address}'.format(address=address)
        response = self.request(end_point, 'GET')
        balance = response.json()
        return balance

    def get_license_info(self, color_id):
        end_point = '/base/v1/license/{color_id}'.format(color_id=color_id)
        response = self.request(end_point, 'GET')
        license_info = response.json()
        return license_info

    def prepare_license_tx(self, alliance_member_address, to_address, color_id, license_info):
        end_point = '/base/v1/license/prepare'
        params= {
            'alliance_member_address': alliance_member_address,
            'to_address': to_address,
            'color_id': color_id,
            'name': license_info['name'],
            'description': license_info['description'],
            'upper_limit': license_info['upper_limit'],
            'member_control': license_info['member_control'],
            'metadata_link': license_info['metadata_link']
        }
        response = self.request(end_point, 'GET', params=params)
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def send_license_tx(self, raw_tx):
        end_point = '/base/v1/license/send'
        data = {'raw_tx': raw_tx}
        response = self.request(end_point, 'POST', data=data)
        tx_hash = response.json()['tx_id']
        return tx_hash

    def prepare_mint_tx(self, mint_address, amount, color_id):
        end_point = '/base/v1/mint/prepare'
        params = {
            'mint_address': mint_address,
            'amount': amount,
            'color_id': color_id
        }
        response = self.request(end_point, 'GET', params=params)
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def send_mint_tx(self, raw_tx):
        end_point = '/base/v1/mint/send'
        data = {'raw_tx': raw_tx}
        response = self.request(end_point, 'POST', data=data)
        tx_hash = response.json()['tx_id']
        return tx_hash

    def prepare_raw_tx(self, from_address, to_address, amount, color_id):
        end_point = '/base/v1/transaction/prepare'
        params = {
            'from_address': from_address,
            'to_address': to_address,
            'amount': amount,
            'color_id': color_id
        }
        response = self.request(end_point, 'GET', params=params)
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def send_tx(self, raw_tx):
        end_point = '/base/v1/transaction/send'
        data = {'raw_tx': raw_tx}
        response = self.request(end_point, 'POST', data=data)
        tx_hash = response.json()['tx_id']
        return tx_hash

    def get_block_by_hash(self, block_hash):
        end_point = '/explorer/v1/blocks/{block_hash}'.format(block_hash=block_hash)
        response = self.request(end_point, 'GET')
        block = response.json()['block']
        return block

    def get_tx(self, tx_hash):
        end_point = '/base/v1/transaction/{tx_hash}'.format(tx_hash=tx_hash)
        response = self.request(end_point, 'GET')
        tx = response.json()
        return tx

    def get_txs_by_address(self, address, starting_after, tx_type):
        end_point = '/explorer/v1/transactions/address/{address}'.format(address=address)
        params = {}
        if starting_after:
            params['starting_after'] = starting_after
        if tx_type:
            params['tx_type'] = tx_type
        response = self.request(end_point, 'GET', params=params)
        page, txs = response.json()['page'], response.json()['txs']
        return page, txs

    def get_latest_blocks(self):
        end_point = '/explorer/v1/blocks'
        response = self.request(end_point, 'GET')
        latest_blocks = response.json()['blocks']
        return latest_blocks

    def subscribe_tx_notification(self, tx_hash, confirmation_count, callback_url):
        end_point = '/notification/v1/tx/subscription'
        data = {
            'tx_hash': tx_hash,
            'confirmation_count': confirmation_count,
            'callback_url': callback_url
        }
        response = self.request(end_point, 'POST', data=data)
        subscription = response.json()
        return subscription
