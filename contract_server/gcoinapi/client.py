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
        if response.status_code >= 500:
            raise error.ServerError
        elif response.status_code == 400:
            raise error.InvalidParameterError(response.json()['error'])
        elif response.status_code == 404:
            raise error.NotFoundError
        else:
            raise error.GcoinAPIError

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
        try:
            response = self.request(end_point, 'POST', data=data)
        except Exception as e:
            raise e

        tx_hash = response.json()['tx_id']
        return tx_hash

    def prepare_smartcontract_raw_tx(self, from_address, to_address, non_diqi_amount, color_id, op_return, diqi_amount):
        end_point = '/base/v1/smartcontract/prepare'
        data = {
            'from_address': from_address,
            'to_address': to_address,
            'amount': non_diqi_amount,
            'color_id': color_id,
            'code': op_return,
            'contract_fee': diqi_amount,
        }
        response = self.request(end_point, 'POST', data=data)
        raw_tx = response.json()['raw_tx']
        return raw_tx

    def deploy_contract_raw_tx(self, from_address, to_address, compiled_code, contract_fee):
        return self.prepare_smartcontract_raw_tx(from_address, to_address, 0, 0, compiled_code, contract_fee)

    def operate_contract_raw_tx(self, from_address, to_address, amount, color_id, compiled_code, contract_fee):
        if color_id == 1:
            diqi_amount = amount + contract_fee
            non_diqi_amount = 0
            color_id = 0
        else:
            diqi_amount = contract_fee
            non_diqi_amount = amount
        return self.prepare_smartcontract_raw_tx(from_address, to_address, non_diqi_amount, color_id, compiled_code, diqi_amount)
