
HeX Orderbook
=============

.. note::
   HeX is a decentralized orderbook for trading tokens on NEAR Protocol.
   It provides limit orders, market orders, and order management through the OmniBalance intents system.

Quick start
-----------

.. code:: python

    from py_near.omni_balance import OmniBalance
    from py_near.dapps.hex import OrderbookClient
    import asyncio

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."

    async def main():
        async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
            # Initialize orderbook client for HOT/USDT pair
            ob = OrderbookClient(
                omni,
                base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",  # HOT token
                decimal_base=9,  # HOT has 9 decimals
            )
            
            # Get and print orderbook
            orderbook = await ob.get_orderbook()
            orderbook.print()

    asyncio.run(main())


Documentation
-------------

.. class:: OrderbookClient

   Client for interacting with HeX orderbook. Provides methods for placing limit/market orders,
   querying orderbook state, and managing orders via OmniBalance.

   .. code:: python

       ob = OrderbookClient(
           near_intent,
           base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
           decimal_base=9,
           quote="nep141:usdt.tether-token.near",  # optional, defaults to USDT
           decimal_quote=6,  # optional, defaults to 6
           fee_collector="intents.fi.tg",  # optional
           fee=30,  # optional, fee in basis points
       )

   :param near_intent: OmniBalance instance for intent operations
   :param base: Base token identifier (e.g., "nep245:v2_1.omni.hot.tg:4444119_wyixUKCL")
   :param decimal_base: Decimal places for base token
   :param quote: Quote token identifier (default: USDT)
   :param decimal_quote: Decimal places for quote token (default: 6)
   :param fee_collector: Fee collector account (default: "intents.fi.tg")
   :param fee: Fee in basis points (default: 30)


Get Orderbook
-------------

Retrieve current orderbook with asks (sell orders) and bids (buy orders).

.. function:: get_orderbook(depth: int = 10) -> RawOrderBookModel

   Get orderbook with asks and bids.

   :param depth: Number of price levels to retrieve (default: 10)
   :return: RawOrderBookModel with asks and bids lists

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Get orderbook with 10 levels
           orderbook = await ob.get_orderbook(depth=10)
           
           # Pretty print orderbook
           orderbook.print()
           
           # Access asks and bids directly
           for ask in orderbook.asks:
               print(f"Ask: price={ask.price}, amount={ask.order_balance}")
           
           for bid in orderbook.bids:
               print(f"Bid: price={bid.price}, amount={bid.order_balance}")


Simulate Market Order
---------------------

Simulate a market order to get a quote before execution. This is useful to check
expected output and slippage.

.. function:: simulate_market_order(amount: str, token_in: str, exact_amount_out: Optional[str] = None, min_amount_out: Optional[str] = None) -> SimulateMarketOrderResponseModel

   Simulate market order to get quote.

   :param amount: Amount to sell in raw units (smallest denomination)
   :param token_in: Token ID being sold
   :param exact_amount_out: Exact amount to receive (optional)
   :param min_amount_out: Minimum amount to receive (optional, slippage protection)
   :return: SimulateMarketOrderResponseModel with fill details

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Simulate selling 0.1 HOT
           amount_in = int(0.1 * 10**9)  # 0.1 HOT in raw units
           result = await ob.simulate_market_order(
               str(amount_in),
               token_in="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               min_amount_out="0",
           )
           
           # Check expected output
           print(f"Will receive: {result.book_fill_result.taker_receive_total}")
           print(f"Unspent input: {result.book_fill_result.taker_unspent}")
           print(f"Total spent: {amount_in - int(result.book_fill_result.taker_unspent)}")

Simulate with exact output amount
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   # Simulate to receive exactly 0.01 HOT worth of USDT
   result = await ob.simulate_market_order(
       str(int(0.1 * 10**6)),  # 0.1 USDT max input
       token_in="nep141:usdt.tether-token.near",
       exact_amount_out=str(int(0.01 * 10**9)),  # exactly 0.01 HOT output
   )
   print(f"Will receive: {result.book_fill_result.taker_receive_total}")

Simulate large order
~~~~~~~~~~~~~~~~~~~~

