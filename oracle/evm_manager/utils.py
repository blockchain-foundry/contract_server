try:
    from Crypto.Hash import keccak

    def sha3_256(x):
        return keccak.new(digest_bits=256, data=x).digest()
except:
    import sha3 as _sha3

    def sha3_256(x):
        return _sha3.keccak_256(x).digest()
import os
import json
import base58
import rlp
from rlp.utils import decode_hex, ascii_chr
from binascii import hexlify
from gcoin import hash160


def is_numeric(x):
    return isinstance(x, int)


def to_string(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return bytes(value, 'utf-8')
    if isinstance(value, int):
        return bytes(str(value), 'utf-8')


def wallet_address_to_evm(address):
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address


def get_evm_balance(multisig_address, address):
    contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address

    user_evm_address = wallet_address_to_evm(address)
    try:
        with open(contract_path.format(multisig_address=multisig_address), 'r') as f:
            content = json.load(f)
            account = content['accounts'][user_evm_address]
            amount = account['balance']
            return amount
    except Exception as e:
        print(e)
        return {}


def mk_contract_address(sender, nonce):
    return sha3(rlp.encode([normalize_address(sender), nonce]))[12:]


def normalize_address(x, allow_blank=False):
    if is_numeric(x):
        return int_to_addr(x)
    if allow_blank and x in {'', b''}:
        return b''
    if len(x) in (42, 50) and x[:2] in {'0x', b'0x'}:
        x = x[2:]
    if len(x) in (40, 48):
        x = decode_hex(x)
    if len(x) == 24:
        assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
        x = x[:20]
    if len(x) != 20:
        raise Exception("Invalid address format: %r" % x)
    return x


def int_to_addr(x):
    o = [b''] * 20
    for i in range(20):
        o[19 - i] = ascii_chr(x & 0xff)
        x >>= 8
    return b''.join(o)


sha3_count = [0]


def sha3(seed):
    sha3_count[0] += 1
    return sha3_256(to_string(seed))
