
Phone number transfer
======================

.. note::
   Phone number transfer available only for mainnet


Quick start
-----------

.. code:: python

    from pynear.account import Account
    from pynear.dapps.fts import FTS
    import asyncio

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."


    async def main():
        acc = Account(ACCOUNT_ID, PRIVATE_KEY)
        await acc.startup()
        transaction = await acc.phone.send_ft_to_phone(FTS.USDC, "+15626200911", 1)
        print(tr.transaction.hash)

    asyncio.run(main())

Documentation
-------------

.. class:: Phone(DappClient)

   Client to `phone.herewallet.near contract`
   With this contract you can send NEAR and fungible tokens to
   phone number. Reciver will get notification with link to claim tokens.

    .. code:: python

        acc = Account(...)
        phone = acc.phone
        await acc.phone.send_near_to_phone("+1234567890", NEAR * 2, "Happy birthday!")


.. function:: send_near_to_phone(phone: str, amount: float, comment: str = "", nowait: bool = False)

    Send NEAR to phone number. Reciver will get sms with link to claim tokens.

    :param phone: +X format phone number
    :param amount: number of NEAR which will be sent
    :param comment: any comment
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.phone.send_near_to_phone('+79999999999', NEAR * 2*)


.. function:: send_ft_to_phone(ft: FtModel, phone: str, amount: float, comment: str = "", nowait: bool = False)

    Send fungible token to phone number. Reciver will get sms with link to claim tokens.

    :param ft: Fungible token model
    :param phone: +X format phone number
    :param amount: number of FT which will be sent
    :param comment:
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        # Send 1 USDC to phone number
        await acc.phone.send_ft_to_phone(FTS.USDC, '+79999999999', 1)

.. function:: get_ft_transfers(phone)

    Get list of fungible token transfers to phone number
    :param phone: phone number
    :return: list of `FtTrustTransaction`

    .. code:: python

        await acc.phone.get_ft_transfers('+79999999999')


.. function:: get_near_transfers(phone)

    Get list of NEAR transfers to phone number

    :param phone: phone number
    :return: list of NEAR transfers

    .. code:: python

        await acc.phone.get_near_transfers('+79999999999')


.. function:: cancel_near_transaction(phone: str, index: int)

    Cancel NEAR transfer to phone number. Use index from get_near_transfers() method

    :param phone: phone number
    :param index: index in transaction list
    :return:

    .. code:: python

        await acc.phone.cancel_near_transaction('+79999999999', 0)




.. function:: cancel_ft_transaction(phone: str, index: int)

    Cancel NEAR transfer to phone number. Use index from get_near_transfers() method

    Cancel fungible token transfer to phone number. Use index from get_ft_transfers() method

    :param phone: phone number
    :param index: index in transaction list
    :return:

    .. code:: python

        await acc.phone.cancel_ft_transaction('+79999999999', 0)





