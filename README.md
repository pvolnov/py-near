# py-near

[![Financial Contributors on Open Collective](https://opencollective.com/py-near/all/badge.svg?style=flat-square)](https://opencollective.com/py-near) 
[![PyPi Package Version](https://img.shields.io/pypi/v/py-near?style=flat-square)](https://pypi.org/project/py-near)
[![Supported python versions](https://img.shields.io/pypi/pyversions/py-near)](https://pypi.python.org/pypi/py-near)
[![Documentation Status](https://img.shields.io/readthedocs/py-near?style=flat-square)](https://py-near.readthedocs.io/en/latest)
[![Github issues](https://img.shields.io/github/issues/pvolnov/py-near.svg?style=flat-square)](https://github.com/pvolnov/py-near/issues)
[![MIT License](https://img.shields.io/pypi/l/py-near.svg?style=flat-square?style=flat-square)](https://opensource.org/licenses/MIT)
[![Twitter](https://img.shields.io/twitter/follow/p_volnov?label=Follow)](https://twitter.com/p_volnov)

[//]: # ([![downloads]&#40;https://img.shields.io/github/downloads/pvolnov/py-near/total?style=flat-square&#41;]&#40;https://pypi.org/project/py-near&#41;)


**py-near** is a Async client for NEAR Blockchain with native HOT Protocol & NEAR Intents support

## Examples
<details>
  <summary>📚 Click to see some basic examples</summary>


**Few steps before getting started...**
- Install the latest stable version of py-near, simply running `pip install py-near`
- Create NEAR account and get your private key [wallet](https://wallet.near.org/create)

### Simple money transfer

```python
from py_near.account import Account
import asyncio
from py_near.dapps.core import NEAR

ACCOUNT_ID = "bob.near"
PRIVATE_KEY = "ed25519:..."


async def main():
   acc = Account(ACCOUNT_ID, PRIVATE_KEY)

   await acc.startup()
   print(await acc.get_balance() / NEAR)
   print(await acc.get_balance("bob.near") / NEAR)

   tr = await acc.send_money("bob.near", NEAR * 2)
   print(tr.transaction.hash)
   print(tr.logs)


asyncio.run(main())
```

### Working with NEAR Intents (OmniBalance)

```python
from py_near.omni_balance import OmniBalance
import asyncio

ACCOUNT_ID = "bob.near"
PRIVATE_KEY = "ed25519:..."


async def main():
    omni = OmniBalance(ACCOUNT_ID, PRIVATE_KEY)
    await omni.startup()
    
    # Create intent with multiple actions: transfer, token swap, and auth call
    commitment = omni.transfer(
        tokens={"nep141:wrap.near": "5"},
        receiver_id="alice.near",
        memo="Test transfer",
    ).token_diff({
        "nep141:wrap.near": "-5",
    }).auth_call("contract.near", msg="test").sign()
    
    # Simulate intent before submitting
    sim = await omni.simulate_intent(commitment)
    print(sim.logged_intents)
    
    # Submit intent to solver network
    intent_hash = await omni.publish_intents(commitment)
    print(f"Intent hash: {intent_hash}")
    
    # Wait for transaction hash
    tr_hash = await omni.get_tr_hash_from_intent(intent_hash)
    print(f"Transaction hash: {tr_hash}")
    
    await omni.shutdown()


asyncio.run(main())
```

### Parallel requests

Only one parallel request can be made from one private key.
All transaction calls execute sequentially.
To make several parallel calls you need to use several private keys



```python3
acc = Account("bob.near", private_key1)

for i in range(2):
  signer = InMemorySigner.from_random(AccountId("bob.near"), KeyType.ED25519)
  await acc.add_full_access_public_key(str(signer.public_key))
  print(signer.secret_key)
```

Now we can call transactions in parallel

```python3
acc = Account("bob.near", [private_key1, private_key2, private_key3])
# request time = count transactions / count public keys
tasks = [
  asyncio.create_task(acc.send_money("alisa.near", 1)),
  asyncio.create_task(acc.send_money("alisa.near", 1)),
  asyncio.create_task(acc.send_money("alisa.near", 1)),
]
for t in tasks:
  await t
```

</details>


## Official py-near resources:
 - News: [@herewallet](https://t.me/herewallet)
 - Social media:
   - 🇺🇸 [Telegram](https://t.me/neafiol)
   - 🇺🇸 [Twitter](https://twitter.com/p_volnov)
 - PyPI: [py-near](https://pypi.python.org/pypi/py-near)
 - Documentation: [py-near.readthedocs.io](https://py-near.readthedocs.io/en/latest)
 - Source: [Github repo](https://github.com/pvolnov/py-near)
 - Issues/Bug tracker: [Github issues tracker](https://github.com/pvolnov/py-near/issues)

## Contributors

### Code Contributors

This project exists thanks to all the people who contribute. [[Code of conduct](CODE_OF_CONDUCT.md)].
<a href="https://github.com/pvolnov/py-near/graphs/contributors"><img src="https://opencollective.com/py-near/contributors.svg?width=890&button=false" /></a>
