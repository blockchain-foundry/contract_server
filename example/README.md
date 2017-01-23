# Interact with the contract 

### Configuration file 

- conf.py

Basic configuration is included.

### Helper file

- utils.py
- create_wallet_address.py

Helper file to create a address with some token.

### Contract source code 

- greeter.sol

The contract you want to play with.

### Main file

- play_contract.py

A tool for deploying and interacting with the contract.

# Usage

1. Modifty `conf.py` to add servers' IPs
2. `greeter.sol` is the default contract or you can create a new one
3. Execute the `play_contract.py` to run your contract
  - At the beginning of the file, there are some settings for your deployment.
  - Modifty the main function to test the function you would like to test.

```python
$ python play_contract.py
```
