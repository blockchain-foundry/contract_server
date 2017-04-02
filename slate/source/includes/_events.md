# Events

## Event Watch
Watch event of specific multisig_address/contract_address.



> Sample Request

```json
{
  "multisig_address": "32uPTcJcKmpgk57M5VGvHunwyWua4KZcnA",
  "event_name": "Deposit",
  "contract_address": "0000000000000000000000000000000000000111",
  "conditions": "[ {"name":"_from", "type": "address", "value": "1cd21750e7fa9cf335afad7ce6c60372467823b0" }]"
}
```


> Sample Response

```js
{
 "data":{
   "event": {
       "args":
           [
         {"name": "Deposit", "args": [{"name": "_from", "value": "1cd21750e7fa9cf335afad7ce6c60372467823b0", "indexed": "True", "type": "address"}, {"name": "_id", "value": "0x0000000000000000000000000000000000000000000000000000000000000123", "indexed": "True", "type": "bytes32"}, {"name": "_value", "value": 0, "indexed": "False", "type": "uint256"}]}
           ],
       "name": "Deposit"
       }
   "watch_id": "2"
 }
}
```

### HTTP Request

`POST http://<CONTRACT_SERVER_URL>/events/watches/`


### Query Parameters

Field            | Type     | Required | Description  
---------------- | -------- | -------- | --------------
multisig_address | string   | T        | multisig address
event_name       | string   | T        | event name
contract_address | string   | T        | contract address
conditions       | array    | F        | conditions of event filter
→ name           | string   | T        | arg name
→ type           | string   | T        | type of value
→ value          | **type** | T        | value


### Return Value
Field           | Type     | Description  
--------------- | -------- | -------------
id              | string   | watch id
args            | array    | event args
→ name          | string   |  arg name
→ type          | string   | type of value
→ value         | **type** | value
