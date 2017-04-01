import json
import sha3
from eth_abi import abi
from contracts import evm_abi_utils
from events.models import Watch
import os
import logging

logger = logging.getLogger(__name__)


def _search_watch(logs):
    """Search for matching watches of logs

    Args:
        logs: a dict of logs

    Returns:
        matching_watch_list: a list of matching watch id
    """
    watches = Watch.objects.alive_list()
    watches = [x for x in watches if not x.is_expired]
    matching_watch_list = []
    for log in logs:
        for watch in watches:
            if log['address'] == watch.contract.contract_address and _check_event_interface(watch, log["topics"][0]):
                result = _decode_log(log, watch)
                if _is_conditions_matching(watch.conditions_list, result["args"]):
                    watch.args = json.dumps(result["args"])
                    watch.save()
                    matching_watch_list.append(watch.id)
    return matching_watch_list


def _decode_log(log, watch):
    """Decode log of certain watch

    Args:
        log: dict format log
        watch: Watch object

    Returns:
        args: a dict of args with decoded values
    """
    # Arrange args
    indexed_args = []
    non_indexed_args = []
    for arg in watch.interface["inputs"]:
        if arg['indexed']:
            indexed_args.append(arg)
        else:
            non_indexed_args.append(arg)
    non_indexed_types = []
    for arg in non_indexed_args:
        non_indexed_types.append(arg['type'])

    result = []
    data = log['data']

    decoded_data = abi.decode_abi(non_indexed_types, data)
    indexed_count = 1
    non_indexed_count = 0
    for arg in watch.interface["inputs"]:
        item = {
            "name": arg["name"],
            "type": arg["type"],
            "indexed": arg["indexed"]
        }
        if arg["indexed"]:
            value = abi.decode_single(
                arg["type"],
                log["topics"][indexed_count])
            indexed_count += 1
        else:
            value = decoded_data[non_indexed_count]
            non_indexed_count += 1

        item['value'] = value
        item = evm_abi_utils.wrap_decoded_data(item)
        result.append(item)

    return {"args": result}


def check_watch(tx_hash, multisig_address):
    """Check if log was updated, then process logs to matching watch.args field

    Args:
        tx_hash: transaction hash
        multisig_address: multisig_address of the state file
    Returns:
        matching_watch_list: a list of matching watch id
    """
    logs = ''
    log_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address + "_" + tx_hash + "_log"
    with open(log_path, 'r') as f:
        content_str = f.read().replace('\n', '')
        logger.debug('[Log content]:{}'.format(content_str))
        content = json.loads(content_str)
        logs = content['logs']

    return _search_watch(logs)


def _is_condition_matching(condition, arg):
    if (condition["name"] == arg["name"] and
            condition["type"] == arg["type"] and
            condition["value"] == arg["value"]):
        return True
    elif (
            condition["name"] != arg["name"] or
            condition["type"] != arg["type"]):
        return True
    else:
        return False


def _is_conditions_matching(conditions_list, args):
    for x in conditions_list:
        for y in args:
            if not _is_condition_matching(x, y):
                return False
    return True


def _check_event_interface(watch, topic_0):
    inputs_type = []
    for i in watch.interface["inputs"]:
        inputs_type.append(i["type"])
    event_interface = watch.event_name + "(" + ",".join(inputs_type) + ")"
    k = sha3.keccak_256()
    k.update(event_interface.encode())
    hashed_event_interface = k.hexdigest()
    return topic_0 == "0x" + hashed_event_interface
