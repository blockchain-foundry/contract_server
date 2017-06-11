import requests

from . import error


class GcoinAPIClient(object):

    def __init__(self, base_url, verify=False, timeout=5):
        self.base_url = base_url
        self.verify = verify
        self.timeout = timeout

    def request(self, end_point, method, params=None, data=None, json=None, headers=None):
        url = self.base_url + end_point
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                verify=self.verify,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as e:
            raise error.TimeoutError
        except requests.exceptions.ConnectionError as e:
            raise error.ConnectionError
        except Exception as e:
            print(e)

        if response.ok:
            return response
        else:
            self.handle_api_error(response)

    def handle_api_error(self, response):
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

    def send_tx(self, raw_tx):
        end_point = '/base/v1/transaction/send'
        data = {'raw_tx': raw_tx}
        try:
            response = self.request(end_point, 'POST', data=data)
        except Exception as e:
            raise e

        tx_hash = response.json()['tx_id']
        return tx_hash

    def get_tx(self, tx_hash):
        end_point = '/base/v1/transaction/{tx_hash}'.format(tx_hash=tx_hash)
        response = self.request(end_point, 'GET')
        tx = response.json()
        return tx

    def get_txs_by_address(self, address, starting_after, since, tx_type):
        end_point = '/explorer/v1/transactions/address/{address}'.format(address=address)
        params = {}
        if starting_after:
            params['starting_after'] = starting_after
        if since:
            params['since'] = since
        if tx_type:
            params['tx_type'] = tx_type
        params['page_size'] = 200
        response = self.request(end_point, 'GET', params=params)
        page, txs = response.json()['page'], response.json()['txs']
        return page, txs

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

    def prepare_general_raw_tx(self, data):
        end_point = '/base/v1/general-transaction/prepare'
        data = {"tx_info": data}
        response = self.request(end_point, 'POST', json=data)
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def prepare_smartcontract_raw_tx(self, from_address, state_multisig_address, contract_multisig_address, amount, color_id, op_return_data, contract_fee):
        end_point = '/base/v1/general-transaction/prepare'
        tx_info = [{
            'from_address': from_address,
            'to_address': state_multisig_address,
            'color_id': '1',
            'amount': contract_fee,
        }]
        if contract_multisig_address:
            tx_info.append({
                'from_address': from_address,
                'to_address': contract_multisig_address,
                'color_id': color_id,
                'amount': amount,
            })

        data = {
            'tx_info': tx_info,
            #'op_return_data': 'abv',
            'op_return_data': op_return_data,
        }
        try:
            response = self.request(end_point, 'POST', json=data)
        except Exception as e:
            print(str(e))
            raise e
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def deploy_contract_raw_tx(self, from_address, state_multisig_address, op_return_data, contract_fee):
        return self.prepare_smartcontract_raw_tx(from_address, state_multisig_address, None, 0, 0, op_return_data, contract_fee)

    def operate_contract_raw_tx(self, from_address, state_multisig_address, contract_multisig_address, amount, color_id, op_return_data, contract_fee):
        return self.prepare_smartcontract_raw_tx(from_address, state_multisig_address, contract_multisig_address, amount, color_id, op_return_data, contract_fee)

    def get_block_by_hash(self, block_hash):
        end_point = '/explorer/v1/blocks/{block_hash}'.format(block_hash=block_hash)
        response = self.request(end_point, 'GET')
        block = response.json()['block']
        return block

    def subscribe_address_notification(self, address, callback_url, confirmation):
        end_point = '/notification/v1/address/subscription'
        data = {
            'address': address,
            'callback_url': callback_url,
            'confirmation': confirmation
        }
        response = self.request(end_point, 'POST', data=data)
        subscription_id = response.json()['id']
        created_time = response.json()['created_time']
        return subscription_id, created_time

    def unsubscribe_address_notification(self, subscription_id):
        end_point = '/notification/v1/address/subscription/' + subscription_id + '/delete'
        response = self.request(end_point, 'POST')
        deleted = response.json()['deleted']
        deleted_id = response.json()['id']
        return deleted, deleted_id
