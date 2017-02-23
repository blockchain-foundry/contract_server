import logging
import os
from subprocess import check_call
from .command import Command
from contract_server.utils import prefixed_wallet_address_to_evm_address

logger = logging.getLogger(__name__)


class Commander:
    def getEvmPath(self):
        '''
        Build EVM command for deployment or calling function
        '''
        evm_path = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
        return evm_path

    def getContractPath(self, multisig_address):
        '''
        Build EVM command for deployment or calling function
        '''
        contract_path = os.path.dirname(os.path.abspath(__file__)) + '/../states/' + multisig_address
        return contract_path

    def buildCommand(self, is_deploy, sender_address, multisig_address, bytecode, value, blocktime, subscription_id='', to_addr=''):
        '''
        Build EVM command for deployment or calling function
        '''
        sender_hex = prefixed_wallet_address_to_evm_address(sender_address)
        contract_path = ''

        if multisig_address == to_addr:
            multisig_hex = prefixed_wallet_address_to_evm_address(multisig_address)
        else:
            multisig_hex = to_addr

        if subscription_id != '':
            contract_path = self.getContractPath(subscription_id)
        else:
            contract_path = self.getContractPath(multisig_address)
        evm_path = self.getEvmPath()

        command = Command(evm_path=evm_path)
        if is_deploy:
            command.addParam('--deploy', '')
        if not is_deploy:
            command.addParam('--read', contract_path)
        command.addParam('--sender', sender_hex)
        command.addParam('--fund', value)
        command.addParam('--value', value)
        command.addParam('--write', contract_path)
        command.addParam('--code', bytecode) if is_deploy else command.addParam('--input', bytecode)
        command.addParam('--receiver', multisig_hex)
        command.addParam('--time', str(blocktime))
        # command.addParam('--dump', '')
        command.addParam('--writelog', contract_path + '_log')

        command_string = command.getCommand()

        return command_string

    def execute(self, command_string):
        '''
        Execute contract on EVM
        '''
        logger.info(command_string)
        check_call(command_string, shell=True)
