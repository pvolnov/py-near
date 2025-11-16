"""Client for working with Solver Bus API."""

import asyncio
import time
from typing import Optional
from uuid import uuid4

import aiohttp
from loguru import logger

from py_near.omni_balance.constants import SOLVER_BUS_URL, INTENTS_HEADERS
from py_near.omni_balance.models import QuoteHashOutModel


async def get_direct_quote(
    token_from: str,
    token_to: str,
    amount_in: Optional[str] = None,
    exact_amount_out: Optional[str] = None,
) -> Optional[QuoteHashOutModel]:
    """
    Get direct token swap quote through Solver Bus API.

    Args:
        token_from: Input token identifier
        token_to: Output token identifier
        amount_in: Input token amount (if specified, uses exact_amount_in)
        exact_amount_out: Exact output token amount (if specified, uses exact_amount_out)

    Returns:
        Quote result model or None if quote is not available
    """
    if not (amount_in or exact_amount_out):
        return None
    request = {
        "defuse_asset_identifier_in": token_from,
        "defuse_asset_identifier_out": token_to,
        **(dict(exact_amount_in=amount_in) if amount_in else dict(exact_amount_out=exact_amount_out)),
        "min_deadline_ms": 10000,
        "max_wait_ms": 1000,
        "min_wait_ms": 100,
    }
    rpc_request = {
        "id": f"hot_wallet_{token_from}_{uuid4().hex}",
        "jsonrpc": "2.0",
        "method": "quote",
        "params": [request],
    }

    ts = time.time()
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(SOLVER_BUS_URL, json=rpc_request, timeout=2, headers=INTENTS_HEADERS) as response:
                result = await response.json()
                logger.info(f"Solver response {time.time() - ts:.1f} {token_from}->{token_to}: {rpc_request['id']} {result}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while getting quote for {token_from} -> {token_to}")
            return None
        except Exception as e:
            logger.error(f"Error while getting quote for {token_from} -> {token_to}: {e}")
            return None

        if result.get("result"):
            results = sorted(
                result["result"],
                key=lambda x: int(x.get("amount_in" if exact_amount_out else "amount_out", 0)),
                reverse=not exact_amount_out,
            )
            if results and "amount_out" in results[0]:
                return QuoteHashOutModel(
                    quote_hashes=[results[0]["quote_hash"]],
                    amount_out=results[0]["amount_out"],
                    amount_in=results[0]["amount_in"],
                    token_in=token_from,
                    token_out=token_to,
                )
    return None

