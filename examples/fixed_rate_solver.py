"""
Example of using SolverFixedRate for OmniBalance.
SolverFixedRate provides quotes based on fixed USD prices for tokens.
"""
import asyncio
from decimal import Decimal

from py_near.omni_balance import OmniBalance
from py_near.omni_balance.solver.solver import run_solver
from py_near.omni_balance.solver.solver_fix_rate import (
    SolverFixedRate,
    SolverRateTokenConfig,
)


async def main():
    """Main function to run the fixed rate solver."""
    omni_balance = OmniBalance(
        account_id="your-account.near",
        private_key="ed25519:your-private-key-here",
        rpc_addr="https://rpc.mainnet.near.org",
    )

    await omni_balance.startup()

    solvers = [
        SolverFixedRate(
            tokens_to_swap=[
                SolverRateTokenConfig(
                    intent_token_id="nep141:wrap.near",
                    decimal=24,
                    sell_to_usd_price=Decimal("3.5"),
                    buy_for_usd_price=Decimal("3.5"),
                ),
                SolverRateTokenConfig(
                    intent_token_id="nep141:usdt.tether-token.near",
                    decimal=6,
                    sell_to_usd_price=Decimal("1"),
                    buy_for_usd_price=Decimal("1"),
                ),
                SolverRateTokenConfig(
                    intent_token_id="nep141:usdc.fakes.testnet",
                    decimal=6,
                    sell_to_usd_price=Decimal("1"),
                    buy_for_usd_price=Decimal("1"),
                ),
            ],
            swap_limit_usd=1000.0,
        )
    ]

    print("Starting fixed rate solver...")
    print("Solver will connect to solver bus and process quote requests.")

    await run_solver(
        solvers=solvers,
        omni_balance=omni_balance,
        extra_headers=dict(),
        deadline=20,
    )


if __name__ == "__main__":
    asyncio.run(main())

