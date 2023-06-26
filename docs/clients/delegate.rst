
Delegate Transactions
======================

Description
-----------

NEAR Protocol supports delegate transactions since version 0.17.0 This is a special type of transaction which can be created and signed by one account but sent on behalf of another account. Delegate transactions used to pay for gas for a third party.

These transactions are performed in three steps.

1. Alice creates a ``delegate_action`` and specifies all the actions, public key and recipient.

2. Alice signs ``delegate_action`` with her private key and gives it to Bob.

3. Bob forms a normal transaction from one action - ``delegate_action``, signs it and sends to the blockchain. In fact, the Alice transaction is executed, but the Bob pays for the gas.

Make delegate transaction with ``py_near``
------------------------------------------

The following Python function creates and signs a delegate transaction.

1. Create a ``DelegateActionModel`` object with the ``create_delegate_action`` method. This method takes the following parameters:

    - ``actions``: A list of ``Action`` objects. In this example, we use a ``TransferAction`` object.
    - ``receiver_id``: The NEAR Protocol account ID where you want to send the transaction.

2. Sign the delegate transaction with the ``sign_delegate_transaction`` method. This method takes the following parameters:

        - ``delegate_action``: The ``DelegateActionModel`` object you created in the previous step.
        - ``private_key``: The private key of the NEAR Protocol account that you want to use to sign the transaction.

3. Execute the delegate transaction with the ``call_delegate_transaction`` method. This method takes the following parameters:

    - ``delegate_action``: The ``DelegateActionModel`` object you created in the previous step.
    - ``signature``: The signature of the delegate transaction that you created in the previous step.

You can execute this transaction from **any** NEAR Protocol account.

.. code-block:: python

    from py_near.account import Account
    from py_near_primitives import TransferAction
    import ed25519


    async def f():
        account = Account(
            "alisa.near",
            "ed25519::...",
            "https://nrpc.herewallet.app",
        )

        action = await account.create_delegate_action(actions=[TransferAction(1)], receiver_id="illia.near")
        sign = account.sign_delegate_transaction(action)

        account_to_execute = Account(
            "bob.near",
            "ed25519:...",
            "https://nrpc.herewallet.app",
        )
        res = account_to_execute acc.call_delegate_transaction(
            delegate_action=action,
            signature=sign,
        )

In this example, we transfer 1 yNEAR from  ``alisa.near``  to ``illia.near`` and pay for gas from ``bob.near`` balance.

.. note::
    Replace the ``ed25519`` public and private keys in the ``Account`` objects with your actual account keys.

    You also need to replace the ``receiver_id`` value in the ``create_delegate_action`` method with the actual NEAR Protocol account ID where you want to send the transaction.

.. warning::
    For now not all rpc support delegate transactions. You can use ``https://nrpc.herewallet.app`` for testing.


Make delegate transaction manually
----------------------------------

The following Python function creates and signs a delegate transaction from ``alisa.near`` account.


.. code-block:: python

    from py_near.account import Account
    from py_near_primitives import TransferAction
    from py_near.models import DelegateActionModel
    import ed25519

    private_key = ed25519.SigningKey(base58.b58decode("...."))
    public_key = base58.b58encode(private_key.get_verifying_key().to_bytes()).decode()

    action = DelegateActionModel(
        sender_id="alisa.near",
        receiver_id="illia.near",
        actions=[TransferAction(1)],
        nonce=ALISA_KEY_NONCE + 1,
        max_block_height=CURRENT_BLOCK_HEIGHT + 1,
        public_key=public_key,
    )

    sign = private_key.sign(action.nep461_hash)



And now send this transaction and pay for gas from ``bob.near`` balance.

.. code-block:: python

    from py_near.account import Account

    account_to_execute = Account(
            "bob.near",
            "ed25519:...",
            "https://nrpc.herewallet.app",
        )
    account_to_execute = await acc.call_delegate_transaction(
        delegate_action=action,
        signature=sign,
    )