.. code:: python

   # Simulate a large market buy
   result = await ob.simulate_market_order(
       "1000000000000000000000000000000",  # Large amount
       token_in="nep141:wrap.near",
   )
   print(result.dict())


Place Market Order
------------------

Execute a market order that fills immediately at the best available prices.

.. function:: place_market_order(amount: str, token_in: str, min_amount_out: Optional[str] = None, exact_amount_out: Optional[str] = None) -> str

   Place market order.

   :param amount: Amount to sell in raw units
   :param token_in: Token ID being sold
   :param min_amount_out: Minimum amount to receive (slippage protection)
   :param exact_amount_out: Exact amount to receive
   :return: Transaction hash

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Sell 0.1 HOT at market price
           tx_hash = await ob.place_market_order(
               amount=str(int(0.1 * 10**9)),
               token_in="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
           )
           print(f"Transaction hash: {tx_hash}")


Place Limit Order
-----------------

Place a limit order at a specific price. The order will remain in the orderbook
until filled or cancelled.

.. function:: place_limit_order(price: str, amount: str, token_in: str) -> str

   Place limit order.

   :param price: Price in orderbook format (use get_price() to convert)
   :param amount: Amount to sell in raw units
   :param token_in: Token ID being sold
   :return: Transaction hash

.. function:: get_price(float_price: float) -> str

   Convert human-readable float price to orderbook price format.

   :param float_price: Human-readable price (e.g., 1.5 for $1.50)
   :return: Price string in orderbook format

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Place sell order: sell 0.35 USDT at price $1.50 per HOT
           tx_hash = await ob.place_limit_order(
               price=ob.get_price(1.50),  # Convert price to orderbook format
               amount=str(int(0.35 * 10**6)),
               token_in="nep141:usdt.tether-token.near",
           )
           print(f"Limit order placed: {tx_hash}")

Place multiple limit orders at different prices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
       ob = OrderbookClient(
           omni,
           base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
           decimal_base=9,
       )
       
       # Place multiple buy orders (USDT -> HOT)
       for price in range(1300, 1700, 30):
           tx_hash = await ob.place_limit_order(
               price=ob.get_price(price / 1000),  # e.g., 1.3, 1.33, 1.36...
               amount=str(int(0.35 * 10**6)),
               token_in="nep141:usdt.tether-token.near",
           )
           print(f"Buy order at ${price/1000}: {tx_hash}")
       
       # Place multiple sell orders (HOT -> USDT)
       for price in range(1700, 2000, 100):
           tx_hash = await ob.place_limit_order(
               price=ob.get_price(price / 1000),  # e.g., 1.7, 1.8, 1.9
               amount=str(int(0.1 * 10**9)),
               token_in="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
           )
           print(f"Sell order at ${price/1000}: {tx_hash}")


Get Orders
----------

Retrieve orders for the token pair.

.. function:: get_orders(skip: int = 0, limit: int = 10) -> List[GetOrdersItemModel]

   Get orders for token pair.

   :param skip: Number of orders to skip (default: 0)
   :param limit: Maximum orders to return (default: 10)
   :return: List of GetOrdersItemModel with order details

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Get orders
           orders = await ob.get_orders(limit=20)
           
           for order in orders:
               print(f"Order hash: {order.hash}")
               print(f"  Maker: {order.order.maker}")
               print(f"  Side: {order.order.side}")
               print(f"  Price: {order.order.price}")
               print(f"  Balance: {order.order_balance}")


Cancel Order
------------

Cancel an existing order by its hash.

.. function:: cancel_order(order_hash: str) -> str

   Cancel order by hash.

   :param order_hash: Hash of the order to cancel
   :return: Transaction hash

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Get orders and cancel own orders
           orders = await ob.get_orders()
           
           for order in orders:
               if order.order.maker == omni.account_id:
                   tx_hash = await ob.cancel_order(order.hash)
                   print(f"Cancelled order {order.hash}: {tx_hash}")


Get Protocol Fee
----------------

Retrieve protocol fee configuration for the token pair.

.. function:: get_protocol_fee() -> OrderBookFeesModel

   Get protocol fee configuration for token pair.

   :return: OrderBookFeesModel with taker and maker fee collectors

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           fees = await ob.get_protocol_fee()
           print(f"Taker fees: {fees.taker_fee_collectors}")
           print(f"Maker fees: {fees.maker_fee_collectors}")


