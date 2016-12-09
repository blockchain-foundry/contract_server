class BaseGcoinBackend(object):
    """
    This is the base class for all Gcoin backends. We can inherit this class and
    implement different Gcoin backends.
    """

    """
    Alliance member only
    """
    def mint_color_zero(self, alliance_member_address):
        raise NotImplementedError

    def issue_license(self, alliance_member_address, to_address, color_id, license_info):
        raise NotImplementedError

    """
    Issuer only
    """
    def transfer_license(self, to_address, color_id):
        raise NotImplementedError

    def mint(self, mint_address, amount, color_id):
        raise NotImplementedError

    """
    Normal function
    """
    def get_address_balance(self, address, color_id, min_conf=0):
        raise NotImplementedError

    def send(self, from_address, to_address, amount, color_id, fee_address=None):
        raise NotImplementedError

    def get_tx(self, tx_hash):
        raise NotImplementedError

    def get_block_by_hash(self, block_hash):
        raise NotImplementedError

    def get_latest_blocks(self):
        raise NotImplementedError

    def get_license_info(self, color_id):
        raise NotImplementedError

    def subscribe_tx_notification(self, tx_hash, confirmation_count, callback_url):
        raise NotImplementedError
