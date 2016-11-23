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
    $ cd solidity
    $ cmake3 .
    $ make
