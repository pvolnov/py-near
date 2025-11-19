
Omni Balance & NEAR Intents
============================

.. note::
   OmniBalance provides a powerful interface for working with NEAR Intents protocol.
   Intents allow you to express desired outcomes (like token swaps) without specifying exact execution paths.
   Solvers find the best way to fulfill your intent.

Quick start
-----------

.. code:: python

    from py_near.omni_balance import OmniBalance
    from py_near.dapps.core import NEAR
    import asyncio

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."

    async def main():
        omni = OmniBalance(ACCOUNT_ID, PRIVATE_KEY)
        await omni.startup()

        # Create and submit a token swap intent
        result = await omni.intent().token_diff(
            diff={"usdt.tether-token.near": "-1000000", "wrap.near": "1000000000000000000000000"}
        ).submit()

        print(result)

        await omni.shutdown()

    asyncio.run(main())


Using context manager
---------------------

.. code:: python

    async def main():
        async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
            result = await omni.intent().token_diff(
                diff={"usdt.tether-token.near": "-1000000", "wrap.near": "1000000000000000000000000"}
            ).submit()
            print(result)

    asyncio.run(main())


Documentation
-------------

.. class:: OmniBalance

   Intent manager for omni_balance operations. Provides methods for creating, signing, and submitting intents.

   .. code:: python

       omni = OmniBalance(account_id, private_key, rpc_urls=None, intents_headers=None)
       await omni.startup()

   :param account_id: NEAR account ID
   :param private_key: Private key (str) or list of private keys (List[str])
   :param rpc_urls: Optional RPC URL or list of URLs (defaults to mainnet)
   :param intents_headers: Optional headers for intents API requests


.. function:: startup() -> OmniBalance

   Initialize and start the OmniBalance manager. Creates HTTP session and initializes account connection.

   :return: Self instance for method chaining

   .. code:: python

       await omni.startup()


.. function:: shutdown() -> None

   Shutdown and cleanup the OmniBalance manager. Closes HTTP session and releases resources.

   .. code:: python

       await omni.shutdown()


.. function:: intent() -> IntentBuilder

   Create a new IntentBuilder instance for building intents.

   :return: IntentBuilder instance

   .. code:: python

       builder = omni.intent()


Intent Builder
--------------

The IntentBuilder provides a fluent interface for creating and submitting intents.

.. class:: IntentBuilder

   Builder for creating and submitting intents. Supports method chaining.

   .. code:: python

       builder = omni.intent()
       builder.transfer(...).token_diff(...).submit()


.. function:: transfer(tokens: Dict[str, str], receiver_id: str, memo: Optional[str] = None) -> IntentBuilder

   Add transfer intent to send tokens to another account.

   :param tokens: Dictionary mapping token_id to amount (as string)
   :param receiver_id: Receiver account ID
   :param memo: Optional memo/comment
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().transfer(
           tokens={"wrap.near": "1000000000000000000000000"},
           receiver_id="alice.near",
           memo="Payment"
       ).submit()


.. function:: token_diff(diff: Dict[str, str], referral: Optional[str] = None) -> IntentBuilder

   Add token diff intent for token swaps. Negative values indicate tokens to sell, positive values indicate tokens to buy.

   :param diff: Dictionary mapping token_id to amount difference (negative = sell, positive = buy)
   :param referral: Optional referral account ID
   :return: IntentBuilder instance for chaining

   .. code:: python

       # Swap 1 USDT for NEAR
       await omni.intent().token_diff(
           diff={
               "usdt.tether-token.near": "-1000000",  # Sell 1 USDT (6 decimals)
               "wrap.near": "1000000000000000000000000"  # Buy ~1 NEAR
           }
       ).submit()


.. function:: mt_withdraw(token_ids: List[str], amounts: List[str], receiver_id: str, msg: str, token: str = "v2_1.omni.hot.tg") -> IntentBuilder

   Add multi-token withdraw intent.

   :param token_ids: List of token IDs to withdraw
   :param amounts: List of amounts to withdraw
   :param receiver_id: Receiver account ID
   :param msg: Message for withdrawal
   :param token: Token contract ID (default: "v2_1.omni.hot.tg")
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().mt_withdraw(
           token_ids=["token1", "token2"],
           amounts=["1000000", "2000000"],
           receiver_id="alice.near",
           msg="Withdrawal"
       ).submit()


