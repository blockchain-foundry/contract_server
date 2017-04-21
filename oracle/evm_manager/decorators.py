import logging
import traceback
import os
import json
import time
from functools import wraps
from django.db import transaction
from .models import StateInfo
from threading import Lock
LOCK_POOL_SIZE = 64
LOCKS = [Lock() for i in range(LOCK_POOL_SIZE)]
logger = logging.getLogger(__name__)
RETRY_SLEEP_TIME = 1


def handle_exception(func):
    """
    This decorator catches all exception that thrown by the view_func,
    log the exception and return json format error response instead of a html
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            return False
    return wrapper


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
                    ret = func(*args, **kwargs)
                    if ret is not None:
                        return ret
                    elif i == last_loop:
                        logger.debug(func.__name__ + ' reach max_retry and return None')
                except Exception as e:
                    if i == last_loop:
                        logger.debug(func.__name__ + ' reach max_retry and raise exception: ' + str(e))
                        raise e
                time.sleep(RETRY_SLEEP_TIME)
        return wrapper2
    return wrapper1


def write_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        tx_info, ex_tx_hash, multisig_address = args[0], args[1], args[2]
        tx_hash, _time = tx_info['hash'], tx_info['time']
        contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
        lock = _get_lock(multisig_address)
        with lock:
            state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
            if state.latest_tx_hash == ex_tx_hash:
                with open(contract_path, 'r') as f:
                    ex_content = json.load(f)
                try:
                    with transaction.atomic():
                        func(*args, **kwargs)
                        state.latest_tx_hash = tx_hash
                        state.latest_tx_time = _time
                        state.save()
                except Exception as e:
                    with open(contract_path, 'w') as f:
                        json.dump(ex_content, f, sort_keys=True, indent=4, separators=(',', ': '))
                    raise e
            else:
                logger.debug('Ignored: update ' + tx_hash + ' uncompleted due to previous error or race condition')
    return wrapper


def read_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        tx_info, ex_tx_hash, multisig_address = args[0], args[1], args[2]
        tx_hash = tx_info['hash']
        lock = _get_lock(multisig_address)
        with lock:
            state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
            if state.latest_tx_hash == ex_tx_hash:
                ret = func(*args, **kwargs)
                return ret
            else:
                logger.debug('Ignored: update ' + tx_hash + ' uncompleted due to previous error or race condition')
                return None
    return wrapper


def _get_lock(filename):
    index = abs(hash(str(filename))) % LOCK_POOL_SIZE
    return LOCKS[index]
