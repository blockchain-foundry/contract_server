class SubscribeAddrsssNotificationError(Exception):
    pass


class UnsubscribeAddrsssNotificationError(Exception):
    pass


class GetStateFromOracleError(Exception):
    pass


class WatchCallbackTimeoutError(Exception):
    pass


class WatchIsClosedError(Exception):
    pass


class WatchIsExpiredError(Exception):
    pass


class LogDecodeFailedError(Exception):
    pass


class GlobalSubscriptionIdNotFoundError(Exception):
    pass


class WatchKeyNotFoundError (Exception):
    pass


class ContractNotFoundError (Exception):
    pass


class SubContractNotFoundError (Exception):
    pass