.. function:: nft_withdraw(contract_id: str, token_id: str, receiver_id: str, msg: Optional[str] = None) -> IntentBuilder

   Add NFT withdraw intent.

   :param contract_id: NFT contract ID
   :param token_id: Token ID to withdraw
   :param receiver_id: Receiver account ID
   :param msg: Optional message
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().nft_withdraw(
           contract_id="nft.contract.near",
           token_id="123",
           receiver_id="alice.near"
       ).submit()


.. function:: auth_call(contract_id: str, msg: str, attached_deposit: str = "0", min_gas: Optional[str] = None) -> IntentBuilder

   Add authentication callback intent.

   :param contract_id: Contract ID to call
   :param msg: Message/parameters for the contract call
   :param attached_deposit: Amount of NEAR to attach (default: "0")
   :param min_gas: Minimum gas required (optional)
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().auth_call(
           contract_id="contract.near",
           msg='{"action": "do_something"}',
           attached_deposit="1000000000000000000000000"
       ).submit()


.. function:: with_nonce(nonce: Optional[str]) -> IntentBuilder

   Set nonce for intents. If not set, a random nonce will be generated.

   :param nonce: Optional nonce string
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().token_diff(...).with_nonce("custom_nonce").submit()


.. function:: with_deadline(deadline_seconds: Optional[int]) -> IntentBuilder

   Set deadline for intents in seconds. Default is 600 seconds (10 minutes) for most intents, 60 seconds for MT withdrawals.

   :param deadline_seconds: Deadline in seconds
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().token_diff(...).with_deadline(300).submit()


.. function:: with_seed(seed: Optional[str]) -> IntentBuilder

   Set seed for nonce generation. The seed will be hashed to generate a deterministic nonce.

   :param seed: Optional seed string
   :return: IntentBuilder instance for chaining

   .. code:: python

       await omni.intent().token_diff(...).with_seed("my_seed").submit()


.. function:: sign() -> Commitment

   Sign the intents and return commitment without submitting.

   :return: Commitment object with signature

   .. code:: python

       commitment = omni.intent().token_diff(...).sign()
       # Can submit later or use for other purposes


.. function:: submit() -> str

   Sign and submit the intents to the solver network.

   :return: Intent hash (string) if submission is successful

   .. code:: python

       intent_hash = await omni.intent().token_diff(...).submit()
       print(f"Intent hash: {intent_hash}")


.. function:: get_quote() -> Quote

   Get quote object without signing. Useful for inspection before signing.

   :return: Quote object

   .. code:: python

       quote = omni.intent().token_diff(...).get_quote()
       print(quote.model_dump())


.. function:: get_tr_hash_from_intent(intent_hash: str, timeout: int = 20) -> Optional[str]

   Get transaction hash from intent hash. Polls the solver network until the intent is settled.

   :param intent_hash: Intent hash returned from submit()
   :param timeout: Timeout in seconds (default: 20)
   :return: Transaction hash if intent is settled, None if timeout or failed

   .. code:: python

       intent_hash = await omni.intent().token_diff(...).submit()
       tr_hash = await omni.get_tr_hash_from_intent(intent_hash, timeout=30)
       if tr_hash:
           print(f"Transaction hash: {tr_hash}")
       else:
           print("Intent not settled yet or failed")


Direct Methods
--------------

These methods provide direct access to intent creation without using the builder pattern.

.. function:: transfer(tokens: Dict[str, str], receiver_id: str, memo: Optional[str] = None) -> IntentBuilder

   Create transfer intent builder (same as intent().transfer()).

   .. code:: python

       await omni.transfer(
           tokens={"wrap.near": "1000000000000000000000000"},
           receiver_id="alice.near"
       ).submit()


.. function:: token_diff(diff: Dict[str, str], referral: Optional[str] = None) -> IntentBuilder

   Create token diff intent builder (same as intent().token_diff()).

   .. code:: python

       await omni.token_diff(
           diff={"usdt.tether-token.near": "-1000000", "wrap.near": "1000000000000000000000000"}
       ).submit()


Token Management
----------------

.. function:: deposit_near_token(token_id: str, amount: str) -> None

   Deposit NEAR fungible token to intents contract. Required before using tokens in intents.

   :param token_id: Token contract ID
   :param amount: Amount to deposit (as string)

   .. code:: python

       await omni.deposit_near_token("usdt.tether-token.near", "1000000")


