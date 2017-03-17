# Errors

> Error Response Format

```json
{
  "errors": [
    {
      "code": "<Error Code>",
      "message": "<Error Message>"
    }
  ]
}
```

The Contract Server API uses the `HTTP Status Code` and following `Custom Error Codes`

## A: SmartContract
Error Code | Meaning
---------- | -------
A000       | contract_not_found_error
A001       | function_not_found_error
A002       | multisig_address_not_found_error

## E: Solidity
Error Code | Meaning
---------- | -------
E000       | compiled_error

## F: gcoinapi
Error Code | Meaning
---------- | -------
F000       | no_txs_error
F001       | multisig_error

## Z: others
Error Code | Meaning
---------- | -------
Z000       |  undefined_error
Z001       |  wrong_api_version
Z002       |  form_invalid_error
