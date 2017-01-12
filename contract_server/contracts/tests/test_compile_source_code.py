import json

from django.test import TestCase

from contracts.views import Contracts


class ComplieSourceCodeTest(TestCase):

    def test_solidity_comliper(self):
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_binary', 'r') as test_binary_code_file:
            test_binary_code = test_binary_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_abi', 'r') as test_abi_file:
            test_abi = test_abi_file.read().replace('\n', '')

        contract = Contracts()
        compiled_code, interface = contract._compile_code_and_interface(source_code)

        # make interface from test_abi
        test_abi = json.loads(test_abi)
        test_interface = []
        ids = 1
        for func in test_abi:
            try:
                func["id"] = ids
                test_interface.append(func)
                ids = ids + 1
            except:
                pass
        test_interface = json.dumps(test_interface)

        self.assertEqual(test_interface, interface)
        self.assertEqual(compiled_code, test_binary_code)

