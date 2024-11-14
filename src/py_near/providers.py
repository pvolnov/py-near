import asyncio
import base64
import datetime
import json
from collections import Counter
from typing import Optional

import httpx
from httpx import Limits
from loguru import logger

from py_near.constants import TIMEOUT_WAIT_RPC
from py_near.exceptions.exceptions import RpcNotAvailableError, RpcEmptyResponse
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
    RPCTimeoutError,
    UnknownAccessKeyError,
    ERROR_CODE_TO_EXCEPTION,
    InvalidNonce,
)
from py_near.models import TransactionResult

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
    "TIMEOUT_ERROR": RPCTimeoutError,
    "UNKNOWN_ACCESS_KEY": UnknownAccessKeyError,
}


class JsonProvider(object):
    def __init__(self, rpc_addr, allow_broadcast=True, timeout=TIMEOUT_WAIT_RPC):
        """
        :param rpc_addr: str or list of str
        :param allow_broadcast: bool - submit signed transaction to all RPCs
        """
        if isinstance(rpc_addr, tuple):
            self._rpc_addresses = ["http://{}:{}".format(*rpc_addr)]
        elif isinstance(rpc_addr, list):
            self._rpc_addresses = rpc_addr
        else:
            self._rpc_addresses = [rpc_addr]
        self._available_rpcs = self._rpc_addresses.copy()
        self._last_rpc_addr_check = 0
        self.allow_broadcast = allow_broadcast
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            limits=Limits(max_connections=1000, max_keepalive_connections=200)
        )

    async def shutdown(self):
        pass

    async def _check_available_rpcs(self):
        available_rpcs = []
        for rpc_addr in self._rpc_addresses:
            try:
                data = {
                    "jsonrpc": "2.0",
                    "method": "status",
                    "params": {"finality": "final"},
                    "id": 1,
                }
                auth_key = "py-near"
                rpc_addr_url = rpc_addr
                if "@" in rpc_addr:
                    auth_key = rpc_addr_url.split("//")[1].split("@")[0]
                    rpc_addr_url = rpc_addr_url.replace(auth_key + "@", "")

                r = await self._client.post(
                    rpc_addr_url,
                    json=data,
                    headers={
                        "Referer": "https://tgapp.herewallet.app",
                        "Authorization": f"Bearer {auth_key}",
                    },
                )
                if r.status_code == 200:
                    data = json.loads(r.text)["result"]
                    diff = 0
                    if data["sync_info"]["syncing"]:
                        last_block_ts = datetime.datetime.fromisoformat(
                            data["sync_info"]["latest_block_time"]
                        )
                        diff = (
                            datetime.datetime.utcnow().timestamp()
                            - last_block_ts.timestamp()
                        )
                        is_syncing = diff > 60
                    else:
                        is_syncing = False
                    if is_syncing:
                        logger.error(f"Remove async RPC : {rpc_addr} ({diff})")
                        continue
                    available_rpcs.append(rpc_addr)
                else:
                    logger.error(
                        f"Remove rpc because of error {r.status_code}: {rpc_addr}"
                    )
            except Exception as e:
                if rpc_addr in self._available_rpcs:
                    logger.error(f"Remove rpc: {e}")
                logger.exception(e)
        self._available_rpcs = available_rpcs

    @staticmethod
    def most_frequent_by_hash(array):
        counter = Counter(array)
        most_frequent = counter.most_common(1)[0][0]
        return most_frequent

    async def call_rpc_request(
        self, method, params, broadcast=False, threshold: int = 0
    ):
        j = {"method": method, "params": params, "id": "dontcare", "jsonrpc": "2.0"}

        async def f(rpc_call_addr):
            auth_key = "py-near"
            if "@" in rpc_call_addr:
                auth_key = rpc_call_addr.split("//")[1].split("@")[0]
                rpc_call_addr = rpc_call_addr.replace(auth_key + "@", "")
            r = await self._client.post(
                rpc_call_addr,
                json=j,
                timeout=self._timeout,
                headers={
                    "Referer": "https://tgapp.herewallet.app",
                    "Authorization": f"Bearer {auth_key}",
                },
            )
            if r.status_code == 200:
                return json.loads(r.text)
            return {
                "error": {
                    "cause": {
                        "name": "RPC_ERROR",
                        "message": f"Status: {r.status_code}",
                    },
                    "data": r.text,
                }
            }

        if broadcast or threshold:
            pending = [
                asyncio.create_task(f(rpc_addr)) for rpc_addr in self._available_rpcs
            ]

            responses = []
            correct_responses = []
            result = None

            while pending and len(pending):
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    try:
                        result = task.result()
                        if "error" not in result and (not threshold or threshold <= 1):
                            return result
                        responses.append(result)
                    except Exception as e:
                        logger.warning(e)
                if responses and threshold:
                    array = [hash(json.dumps(x)) for x in responses]
                    most_frequent_element = self.most_frequent_by_hash(array)
                    correct_responses = [
                        x
                        for x in responses
                        if hash(json.dumps(x)) == most_frequent_element
                    ]
                    if len(correct_responses) >= threshold:
                        for task in pending:
                            task.cancel()
                        return correct_responses[0]
            if threshold and threshold > 0:
                raise RpcEmptyResponse(
                    f"Threshold not reached: {len(correct_responses)}/{threshold}"
                )
            return result
        else:
            res = None
            for rpc_addr in self._available_rpcs:
                try:
                    res = await f(rpc_addr)
                    if "error" not in res:
                        return res
                except Exception as e:
                    logger.error(f"Rpc error: {e}")
                    continue
            return res

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
                if not body:
                    return error
                key, body = list(body.items())[0]
                if key in ERROR_CODE_TO_EXCEPTION:
                    error = ERROR_CODE_TO_EXCEPTION[key](
                        body, error_json=content["error"]
                    )
                else:
                    break
            return error

    async def json_rpc(self, method, params, broadcast=False, threshold=None):
        content = await self.call_rpc_request(
            method, params, broadcast=broadcast, threshold=threshold
        )
        if not content:
            raise RpcEmptyResponse("RPC returned empty response")

        error = self.get_error_from_response(content)
        if error:
            raise error
        return content["result"]

    async def send_tx(self, signed_tx: str):
        """
        Send a signed transaction to the network and return the hash of the transaction
        :param signed_tx: base64 encoded signed transaction, str.
        :param timeout: rpc request timeout
        :return:
        """
        return await self.json_rpc(
            "broadcast_tx_async",
            [signed_tx],
            broadcast=self.allow_broadcast,
        )

    async def send_tx_included(self, signed_tx: str):
        """
        Send a signed transaction to the network and return the hash of the transaction
        :param signed_tx: base64 encoded signed transaction, str.
        :param timeout: rpc request timeout
        :return:
        """
        try:
            return await self.json_rpc(
                "send_tx",
                {"signed_tx_base64": signed_tx, "wait_until": "INCLUDED"},
                broadcast=self.allow_broadcast,
            )
        except InvalidNonce:
            logger.warning("Invalid nonce during broadcast included transaction")
            return None

    async def wait_for_trx(self, trx_hash, receiver_id) -> TransactionResult:
        for _ in range(6):
            await asyncio.sleep(5)
            try:
                result = await self.get_tx(trx_hash, receiver_id)
            except InternalError:
                continue
            except Exception as e:
                logger.exception(e)
                continue
            if result:
                return result
        raise RPCTimeoutError("Transaction not found")

    async def send_tx_and_wait(
        self,
        signed_tx: str,
        trx_hash: Optional[str] = None,
        receiver_id: Optional[str] = None,
    ) -> TransactionResult:
        """
        Send a signed transaction to the network and wait for it to be included in a block
        :param signed_tx: base64 encoded signed transaction, str
        :param timeout: rpc request timeout
        :return:
        """
        try:
            res = await self.json_rpc(
                "broadcast_tx_commit",
                [signed_tx],
                broadcast=self.allow_broadcast,
            )
            return TransactionResult(**res)
        except RPCTimeoutError:
            if receiver_id and trx_hash:
                return await self.wait_for_trx(trx_hash, receiver_id)

    async def get_status(self):
        for rpc_addr in self._available_rpcs.copy():
            try:
                data = {
                    "jsonrpc": "2.0",
                    "method": "status",
                    "params": {"finality": "final"},
                    "id": 1,
                }
                headers = {
                    "Referer": "https://tgapp.herewallet.app",
                }
                if "@" in rpc_addr:
                    auth_key = rpc_addr.split("//")[1].split("@")[0]
                    rpc_addr = rpc_addr.replace(auth_key + "@", "")
                    headers = {"Authorization": f"Bearer {auth_key}"}
                r = await self._client.post(rpc_addr, json=data, headers=headers)
                if r.status_code == 200:
                    return json.loads(r.text)["result"]
            except ConnectionError as e:
                logger.error(f"Rpc get status error: {e}")
            except Exception as e:
                logger.error(e)

        raise RpcNotAvailableError("RPC not available")

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
        """

        :param account_id:
        :param public_key:
        :param finality:
        :return: {'block_hash': '..', 'block_height': int, 'nonce': int, 'permission': 'FullAccess'}
        """
        return await self.json_rpc(
            "query",
            {
                "request_type": "view_access_key",
                "account_id": account_id,
                "public_key": public_key,
                "finality": finality,
            },
        )

    async def view_call(
        self,
        account_id,
        method_name,
        args,
        finality="optimistic",
        block_id: Optional[int] = None,
        threshold: Optional[int] = None,
    ):
        body = {
            "request_type": "call_function",
            "account_id": account_id,
            "method_name": method_name,
            "args_base64": base64.b64encode(args).decode("utf8"),
        }
        if block_id:
            body["block_id"] = block_id
        else:
            body["finality"] = finality
        return await self.json_rpc("query", body, threshold=threshold)

    async def get_block(self, block_id):
        return await self.json_rpc("block", [block_id])

    async def get_chunk(self, chunk_id):
        return await self.json_rpc("chunk", [chunk_id])

    async def get_tx(self, tx_hash, tx_recipient_id) -> TransactionResult:
        return TransactionResult(
            **await self.json_rpc("tx", [tx_hash, tx_recipient_id])
        )

    async def get_tx_status(self, tx_hash, tx_recipient_id) -> TransactionResult:
        return TransactionResult(
            **await self.json_rpc("EXPERIMENTAL_tx_status", [tx_hash, tx_recipient_id])
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
