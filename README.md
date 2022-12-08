# py-near

[![Financial Contributors on Open Collective](https://opencollective.com/py-near/all/badge.svg?style=flat-square)](https://opencollective.com/py-near) 
[![PyPi Package Version](https://img.shields.io/pypi/v/py-near?style=flat-square)](https://pypi.org/project/py-near)
[![Supported python versions](https://img.shields.io/pypi/pyversions/py-near)](https://pypi.python.org/pypi/py-near)
[![Documentation Status](https://img.shields.io/readthedocs/py-near?style=flat-square)](https://py-near.readthedocs.io/en/latest)
[![Github issues](https://img.shields.io/github/issues/pvolnov/py-near.svg?style=flat-square)](https://twitter.com/p_volnov)
[![MIT License](https://img.shields.io/pypi/l/py-near.svg?style=flat-square?style=flat-square)](https://opensource.org/licenses/MIT)
[![Twitter](https://img.shields.io/twitter/follow/p_volnov?label=Follow)](https://github.com/pvolnov/py-near/issues)

[//]: # ([![downloads]&#40;https://img.shields.io/github/downloads/pvolnov/py-near/total?style=flat-square&#41;]&#40;https://pypi.org/project/py-near&#41;)


**py-near** is a pretty simple and fully asynchronous framework for working with NEAR blockchain.

## Examples
<details>
  <summary>📚 Click to see some basic examples</summary>


**Few steps before getting started...**
- Install the latest stable version of py-near, simply running `pip install py-near`
- Create NEAR account and get your private key [wallet](https://wallet.near.org/create)

### Simple money transfer

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

    tr = await acc.send_money("bob.near", NEAR * 2)
    print(tr.transaction.hash)
    print(tr.logs)

asyncio.run(main())
```

### Transfer money by phone number

```python
from pynear.account import Account
import asyncio
from pynear.dapps.core import NEAR

ACCOUNT_ID = "mydev.near"
PRIVATE_KEY = "ed25519:..."

async def main():
    acc = Account(ACCOUNT_ID, PRIVATE_KEY)

    await acc.startup()
    tr = await acc.phone.send_near_to_phone("+15626200911", NEAR // 10)
    print(tr.transaction.hash)

asyncio.run(main())
```

</details>


## Official py-near resources:
 - News: [@herewallet](https://t.me/here_wallet)
 - Communities:
   - 🇺🇸 [@py-near](https://t.me/neafiol)
 - PyPI: [py-near](https://pypi.python.org/pypi/py-near)
 - Documentation: [py-near site](https://py-near.readthedocs.io/en/latest)
 - Source: [Github repo](https://github.com/pvolnov/py-near)
 - Issues/Bug tracker: [Github issues tracker](https://github.com/pvolnov/py-near/issues)

## Contributors

### Code Contributors

This project exists thanks to all the people who contribute. [[Code of conduct](CODE_OF_CONDUCT.md)].
<a href="https://github.com/py-near/py-near/graphs/contributors"><img src="https://opencollective.com/py-near/contributors.svg?width=890&button=false" /></a>
