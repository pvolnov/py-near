from decimal import Decimal
from typing import Optional


class SolverRate:
    async def get_amount_out(self, token_in, token_out, amount_in: float) -> Optional[Decimal]:
        raise NotImplementedError("get_swap_rate method not implemented")

    async def get_amount_in(self, token_in, token_out, amount_out: float) -> Optional[Decimal]:
        raise NotImplementedError("get_swap_rate method not implemented")
