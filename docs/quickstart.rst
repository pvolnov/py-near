Quick start
=================

At first you have to import all necessary modules

.. code:: python

    from py_near.account import Account

Then you have to initialize `Account`


.. code:: python

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."

    acc = Account(ACCOUNT_ID, PRIVATE_KEY)


Next step: check account balance

.. code:: python

    import asyncio
    from py_near.dapps.core import NEAR

    async def main():
        await acc.startup()
        print(await acc.get_balance() / NEAR)
        print(await acc.get_balance("bob.near") / NEAR)

    asyncio.run(main())


Next step: send 2 NEAR to `bob.near`

.. code:: python

    tr = await acc.send_money("bob.near", NEAR * 2)
    print(tr.transaction.hash)
    print(tr.logs)

Next step: send 2 NEAR to `bob.near` no waiting for transaction confirmation

.. code:: python

    transaction_hash = await acc.send_money("bob.near", NEAR * 2, nowait=True)
    print(transaction_hash)


Next step: send 2 NEAR and wait until transaction is included in a block

.. code:: python

    transaction_hash = await acc.send_money("bob.near", NEAR * 2, included=True)
    print(transaction_hash)

Summary
----------------

.. code:: python

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



Parallel requests
-----------------

Only one parallel request can be made from one private key.
All transaction calls execute sequentially.
To make several parallel calls you need to use several private keys


Add 2 new full access keys:

.. code:: python

    from nacl.signing import SigningKey
    from nacl.encoding import RawEncoder
    import base58

    acc = Account("bob.near", private_key1)
    await acc.startup()

    for i in range(2):
        signing_key = SigningKey.generate()
        public_key = base58.b58encode(signing_key.verify_key.encode()).decode("utf-8")
        await acc.add_full_access_public_key(public_key)
        private_key_bytes = signing_key.encode(encoder=RawEncoder)
        print(f"ed25519:{base58.b58encode(private_key_bytes).decode('utf-8')}")


Now we can call transactions in parallel

.. code:: python

    acc = Account("bob.near", [private_key1, private_key2, private_key3])
    # request time = count transactions / count public keys
    tasks = [
        asyncio.create_task(acc.send_money("alisa.near", 1)),
        asyncio.create_task(acc.send_money("alisa.near", 1)),
        asyncio.create_task(acc.send_money("alisa.near", 1)),
    ]
    for t in tasks:
        await t
