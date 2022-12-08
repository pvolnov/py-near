
Account
======================

Quick start
-----------
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


Documentation
-------------

.. class:: Account

      This class implement all blockchain functions for your account

    .. code:: python

        acc = Account(...)
        await acc.startup()

.. function:: get_access_key()

    Get access key for current account

    :return: AccountAccessKey

    .. code:: python

        await acc.get_access_key()


.. function:: get_access_key_list(account_id=None)

    Send fungible token to phone number. Reciver will get sms with link to claim tokens.

    Get access key list for account_id, if account_id is None, get access key list for current account

    :param account_id:
    :return: list of PublicKey

    .. code:: python

        keys = await acc.get_access_key_list()
        print(len(keys))

.. function:: fetch_state(phone)

    Fetch state for given account

    :return: dict

    .. code:: python

        state = await acc.fetch_state()
        print(state)


.. function:: send_money(account_id: str, amount: int, nowait=False)

    Send money to account_id

    :param account_id: receiver account id
    :param amount: amount in yoctoNEAR
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.send_money('bob.near', NEAR * 3)


.. function:: view_function(contract_id: str, method_name: str, args: dict)

    Call view function on smart contract. View function is read only function, it can't change state

    :param contract_id: smart contract account id
    :param method_name: method name to call
    :param args: json args to call method
    :return: result of view function call

    .. code:: python

        result = await acc.view_function("usn.near", "ft_balance_of", {"account_id": "bob.near"})
        print(result)


.. function:: function_call(contract_id: str, method_name: str, args: dict, gas=DEFAULT_ATTACHED_GAS, amount=0, nowait=False)

    Call function on smart contract

    :param contract_id: smart contract adress
    :param method_name: call method name
    :param args: json params for method
    :param gas: amount of attachment gas
    :param amount: amount of attachment NEAR
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.function_call('usn.near', "ft_transfer", {"receiver_id": "bob.near", "amount": "1000000000000000000000000"})


.. function:: create_account(account_id: str, public_key: Union[str, bytes], initial_balance: int, nowait=False)

    Create new account in subdomian of current account. For example, if current account is "test.near",
        you can create "wwww.test.near"

    :param account_id: new account id
    :param public_key: add public key to new account
    :param initial_balance: amount to transfer NEAR to new account
    :param nowait: is nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.create_account('test.mydev.near', "5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj", NEAR * 3)


.. function:: add_public_key(public_key: Union[str, bytes], receiver_id: str, method_names: List[str] = None, allowance: int = 25000000000000000000000, nowait=False)

    Add public key to account with access to smart contract methods

    :param public_key: public_key to add
    :param receiver_id: smart contract account id
    :param method_names: list of method names to allow
    :param allowance: maximum amount of gas to use for this key
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult


    .. code:: python

        await acc.add_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj", "usn.near", [])


.. function:: add_full_access_public_key(public_key: Union[str, bytes], nowait=False)

    Add public key to account with full access

    :param public_key: public_key to add
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.add_full_access_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj")

.. function:: delete_public_key(public_key: Union[str, bytes], nowait=False)

    Delete public key from account

    :param public_key: public_key to delete
    :param nowait: is nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.delete_public_key("5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj")


.. function:: deploy_contract(contract_code: bytes, nowait=False)

    Deploy smart contract to account

    :param contract_code: smart contract code
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        with open("contract.wasm", "rb") as f:
            contract_code = f.read()
        await acc.deploy_contract(contract_code, nowait=True)


.. function:: stake(contract_code: bytes, nowait=False)

    Stake NEAR on account. Account must have enough balance to be in validators pool

    :param public_key: public_key to stake
    :param amount: amount of NEAR to stake
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult


.. function:: get_balance(account_id: str = None)

    Get account balance

    :param account_id: if account_id is None, return balance of current account
    :return: balance of account in yoctoNEAR

    .. code:: python

        result = await acc.get_balance("usn.near")
        print(result)


.. property:: phone

    Get client for phone.herewallet.near

    :return: Phone(self)


.. property:: ft

    Get client for fungible tokens

    :return: FT(self)