.. function:: deposit_nft(contract_id: str, token_id: str) -> None

   Deposit NFT to intents contract. Required before using NFTs in intents.

   :param contract_id: NFT contract ID
   :param token_id: Token ID to deposit

   .. code:: python

       await omni.deposit_nft("nft.contract.near", "123")


.. function:: register_token_storage(token_id: str, other_account: Optional[str] = None) -> None

   Register token storage for account. Automatically called by deposit methods if needed.

   :param token_id: Token contract ID
   :param other_account: Optional account ID (defaults to current account)

   .. code:: python

       await omni.register_token_storage("usdt.tether-token.near")


Key Management
--------------

.. function:: register_intent_public_key(public_key: Optional[str] = None) -> None

   Register public key for intents. Required before submitting intents.

   :param public_key: Optional public key (defaults to account's public key)

   .. code:: python

       await omni.register_intent_public_key()


.. function:: remove_intent_public_key(public_key: Optional[str] = None) -> None

   Remove public key from intents.

   :param public_key: Optional public key (defaults to account's public key)

   .. code:: python

       await omni.remove_intent_public_key()


Simulation & Execution
----------------------

.. function:: simulate_intent(commitment: Union[Commitment, dict]) -> SimulationResult

   Simulate intent execution to check if it will succeed.

   :param commitment: Commitment object or dict
   :return: SimulationResult with execution details
   :raises SimulationError: If simulation fails

   .. code:: python

       commitment = omni.intent().token_diff(...).sign()
       try:
           result = await omni.simulate_intent(commitment)
           print(f"Simulation successful: {result}")
       except SimulationError as e:
           print(f"Simulation failed: {e}")


.. function:: sign_and_submit_intents(intents: List[IntentType], nonce: Optional[str] = None, deadline_seconds: Optional[int] = None) -> str

   Sign and submit intents directly (lower-level API).

   :param intents: List of intent objects
   :param nonce: Optional nonce (will be generated if not provided)
   :param deadline_seconds: Optional deadline in seconds (default: 600)
   :return: Intent hash (string)

   .. code:: python

       from py_near.omni_balance.models import IntentTokenDiff

       intents = [
           IntentTokenDiff(
               diff={"usdt.tether-token.near": "-1000000", "wrap.near": "1000000000000000000000000"}
           )
       ]
       intent_hash = await omni.sign_and_submit_intents(intents)
       print(f"Intent hash: {intent_hash}")


.. function:: publish_intents(signed_intents: Union[Commitment, dict, List[Commitment], List[dict]], quote_hashes: Optional[List[str]] = None) -> str

   Publish intent(s) to solver network. This is the method used internally by submit().

   :param signed_intents: Commitment object, dict, or list of commitments
   :param quote_hashes: Optional list of quote hashes for token swaps
   :return: Intent hash (string) if submission is successful
   :raises SimulationError: If submission fails

   .. code:: python

       commitment = omni.intent().token_diff(...).sign()
       intent_hash = await omni.publish_intents(commitment)


.. function:: submit_signed_intent(signed_intents: Union[List[Commitment], Commitment]) -> TransactionResult

   Submit signed intents directly to blockchain (bypasses solver network).

   :param signed_intents: List of signed commitments or single commitment
   :return: TransactionResult

   .. code:: python

       commitment = omni.intent().token_diff(...).sign()
       result = await omni.submit_signed_intent(commitment)


Quote Functions
---------------

.. function:: get_quote_hash(token_from: str, token_to: str, amount_in: Optional[str] = None, exact_amount_out: Optional[str] = None, deep: int = 1, asset_from: Optional[str] = None, asset_to: Optional[str] = None) -> Optional[QuoteHashOutModel]

   Get token swap quote with support for intermediate routes. This function attempts to find the best swap route between two tokens.

   :param token_from: Input token identifier
   :param token_to: Output token identifier
   :param amount_in: Input token amount (for calculating exact_amount_in)
   :param exact_amount_out: Exact output token amount (for calculating exact_amount_out)
   :param deep: Recursion depth for searching intermediate routes (default: 1, max: 2)
   :param asset_from: Asset identifier for input token (for contract lookup)
   :param asset_to: Asset identifier for output token (for contract lookup)
   :return: QuoteHashOutModel with the best route or None if swap is not possible

   .. code:: python

       from py_near.omni_balance.quote import get_quote_hash

       # Get quote for swapping 1 USDT to NEAR
       quote = await get_quote_hash(
           token_from="usdt.tether-token.near",
           token_to="wrap.near",
           amount_in="1000000"  # 1 USDT (6 decimals)
       )
       if quote:
           print(f"Will receive: {quote.amount_out}")
           print(f"Route: {quote.quote_hashes}")


Examples
--------

Complete token swap example
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from py_near.omni_balance import OmniBalance
    from py_near.dapps.core import NEAR
    import asyncio

    async def swap_tokens():
        async with OmniBalance("bob.near", "ed25519:...") as omni:
            # First, deposit tokens if needed
            await omni.deposit_near_token("usdt.tether-token.near", "1000000")

            # Register public key if not already registered
            await omni.register_intent_public_key()

            # Create and submit swap intent
            intent_hash = await omni.intent().token_diff(
                diff={
                    "usdt.tether-token.near": "-1000000",  # Sell 1 USDT
                    "wrap.near": "1000000000000000000000000"  # Buy ~1 NEAR
                }
            ).with_deadline(600).submit()

            print(f"Intent submitted: {intent_hash}")
            
            # Optionally wait for transaction hash
            tr_hash = await omni.get_tr_hash_from_intent(intent_hash)
            if tr_hash:
                print(f"Transaction hash: {tr_hash}")

    asyncio.run(swap_tokens())


Transfer tokens via intent
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    async def transfer_via_intent():
        async with OmniBalance("bob.near", "ed25519:...") as omni:
            intent_hash = await omni.intent().transfer(
                tokens={"wrap.near": str(NEAR * 2)},  # Transfer 2 NEAR
                receiver_id="alice.near",
                memo="Payment for services"
            ).submit()

            print(f"Transfer intent submitted: {intent_hash}")

    asyncio.run(transfer_via_intent())


Multiple intents in one transaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    async def multiple_intents():
        async with OmniBalance("bob.near", "ed25519:...") as omni:
            intent_hash = await omni.intent() \
                .transfer(
                    tokens={"wrap.near": str(NEAR)},
                    receiver_id="alice.near"
                ) \
                .token_diff(
                    diff={"usdt.tether-token.near": "-500000", "wrap.near": "500000000000000000000000"}
                ) \
                .submit()

            print(f"Multiple intents submitted: {intent_hash}")

    asyncio.run(multiple_intents())


Simulate before submitting
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    async def simulate_first():
        async with OmniBalance("bob.near", "ed25519:...") as omni:
            builder = omni.intent().token_diff(
                diff={"usdt.tether-token.near": "-1000000", "wrap.near": "1000000000000000000000000"}
            )

            # Simulate first
            commitment = builder.sign()
            try:
                simulation = await omni.simulate_intent(commitment)
                print(f"Simulation successful: {simulation}")
                
                # If simulation succeeds, submit
                intent_hash = await omni.publish_intents(commitment)
                print(f"Intent submitted: {intent_hash}")
                
                # Wait for transaction hash
                tr_hash = await omni.get_tr_hash_from_intent(intent_hash)
                if tr_hash:
                    print(f"Transaction hash: {tr_hash}")
            except SimulationError as e:
                print(f"Simulation failed: {e}")

    asyncio.run(simulate_first())


Get swap quote
~~~~~~~~~~~~~~

.. code:: python

    from py_near.omni_balance.quote import get_quote_hash

    async def get_quote():
        quote = await get_quote_hash(
            token_from="usdt.tether-token.near",
            token_to="wrap.near",
            amount_in="1000000"  # 1 USDT
        )

        if quote:
            print(f"Input: {quote.amount_in} {quote.token_in}")
            print(f"Output: {quote.amount_out} {quote.token_out}")
            print(f"Route hashes: {quote.quote_hashes}")
        else:
            print("No quote available")

    asyncio.run(get_quote())


Exceptions
----------

.. exception:: SimulationError

   Exception raised when intent simulation fails.

   .. code:: python

       from py_near.omni_balance import SimulationError

       try:
           await omni.simulate_intent(commitment)
       except SimulationError as e:
           print(f"Error: {e.message}")
           print(f"Error data: {e.error_data}")

