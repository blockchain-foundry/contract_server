# GCoin Smart Contract Server, Oracle Server Environment Setup
## Using virtualenv
To install the required package, you can use

	$ pip install -r requirements.txt

to install packages, but there is one package, gcoin-rpc, need access premission to install, so checkout the first step to install gcoin-rpc, then you can simply use pip install to install the rest packages.

### Install gcoin-rpc
	$ git clone https://github.com/OpenNetworking/gcoin-rpc.git

This requires access permission in OpenNetworking group.

	$ cd gcoin-rpc  
	$ which python // to list where is your python in virtualenv  
	/home/user/PythonWorkspace/django/smart_contract/bin/python // this is example  
	$ /home/user/PythonWorkspace/django/smart_contract/bin/python setup.py build  
	$ /home/user/PythonWorkspace/django/smart_contract/bin/python setup.py install

### Install pygcointools
	$ git clone https://github.com/OpenNetworking/pygcointools.git

This also requires the access permission in OpenNetworking group.

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
