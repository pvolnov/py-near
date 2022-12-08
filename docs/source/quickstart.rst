Quick start
=================

At first you have to import all necessary modules

.. code:: python

    from pynear.account import Account

Then you have to initialize `Account`


.. code:: python

    ACCOUNT_ID = "mydev.near"
    PRIVATE_KEY = "ed25519:..."

    acc = Account(ACCOUNT_ID, PRIVATE_KEY)


Next step: check account balance

.. code:: python

    import asyncio
    from pynear.dapps.core import NEAR

    async def main():
        await acc.startup()
        print(await acc.get_balance() / NEAR)
        print(await acc.get_balance("bob.near") / NEAR)

    asyncio.run(main())


Next step: send 2 NEAR to `bob.near`

.. code:: python

    transaction = await acc.send_money("bob.near", NEAR * 2)
    print(tr.transaction.hash)
    print(tr.logs)

Next step: send 2 NEAR to `bob.near` no waiting for transaction confirmation

.. code:: python

    transaction_hash = await acc.send_money("bob.near", NEAR * 2, nowait=True)
    print(transaction_hash)


Next step: send 0.1 NEAR by phone number

.. code:: python

    transaction = await acc.phone.send_near_to_phone("+15626200814", NEAR // 10)
    print(tr.transaction.hash)


Summary
==================

.. code:: python

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