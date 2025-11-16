
Fungible tokens
======================


Quick start
-----------

.. code:: python

    from py_near.account import Account
    from py_near.dapps.fts import FTS
    import asyncio

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."


    async def main():
        acc = Account(ACCOUNT_ID, PRIVATE_KEY)
        await acc.startup()
        # send 5 USDC to azbang.near
        tr = await acc.ft.transfer(FTS.USDC, "azbang.near", 5, force_register=True)
        print(tr.transaction.hash)

    asyncio.run(main())

Documentation
-------------

.. class:: FT(DappClient)

   Client for interacting with fungible tokens (FT) on NEAR.
   Provides methods for querying balances, transferring tokens, and managing
   storage deposits for FT contracts following the NEP-141 standard.

    .. code:: python

        acc = Account(...)
        ft = acc.ft
        await acc.ft.transfer(FTS.USDC, "azbang.near", 5, force_register=True)



.. function:: get_ft_balance(ft: FtModel, account_id: Optional[str] = None)

    Get fungible token balance

    :param ft: fungible token model (e.g., FTS.USDC)
    :param account_id: account id. If None, uses the current account
    :return: token balance as float (amount divided by 10^ft.decimal)

    .. code:: python

        await acc.ft.get_ft_balance(FTS.USDC, account_id="azbang.near")


.. function:: get_metadata(ft: Union[FtModel, str])

    Get fungible token metadata

    :param ft: fungible token model (e.g., FTS.USDC) or contract ID string
    :return: FtTokenMetadata containing token name, symbol, decimals, etc.

    .. code:: python

        await acc.ft.get_metadata(FTS.USDC)


.. function:: transfer(ft: FtModel, receiver_id: str, amount: float, memo: str = "", force_register: bool = False, nowait: bool = False)

    Transfer fungible token to account

    :param ft: fungible token model (e.g., FTS.USDC)
    :param receiver_id: receiver account id
    :param amount: float amount to transfer. 1 for 1 USDC
    :param memo: comment
    :param force_register: use storage_deposit() if account is not registered
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.ft.transfer(FTS.USDC, "azbang.near", 5, force_register=True)


.. function:: transfer_call(ft: FtModel, receiver_id: str, amount: float, memo: str = "", force_register: bool = False, nowait: bool = False)

    Transfer fungible token to account and call ft_on_transfer() method in receiver contract

    :param ft: fungible token model (e.g., FTS.USDC)
    :param receiver_id: receiver account id
    :param amount: float amount to transfer. 1 for 1 USDC
    :param memo: comment
    :param force_register: use storage_deposit() if account is not registered
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.ft.transfer_call(FTS.USDC, "azbang.near", 5, force_register=True)



.. function:: storage_balance_of(ft: Union[FtModel, str], account_id: Optional[str] = None)

    Get storage balance of account. The balance must be greater than 0.01 NEAR for some smart contracts
    in order for the recipient to accept the token

    :param ft: fungible token model (e.g., FTS.USDC) or contract ID string
    :param account_id: account id. If None, uses the current account
    :return: int balance in yoctoNEAR (0 if account is not registered), 1_000_000_000_000_000_000_000_000 for 1 NEAR


    .. code:: python

        await acc.ft.storage_balance_of(FTS.USDC, "azbang.near")


.. function:: storage_deposit(ft: Union[FtModel, str], account_id: Optional[str] = None, amount: int = NEAR // 50)

    Deposit storage balance for account. The balance must be greater than 0.01 NEAR for some smart contracts

    :param ft: fungible token model (e.g., FTS.USDC) or contract ID string
    :param account_id: receiver account id. If None, uses the current account
    :param amount: amount to deposit in yoctoNEAR (default: 0.02 NEAR)
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.ft.storage_deposit(FTS.USDC, "azbang.near")

