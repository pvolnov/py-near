from decimal import Decimal
from typing import List, Optional

from py_near.omni_balance.solver.core import SolverRate


class SolverRateTokenConfig:
    def __init__(
        self,
        intent_token_id: str,
        decimal: int,
        sell_to_usd_price: Decimal,
        buy_for_usd_price: Decimal,
    ):
        self.intent_token_id = intent_token_id
        self.decimal = decimal
        self.sell_to_usd_price = sell_to_usd_price  # amount of USD for 1 token
        self.buy_for_usd_price = buy_for_usd_price  # amount of token for 1 USD


class SolverFixedRate(SolverRate):
    def __init__(
        self, tokens_to_swap: List[SolverRateTokenConfig], swap_limit_usd: float = 10
    ):
        self.tokens_to_swap = tokens_to_swap
        self.swap_limit_usd = swap_limit_usd
        self.token_by_contract = {t.intent_token_id: t for t in tokens_to_swap}

    async def get_amount_in(
        self, token_in_contract, token_out_contract, amount_out: str
    ) -> Optional[Decimal]:
        token_in = self.token_by_contract.get(token_in_contract)
        token_out = self.token_by_contract.get(token_out_contract)

        if not token_in or not token_out:
            return None

        try:
            amount = Decimal(amount_out)
            amount_out_usd = (
                amount / Decimal(10) ** token_out.decimal * token_out.buy_for_usd_price
            )
            amount_in = (
                amount_out_usd
                / token_in.sell_to_usd_price
                * Decimal(10) ** token_in.decimal
            )
            return amount_in.quantize(Decimal("1"))
        except (ArithmeticError, ValueError):
            return None

    async def get_amount_out(
        self, token_in_contract, token_out_contract, amount_in: str
    ) -> Optional[Decimal]:
        token_in = self.token_by_contract.get(token_in_contract)
        token_out = self.token_by_contract.get(token_out_contract)

        if not token_in or not token_out:
            return None

        try:
            amount = Decimal(amount_in)
            amount_in_usd = (
                amount / Decimal(10) ** token_in.decimal * token_in.sell_to_usd_price
            )
            amount_out = (
                amount_in_usd
                / token_out.buy_for_usd_price
                * Decimal(10) ** token_out.decimal
            )
            return amount_out.quantize(Decimal("1"))
        except (ArithmeticError, ValueError):
            return None
