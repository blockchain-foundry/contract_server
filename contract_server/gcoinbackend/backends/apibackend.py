import decimal

from django.conf import settings

from gcoin import signall
from gcoinapi.client import GcoinAPIClient
from gcoinapi.error import GcoinAPIError, InvalidParameterError, NotFoundError
from gcoinbackend import exceptions

from .base import BaseGcoinBackend

gcoinbackend_settings = getattr(settings, 'GCOIN_BACKEND_SETTINGS')


class KeyStore(object):

    # TODO: provide private key here
    def get_privkey(self, address):
        return None


class GcoinAPIBackend(BaseGcoinBackend):
    """
    Use GcoinAPIClient to implement GcoinAPIBackend
    """

    def __init__(self, client=None, key_store=None):
        self.client = client or GcoinAPIClient(gcoinbackend_settings['BASE_URL'])

        # TODO: key_store is not used now
        if key_store:
            self.key_store = key_store
        else:
            self.key_store = KeyStore()

    """
    Alliance member only
    """

    def mint_color_zero(self, alliance_member_address):
        return self.mint(
            mint_address=alliance_member_address,
            amount=decimal.Decimal('1'),
            color_id=0
        )

    def issue_license(self, alliance_member_address, to_address, color_id, license_info):
        raw_tx = self.client.prepare_license_tx(
            alliance_member_address=alliance_member_address,
            to_address=to_address,
            color_id=color_id,
            license_info=license_info
        )
        privkey = self.key_store.get_privkey(alliance_member_address)
        signed_tx = signall(str(raw_tx), privkey)
        tx_hash = self.client.send_license_tx(signed_tx)
        return tx_hash

    """
    Issuer only
    """

    def transfer_license(self, to_address, color_id):
        raise NotImplementedError

    def mint(self, mint_address, amount, color_id):
        raw_tx = self.client.prepare_mint_tx(
            mint_address=mint_address,
            amount=amount,
            color_id=color_id
        )
        privkey = self.key_store.get_privkey(mint_address)
        signed_tx = signall(str(raw_tx), privkey)
        tx_hash = self.client.send_mint_tx(signed_tx)
        return tx_hash

    """
    Normal function
    """

    def get_address_balance(self, address, color_id=None, min_conf=0):
        balance = self.client.get_address_balance(address)

        if color_id:
            return {color_id: balance.get(color_id, decimal.Decimal('0'))}
        else:
            return balance

    def send(self, from_address, to_address, amount, color_id):
        try:
            raw_tx = self.client.prepare_raw_tx(
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                color_id=color_id
            )
        except InvalidParameterError as e:
            self._handle_invalid_parameter(e)

        privkey = self.key_store.get_privkey(from_address)

        # raw_tx is unicode need to tranform to str
        signed_tx = signall(str(raw_tx), privkey)

        tx_hash = self.client.send_tx(signed_tx)
        return tx_hash

    def send_tx(self, signed_tx):
        return self.client.send_tx(signed_tx)

    def prepare_general_raw_tx(self, data):
        return self.client.prepare_general_raw_tx(data)

    def get_tx(self, tx_hash):
        return self.client.get_tx(tx_hash)

    def get_txs_by_address(self, address, starting_after=None, since=None, tx_type=None):
        page, txs = self.client.get_txs_by_address(address, starting_after, since, tx_type)
        response = {
            'page': page,
            'txs': txs
        }
        return response

    def get_block_by_hash(self, block_hash):
        return self.client.get_block_by_hash(block_hash)

    def get_latest_blocks(self):
        return self.client.get_latest_blocks()

    def get_license_info(self, color_id):
        try:
            return self.client.get_license_info(color_id)
        except NotFoundError:
            raise exceptions.LicenseNotFound

    def subscribe_tx_notification(self, tx_hash, confirmation_count, callback_url):
        try:
            return self.client.subscribe_tx_notification(tx_hash, confirmation_count, callback_url)
        except GcoinAPIError:
            raise exceptions.SubscribeTxNotificationFail

    def _handle_invalid_parameter(self, e):
        if e.message == 'insufficient funds':
            raise exceptions.InsufficientFunds
        elif e.message == 'insufficient fee':
            raise exceptions.InsufficientFee
        elif e.message == '`color_id` should be greater than or equal to 0':
            raise exceptions.InvalidColor
        elif e.message == '`color_id` should be less than or equal to 4294967295':
            raise exceptions.InvalidColor
        raise e

    def send_contract_tx(self, from_address, raw_tx):
        privkey = self.key_store.get_privkey(from_address)
        signed_tx = signall(str(raw_tx), privkey)
        tx_hash = self.client.send_tx(signed_tx)
        return tx_hash

    def send_cashout_tx(self, signed_tx, oracles=None):
        tx_hash = self.client.send_tx(signed_tx)

        # subscribe tx notifiaction
        if oracles is not None:
            for oracle in oracles:
                callback_url = oracle + "/notify/" + tx_hash
                self.subscribe_tx_notification(tx_hash, 1, callback_url)
        return tx_hash
