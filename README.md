# GCoin Smart Contract Server, Oracle Server Environment Setup

- [Installation Guide for Contract Server, Oracle Server](https://github.com/OpenNetworking/Smart-Contract/wiki)

## Clone gcoin-rpc first

	$ git clone https://github.com/OpenNetworking/gcoin-rpc.git

This requires access permission in OpenNetworking group.

## Install pygcointools
	$ git clone https://github.com/OpenNetworking/pygcointools.git

This also requires the access permission in OpenNetworking group.

## Using build script
To install setup the environment.
	$ ./setup_venv.sh

## Install GCoin
Please refer to [Gcoin github](https://github.com/OpenNetworking/gcoin-community)

### Add GCoin config file
After building gcoin, run

	$ ./src/gcoind -daemon

and you'll get **rpcuser**, **rpcpassword**.

	$ mkdir ~/.gcoin
	$ vim ~/.gcoin/gcoin.conf

	rpcuser=gcoinrpc
	rpcpassword=D1ciXaD7Hs4j3awZJrfJv7T9cQ6eZRWULWG4LCKLUF1m
	rpcport=9999
	rpcallowip=127.0.0.1/0
	port=12321

	// save and leave
    // every one need to have own port and rpcport
## Install Evm
    $ cd go-ethereum
    $ make evm

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

## Install py-solc 
    $ source env/bin/activate
    $ pip install py-solc

# Set solc path
    Set environment variable SOLC_BINARY to your solc binary file
    It's better setting up in bash
    
