class Command:
    command = ''
    evm_path = ''

    def __init__(self, evm_path):
        self.evm_path = evm_path

    def getCommand(self):
        return self.evm_path + self.command

    def addParam(self, flag, value):
        param = ' ' + flag + ' ' + value
        self.command += param

    def setEvmPath(self, evm_path):
        self.evm_path = evm_path
