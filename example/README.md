# 合約測試

這份檔案是一個簡單的 wallet client, 目的是用來測試不同合約的功能,

```
.
├── README.md
├── conf.py
├── test/
├── test/test_scripts/                 # 測試合約script
├── test/test_scripts/test_contracts/  # 測試合約solidity code
├── test/test_utils/                   # 測試 utils 功能
├── utils/                             # utility
├── utils/api_helper                   # 呼叫 api 相關
├── utils/apply                        # script 使用apply介面
└── requirements.txt
```

## 如何使用

### 1. 需要的套件

```
pip install ethereum-abi-utils
```

> 如果遇到沒有 `abi-utils` 套件時

### 2. 設定 `conf.py`

- 設定 server 的位址
- 設定預設的 Gcoin private key, public key, address
    - 必須先有地氣幣
```
# Setting for each server
OSS_URL =       "<OSS_URL>"
CONTRACT_URL =  "<CONTRACT_URL>"
ORACLE_URL =    "<ORACLE_URL>"

# Set personal address
owner_address = '<owner_address>'
owner_privkey = '<owner_privkey>'
owner_pubkey  = '<owner_pubkey>'
```

### 3. 測試範例script

位於 `tests/script/` 資料夾下

### 4. 要測試合約的原始碼

位於 `tests/script/test_contracts/` 資料夾下

## Script 範例

### `tests/test_scripts/test_multi_contracts_script` includes:
1. Deploy multisig contract
2. Transaction call  multisig contract function
3. Constant function call -> multisig contract
4. Deploy SubContract
5. Transaction call  SubContract function

### `tests/test_scripts/test_event_script` includes:
1. Deploy multisig contract
2. Thread 1: watch events at **multisig contract** and wait for callback
3. Thread 2: transaction call function -> **multisig contract**
4. Thread 2 would trigger the watched event, then event will callback in Thread 1.

### `tests/test_scripts/test_bytes32_passer_script` includes:
1. Deploy multisig contract (Descriptor)
1. Deploy SubContract (Bytes32Passer)
2. Thread 1: watch events at **SubContract** and wait for callback
3. Thread 2:  transaction call function -> **SubContract**
4.  Thread 2 would trigger the watched event, then event will callback in Thread 1.

### 測試個別script
```sh
$ cd example
$ python tests/test_scripts/test_multi_contracts_script.py
$ python tests/test_scripts/test_event_script.py
$ python tests/test_scripts/test_bytes32_passer_script.py
```

---

# Apply Function

## For Multisig Address Contract
### apply_deploy_contract
- input: contract_file, contract_name
- output: contract_address

### apply_deploy_sub_contract
- input: contract_file, contract_name, multisig_address, deploy_address, source_code, from_address, privkey
- no output

### apply_get_contract_status:
- print multisig contract address
- input: contract_address
- no output

### apply_transaction_call_contract
- input: contract_address, function_name, function_inputs, from_address, privkey
- no output

## For SubContract
### apply_transaction_call_sub_contract
- input: contract_address, deploy_address, function_name, function_inputs, from_address, privkey
- no output

### apply_call_constant_contract
- input: contract_address, function_name, function_inputs, from_address
- output: function_outputs

### apply_call_constant_sub_contract
- input: contract_address, function_name, function_inputs, from_address
- output: function_outputs

## For Event
### apply_watch_event
- input: contract_address, key, oracle_url, callback_url, receiver_address
  - For testing Multisig Contract, set receiver_address = ''
  - For testing SubContract, set receiver_address = deploy_address
- output: event