Pending Balance
---------------

Manage pending balances from filled orders.

.. function:: get_pending_balance() -> Dict[str, str]

   Get pending balance for current user.

   :return: Dict mapping token IDs to pending amounts

.. function:: claim_pending_balance() -> str

   Claim pending balance from orderbook.

   :return: Transaction hash

   .. code:: python

       async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
           ob = OrderbookClient(
               omni,
               base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
               decimal_base=9,
           )
           
           # Check pending balance
           pending = await ob.get_pending_balance()
           print(f"Pending balances: {pending}")
           
           # Claim pending balance
           if pending:
               tx_hash = await ob.claim_pending_balance()
               print(f"Claimed: {tx_hash}")


Complete Example
----------------

Full trading workflow
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from py_near.omni_balance import OmniBalance
    from py_near.dapps.hex import OrderbookClient
    import asyncio

    ACCOUNT_ID = "bob.near"
    PRIVATE_KEY = "ed25519:..."

    async def trading_example():
        async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
            # Initialize orderbook for HOT/USDT
            ob = OrderbookClient(
                omni,
                base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
                decimal_base=9,
            )
            
            # 1. View orderbook
            orderbook = await ob.get_orderbook(depth=10)
            orderbook.print()
            
            # 2. Get protocol fees
            fees = await ob.get_protocol_fee()
            print(f"Protocol fees: {fees}")
            
            # 3. Simulate market order before execution
            amount_in = int(0.1 * 10**9)
            simulation = await ob.simulate_market_order(
                str(amount_in),
                token_in="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
                min_amount_out="0",
            )
            print(f"Expected output: {simulation.book_fill_result.taker_receive_total}")
            
            # 4. Place limit orders
            for price in [1.30, 1.35, 1.40]:
                tx = await ob.place_limit_order(
                    price=ob.get_price(price),
                    amount=str(int(0.5 * 10**6)),
                    token_in="nep141:usdt.tether-token.near",
                )
                print(f"Limit order at ${price}: {tx}")
            
            # 5. Place market order
            tx = await ob.place_market_order(
                amount=str(int(0.1 * 10**9)),
                token_in="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
            )
            print(f"Market order: {tx}")
            
            # 6. Check and cancel own orders
            orders = await ob.get_orders()
            for order in orders:
                if order.order.maker == omni.account_id:
                    tx = await ob.cancel_order(order.hash)
                    print(f"Cancelled: {tx}")
            
            # 7. Claim pending balance
            pending = await ob.get_pending_balance()
            if pending:
                tx = await ob.claim_pending_balance()
                print(f"Claimed pending: {tx}")

    asyncio.run(trading_example())


Models
------

.. class:: RawOrderBookModel

   Raw orderbook with asks and bids.

   :param decimal_from: Decimal places for base token
   :param decimal_to: Decimal places for quote token
   :param asks: List of sell orders (sorted by price ascending)
   :param bids: List of buy orders (sorted by price descending)

   .. method:: print()

      Print formatted orderbook to console.


.. class:: OrderEntryModel

   Single order entry in orderbook.

   :param price: Order price in raw format
   :param order_balance: Remaining order balance in raw units


.. class:: GetOrdersItemModel

   Order item from get_orders response.

   :param hash: Order hash identifier
   :param order: Order details (OrderInfoModel)
   :param order_balance: Remaining order balance


.. class:: OrderInfoModel

   Order information.

   :param side: Order side (buy/sell)
   :param maker: Maker account ID
   :param price: Order price in raw format
   :param token_pair: Token pair
   :param created_ts: Creation timestamp (unix)


.. class:: SimulateMarketOrderResponseModel

   Response from market order simulation.

   :param book_fill_result: Detailed fill result
   :param taker_remainder: Remaining taker input if partially filled
   :param increase_user_balance: Balance increases by user and token


.. class:: OrderBookFeesModel

   Protocol fee configuration for orderbook.

   :param taker_fee_collectors: List of taker fee collectors
   :param maker_fee_collectors: List of maker fee collectors

