# GCoin Smart Contract Server, Oracle Server Environment Setup

- [Installation Guide for Contract Server, Oracle Server](https://github.com/OpenNetworking/Smart-Contract/wiki)

This requires access permission in OpenNetworking group.

## Install pygcointools
    $ git clone https://github.com/OpenNetworking/pygcointools.git

This also requires the access permission in OpenNetworking group.

## Using build script
To install setup the environment.
    $ ./setup_venv.sh

## Install Evm and Daemon
    $ cd go-ethereum
    $ make evm
    $ make daemon
    $ make caller
### Run Daemon
    in go-ethereum/
    $ ./build/bin/daemon --ipc <ipc file name>
    
    Note that the ipc file path is in go-ethereum/ and will be written in the config file.

## Install Solidity
    $ cd solidity
    $ cmake3 .
    $ make

## Set solc path
    Set environment variable SOLC_BINARY to your solc binary file.
    The solc binary file is at solidity/solc/solc
    It's better setting up in bash.
    
## Set .env Config File
    Set config file in both contract_server/ and oracle/
[Installation Guide for Contract Server, Oracle Server](https://github.com/OpenNetworking/Smart-Contract/wiki)

## In Contract Server

### Add Oracle Server into DB
    cd contract_server/
    $ python manage.py shell
    >>> from oracles.models import Oracle
    >>> oracle = Oracle(name="test server", url="http://localhost:8080")
    >>> oracle.save()
    >>> exit()
    

## Cash Target Address
Each contract has a multisignature address which is the account of the contract. Anyone who participate in the contract can put money into the account.  
  
When a user get the money from the contract, there would be a transaction sending money from contract account to user address.  
  
Remind that the user address need to participate in the contract (either deploy or call function) before it get money from the contract, or the target address from the contract account may be ambiguous.
