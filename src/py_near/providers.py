import base64
import json

import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError
from py_near.models import TransactionResult

from py_near import constants
from py_near.exceptions.exceptions import RpcNotAvailableError
from py_near.exceptions.provider import (
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
    ERROR_CODE_TO_EXCEPTION,
)


PROVIDER_CODE_TO_EXCEPTION = {
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
            self._rpc_addresses = ["http://{}:{}".format(*rpc_addr)]
        elif isinstance(rpc_addr, list):
            self._rpc_addresses = rpc_addr
        else:
            self._rpc_addresses = [rpc_addr]

    async def call_rpc_request(self, method, params, timeout=60):
        j = {"method": method, "params": params, "id": "dontcare", "jsonrpc": "2.0"}

        content = None
        for rpc_addr in self._rpc_addresses:
            try:
                async with aiohttp.ClientSession() as session:
                    r = await session.post(rpc_addr, json=j, timeout=timeout)
                    r.raise_for_status()
                    content = json.loads(await r.text())
                if self._rpc_addresses[0] != rpc_addr:
                    self._rpc_addresses.remove(rpc_addr)
                    self._rpc_addresses.insert(0, rpc_addr)
                break
            except ClientResponseError:
                continue
            except ClientConnectorError:
                continue
            except ConnectionError:
                continue
        return content

    @staticmethod
    def get_error_from_response(content: dict):
        if "error" in content:
            error_code = content["error"].get("cause", {}).get("name", "")
            body = content["error"]["data"]
            error = PROVIDER_CODE_TO_EXCEPTION.get(error_code, InternalError)(
                body, error_json=content["error"]
            )
            while True:
                if not isinstance(body, dict):
                    break
                key, body = list(body.items())[0]
                if key in ERROR_CODE_TO_EXCEPTION:
                    error = ERROR_CODE_TO_EXCEPTION[key](
                        body, error_json=content["error"]
                    )
                else:
                    break
            return error

    async def json_rpc(self, method, params, timeout=60):
        content = await self.call_rpc_request(method, params, timeout)
        if not content:
            raise RpcNotAvailableError("RPC not available")

        error = self.get_error_from_response(content)
        if error:
            raise error
        return content["result"]

    async def send_tx(self, signed_tx: str, timeout: int = constants.TIMEOUT_WAIT_RPC):
        """
        Send a signed transaction to the network and return the hash of the transaction
        :param signed_tx: base64 encoded signed transaction, str.
        :param timeout: rpc request timeout
        :return:
        """
        return await self.json_rpc("broadcast_tx_async", [signed_tx], timeout=timeout)

    async def send_tx_and_wait(
        self, signed_tx: str, timeout: int = constants.TIMEOUT_WAIT_RPC
    ):
        """
        Send a signed transaction to the network and wait for it to be included in a block
        :param signed_tx: base64 encoded signed transaction, str
        :param timeout: rpc request timeout
        :return:
        """
        return await self.json_rpc(
            "broadcast_tx_commit",
            [signed_tx],
            timeout=timeout,
        )

    async def get_status(self):
        async with aiohttp.ClientSession() as session:
            r = await session.get("%s/status" % self._rpc_addresses[0], timeout=60)
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

    async def get_tx(self, tx_hash, tx_recipient_id) -> TransactionResult:
        return TransactionResult(
            **await self.json_rpc("tx", [tx_hash, tx_recipient_id])
        )

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
