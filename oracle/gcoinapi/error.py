
class ConnectionError(Exception):
    pass


class TimeoutError(Exception):
    pass


class GcoinAPIError(Exception):
    pass


class InvalidParameterError(GcoinAPIError):
    pass


class NotFoundError(GcoinAPIError):
    pass


class ServerError(GcoinAPIError):
    pass
