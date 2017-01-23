#!/usr/bin/python
# encoding: utf-8

import requests


# GET
def get(url, payload={}):
    r = requests.get(url, params=payload)
    if r.status_code == requests.codes.ok:
        return r
    else:
        print(r.raise_for_status())


#  POST
def post(url, data={}, headers={}, json={}):
    r = requests.post(url, data=data, headers=headers, json=json)
    if r.status_code == requests.codes.ok:
        return r
    else:
        print(r.raise_for_status())
