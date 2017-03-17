# Tutorial

## Event

`event` 為智能合約中的 keyword，開發者可在合約中 trigger event，並使用 `Events/Watches API` 訂閱 `event`，原因為合約在執行後雖會改變 state，但並不會返回結果，透過 `event` 可將合約觸發後的行為記錄下來存到 log 裡，以得知合約運行的結果。

### 合約中使用 event 範例

```js
pragma solidity ^0.4.0;

contract ClientReceipt {
    event Deposit(
        address indexed _from,
        bytes32 indexed _id,
        uint _value
    );

    function deposit(bytes32 _id) payable {
        Deposit(msg.sender, _id, msg.value);
    }
}
```

在上述合約中，當 `function deposit(bytes32 _id)` 被執行時會 trigger `event Deposit`，EVM 會將`event Deposit` 中所填的參數 (msg.sender, _id, msg.value) 寫入 log 中。

以上述合約為範例，log的格式如下：

```js
{ "logs":
[
	{
		"address":"2e18ebac107d5e602c3bf0ce372f32808315f8ab",
		"topics":[
			"0x19dacbf83c5de6658e14cbf7bcae5c15eca2eedecf1c66fbca928e4d351bea0f",
			"0x0000000000000000000000001cd21750e7fa9cf335afad7ce6c60372467823b0",
			"0x0000000000000000000000000000000000000000000000000000000000000123"
		],
		"data":"0000000000000000000000000000000000000000000000000000000000000000",
		"transactionHash":"0000000000000000000000000000000000000000000000000    000000000000000",
		"transactionIndex":0,
		"blockHash":"0000000000000000000000000000000000000000000000000000000000000000",
		"logIndex":0}
]}
```

1. **topics[0]** 為 event 名稱經過hash後的值
2. **topics[1]~[n]** 為 `indexed` event outputs，例如上述合約的 `_from` 和 `_id` 欄位
3. **data** 中存放 `非indexed` event outputs，例如例如上述合約的 `_value` 欄位

### 使用 `events/watches/` API 訂閱 event
在應用中若想知道 event 所紀錄的資訊，可使用 Contract Server 之 Events/Watches API 訂閱 event，從 EVM log 中取得 event 紀錄。具體的操作範例與步驟如下：

	Step 1. 呼叫 `POST` [CONTRACT_SERVER_URL]/events/watches/ ，等待 Response
	Step 2. 呼叫 API 執行合約中的 function
	Step 3. 接收 Contract Server callback


### Step 1. 呼叫 `POST` [CONTRACT_SERVER_URL]/events/watches/ ，等待 Response
以上述 ClientReceipt event為範例，先送出訂閱 `Deposit event` 的Request


```json
{
    "multisig_address": "32uPTcJcKmpgk57M5VGvHunwyWua4KZcnA",
    "event_name": "Deposit",
    "contract_address": "0000000000000000000000000000000000000111" ,
}
```


<aside class="notice">送出 Request 後 Contract Server 不會立即回覆Response，應用端需等待 Step 3 的Response。</aside>



### Step 2. 呼叫 API 執行合約中的 function
請參考上面章節，呼叫 `function deposit(bytes32 _id)`，`function_inputs` 參數可設為：

```json
{
	"name": "_id",
	"type": "bytes32",
	"value": "0x0000000000000000000000000000000000000000000000000000000000000123"
}
```

### Step 3. 接收 Contract Server callback

若 function 在 Contract Server 中順利執行完，則會收到第一步所執行的 API 之 JSON format Response，範例如下：

```json
{
    "event": {
        "args":
            [
					{"name": "Deposit", "args": [{"name": "_from", "value": "1cd21750e7fa9cf335afad7ce6c60372467823b0", "indexed": "True", "type": "address"}, {"name": "_id", "value": "0x0000000000000000000000000000000000000000000000000000000000000123", "indexed": "True", "type": "bytes32"}, {"name": "_value", "value": 0, "indexed": "False", "type": "uint256"}]}
            ],
        "name": "Deposit"
        }
    "subscription_id": "90d9931e-88cd-458b-96b3-3cea31ae05eb"
}
```

即可由 args 欄位中取得對應的 log output。
