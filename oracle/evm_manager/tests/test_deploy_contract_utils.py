import os
from django.test import TestCase
# from evm_manager import deploy_contract_utils


class DeployContractUtilsTest(TestCase):
    def tearDown(self):
        multisig_address = "test_multisig_address"
        contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../../states/' + multisig_address
        os.remove(contract_path)

    # def test_make_multisig_address_file(self):
    #     multisig_address = "test_multisig_address"
    #     contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../../states/' + multisig_address
    #
    #     self.assertFalse(os.path.exists(contract_path))
    #
    #     result = deploy_contract_utils.make_multisig_address_file(multisig_address)
    #     self.assertTrue(result)
    #     self.assertTrue(os.path.exists(contract_path))
