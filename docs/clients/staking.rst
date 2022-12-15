
Staking
======================

.. note::
   Class to stake NEAR on liquid staking. You can stake NEAR and withdraw at any time without fees

   Read more about staking: https://docs.herewallet.app/technology-description/readme


Quick start
-----------

.. code:: python

    from pynear.account import Account
    from pynear.dapps.fts import FTS
    import asyncio

    ACCOUNT_ID = "mydev.near"
    PRIVATE_KEY = "ed25519:..."


    async def main():
        acc = Account(ACCOUNT_ID, PRIVATE_KEY)
        await acc.startup()
        transaction = await acc.staking.stake(10000)
        print(tr.transaction.hash)

        transaction = await acc.staking.receive_dividends()
        print(tr.logs)

        transaction = await acc.staking.unstake(10000)
        print(tr.transaction.hash)

    asyncio.run(main())

Documentation
-------------

.. class:: Staking(DappClient)

   Client to `storage.herewallet.near contract`
   With this contract you can stake NEAR without blocking and receive passive income ~9% APY

    .. code:: python

        acc = Account(...)
        staking = acc.staking


.. class:: StakingData(DappClient)

    .. py:attribute:: apy_value
        :type: int

        current APY value * 100 (908=9.08%)

    .. py:attribute:: last_accrual_ts
        :type: int

        Last UTC timestamp of accrued recalc

    .. py:attribute:: accrued
        :type: int

        Total accrued in yoctoNEAR, which can be receiver by `receive_dividends()` call


.. function:: transfer(account_id: str, amount: int, memo: str = "", force_register: bool = False)

    Transfer hNEAR to account

    :param receiver_id: receiver account id
    :param amount: amount in yoctoNEAR
    :param memo: comment
    :param nowait if True, method will return before transaction is confirmed
    :return: transaction hash ot TransactionResult

    .. code:: python

        await acc.staking.transfer("azbang.near", 10000)


.. function:: transfer_call(account_id: str, amount: int, memo: str = "", force_register: bool = False)

    Transfer hNEAR to account and call on_transfer_call() on receiver smart contract

    :param receiver_id: receiver account id
    :param amount: amount in yoctoNEAR
    :param memo: comment
    :param nowait if True, method will return before transaction is confirmed
    :return: transaction hash ot TransactionResult

    .. code:: python

        await acc.staking.transfer_call("azbang.near", 10000)



.. function:: get_staking_amount(account_id: str)

    Get staking balance of account.

    :param account_id: account id
    :param nowait if True, method will return before transaction is confirmed
    :return: int balance in yoctoNEAR

    .. code:: python

        amount = await acc.staking.get_staking_amount("azbang.near")
        print(amount)


.. function:: get_user(account_id: str)

    Get user staking parameters

    :param account_id: account id
    :return: StakingData

    .. code:: python

        data = await acc.staking.get_user("azbang.near")
        print(data.apy_value / 100)



.. function:: stake(amount: int, nowait: bool = False)

    Deposit staking for account

    :param amount: in amount of yoctoNEAR
    :param nowait: if True, method will return before transaction is confirmed
    :return: transaction hash or TransactionResult

    .. code:: python

        res = await acc.staking.stake(1_000_000_000_000_000)
        print(res.transaction.hash)



.. function:: unstake(amount: int, nowait: bool = False)

    Withdraw from staking

    :param amount: in amount of yoctoNEAR
    :param nowait: if True, method will return before transaction is confirmed
    :return: transaction hash or TransactionResult

    .. code:: python

        res = await acc.staking.unstake(1_000_000_000_000_000)
        print(res.transaction.hash)


.. function:: receive_dividends(nowait: bool = False)

    Receive dividends. user.accrued yoctoNEAR amount will transfer to staking balance

    :param nowait: if True, method will return before transaction is confirmed
    :return: transaction hash ot TransactionResult

    .. code:: python

        res = await acc.staking.receive_dividends()
        print(res.transaction.hash)

