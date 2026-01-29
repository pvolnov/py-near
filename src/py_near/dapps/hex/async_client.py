"""HEX Orderbook client for NEAR Protocol."""

import json
from decimal import Decimal
from typing import Dict, List, Optional, TYPE_CHECKING

from py_near.omni_balance.constants import OmniToken
from py_near.dapps.hex.models import (
    GetOrdersItemModel,
    LimitOrderModel,
    MarketOrderModel,
    OrderBookFeesModel,
    RawOrderBookModel,
    SimulateMarketOrderResponseModel,
)

if TYPE_CHECKING:
    from py_near.omni_balance import OmniBalance


ORDERBOOK_CONTRACT = "orderbook.fi.tg"
FEE_COLLECTOR = "intents.fi.tg"
DEFAULT_FEE = 30


class OrderbookClient:
    """
    Client for interacting with HEX orderbook.

    Provides methods for placing limit/market orders, querying orderbook state,
    and managing orders via OmniBalance.

    Args:
        near_intent: OmniBalance instance for intent operations.
        base: Base token identifier (e.g., "nep245:v2_1.omni.hot.tg:4444119_wyixUKCL").
        decimal_base: Decimal places for base token.
        quote: Quote token identifier. Defaults to USDT.
        decimal_quote: Decimal places for quote token. Defaults to 6.
        fee_collector: Fee collector account. Defaults to "intents.fi.tg".
        fee: Fee in basis points. Defaults to 100 (0.01%).

    Example:
        >>> async with OmniBalance(...) as near_intent:
        ...     ob = OrderbookClient(
        ...         near_intent,
        ...         base="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
        ...         decimal_base=9,
        ...     )
        ...     orderbook = await ob.get_orderbook()
        ...     orderbook.print()
    """

    def __init__(
        self,
        near_intent: "OmniBalance",
        base: str,
        decimal_base: int,
        quote: str = OmniToken.USDT,
        decimal_quote: int = 6,
        fee_collector: str = FEE_COLLECTOR,
        fee: int = DEFAULT_FEE,
    ):
        self.near_intent = near_intent
        self.base = base
        self.quote = quote
        self.decimal_base = decimal_base
        self.decimal_quote = decimal_quote
        self.fee_collector = fee_collector
        self.fee = fee

    @property
    def token_pair(self) -> dict:
        """Token pair dict with base and quote."""
        return dict(base=self.base, quote=self.quote)

    @property
    def fee_token_id(self) -> str:
        """Token ID used for fees."""
        return self.base

    @property
    def fee_data(self) -> dict:
        """Fee configuration for order placement."""
        return dict(refs=[dict(fee=self.fee, collector=self.fee_collector)])

    def get_price(self, float_price: float) -> str:
        """
        Convert float price to orderbook price format.

        Args:
            float_price: Human-readable price (e.g., 1.5 for $1.50).

        Returns:
            Price string in orderbook format accounting for decimal differences.
        """
        float_price = Decimal(str(float_price))
        price = float_price * (10**self.decimal_quote) / (10**self.decimal_base)
        return format(price, "f")

    async def get_orderbook(self, depth: int = 10) -> RawOrderBookModel:
        """
        Get orderbook with asks and bids.

        Args:
            depth: Number of price levels to retrieve. Defaults to 10.

        Returns:
            RawOrderBookModel with asks and bids lists.
        """
        res = await self.near_intent._account.view_function(
            ORDERBOOK_CONTRACT,
            "get_orderbook",
            dict(token_pair=self.token_pair, depth=depth),
        )
        return RawOrderBookModel(**res.result, decimal_from=self.decimal_base, decimal_to=self.decimal_quote)

    async def get_protocol_fee(self) -> OrderBookFeesModel:
        """
        Get protocol fee configuration for token pair.

        Returns:
            OrderBookFeesModel with taker and maker fee collectors.
        """
        res = await self.near_intent._account.view_function(
            ORDERBOOK_CONTRACT,
            "get_protocol_fee",
            dict(token_pair=self.token_pair),
        )
        return OrderBookFeesModel(**res.result)

    async def get_pending_balance(self) -> Dict[str, str]:
        """
        Get pending balance for current user.

        Returns:
            Dict mapping token IDs to pending amounts.
        """
        res = await self.near_intent._account.view_function(
            ORDERBOOK_CONTRACT,
            "get_user_balance",
            dict(account_id=self.near_intent.account_id),
        )
        return res.result

    async def claim_pending_balance(self) -> str:
        """
        Claim pending balance from orderbook.

        Returns:
            Transaction hash.
        """
        intent = self.near_intent.auth_call(
            contract_id=ORDERBOOK_CONTRACT,
            msg=json.dumps(dict(action="claim_balance")),
        ).sign()
        return await self.near_intent.publish_intents(intent, wait_for_settlement=True)

    async def get_orders(
        self, skip: int = 0, limit: int = 10
    ) -> List[GetOrdersItemModel]:
        """
        Get orders for token pair.

        Args:
            skip: Number of orders to skip. Defaults to 0.
            limit: Maximum orders to return. Defaults to 10.

        Returns:
            List of GetOrdersItemModel with order details.
        """
        res = await self.near_intent._account.view_function(
            ORDERBOOK_CONTRACT,
            "get_orders",
            dict(skip=skip, limit=limit, token_pair=self.token_pair),
        )
        return [GetOrdersItemModel(**item) for item in res.result]

    def build_limit_order(self, price: str) -> dict:
        """
        Build limit order data.

        Args:
            price: Price in orderbook format (use get_price() to convert).

        Returns:
            Order data dict ready for submission.
        """
        order = LimitOrderModel(
            token_pair=self.token_pair,
            price=price,
            **self.fee_data,
        )
        return order.model_dump(exclude_none=True)

    def build_market_order(
        self,
        min_amount_out: Optional[str] = None,
        exact_amount_out: Optional[str] = None,
    ) -> dict:
        """
        Build market order data.

        Args:
            min_amount_out: Minimum amount to receive (slippage protection).
            exact_amount_out: Exact amount to receive.

        Returns:
            Order data dict ready for submission.
        """
        if min_amount_out is None and exact_amount_out is None:
            min_amount_out = "0"
        order = MarketOrderModel(
            token_pair=self.token_pair,
            min_amount_out=str(int(min_amount_out)) if min_amount_out else None,
            exact_amount_out=str(int(exact_amount_out)) if exact_amount_out else None,
            **self.fee_data,
        )
        return order.model_dump(exclude_none=True)

    async def place_limit_order(self, price: str, amount: str, token_in: str) -> str:
        """
        Place limit order.

        Args:
            price: Price in orderbook format (use get_price() to convert).
            amount: Amount to sell in raw units (smallest denomination).
            token_in: Token ID being sold.

        Returns:
            Transaction hash.
        """
        tokens = {token_in: amount}
        order_data = self.build_limit_order(price)
        intent = self.near_intent.transfer(
            tokens=tokens,
            receiver_id=ORDERBOOK_CONTRACT,
            msg=json.dumps(order_data),
        ).sign()
        return await self.near_intent.publish_intents(intent, wait_for_settlement=True)

    async def place_market_order(
        self,
        amount: str,
        token_in: str,
        min_amount_out: Optional[str] = None,
        exact_amount_out: Optional[str] = None,
    ) -> str:
        """
        Place market order.

        Args:
            amount: Amount to sell in raw units.
            token_in: Token ID being sold.
            min_amount_out: Minimum amount to receive (slippage protection).
            exact_amount_out: Exact amount to receive.

        Returns:
            Transaction hash.
        """
        tokens = {token_in: amount}
        order_data = self.build_market_order(min_amount_out, exact_amount_out)
        intent = self.near_intent.transfer(
            tokens=tokens,
            receiver_id=ORDERBOOK_CONTRACT,
            msg=json.dumps(order_data),
        ).sign()
        return await self.near_intent.publish_intents(intent, wait_for_settlement=True)

    async def cancel_order(self, order_hash: str) -> str:
        """
        Cancel order by hash.

        Args:
            order_hash: Hash of the order to cancel.

        Returns:
            Transaction hash.
        """
        intent = self.near_intent.auth_call(
            contract_id=ORDERBOOK_CONTRACT,
            msg=json.dumps(dict(action="close_order", data=order_hash)),
        ).sign()
        return await self.near_intent.publish_intents(intent, wait_for_settlement=True)



    async def simulate_market_order(
        self,
        amount: str,
        token_in: str,
        exact_amount_out: Optional[str] = None,
        min_amount_out: Optional[str] = None,
    ) -> SimulateMarketOrderResponseModel:
        """
        Simulate market order to get quote.

        Args:
            amount: Amount to sell in raw units.
            token_in: Token ID being sold.
            exact_amount_out: Exact amount to receive.
            min_amount_out: Minimum amount to receive. (Only if exact_amount_out is not provided)

        Returns:
            SimulateMarketOrderResponseModel with fill details.
        """
        amount = str(int(amount))
        order_placement_action = dict(
            token_pair=self.token_pair,
            order_type="market",
        )
        if min_amount_out is not None:
            order_placement_action["min_amount_out"] = str(int(min_amount_out))
        elif exact_amount_out is not None:
            order_placement_action["exact_amount_out"] = str(int(exact_amount_out))
        else:
            order_placement_action["min_amount_out"] = "0"
        res = await self.near_intent._account.view_function(
            ORDERBOOK_CONTRACT,
            "get_quote_pub",
            dict(
                ext=self.fee_data,
                amount=amount,
                token_id=token_in,
                order_placement_action=order_placement_action,
            ),
        )
        return SimulateMarketOrderResponseModel(**res.result)
