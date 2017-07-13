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
    $ git clone https://github.com/ethereum/solidity.git
    $ cd solidity
    $ git checkout v0.4.7
    $ git submodule update --init --recursive

Need to add boost_1_54_0 in CMakeLists.txt

    $ vim CMakeLists.txt

    set(Boost_INCLUDE_DIR "/usr/local/boost_1_54_0/include")
    set(BOOST_LIBRARYDIR "/usr/local/boost_1_54_0/lib")

Install boost_1_54_0

    $ wget https://cl.ly/i8pU/boost_1_54_0.tar.gz
    $ tar -zxvf boost_1_54_0.tar.gz
    $ cd boost_1_54_0
    $ ./bootstrap.sh --prefix=/usr/local/boost_1_54_0
    $ sudo ./b2 --with=all install
    $ cd ..

Compile solidity

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
