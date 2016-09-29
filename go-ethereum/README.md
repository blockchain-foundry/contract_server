因為Gcoin EVM是由Ethereum EVM增修而來，此資料夾(Smart-Contract)必須和你安裝的Ethereum放在不同的資料夾。
安裝官方的Ethereum照1的步驟，已安裝過Ethereum請跳到步驟2安裝Gcoin EVM。

## 1.Building the source (Ethereum)

For prerequisites and detailed build instructions please read the
[Installation Instructions](https://github.com/ethereum/go-ethereum/wiki/Building-Ethereum)
on the wiki.

Building geth requires both a Go and a C compiler.
You can install them using your favourite package manager.
Once the dependencies are installed, run

    make geth

or, to build the full suite of utilities:

    make all

## 2.Building the source (Gcoin EVM)

假設已經安裝過必須的套件或程式如Go，如未安裝，請到步驟1的連結安裝。確認後直接執行

    make evm

## Executable

| Command    | Description |
|:----------:|-------------|
| `evm` | Developer utility version of the EVM (Ethereum Virtual Machine) that is capable of running bytecode snippets within a configurable environment and execution mode. Its purpose is to allow insolated, fine graned debugging of EVM opcodes (e.g. `evm --code 60ff60ff --debug`). |

##Flags
| Command    | Description |
|:----------:|-------------|
| `--dump` | 將evm執行後的結果(state)輸出至standard output |
| `--write [filename]` | 將evm執行後的結果(state)寫入檔案 |
| `--read [filename]` | 從檔案讀取state |
| `--sender [address]` | |
| `--receiver [address]` | |
| `--deploy` | 若要deploy一個新的contract，要加這個flag才會存下正確的code |
| `--fund '{"[color]":"[value]"}' ` | 生出指定顏色和數量的coin給sender；測試可用 |
| `--code [bytecode]` | contract的bytecode |
| `--value '{"[color]":"[value]"}' ` | 要附加在Transaction的value |
| `--input [code]` | call某一function需要給的code，包含該function的identifier及參數 |
| `--time [time]` | 由Oracle帶入該Transaction所屬的Block的timestamp |
|使用到color和value時請注意單引號和雙引號|


## Usage example

The user [User] trying to deploy the contract at [Adr] with money color [5566] and value [500] and save the state into [MyJson.json]:
```
$sudo ./evm --deploy --sender [User]  --receiver [Adr] --value '{"5566":"500"}' --code [Bytecode] --write [MyJson.json]
```
The sender must have enough balance before deploy the contract: Suppose [User] has $10000 of color X
adding the balance [10000] of color [5566] to the user [User]
```
sudo ./evm --fund '{"5566":"10000"}' --read [MyJson.json] --sender [User] --write [MyJson.json]
```

### Call a function in a contract 

contract example:
```
contract Information{
  ...
  function setWeather(uint today){
    ...
  }
  ...
}
```
#### Keccak256 online
https://emn178.github.io/online-tools/keccak_256.html

take the first 8 bytes of the keccak256 hash of the **setWeather(uint256)**, which is **39b490bd**, appended with arguments(64 bits each, if any).


```
--input 39b490bd00000000000000000000000000000000000000000000000000000020    //setWeather(0x20) == setWeather(32)
```

## Contract example
```js
contract Information{
    uint256 private number;
    address master;
    string asd;
    function Information()
    {
        master = msg.sender;
        number = 0x1fff;
        asd = "ddd";    
    }
    function setWeather(uint today)
    {
        if(msg.sender==master)  number=today;
    }
     function setWeather2(uint today,uint tom)
    {
        if(msg.sender==master)  number=today+1;
        asd="dddd";    

    }
}
```

#### Bytecode
```
 60606040525b33600160006101000a81548173ffffffffffffffffffffffffffffffffffffffff02191690830217905550611fff600060005081905550604060405190810160405280600381526020017f646464000000000000000000000000000000000000000000000000000000000081526020015060026000509080519060200190828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f106100c457805160ff19168380011785556100f5565b828001600101855582156100f5579182015b828111156100f45782518260005055916020019190600101906100d6565b5b5090506101209190610102565b8082111561011c5760008181506000905550600101610102565b5090565b50505b610231806101316000396000f360606040526000357c01000000000000000000000000000000000000000000000000000000009004806339b490bd14610044578063db19622f1461005c57610042565b005b61005a600480803590602001909190505061007d565b005b61007b60048080359060200190919080359060200190919050506100e2565b005b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614156100de57806000600050819055505b5b50565b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16141561014657600182016000600050819055505b604060405190810160405280600481526020017f646464640000000000000000000000000000000000000000000000000000000081526020015060026000509080519060200190828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f106101ce57805160ff19168380011785556101ff565b828001600101855582156101ff579182015b828111156101fe5782518260005055916020019190600101906101e0565b5b50905061022a919061020c565b80821115610226576000818150600090555060010161020c565b5090565b50505b505056
```

#### Transfer Coins
_address_.send(_amount_, _color_);
`msg.sender.send(20, 5566);    //send 20 units of color 5566 coin to msg.sender`

_address_.balance(_color_);
`0xdf1a92bd1607100075c03f0309c53c9b8671b034.balance(5566);    //return the amount of coin 5566 that 0xdf1a92bd1607100075c03f0309c53c9b8671b034 have`

msg.value(_color_);		
`msg.value(5566);    //return the amount of coin 5566 that sent along with this transaction`

## License

The go-ethereum library (i.e. all code outside of the `cmd` directory) is licensed under the
[GNU Lesser General Public License v3.0](http://www.gnu.org/licenses/lgpl-3.0.en.html), also
included in our repository in the `COPYING.LESSER` file.

The go-ethereum binaries (i.e. all code inside of the `cmd` directory) is licensed under the
[GNU General Public License v3.0](http://www.gnu.org/licenses/gpl-3.0.en.html), also included
in our repository in the `COPYING` file.
