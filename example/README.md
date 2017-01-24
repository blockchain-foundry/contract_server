# 合約測試

這份檔案是一個簡單的 wallet client, 目的是用來測試不同合約的功能, 


```
.
├── README.md
├── conf.py
├── create_wallet_address.py
├── greeter.sol
├── play_contract.py
├── requirements.txt
└── utils.py
```

## 如何使用

### 0. 需要的套件

```
pip install ethereum-abi-utils
```

> 如果遇到沒有 `abi-utils` 套件時

### 1. 設定 `conf.py`

- 設定 server 的位址
- 設定有權限聯盟成員的地址, 要用來發 license 與鑄幣

### 2. 生成可用的 wallet 地址與進行鑄幣

> 這段可以省略，如果你有一個有地氣幣的合約地址, 直接跳 step 3

```python
python create_wallet_address.py
```

### 3. 要測試合約的原始碼

- greeter.sol

### 4. 執行檔

設定

1. 一個有錢的合約地址
2. 設定要測試的合約檔案路徑: `contract_file = 'greeter.sol'`

Main function 包含:

1. 佈署合約函數
2. 測試會改變狀態的合約函數 (transaction call)
3. 測試僅回傳狀態的合約函數 (contant function call)


```python
python play_contract.py
```

## 合約範例

測試合約函數, 需要搭配合約的程式碼, 以下例為例:

- `greet()`: constant function
- `setGreeting(string _newgreeting)`: transaction function call

依據函數帶有參數與否, 自行調整呼叫函數的 `params`


```
contract greeter
{
    address owner;
    string greeting;

    function greeter(string _greeting) public {
        owner = msg.sender;
        greeting = _greeting;
    }

    function greet() constant returns (string) {
        return greeting;
    }

    function setGreeting(string _newgreeting) public {
        greeting = _newgreeting;
    }

    function kill() {
        if (msg.sender == owner)
            suicide(owner);
    }
}
```
