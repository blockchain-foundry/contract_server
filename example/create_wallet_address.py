#!/usr/bin/python
# encoding: utf-8

import conf

from gcoin import signall
from utils import get, post

# url setting
oss_url = conf.OSS_URL
contract_url = conf.CONTRACT_URL
oracle_url = conf.ORACLE_URL

# alliance
alliance_addr = conf.ALLIANCE_ADDRESS
alliance_privkey = conf.ALLIANCE_PRIVKEY
alliance_pubkey = conf.ALLIANCE_PUBKEY

# alliance member
alliance_member_address = '1BykHSXsmhzKYX2pNQGSdToU9uSNLzq4Db'

license_user_address = '1AmwJRn9YVw9kWtryt2DKPC38DcB3nURSx'
license_user_privkey = 'KxB7cmypsXFweU8AjcsM7qJK1hC1bX8wmsDpdwDkT6XEq1EkoCRk'
license_user_pubkey = '03da1ff0041a1073634d0cc48d4d8e6fc7c63791da63815545c27ef826b666fb8d'

bonus_user_address = '14UeDhNQWCprVdFWfUoFNQwJ9fvh4kLvvL'
bonus_user_privkey = 'KyNBNdEzvVHyFVYcTAdBmZTd9dMkpXJPT54mPnWfQedTvRDy4B6Y'
bonus_user_pubkey = '02c37ee4139e22fb6b234f5a1e92d964805c82196fcd895f88553503f742e51e86'


# mint
# 1. prepare mint tx
# 2. sign mint tx
# 3. broadcast mint tx
def mint(color_id, mint_amount, mint_pubkey, mint_privkey):
    url = oss_url + 'base/v1/mint/prepare'
    # print(url)
    data = {
        'mint_pubkey': mint_pubkey,
        'color_id': color_id,
        'amount': mint_amount,
    }
    r = get(url, data)
    r_json = r.json()
    raw_tx = r_json['raw_tx']
    # print(raw_tx)

    signed_tx = signall(raw_tx, mint_privkey)
    # print(signed_tx)

    url = oss_url + 'base/v1/mint/send'
    # print(url)
    data = {
        'raw_tx': signed_tx,
    }
    r = post(url, data)
    # r_json = r.json()
    # tx_id = r_json['tx_id']
    # print('tx_id: {0}'.format(tx_id))
    return True


# Get license
# 1. prepare license tx
# 2. sign license tx
# 3. broadcast license tx
def getLicense(alliance_member_address, color_id, name, to_address,
               alliance_pubkey, alliance_privkey):
    url = oss_url + 'base/v1/license/prepare'
    # print(url)
    data = {
        'alliance_member_address': alliance_member_address,
        'color_id': color_id,
        'name': name,
        'description': 'test',
        'member_control': 'false',
        'metadata_link': 'http://www.google.com/',
        'to_address': to_address,
    }
    r = get(url, data)
    r_json = r.json()
    raw_tx = r_json['raw_tx']
    # print(raw_tx)

    signed_tx = signall(raw_tx, alliance_privkey)
    # print(signed_tx)

    url = oss_url + 'base/v1/license/send'
    # print(url)
    data = {
        'raw_tx': signed_tx,
    }
    r = post(url, data)
    # r_json = r.json()
    # tx_id = r_json['tx_id']
    # print('tx_id: {0}'.format(tx_id))
    return True


# Send transaction
# 1. prepare tx
# 2. sign tx
# 3. broadcast tx
def sendTx(from_address, to_address, color_id, amount, from_privkey):
    url = oss_url + 'base/v1/transaction/prepare'
    # print(url)
    data = {
        'from_address': from_address,
        'to_address': to_address,
        'color_id': color_id,
        'amount': amount,
        'op_return_data': '',
    }
    r = get(url, data)
    r_json = r.json()
    raw_tx = r_json['raw_tx']
    # print(raw_tx)

    signed_tx = signall(raw_tx, from_privkey)
    # print(signed_tx)

    url = oss_url + 'base/v1/transaction/send'
    # print(url)
    data = {
        'raw_tx': signed_tx,
    }
    r = post(url, data=data)
    # r_json = r.json()
    # tx_id = r_json['tx_id']
    # print('tx_id: {0}'.format(tx_id))
    return True


if __name__ == '__main__':
    isGetLicense = True

    # mint color 0
    # para: color_id, mint_amount, mint_pubkey, mint_privkey
    for i in range(3):
        r_mint0 = mint(0, 1, alliance_pubkey, alliance_privkey)
        if not r_mint0:
            raise Exception('Mint color 0 failed!')

    # get license for color 1 coin
    if not isGetLicense:
        r_getlicense = getLicense(alliance_member_address, 1, 'vent',
                                  license_user_address,
                                  alliance_pubkey,
                                  alliance_privkey)
        if not r_getlicense:
            raise Exception('Get license failed!')

    # mint color 1
    r_mint1 = mint(1, 1000000, license_user_pubkey, license_user_privkey)
    if not r_mint1:
        raise Exception('Mint color 1 failed!')

    # send money to bonus user
    r_addBonus = sendTx(license_user_address, bonus_user_address, 1, 500000, license_user_privkey)
    if not r_addBonus:
        raise Exception('Refill bonus user failed!')
    print('Now, you can use this address {wallet_address} to create smart contract.'.format(wallet_address=bonus_user_address))
