# GCoin Smart Contract Server, Oracle Server Environment Setup
## Clone gcoin-rpc first

	$ git clone https://github.com/OpenNetworking/gcoin-rpc.git

This requires access permission in OpenNetworking group.

## Install pygcointools
	$ git clone https://github.com/OpenNetworking/pygcointools.git

This also requires the access permission in OpenNetworking group.

## Using build script
To install setup the environment.
	$ ./setup_venv.sh

### Install the rest packages
	$ pip install -r requirements.txt

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
