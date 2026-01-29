"""Models for HEX orderbook."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class TokenPairModel(BaseModel):
    """
    Token pair for orderbook trading.

    Attributes:
        base: Base token identifier.
        quote: Quote token identifier.
    """

    base: str
    quote: str


class OrderEntryModel(BaseModel):
    """
    Single order entry in orderbook.

    Attributes:
        price: Order price in raw format.
        order_balance: Remaining order balance in raw units.
    """

    price: str
    order_balance: str


class FeeCollectorModel(BaseModel):
    """
    Fee collector configuration.

    Attributes:
        fee: Fee in basis points.
        collector: Fee collector account ID.
    """

    fee: int
    collector: str


class OrderBookFeesModel(BaseModel):
    """
    Protocol fee configuration for orderbook.

    Attributes:
        taker_fee_collectors: List of taker fee collectors.
        maker_fee_collectors: List of maker fee collectors.
    """

    taker_fee_collectors: List[FeeCollectorModel]
    maker_fee_collectors: List[FeeCollectorModel]


class RawOrderBookModel(BaseModel):
    """
    Raw orderbook with asks and bids.

    Attributes:
        decimal_from: Decimal places for base token.
        decimal_to: Decimal places for quote token.
        asks: List of sell orders (sorted by price ascending).
        bids: List of buy orders (sorted by price descending).
    """

    decimal_from: int
    decimal_to: int
    asks: List[OrderEntryModel]
    bids: List[OrderEntryModel]

    def print(self) -> None:
        """Print formatted orderbook."""
        print(f"ASKS:↓ {self.decimal_from} {self.decimal_to}")
        for ask in self.asks[::-1]:
            price = float(ask.price) / 10**(self.decimal_to - self.decimal_from)
            print(f"${price}", int(ask.order_balance) / 10**self.decimal_from)
        print("-----")
        for bid in self.bids:
            price = float(bid.price) / 10**(self.decimal_to - self.decimal_from)
            print(f"${price}", int(bid.order_balance) / 10**self.decimal_to)
        print(f"BIDS:↑ {self.decimal_from} {self.decimal_to}")


class FeeRefModel(BaseModel):
    """
    Fee reference for order placement.

    Attributes:
        fee: Fee in basis points.
        collector: Fee collector account ID.
    """

    fee: int
    collector: str


class LimitOrderModel(BaseModel):
    """
    Limit order data model.

    Attributes:
        token_pair: Token pair with base and quote.
        price: Limit price in raw format.
        refs: Fee references.
        order_type: Order type identifier.
    """

    token_pair: dict
    price: str
    refs: List[FeeRefModel] = []
    order_type: str = "limit"


class MarketOrderModel(BaseModel):
    """
    Market order data model.

    Attributes:
        token_pair: Token pair with base and quote.
        min_amount_out: Minimum amount to receive (slippage protection).
        exact_amount_out: Exact amount to receive.
        refs: Fee references.
        order_type: Order type identifier.
    """

    token_pair: dict
    min_amount_out: Optional[str] = None
    exact_amount_out: Optional[str] = None
    refs: List[FeeRefModel] = []
    order_type: str = "market"


class FeeConfigModel(BaseModel):
    """
    Fee configuration in order fill result.

    Attributes:
        taker_fee_collectors: List of taker fee collectors.
        maker_fee_collectors: List of maker fee collectors.
    """

    taker_fee_collectors: List[FeeCollectorModel]
    maker_fee_collectors: List[FeeCollectorModel]


class TakerTypeModel(BaseModel):
    """
    Taker order type details.

    Attributes:
        order_type: Order type (market/limit).
        min_amount_out: Minimum output amount.
    """

    order_type: str
    min_amount_out: str


class BookFillResultDetailModel(BaseModel):
    """
    Detailed result of orderbook fill simulation.

    Attributes:
        taker_type: Taker order type details.
        taker_side: Taker side (buy/sell).
        token_pair: Token pair with base and quote.
        taker_receive_total: Total amount taker receives.
        taker_unspent: Unspent taker input amount.
        makers_receive_total_by_account: Total received by each maker account.
        updated_balance_by_order: Updated balance for each order.
        taker_fee_quote: Taker fee in quote token.
        makers_total_fee_quote: Total maker fees in quote token.
        fee_config: Fee configuration.
    """

    taker_type: TakerTypeModel
    taker_side: str
    token_pair: Dict[str, str]
    taker_receive_total: str
    taker_unspent: str
    makers_receive_total_by_account: Dict[str, str]
    updated_balance_by_order: Dict[str, str]
    taker_fee_quote: str
    makers_total_fee_quote: str
    fee_config: FeeConfigModel


class SimulateMarketOrderResponseModel(BaseModel):
    """
    Response from market order simulation.

    Attributes:
        book_fill_result: Detailed fill result.
        taker_remainder: Remaining taker input if partially filled.
        increase_user_balance: Balance increases by user and token.
    """

    book_fill_result: BookFillResultDetailModel
    taker_remainder: Optional[Dict[str, str]] = None
    increase_user_balance: Dict[str, Dict[str, int]]


class OrderInfoModel(BaseModel):
    """
    Order information.

    Attributes:
        side: Order side (buy/sell).
        maker: Maker account ID.
        price: Order price in raw format.
        token_pair: Token pair.
        created_ts: Creation timestamp (unix).
    """

    side: str
    maker: str
    price: str
    token_pair: TokenPairModel
    created_ts: int


class GetOrdersItemModel(BaseModel):
    """
    Order item from get_orders response.

    Attributes:
        hash: Order hash identifier.
        order: Order details.
        order_balance: Remaining order balance.
    """

    hash: str
    order: OrderInfoModel
    order_balance: str
