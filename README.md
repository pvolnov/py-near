<h1 align="center">
Near async rpc client
</h1><br>

# Welcome to py-near’s documentation!


* [Quick start](quickstart.md)


* [Summary](quickstart.md#summary)


* [Account](account.md)


    * [Quick start](account.md#quick-start)


    * [Documentation](account.md#documentation)


        * [`Account`](account.md#Account)


        * [`get_access_key()`](account.md#get_access_key)


        * [`get_access_key_list()`](account.md#get_access_key_list)


        * [`fetch_state()`](account.md#fetch_state)


        * [`send_money()`](account.md#send_money)


        * [`view_function()`](account.md#view_function)


        * [`function_call()`](account.md#function_call)


        * [`create_account()`](account.md#create_account)


        * [`add_public_key()`](account.md#add_public_key)


        * [`add_full_access_public_key()`](account.md#add_full_access_public_key)


        * [`delete_public_key()`](account.md#delete_public_key)


        * [`deploy_contract()`](account.md#deploy_contract)


        * [`stake()`](account.md#stake)


        * [`get_balance()`](account.md#get_balance)


        * [`phone`](account.md#phone)


        * [`ft`](account.md#ft)


* [Phone number transfer](clients/phone.md)


    * [Quick start](clients/phone.md#quick-start)


    * [Documentation](clients/phone.md#documentation)


        * [`Phone`](clients/phone.md#Phone)


        * [`send_near_to_phone()`](clients/phone.md#send_near_to_phone)


        * [`send_ft_to_phone()`](clients/phone.md#send_ft_to_phone)


        * [`get_ft_transfers()`](clients/phone.md#get_ft_transfers)


        * [`get_near_transfers()`](clients/phone.md#get_near_transfers)


        * [`cancel_near_transaction()`](clients/phone.md#cancel_near_transaction)


        * [`cancel_ft_transaction()`](clients/phone.md#cancel_ft_transaction)


# Quick start

At first you have to import all necessary modules

```python
from pynear.account import Account
```

Then you have to initialize Account

```python
ACCOUNT_ID = "mydev.near"
PRIVATE_KEY = "ed25519:..."

acc = Account(ACCOUNT_ID, PRIVATE_KEY)
```

Next step: check account balance

```python
import asyncio
from pynear.dapps.core import NEAR

async def main():
    await acc.startup()
    print(await acc.get_balance() / NEAR)
    print(await acc.get_balance("bob.near") / NEAR)

asyncio.run(main())
```

Next step: send 2 NEAR to bob.near

```python
transaction = await acc.send_money("bob.near", NEAR * 2)
print(tr.transaction.hash)
print(tr.logs)
```

Next step: send 2 NEAR to bob.near no waiting for transaction confirmation

```python
transaction_hash = await acc.send_money("bob.near", NEAR * 2, nowait=True)
print(transaction_hash)
```

Next step: send 0.1 NEAR by phone number

```python
transaction = await acc.phone.send_near_to_phone("+15626200814", NEAR // 10)
print(tr.transaction.hash)
```

# Summary

```python
from pynear.account import Account
import asyncio
from pynear.dapps.core import NEAR

ACCOUNT_ID = "mydev.near"
PRIVATE_KEY = "ed25519:..."

async def main():
    acc = Account(ACCOUNT_ID, PRIVATE_KEY)

    await acc.startup()
    print(await acc.get_balance() / NEAR)
    print(await acc.get_balance("bob.near") / NEAR)

    transaction = await acc.send_money("bob.near", NEAR * 2)
    print(tr.transaction.hash)
    print(tr.logs)

    transaction = await acc.phone.send_near_to_phone("+15626200911", NEAR // 10)
    print(tr.transaction.hash)

asyncio.run(main())
```

# Account

## Quick start

```python
from pynear.account import Account
import asyncio
from pynear.dapps.core import NEAR

ACCOUNT_ID = "mydev.near"
PRIVATE_KEY = "ed25519:..."

async def main():
    acc = Account(ACCOUNT_ID, PRIVATE_KEY)

    await acc.startup()
    print(await acc.get_balance() / NEAR)
    print(await acc.get_balance("bob.near") / NEAR)

    transaction = await acc.send_money("bob.near", NEAR * 2)
    print(tr.transaction.hash)
    print(tr.logs)

    transaction = await acc.phone.send_near_to_phone("+15626200911", NEAR // 10)
    print(tr.transaction.hash)

asyncio.run(main())
```

## Documentation


### _class_ Account()
> This class implement all blockchain functions for your account

```python
acc = Account(...)
await acc.startup()
```


### get_access_key()
Get access key for current account


* **Returns**

    AccountAccessKey


```python
await acc.get_access_key()
```


### get_access_key_list(account_id=None)
Send fungible token to phone number. Reciver will get sms with link to claim tokens.

Get access key list for account_id, if account_id is None, get access key list for current account


* **Parameters**

    **account_id** – 



* **Returns**

    list of PublicKey


```python
keys = await acc.get_access_key_list()
print(len(keys))
```


### fetch_state(phone)
Fetch state for given account


* **Returns**

    dict


```python
state = await acc.fetch_state()
print(state)
```


### send_money(account_id: str, amount: int, nowait=False)
Send money to account_id


* **Parameters**

    
    * **account_id** – receiver account id


    * **amount** – amount in yoctoNEAR


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.send_money('bob.near', NEAR * 3)
```


### view_function(contract_id: str, method_name: str, args: dict)
Call view function on smart contract. View function is read only function, it can’t change state


* **Parameters**

    
    * **contract_id** – smart contract account id


    * **method_name** – method name to call


    * **args** – json args to call method



* **Returns**

    result of view function call


```python
result = await acc.view_function("usn.near", "ft_balance_of", {"account_id": "bob.near"})
print(result)
```


### function_call(contract_id: str, method_name: str, args: dict, gas=DEFAULT_ATTACHED_GAS, amount=0, nowait=False)
Call function on smart contract


* **Parameters**

    
    * **contract_id** – smart contract adress


    * **method_name** – call method name


    * **args** – json params for method


    * **gas** – amount of attachment gas


    * **amount** – amount of attachment NEAR


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.function_call('usn.near', "ft_transfer", {"receiver_id": "bob.near", "amount": "1000000000000000000000000"})
```


### create_account(account_id: str, public_key: Union[str, bytes], initial_balance: int, nowait=False)
Create new account in subdomian of current account. For example, if current account is “test.near”,

    you can create “wwww.test.near”


* **Parameters**

    
    * **account_id** – new account id


    * **public_key** – add public key to new account


    * **initial_balance** – amount to transfer NEAR to new account


    * **nowait** – is nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.create_account('test.mydev.near', "5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj", NEAR * 3)
```


### add_public_key(public_key: Union[str, bytes], receiver_id: str, method_names: List[str] = None, allowance: int = 25000000000000000000000, nowait=False)
Add public key to account with access to smart contract methods


* **Parameters**

    
    * **public_key** – public_key to add


    * **receiver_id** – smart contract account id


    * **method_names** – list of method names to allow


    * **allowance** – maximum amount of gas to use for this key


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.add_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj", "usn.near", [])
```


### add_full_access_public_key(public_key: Union[str, bytes], nowait=False)
Add public key to account with full access


* **Parameters**

    
    * **public_key** – public_key to add


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.add_full_access_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj")
```


### delete_public_key(public_key: Union[str, bytes], nowait=False)
Delete public key from account


* **Parameters**

    
    * **public_key** – public_key to delete


    * **nowait** – is nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
await acc.delete_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj")
```


### deploy_contract(contract_code: bytes, nowait=False)
Deploy smart contract to account


* **Parameters**

    
    * **contract_code** – smart contract code


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult


```python
with open("contract.wasm", "rb") as f:
    contract_code = f.read()
await acc.deploy_contract(contract_code, nowait=True)
```


### stake(contract_code: bytes, nowait=False)
Stake NEAR on account. Account must have enough balance to be in validators pool


* **Parameters**

    
    * **public_key** – public_key to stake


    * **amount** – amount of NEAR to stake


    * **nowait** – if nowait is True, return transaction hash, else wait execution



* **Returns**

    transaction hash or TransactionResult



### get_balance(account_id: str = None)
Get account balance


* **Parameters**

    **account_id** – if account_id is None, return balance of current account



* **Returns**

    balance of account in yoctoNEAR


```python
result = await acc.get_balance("usn.near")
print(result)
```


### _property_ phone()
Get client for phone.herewallet.near


* **Returns**

    Phone(self)



### _property_ ft()
Get client for fungible tokens


* **Returns**

    FT(self)



# License

This repository is distributed under the terms of both the MIT license and the Apache License (Version 2.0). See LICENSE and LICENSE-APACHE for details.