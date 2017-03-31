from contracts.models import Contract
import hashlib
def set_contract_address(multisig_address, contract_address, sender_evm_address, tx):
    nulldata_hex, tx_hash = _get_nulldata_hex_and_hash(tx)
    hash_op_return = hash(nulldata_hex) % (2**31)
    sender_evm_address = sender_evm_address if sender_evm_address[:2] != '0x' else sender_evm_address[2:]
    print(multisig_address)
    c = Contract.objects.filter(
        multisig_address__address=multisig_address,
        sender_evm_address=sender_evm_address,
        hash_op_return=Contract.make_hash_op_return(nulldata_hex)
    )[0]
    print(c.sender_evm_address)
    print(sender_evm_address)
    print(c.hash_op_return)
    print(int(hashlib.sha1(nulldata_hex.encode('utf-8')).hexdigest(), 16) % (2 ** 31))
    c.contract_address = contract_address
    c.tx_hash_init = tx_hash
    c.is_deployed = True
    c.save()

def _get_nulldata_hex_and_hash(tx):
    for out in tx['vout']:
        if out['color'] == 0:
            print("**********************************")
            print(out['scriptPubKey']['hex'])
            return out['scriptPubKey']['hex'], tx['txid']
    raise Exception('tx_format_error')
