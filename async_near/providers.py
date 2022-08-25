import aiohttp
import base64
import json

from async_near.exceptions.provider import UnknownBlockError, InvalidAccount, NoContractCodeError, UnknownAccount, \
    TooLargeContractStateError, UnavailableShardError, NoSyncedBlocksError, InternalError, NoSyncedYetError, \
    InvalidTransactionError, RpcTimeoutError, UnknownAccessKeyError

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
    def __init__(self, rpc_addr):
        if isinstance(rpc_addr, tuple):
            self._rpc_addr = "http://{}:{}".format(*rpc_addr)
        else:
            self._rpc_addr = rpc_addr

    def rpc_addr(self):
        return self._rpc_addr

    async def json_rpc(self, method, params, timeout=20):
        j = {"method": method, "params": params, "id": "dontcare", "jsonrpc": "2.0"}
        async with aiohttp.ClientSession() as session:
            r = await session.post(self.rpc_addr(), json=j, timeout=timeout)
            r.raise_for_status()
            content = json.loads(await r.text())

        if "error" in content:
            error_code = content["error"].get("cause", {}).get("name", "")
            raise _ERROR_CODE_TO_EXCEPTION.get(error_code, InternalError)(content["error"]["data"])
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
            r = await session.get("%s/status" % self.rpc_addr(), timeout=5)
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
