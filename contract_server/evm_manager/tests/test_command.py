from django.test import TestCase
from evm_manager.command import Command

class CommandTestCase(TestCase):
    def setUp(self):
        self.command = Command('TEST_EVM_PATH')

    def test_add_param(self):
        self.command.addParam('TEST_FLAG_1', 'TEST_VALUE_1')
        self.command.addParam('TEST_FLAG_2', 'TEST_VALUE_2')
        self.assertEqual(self.command.getCommand(),
            'TEST_EVM_PATH TEST_FLAG_1 TEST_VALUE_1 TEST_FLAG_2 TEST_VALUE_2')

    def test_set_param(self):
        self.command.setEvmPath('TEST_EVM_PATH_2')
        self.assertEqual(self.command.getCommand(),
            'TEST_EVM_PATH_2')
