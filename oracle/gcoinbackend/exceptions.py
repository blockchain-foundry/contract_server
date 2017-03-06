
class GcoinBackendException(Exception):
    pass


class ConnectionError(Exception):
    pass


class InsufficientFunds(GcoinBackendException):
    pass


class InsufficientFee(GcoinBackendException):
    pass


class InvalidRawTx(GcoinBackendException):
    pass


class InvalidKey(GcoinBackendException):
    pass


class InvalidAddress(GcoinBackendException):
    pass


class InvalidColor(GcoinBackendException):
    pass


class LicenseNotFound(GcoinBackendException):
    pass


class SubscribeTxNotificationFail(GcoinBackendException):
    pass
