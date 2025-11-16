
Account
======================

Quick start
-----------
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

        transaction = await acc.send_money("bob.near", NEAR * 2)
        print(transaction.transaction.hash)
        print(transaction.logs)

    asyncio.run(main())


Documentation
-------------

.. class:: Account

      This class implement all blockchain functions for your account.
      Only one parallel request can be made from one private key.
      All transaction calls execute sequentially.

      .. code:: python

        acc = Account("bob.near", private_key1)

        # requests time ~18s
        tasks = [
            asyncio.create_task(acc.send_money("alisa.near", 1)),
            asyncio.create_task(acc.send_money("alisa.near", 1)),
            asyncio.create_task(acc.send_money("alisa.near", 1)),
        ]
        for t in tasks:
            await t


      `Account()` support multikeys. In this case you can make a few parallel requests.

      .. code:: python

        acc = Account("bob.near", [private_key1, private_key2, private_key3])

        # requests time ~6s
        tasks = [
            asyncio.create_task(acc.send_money("alisa.near", 1)),
            asyncio.create_task(acc.send_money("alisa.near", 1)),
            asyncio.create_task(acc.send_money("alisa.near", 1)),
        ]
        for t in tasks:
            await t





.. function:: get_access_key()

    Get access key for current account

    :return: AccountAccessKey

    .. code:: python

        await acc.get_access_key()


.. function:: get_access_key_list(account_id=None)

    Get access key list for account_id, if account_id is None, get access key list for current account

    :param account_id: if account_id is None, return balance of current account
    :return: list of PublicKey

    .. code:: python

        keys = await acc.get_access_key_list()
        print(len(keys))

.. function:: fetch_state(phone)

    Fetch state for given account

    :return: state dict

    .. code:: python

        state = await acc.fetch_state()
        print(state)


.. function:: send_money(account_id: str, amount: int, nowait=False, included=False)

    Send money to account_id

    :param account_id: receiver account id
    :param amount: amount in yoctoNEAR
    :param nowait: if nowait is True, return transaction hash, else wait execution (legacy, same as included)
    :param included: if included is True, wait until transaction is included in a block, then return transaction hash
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.send_money('bob.near', NEAR * 3)


.. function:: view_function(contract_id: str, method_name: str, args: dict, block_id=None, threshold=None)

    Call view function on smart contract. View function is read only function, it can't change state

    :param contract_id: smart contract account id
    :param method_name: method name to call
    :param args: json args to call method
    :param block_id: optional block ID to query at a specific block height
    :param threshold: minimum number of nodes that must return the same result (for consensus verification)
    :return: ViewFunctionResult containing the method result, logs, and block info

    .. code:: python

        result = await acc.view_function("usn.near", "ft_balance_of", {"account_id": "bob.near"})
        print(result.result)


.. function:: function_call(contract_id: str, method_name: str, args: dict, gas=DEFAULT_ATTACHED_GAS, amount=0, nowait=False, included=False)

    Call function on smart contract

    :param contract_id: smart contract address
    :param method_name: call method name
    :param args: json params for method
    :param gas: amount of attachment gas
    :param amount: amount of attachment NEAR
    :param nowait: if nowait is True, return transaction hash, else wait execution (legacy, same as included)
    :param included: if included is True, wait until transaction is included in a block, then return transaction hash
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.function_call('usn.near', "ft_transfer", {"receiver_id": "bob.near", "amount": "1000000000000000000000000"})


.. function:: create_account(account_id: str, public_key: Union[str, bytes], initial_balance: int, nowait=False)

    Create new account in subdomain of current account. For example, if current account is "test.near",
        you can create "sub.test.near"

    :param account_id: new account id
    :param public_key: add public key to new account
    :param initial_balance: amount to transfer NEAR to new account in yoctoNEAR
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. code:: python

        await acc.create_account('test.bob.near', "5X9WvUbRV3aSd9Py1LK7HAndqoktZtcgYdRjMt86SxMj", NEAR * 3)


.. function:: add_public_key(public_key: Union[str, bytes], receiver_id: str, method_names: List[str] = None, allowance: int = 25000000000000000000000, nowait=False)

    Add public key to account with access to smart contract methods

    :param public_key: public_key to add
    :param receiver_id: smart contract account id
    :param method_names: list of method names to allow (empty list means all methods)
    :param allowance: maximum amount of gas to use for this key (in yoctoNEAR gas units, default is 25 TGas)
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
    :param nowait: if nowait is True, return transaction hash, else wait execution
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


.. function:: stake(public_key: str, amount: str, nowait=False)

    Stake NEAR tokens with a validator

    :param public_key: validator's public key to stake with
    :param amount: amount of NEAR to stake (as string in yoctoNEAR)
    :param nowait: if nowait is True, return transaction hash, else wait execution
    :return: transaction hash or TransactionResult

    .. note::
        Account must have sufficient balance to meet validator pool requirements


.. function:: get_balance(account_id: str = None)

    Get account balance

    :param account_id: if account_id is None, return balance of current account
    :return: balance of account in yoctoNEAR

    .. code:: python

        result = await acc.get_balance("usn.near")
        print(result)


.. property:: ft

    Get client for fungible tokens

    :return: FT(self)

.. function:: call_delegate_transaction(delegate_action: Union[DelegateAction, DelegateActionModel], signature: Union[bytes, str], nowait=False, included=False)

    Execute a signed delegate action transaction

    :param delegate_action: DelegateAction or DelegateActionModel to execute
    :param signature: signature for the delegate action (bytes or base58 string)
    :param nowait: if nowait is True, return transaction hash immediately (legacy, same as included)
    :param included: if included is True, wait until transaction is included in a block, then return transaction hash
    :return: transaction hash or TransactionResult

    .. code:: python

        from py_near_primitives import TransferAction
        action = await acc.create_delegate_action(actions=[TransferAction(1)], receiver_id="illia.near")
        sign = acc.sign_delegate_transaction(action)
        res = await acc.call_delegate_transaction(delegate_action=action, signature=sign)

.. function:: create_delegate_action(actions: List[Action], receiver_id, public_key: Optional[str] = None)

    Create a delegate action from a list of actions

    :param actions: list of actions to include in the delegate action
    :param receiver_id: account ID that will receive the delegate action
    :param public_key: optional public key to use for signing. If None, uses the first configured signer
    :return: DelegateActionModel ready to be signed

.. function:: sign_delegate_transaction(delegate_action: Union[DelegateAction, DelegateActionModel]) -> str

    Sign a delegate action transaction

    :param delegate_action: DelegateAction or DelegateActionModel to sign
    :return: base58-encoded signature string

    .. code:: python

        signature = acc.sign_delegate_transaction(delegate_action)

.. function:: use_global_contract(account_id: Optional[str] = None, contract_code_hash: Union[str, bytes, None] = None, nowait=False, included=False)

    Use a global contract by account ID or code hash

    :param account_id: account ID of the global contract to use
    :param contract_code_hash: code hash of the global contract to use (32 bytes)
    :param nowait: if nowait is True, return transaction hash immediately (legacy, same as included)
    :param included: if included is True, wait until transaction is included in a block, then return transaction hash
    :return: transaction hash or TransactionResult

.. function:: shutdown()

    Clean up async resources. Closes the RPC provider connection. Should be called when done using the account instance.

    .. code:: python

        await acc.shutdown()
