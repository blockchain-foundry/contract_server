from app.models import Proposal
from app.oraclize import deployOraclizeContract, set_var_oraclize_contract
from gcoinbackend import core as gcoincore


def deploy_oraclize_contract(multisig_address):
    p = Proposal.objects.get(multisig_address=multisig_address)
    links = p.links.all()
    for link in links:
        contract = link.oraclize_contract
        deployOraclizeContract(multisig_address, contract.address, contract.byte_code)


def set_var_to_oraclize_contract(multisig_address, tx_info):
    p = Proposal.objects.get(multisig_address=multisig_address)
    links = p.links.all()
    for link in links:
        info = get_oraclize_info(link, tx_info)
        contract = link.oraclize_contract
        set_var_oraclize_contract(multisig_address, contract.address, info)


def get_oraclize_info(link, tx_info):
    contract = link.oraclize_contract
    blockhash = tx_info['blockhash']
    block = get_block_info(blockhash)
    if contract.name == 'start_of_block' or contract.name == 'end_of_block':
        return block['height']
    elif contract.name == 'block_confirm_number':
        blocks = get_latest_blocks()
        latest_block_number = blocks[0]['height']
        block_confirmation_count = str(int(latest_block_number) - int(block['height']))
        return block_confirmation_count
    elif contract.name == 'trand_confirm_number':
        return str(tx_info['confirmations'])
    elif contract.name == 'specifies_balance':
        balance = get_address_balance(link.receiver, link.color)
        return balance[link.color]
    elif contract.name == 'issuance_of_asset_transfer':
        license_info = get_license_info(link.color)
        if license_info['owner'] == link.receiver:
            return '1'
        else:
            return '0'
    else:
        print('Exception OC')


def get_block_info(block_hash):
    block = gcoincore.get_block_by_hash(block_hash)
    return block


def get_latest_blocks():
    blocks = gcoincore.get_latest_blocks()
    return blocks


def get_sender_addr(txid, vout):
    try:
        tx = gcoincore.get_tx(txid)
        return tx['vout'][vout]['scriptPubKey']['addresses'][0]
    except:
        print("[ERROR] getting sender address")


def get_address_balance(address, color):
    balance = gcoincore.get_address_balance(address, color)
    return balance


def get_license_info(color):
    info = gcoincore.get_license_info(color)
    return info
