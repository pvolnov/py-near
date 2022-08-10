<h1 align="center">
Near async rpc client
</h1><br>



### JsonProvider

Use JsonProvider to process api calls to NEAR rpc node

`rpc_url` varies by network:

- mainnet https://rpc.mainnet.near.org
- testnet https://rpc.testnet.near.org
- betanet https://rpc.betanet.near.org (may be unstable)
- localnet http://localhost:3030

```python
from async_near.providers import JsonProvider
jp = JsonProvider(rpc_url)

res = jp.view_call(account_id, method_name, args, finality="optimistic")
```


### Signer

Use Signer to sign or request to rpc node
    
```python
from async_near.signer import Signer, KeyPair

key = KeyPair(private_key) # create key pair (private-publish)

signer = Signer(
        signer_account_id,
        key,
    )

signer.sign(message)
```


### Account

Use Account to create and execute transactions
    
```python
from async_near.signer import Signer, KeyPair
from async_near.providers import JsonProvider
from async_near.account import Account


acc = Account(
        JsonProvider("https://rpc.testnet.near.org"),
        Signer(
            "example.testnet",
            KeyPair("ed25519:5sn12Kwd2TZn4A3...7979"),
        ),
    )

await acc.startup()
```

Make contract calls

```python

btc_amount = (await acc.view_function("btc_contract_id", "available_btc", {})).result


await acc.function_call(
        "btc_contract_id",
        "ft_transfer_call",
        {"target_btc_address": "..."},
    )
```




# License

This repository is distributed under the terms of both the MIT license and the Apache License (Version 2.0). See LICENSE and LICENSE-APACHE for details.