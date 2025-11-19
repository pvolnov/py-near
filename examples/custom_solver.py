"""
Example of creating and running a custom solver for OmniBalance.
Solver provides token swap quotes via WebSocket connection to solver bus.
"""
import asyncio
from decimal import Decimal
from typing import Optional

from py_near.omni_balance import OmniBalance
from py_near.omni_balance.solver.core import SolverRate
from py_near.omni_balance.solver.solver import run_solver


class MyCustomSolver(SolverRate):
    """Custom solver with simple 1:1 exchange rate logic for supported token pairs."""

    def __init__(self):
        self.supported_tokens = {
            "nep141:wrap.near": {"decimal": 24, "rate": Decimal("1")},
            "nep141:usdt.tether-token.near": {"decimal": 6, "rate": Decimal("1")},
        }

    async def get_amount_out(
        self, token_in: str, token_out: str, amount_in: float
    ) -> Optional[Decimal]:
        """Calculate output token amount for given input amount."""
        if token_in not in self.supported_tokens:
            return None
        if token_out not in self.supported_tokens:
            return None

        token_in_info = self.supported_tokens[token_in]
        token_out_info = self.supported_tokens[token_out]

        try:
            amount_in_decimal = Decimal(str(amount_in))
            amount_in_normalized = amount_in_decimal / (
                Decimal(10) ** token_in_info["decimal"]
            )

            amount_out_normalized = (
                amount_in_normalized
                * token_in_info["rate"]
                / token_out_info["rate"]
            )

            amount_out = amount_out_normalized * (Decimal(10) ** token_out_info["decimal"])

            return amount_out.quantize(Decimal("1"))
        except (ArithmeticError, ValueError):
            return None

    async def get_amount_in(
        self, token_in: str, token_out: str, amount_out: float
    ) -> Optional[Decimal]:
        """Calculate required input token amount for desired output amount."""
        if token_in not in self.supported_tokens:
            return None
        if token_out not in self.supported_tokens:
            return None

        token_in_info = self.supported_tokens[token_in]
        token_out_info = self.supported_tokens[token_out]

        try:
            amount_out_decimal = Decimal(str(amount_out))
            amount_out_normalized = amount_out_decimal / (
                Decimal(10) ** token_out_info["decimal"]
            )

            amount_in_normalized = (
                amount_out_normalized
                * token_out_info["rate"]
                / token_in_info["rate"]
            )

            amount_in = amount_in_normalized * (Decimal(10) ** token_in_info["decimal"])

            return amount_in.quantize(Decimal("1"))
        except (ArithmeticError, ValueError):
            return None


async def main():
    """Main function to run the solver."""
    omni_balance = OmniBalance(
        account_id="your-account.near",
        private_key="ed25519:your-private-key-here",
        rpc_addr="https://rpc.mainnet.near.org",
    )

    await omni_balance.startup()

    solvers = [
        MyCustomSolver(),
    ]

    print("Starting solver...")
    print("Solver will connect to solver bus and process quote requests.")

    await run_solver(
        solvers=solvers,
        omni_balance=omni_balance,
        extra_headers=dict(),
        deadline=20,
    )


if __name__ == "__main__":
    asyncio.run(main())
