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


## Init user
```python
json_provider = JsonProvider("https://rpc.herewallet.app")
acc = Account(
    json_provider,
    Signer(
        "mydev.near",
        KeyPair(
            "ed25519:..."
        ),
    ),
)
await acc.startup()
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



```angular2html
Example

    async def create_and_deploy_contract(
        self, contract_id, public_key, contract_code, initial_balance
    ):
        actions = [
            transactions.create_create_account_action(),
            transactions.create_transfer_action(initial_balance),
            transactions.create_deploy_contract_action(contract_code),
        ] + (
            [transactions.create_full_access_key_action(public_key)]
            if public_key is not None
            else []
        )
        return await self._sign_and_submit_tx(contract_id, actions)

    async def create_deploy_and_init_contract(
        self,
        contract_id,
        public_key,
        contract_code,
        initial_balance,
        args,
        gas=DEFAULT_ATTACHED_GAS,
        init_method_name="new",
    ):
        args = json.dumps(args).encode("utf8")
        actions = [
            transactions.create_create_account_action(),
            transactions.create_transfer_action(initial_balance),
            transactions.create_deploy_contract_action(contract_code),
            transactions.create_function_call_action(init_method_name, args, gas, 0),
        ] + (
            [transactions.create_full_access_key_action(public_key)]
            if public_key is not None
            else []
        )
        return await self._sign_and_submit_tx(contract_id, actions)
```




# License

This repository is distributed under the terms of both the MIT license and the Apache License (Version 2.0). See LICENSE and LICENSE-APACHE for details.