import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(max_retry):
    """
    This decorator retry a function which returns None or raises exception
    """
    def wrapper1(func):
        @wraps(func)
        def wrapper2(*args, **kwargs):
            last_loop = max_retry - 1
            for i in range(max_retry):
                try:
                    logger.debug(func.__name__ + ' retry_count: ' + str(i))
                    ret = func(*args, **kwargs)
                    if ret is not None:
                        return ret
                    elif i == last_loop:
                        logger.debug(func.__name__ + ' reach max_retry and return None')
                except Exception as e:
                    if i == last_loop:
                        logger.debug(func.__name__ + ' reach max_retry and raise exception: ' + str(e))
                        raise e
        return wrapper2
    return wrapper1
