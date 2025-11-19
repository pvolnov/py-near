import asyncio
import json
import time
from decimal import Decimal
from typing import Any, Dict, List

import websockets
from loguru import logger
from websockets import ClientConnection

from py_near.omni_balance import OmniBalance
from py_near.omni_balance.constants import INTENTS_HEADERS, SOLVER_BUS_WSS
from py_near.omni_balance.solver.core import SolverRate


async def _process_ws_response(
    websocket: ClientConnection,
    solvers: List[SolverRate],
    omni_balance: OmniBalance,
    response: Dict[str, Any],
    deadline: int = 20,
) -> None:
    """
    Process WebSocket response from solver bus and send quote response.

    Handles both exact_amount_in and exact_amount_out quote requests by:
    1. Extracting token pair and amount from the request
    2. Querying all solvers for the best rate
    3. Creating and signing a quote response
    4. Sending the response back through the WebSocket

    Args:
        websocket: WebSocket client connection to solver bus
        solvers: List of solver rate providers to query for quotes
        omni_balance: OmniBalance instance for creating and signing quotes
        response: WebSocket response dictionary containing quote request data
        deadline: Quote deadline in seconds. Defaults to 20 seconds

    Returns:
        None. If no valid quote can be generated, the function returns early.
    """
    data = response["params"]["data"]
    if "exact_amount_in" in data:
        token_in, token_out = (
            data["defuse_asset_identifier_in"],
            data["defuse_asset_identifier_out"],
        )
        amount_in = data["exact_amount_in"]
        amount_out = Decimal(0)
        for s in solvers:
            solver_amount_out = await s.get_amount_out(token_in, token_out, amount_in)
            if solver_amount_out:
                amount_out = max(amount_out, solver_amount_out)
        if not amount_out:
            return
    else:
        token_in, token_out = (
            data["defuse_asset_identifier_in"],
            data["defuse_asset_identifier_out"],
        )
        amount_out = data["exact_amount_out"]
        amount_in = Decimal("inf")
        for s in solvers:
            solver_amount_in = await s.get_amount_in(token_in, token_out, amount_out)
            if solver_amount_in:
                amount_in = min(amount_in, solver_amount_in)
        if amount_in == Decimal("inf"):
            return
    signed_quote = (
        omni_balance.token_diff(
            diff={token_in: str(int(amount_in)), token_out: str(-int(amount_out))},
        )
        .with_deadline(deadline)
        .sign()
    )

    await websocket.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": int(time.time() * 100000),
                "method": "quote_response",
                "params": [
                    dict(
                        quote_id=data["quote_id"],
                        quote_output={
                            "amount_out": str(int(amount_out)),
                            "amount_in": str(int(amount_in)),
                        },
                        signed_data=signed_quote.model_dump(),
                    )
                ],
            }
        )
    )
    logger.info(f"Send quote response to {data['quote_id']}")


async def run_solver(
    solvers: List[SolverRate],
    omni_balance: OmniBalance,
    extra_headers: Dict[str, str] = INTENTS_HEADERS,
    deadline: int = 20,
) -> None:
    """
    Run solver service that listens for quote requests and responds with quotes.

    This function establishes a WebSocket connection to the solver bus and:
    1. Subscribes to quote requests
    2. Processes incoming quote requests asynchronously
    3. Queries multiple solvers to find the best rate
    4. Sends signed quote responses back through the WebSocket
    5. Handles connection errors with automatic reconnection

    The function runs indefinitely, automatically reconnecting on errors with
    a 2-second delay. Quote processing is batched (up to 100 concurrent tasks)
    for better performance.

    Args:
        solvers: List of solver rate providers to use for generating quotes
        omni_balance: OmniBalance instance for creating and signing quotes.
            Must be initialized and ready to use
        extra_headers: Additional HTTP headers for WebSocket connection.
            Defaults to INTENTS_HEADERS
        deadline: Quote deadline in seconds. Defaults to 20 seconds

    Returns:
        None. This function runs indefinitely until interrupted.

    Raises:
        Exception: Logs exceptions but continues running with reconnection logic
    """
    while True:
        try:
            tasks = []
            async with websockets.connect(
                SOLVER_BUS_WSS, additional_headers=extra_headers
            ) as websocket:
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "subscribe",
                            "params": ["quote"],
                        }
                    )
                )

                while True:
                    response = await websocket.recv()
                    response = json.loads(response)
                    if "params" not in response:
                        continue
                    tasks.append(
                        asyncio.create_task(
                            _process_ws_response(
                                websocket,
                                solvers,
                                omni_balance,
                                response,
                                deadline=deadline,
                            )  # Process each response in a separate task
                        )
                    )
                    if len(tasks) >= 100:
                        try:
                            await asyncio.gather(*tasks)
                            tasks.clear()
                        except Exception as e:
                            logger.exception(e)
                            logger.error(f"Error processing tasks: {e}")
        except Exception as e:
            logger.exception(e)
            logger.error(f"Error in WebSocket connection: {e}")
            await asyncio.sleep(2)
