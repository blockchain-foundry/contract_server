# States

## Check if state is updated

### Description
Check if specific transaction is executed in VM


> Sample Response of Deploying Contract

```js
{
  "data": {
    "completed": 1,
    "min_completed_needed": 1,
    "total": 1,
    "contract_server_completed": true,
    "contract_address": "3300f5d521dc76f8a5e99d848bc4ae91a209f7c5"
  }
}
```

> Sample Response of Calling Transaction Function

```js
{
  "data": {
    "completed": 1,
    "min_completed_needed": 1,
    "total": 1,
    "contract_server_completed": true
  }
}
```

### HTTP Request
`GET http://<contract_server>/states/checkupdate/:multisig_address/:tx_hash`

### Return Value

Field                     | Type    | Description
------------------------- | ------- | -------------------
completed                 | int     | number of oracles have update the tx_hash
total                     | int     | number of total oracles
min_completed_needed      | int     | number of oracles need to approve according to multisig_address
contract_server_completed | boolean | if the transaction is executed in contract server or not
contract_address          | string  | contract address if the transaction is for deploying contract
