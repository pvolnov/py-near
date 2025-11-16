"""Main logic for getting token swap quotes."""

import asyncio
from typing import Optional, List

from py_near.omni_balance.constants import (
    USDT_TOKEN,
    WRAP_NEAR,
    NEAR_CONTRACT_BY_ASSET,
)
from py_near.omni_balance.models import QuoteHashOutModel
from py_near.omni_balance.solver import get_direct_quote


async def _check_with_middleware(
    path: List[str],
    amount_in: Optional[str] = None,
    exact_amount_out: Optional[str] = None,
) -> Optional[QuoteHashOutModel]:
    """
    Check if swap is possible through intermediate tokens.

    Performs sequential swaps through a chain of tokens from path.
    For example, for path=[A, B, C] performs swap A->B, then B->C.

    Args:
        path: List of tokens for sequential swap
        amount_in: Input token amount (for the first swap)
        exact_amount_out: Exact output token amount (for the last swap)

    Returns:
        Quote result model or None if swap is not possible
    """
    if len(path) < 2:
        return None

    # Import here to avoid circular dependencies
    from py_near.omni_balance.quote import get_quote_hash

    current_amount_in = amount_in
    current_exact_amount_out = None
    total_quote_hashes = []
    final_amount_out = None
    final_amount_in = amount_in

    for i in range(len(path) - 1):
        token_from = path[i]
        token_to = path[i + 1]

        if i == len(path) - 2 and exact_amount_out:
            current_exact_amount_out, current_amount_in = exact_amount_out, None
        quote = await get_quote_hash(token_from=token_from, token_to=token_to, amount_in=current_amount_in, exact_amount_out=current_exact_amount_out, deep=2)
        if not quote:
            return None
        total_quote_hashes.extend(quote.quote_hashes)
        final_amount_out = quote.amount_out
        if i < len(path) - 2:
            current_amount_in, current_exact_amount_out = quote.amount_out, None

    if not final_amount_out or not total_quote_hashes:
        return None

    return QuoteHashOutModel(
        quote_hashes=total_quote_hashes,
        amount_out=final_amount_out,
        amount_in=final_amount_in or "0",
        token_in=path[0],
        token_out=path[-1],
    )


async def get_quote_hash(
    token_from: str,
    token_to: str,
    amount_in: Optional[str] = None,
    deep: int = 1,
    exact_amount_out: Optional[str] = None,
    asset_from: Optional[str] = None,
    asset_to: Optional[str] = None,
) -> Optional[QuoteHashOutModel]:
    """
    Get token swap quote with support for intermediate routes.

    Function attempts to find the best swap route between two tokens:
    1. Direct swap through Solver Bus API
    2. Swap through intermediate tokens (USDT, WRAP_NEAR, or asset contracts)

    Args:
        token_from: Input token identifier
        token_to: Output token identifier
        amount_in: Input token amount (for calculating exact_amount_in)
        deep: Recursion depth for searching intermediate routes (default 1)
        exact_amount_out: Exact output token amount (for calculating exact_amount_out)
        asset_from: Asset identifier for input token (for contract lookup)
        asset_to: Asset identifier for output token (for contract lookup)

    Returns:
        Quote result model with the best route or None if swap is not possible

    Note:
        - If token_from == token_to, returns None
        - If deep > 2, returns None (recursion depth limit)
        - Route with maximum amount_out is selected
    """
    if deep > 2:
        return None

    if token_from == token_to:
        return None

    # Get direct quote
    direct_quote = await get_direct_quote(
        token_from=token_from,
        token_to=token_to,
        amount_in=amount_in,
        exact_amount_out=exact_amount_out,
    )

    quotes_with_middleware = []
    if deep == 1:
        quotes_with_middleware = [
            _check_with_middleware([token_from, USDT_TOKEN, token_to], amount_in=amount_in, exact_amount_out=exact_amount_out),
            _check_with_middleware([token_from, WRAP_NEAR, token_to], amount_in=amount_in, exact_amount_out=exact_amount_out),
        ]
        asset_from_contract = NEAR_CONTRACT_BY_ASSET.get(asset_from) if asset_from else None
        asset_to_contract = NEAR_CONTRACT_BY_ASSET.get(asset_to) if asset_to else None
        for cond, path in [
            (asset_from_contract and asset_from_contract != token_from, [token_from, asset_from_contract, token_to]),
            (asset_to_contract and asset_to_contract != token_to, [token_from, asset_to_contract, token_to]),
            (asset_from_contract and asset_from_contract != token_from and asset_to_contract and asset_to_contract != token_to, [token_from, asset_from_contract, asset_to_contract, token_to]),
        ]:
            if cond:
                quotes_with_middleware.append(_check_with_middleware(path, amount_in=amount_in, exact_amount_out=exact_amount_out))

    res = direct_quote
    if quotes_with_middleware:
        for quote in await asyncio.gather(*quotes_with_middleware):
            if quote and (not res or int(res.amount_out) < int(quote.amount_out)):
                res = quote
    return res

