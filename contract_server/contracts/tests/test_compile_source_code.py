"""
import json

from django.test import TestCase

from contracts.views import Contracts


class ComplieSourceCodeTest(TestCase):

    def test_solidity_comliper(self):
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_binary', 'r') as test_binary_code_file:
            test_binary_code = test_binary_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_interface', 'r') as test_abi_file:
            test_interface = test_abi_file.read().replace('\n', '')

        contract = Contracts()
        compiled_code, interface = contract._compile_code_and_interface(source_code, 'abc')

        interface_list = json.loads(interface)
        test_interface_list = json.loads(test_interface)

        for i in interface_list:
            found = False
            i_length = len(set(i))
            for test_i in test_interface_list:
                shared_items = set(i) & set(test_i)
                if i_length == len(shared_items):
                    found = True
                    break
            # failed
            if not found:
                self.assertNotEqual(None, None)

        self.assertEqual(compiled_code, test_binary_code)
"""
