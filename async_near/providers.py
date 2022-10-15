import asyncio

import aiohttp
import base64
import json

from aiohttp import ClientResponseError, ClientConnectorError

from async_near.exceptions.execution import RpcNotAvailableError
from async_near.exceptions.provider import (
    UnknownBlockError,
    InvalidAccount,
    NoContractCodeError,
    UnknownAccount,
    TooLargeContractStateError,
    UnavailableShardError,
    NoSyncedBlocksError,
    InternalError,
    NoSyncedYetError,
    InvalidTransactionError,
    RpcTimeoutError,
    UnknownAccessKeyError,
)

_ERROR_CODE_TO_EXCEPTION = {
    "UNKNOWN_BLOCK": UnknownBlockError,
    "INVALID_ACCOUNT": InvalidAccount,
    "UNKNOWN_ACCOUNT": UnknownAccount,
    "NO_CONTRACT_CODE": NoContractCodeError,
    "TOO_LARGE_CONTRACT_STATE": TooLargeContractStateError,
    "UNAVAILABLE_SHARD": UnavailableShardError,
    "NO_SYNCED_BLOCKS": NoSyncedBlocksError,
    "INTERNAL_ERROR": InternalError,
    "NOT_SYNCED_YET": NoSyncedYetError,
    "INVALID_TRANSACTION": InvalidTransactionError,
    "TIMEOUT_ERROR": RpcTimeoutError,
    "UNKNOWN_ACCESS_KEY": UnknownAccessKeyError,
}


class JsonProvider(object):
    _lock: asyncio.Lock

    def __init__(self, rpc_addr):
        if isinstance(rpc_addr, tuple):
            self._rpc_addresses = ["http://{}:{}".format(*rpc_addr)]
        elif isinstance(rpc_addr, list):
            self._rpc_addresses = rpc_addr
        else:
            self._rpc_addresses = [rpc_addr]

    async def startup(self):
        self._lock = asyncio.Lock()

    async def json_rpc(self, method, params, timeout=60):
        j = {"method": method, "params": params, "id": "dontcare", "jsonrpc": "2.0"}

        content = None
        with await self._lock:
            for rpc_addr in self._rpc_addresses:
                try:
                    async with aiohttp.ClientSession() as session:
                        r = await session.post(rpc_addr, json=j, timeout=timeout)
                        r.raise_for_status()
                        content = json.loads(await r.text())
                    if self._rpc_addresses[0] != rpc_addr:
                        self._rpc_addresses.remove(rpc_addr)
                        self._rpc_addresses.insert(0, rpc_addr)
                        print("Switching RPC to %s" % rpc_addr)
                    break
                except ClientResponseError:
                    continue
                except ClientConnectorError:
                    continue
                except ConnectionError:
                    continue

        if not content:
            raise RpcNotAvailableError("RPC not available")

        if "error" in content:
            error_code = content["error"].get("cause", {}).get("name", "")
            raise _ERROR_CODE_TO_EXCEPTION.get(error_code, InternalError)(
                content["error"]["data"]
            )
        return content["result"]

    async def send_tx(self, signed_tx):
        return await self.json_rpc(
            "broadcast_tx_async", [base64.b64encode(signed_tx).decode("utf8")]
        )

    async def send_tx_and_wait(self, signed_tx, timeout=60):
        return await self.json_rpc(
            "broadcast_tx_commit",
            [base64.b64encode(signed_tx).decode("utf8")],
            timeout=timeout,
        )

    async def get_status(self):
        async with aiohttp.ClientSession() as session:
            r = await session.get("%s/status" % self._rpc_addresses[0], timeout=5)
            r.raise_for_status()
            return json.loads(await r.text())

    async def get_validators(self):
        return await self.json_rpc("validators", [None])

    async def query(self, query_object):
        return await self.json_rpc("query", query_object)

    async def get_account(self, account_id, finality="optimistic"):
        return await self.json_rpc(
            "query",
            {
                "request_type": "view_account",
                "account_id": account_id,
                "finality": finality,
            },
        )

    async def get_access_key_list(self, account_id, finality="optimistic"):
        return await self.json_rpc(
            "query",
            {
                "request_type": "view_access_key_list",
                "account_id": account_id,
                "finality": finality,
            },
        )

    async def get_access_key(self, account_id, public_key, finality="optimistic"):
        return await self.json_rpc(
            "query",
            {
                "request_type": "view_access_key",
                "account_id": account_id,
                "public_key": public_key,
                "finality": finality,
            },
        )

    async def view_call(self, account_id, method_name, args, finality="optimistic"):
        return await self.json_rpc(
            "query",
            {
                "request_type": "call_function",
                "account_id": account_id,
                "method_name": method_name,
                "args_base64": base64.b64encode(args).decode("utf8"),
                "finality": finality,
            },
        )

    async def get_block(self, block_id):
        return await self.json_rpc("block", [block_id])

    async def get_chunk(self, chunk_id):
        return await self.json_rpc("chunk", [chunk_id])

    async def get_tx(self, tx_hash, tx_recipient_id):
        return await self.json_rpc("tx", [tx_hash, tx_recipient_id])

    async def get_changes_in_block(self, changes_in_block_request):
        return await self.json_rpc(
            "EXPERIMENTAL_changes_in_block", changes_in_block_request
        )

    async def get_validators_ordered(self, block_hash):
        return await self.json_rpc("EXPERIMENTAL_validators_ordered", [block_hash])

    async def get_light_client_proof(
        self, outcome_type, tx_or_receipt_id, sender_or_receiver_id, light_client_head
    ):
        if outcome_type == "receipt":
            params = {
                "type": "receipt",
                "receipt_id": tx_or_receipt_id,
                "receiver_id": sender_or_receiver_id,
                "light_client_head": light_client_head,
            }
        else:
            params = {
                "type": "transaction",
                "transaction_hash": tx_or_receipt_id,
                "sender_id": sender_or_receiver_id,
                "light_client_head": light_client_head,
            }
        return await self.json_rpc("light_client_proof", params)

    async def get_next_light_client_block(self, last_block_hash):
        return await self.json_rpc("next_light_client_block", [last_block_hash])
