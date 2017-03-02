from django.test import TestCase
from contracts.evm_abi_utils import *


class EvmAbiUtilsTest(TestCase):
    def test_wrap_decoded_data(self):
        # string
        item = {
            "type": "string",
            "value": b'hello world'
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], "hello world")

        # bytes
        item = {
            "type": "bytes",
            "value": b'Uf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12Uf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12'
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], "5566000000000000000000000000001255660000000000000000000000000012")

        # bytes2
        item = {
            "type": "bytes2",
            "value": b'12'
            }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], "12")

        # int
        item = {
            "type": "int256",
            "value": -123
            }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], -123)

        # bool
        item = {
            "type": "bool",
            "value": True
            }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], True)
