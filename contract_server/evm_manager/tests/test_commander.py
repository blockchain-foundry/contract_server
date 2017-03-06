import logging
from django.test import TestCase
from evm_manager.commander import Commander

logger = logging.getLogger(__name__)


class CommanderTestCase(TestCase):

    def setUp(self):
        self.commander = Commander()

    def test_buildCommand(self):
        """
        with open('./evm_manager/test_files/test_deploy_attribute_lookup_contract_tx.json', 'r') as test_tx_file:
            test_tx = test_tx_file.read().replace('\n', '')

        test_tx = json.loads(test_tx)

        sender_address, multisig_address, bytecode, value, is_deploy, blocktime = get_contracts_info(test_tx)
        value = "\'" + str(value) + "\'"
        blocktime = "\'" + str(blocktime) + "\'"


        # deploy
        command = self.commander.buildCommand(True, sender_address, multisig_address, bytecode, value, blocktime)
        print(command)
        self.commander.execute(command)

        with open('./evm_manager/test_files/test_called_attribute_lookup_contract_tx.json', 'r') as test_tx_file:
            test_tx = test_tx_file.read().replace('\n', '')
        """
        """
        deployed contract: test_called_attribute_lookup_contract_tx.json

        orgin contract content
        pragma solidity ^0.4.2;

        contract AttributeLookup {
          event AttributesSet(address indexed _sender, uint _timestamp);

          mapping(int => int) public attributeLookupMap;

          function setAttributes(int index, int value) {
            attributeLookupMap[index] = value;
            AttributesSet(msg.sender, now);
          }

          function getAttributes(int index) constant returns(int) {
            return attributeLookupMap[index];
          }
        }
        """
        """
        test_tx = json.loads(test_tx)

        sender_address, multisig_address, bytecode, value, is_deploy, blocktime = get_contracts_info(test_tx)
        value = "\'" + str(value) + "\'"
        blocktime = "\'" + str(blocktime) + "\'"

        self.assertEqual(sender_address, '1EGK23U1LXWpcC1yjUHoFv84WDws9BkvRs')
        self.assertEqual(blocktime, '\'1483425584\'')

        # call function
        command = self.commander.buildCommand(False, sender_address, multisig_address, bytecode, value, blocktime)
        """
