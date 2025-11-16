import asyncio
import base64
import datetime
import json
from collections import Counter
from typing import Optional

import aiohttp
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
    """
    JSON-RPC provider for interacting with NEAR blockchain nodes.

    Handles RPC requests, transaction broadcasting, and response parsing.
    Supports multiple RPC endpoints with automatic failover and health checking.
    """

    def __init__(
        self, rpc_addr, allow_broadcast=True, timeout=TIMEOUT_WAIT_RPC, headers=None
    ):
        """
        Initialize JSON-RPC provider.

        Args:
            rpc_addr: RPC endpoint URL(s). Can be:
                - Single URL string
                - List of URL strings
                - Tuple (host, port) for HTTP endpoint
            allow_broadcast: If True, submit signed transactions to all available RPCs
            timeout: Request timeout in seconds (default: 600)
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
        self._headers = headers or dict()
        self.timeout = timeout
        self._timeout: aiohttp.ClientTimeout = None
        self._connector: aiohttp.TCPConnector = None
        self._client: aiohttp.ClientSession = None


    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.shutdown()

    async def startup(self):
        self._timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._connector = aiohttp.TCPConnector(limit=1000, limit_per_host=200)
        self._client = aiohttp.ClientSession(
            connector=self._connector, timeout=self._timeout
        )

    async def shutdown(self):
        """
        Shutdown the provider and close connections.

        Closes the HTTP client and cleans up resources.
        """
        if not self._client.closed:
            await self._client.close()
        if not self._connector.closed:
            await self._connector.close()

    async def _check_available_rpcs(self):
        """
        Check and update list of available RPC endpoints.

        Removes RPCs that are not responding or are out of sync.
        """
        if not self._client:
            await self.startup()
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

                async with self._client.post(
                    rpc_addr_url,
                    json=data,
                    headers={
                        "Referer": "https://tgapp.herewallet.app",
                        "Authorization": f"Bearer {auth_key}",
                    },
                ) as r:
                    if r.status == 200:
                        text = await r.text()
                        data = json.loads(text)["result"]
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
                            f"Remove rpc because of error {r.status}: {rpc_addr}"
                        )
            except Exception as e:
                if rpc_addr in self._available_rpcs:
                    logger.error(f"Remove rpc: {e}")
                logger.exception(e)
        self._available_rpcs = available_rpcs

    @staticmethod
    def most_frequent_by_hash(array):
        """
        Find the most frequent element in an array by hash.

        Args:
            array: List of hashable elements

        Returns:
            The most frequently occurring element
        """
        counter = Counter(array)
        most_frequent = counter.most_common(1)[0][0]
        return most_frequent

    async def call_rpc_request(
        self, method, params, broadcast=False, threshold: int = 0
    ):
        """
        Make an RPC request to the NEAR network.

        Args:
            method: RPC method name
            params: Method parameters
            broadcast: If True, send request to all available RPCs
            threshold: Minimum number of nodes that must return the same result
                (for consensus verification). If 0, uses first successful response.

        Returns:
            RPC response dictionary
        """
        if not self._client:
            await self.startup()
        j = {"method": method, "params": params, "id": "dontcare", "jsonrpc": "2.0"}

        async def f(rpc_call_addr):
            headers = self._headers.copy()
            if "@" in rpc_call_addr:
                auth_key = rpc_call_addr.split("//")[1].split("@")[0]
                rpc_call_addr = rpc_call_addr.replace(auth_key + "@", "")
                headers["Authorization"] = f"Bearer {auth_key}"

            async with self._client.post(
                rpc_call_addr, json=j, headers=headers
            ) as r:
                if r.status == 200:
                    text = await r.text()
                    return json.loads(text)
                text = await r.text()
                return {
                    "error": {
                        "cause": {
                            "name": "RPC_ERROR",
                            "message": f"Status: {r.status}",
                        },
                        "data": text,
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
        """
        Parse error from RPC response and convert to appropriate exception.

        Args:
            content: RPC response dictionary

        Returns:
            Exception instance if error found, None otherwise
        """
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
                if len(body) == 1 and list(body.keys())[0] in ERROR_CODE_TO_EXCEPTION:
                    key, body = list(body.items())[0]
                    if isinstance(body, str) and body in ERROR_CODE_TO_EXCEPTION:
                        key = body
                        body = {}
                    error = ERROR_CODE_TO_EXCEPTION[key](
                        body, error_json=content["error"]
                    )
                else:
                    break
            return error

    async def json_rpc(self, method, params, broadcast=False, threshold=None):
        """
        Execute JSON-RPC call and parse response.

        Args:
            method: RPC method name
            params: Method parameters
            broadcast: If True, send request to all available RPCs
            threshold: Minimum number of nodes that must return the same result

        Returns:
            Result from RPC response

        Raises:
            RpcEmptyResponse: If RPC returns empty response
            Various provider exceptions: Based on error codes in response
        """
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
        Send a signed transaction to the network asynchronously.

        Args:
            signed_tx: Base64-encoded signed transaction string

        Returns:
            Transaction hash string

        Note:
            This method does not wait for transaction confirmation.
            Use send_tx_and_wait() to wait for execution.
        """
        return await self.json_rpc(
            "broadcast_tx_async",
            [signed_tx],
            broadcast=self.allow_broadcast,
        )

    async def send_tx_included(self, signed_tx: str):
        """
        Send a signed transaction and wait until it's included in a block.

        Args:
            signed_tx: Base64-encoded signed transaction string

        Returns:
            Transaction hash string, or None if transaction was not included

        Note:
            This method waits for inclusion but not for final execution.
            Use send_tx_and_wait() to wait for full execution.
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

    async def wait_for_trx(
        self, trx_hash, receiver_id, attempts: int = 6
    ) -> TransactionResult:
        """
        Wait for a transaction to be processed by polling.

        Args:
            trx_hash: Transaction hash to wait for
            receiver_id: Account ID that received the transaction

        Returns:
            TransactionResult when transaction is found

        Raises:
            RPCTimeoutError: If transaction is not found after multiple attempts
        """
        for _ in range(attempts):
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
        Send a signed transaction and wait for full execution.

        Args:
            signed_tx: Base64-encoded signed transaction string
            trx_hash: Optional transaction hash (for fallback polling)
            receiver_id: Optional receiver account ID (for fallback polling)

        Returns:
            TransactionResult containing execution outcome

        Note:
            If RPC timeout occurs, falls back to polling with wait_for_trx()
        """
        try:
            res = await self.json_rpc(
                "broadcast_tx_commit",
                [signed_tx],
                broadcast=self.allow_broadcast,
            )
            return TransactionResult(**res)
        except RPCTimeoutError as e:
            if receiver_id and trx_hash:
                return await self.wait_for_trx(trx_hash, receiver_id)
            raise e

    async def get_status(self):
        """
        Get network status from RPC node.

        Returns:
            Dictionary containing network status information

        Raises:
            RpcNotAvailableError: If no RPC nodes are available
        """
        if not self._client:
            await self.startup()
        for rpc_addr in self._available_rpcs.copy():
            try:
                data = {
                    "jsonrpc": "2.0",
                    "method": "status",
                    "params": {"finality": "final"},
                    "id": 1,
                }
                headers = self._headers.copy()
                if "@" in rpc_addr:
                    auth_key = rpc_addr.split("//")[1].split("@")[0]
                    rpc_addr = rpc_addr.replace(auth_key + "@", "")
                    headers["Authorization"] = f"Bearer {auth_key}"
                async with self._client.post(
                    rpc_addr, json=data, headers=headers
                ) as r:
                    if r.status == 200:
                        text = await r.text()
                        return json.loads(text)["result"]
            except ConnectionError as e:
                logger.error(f"Rpc get status error: {rpc_addr} {e}")
            except Exception as e:
                logger.error(e)

        raise RpcNotAvailableError("RPC not available")

    async def get_validators(self):
        """
        Get current validators from the network.

        Returns:
            Dictionary containing validator information
        """
        return await self.json_rpc("validators", [None])

    async def query(self, query_object):
        """
        Execute a query on the blockchain state.

        Args:
            query_object: Query parameters dictionary

        Returns:
            Query result dictionary
        """
        return await self.json_rpc("query", query_object)

    async def get_account(self, account_id, finality="optimistic"):
        """
        Get account information.

        Args:
            account_id: Account ID to query
            finality: Finality level ("optimistic", "near-final", or "final")

        Returns:
            Dictionary containing account information (balance, code_hash, etc.)
        """
        return await self.json_rpc(
            "query",
            {
                "request_type": "view_account",
                "account_id": account_id,
                "finality": finality,
            },
        )

    async def get_access_key_list(self, account_id, finality="optimistic"):
        """
        Get list of access keys for an account.

        Args:
            account_id: Account ID to query
            finality: Finality level ("optimistic", "near-final", or "final")

        Returns:
            Dictionary containing list of access keys
        """
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
        Get access key information for a specific public key.

        Args:
            account_id: Account ID to query
            public_key: Public key (base58 string)
            finality: Finality level ("optimistic", "near-final", or "final")

        Returns:
            Dictionary containing access key info:
            {'block_hash': str, 'block_height': int, 'nonce': int, 'permission': str|dict}
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
        """
        Call a view function on a smart contract.

        Args:
            account_id: Contract account ID
            method_name: Method name to call
            args: Serialized method arguments (bytes, will be base64 encoded)
            finality: Finality level (used if block_id is not provided)
            block_id: Optional block ID to query at specific height
            threshold: Minimum number of nodes that must return the same result

        Returns:
            Dictionary containing view function result
        """
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
        """
        Get block information.

        Args:
            block_id: Block hash or block height

        Returns:
            Dictionary containing block information
        """
        return await self.json_rpc("block", [block_id])

    async def get_chunk(self, chunk_id):
        """
        Get chunk information.

        Args:
            chunk_id: Chunk hash

        Returns:
            Dictionary containing chunk information
        """
        return await self.json_rpc("chunk", [chunk_id])

    async def get_tx(self, tx_hash, tx_recipient_id) -> TransactionResult:
        """
        Get transaction information.

        Args:
            tx_hash: Transaction hash
            tx_recipient_id: Account ID that received the transaction

        Returns:
            TransactionResult containing transaction data and outcomes
        """
        return TransactionResult(
            **await self.json_rpc("tx", [tx_hash, tx_recipient_id])
        )

    async def get_tx_status(self, tx_hash, tx_recipient_id) -> TransactionResult:
        """
        Get transaction status (experimental method).

        Args:
            tx_hash: Transaction hash
            tx_recipient_id: Account ID that received the transaction

        Returns:
            TransactionResult containing transaction status
        """
        return TransactionResult(
            **await self.json_rpc("EXPERIMENTAL_tx_status", [tx_hash, tx_recipient_id])
        )

    async def get_changes_in_block(self, changes_in_block_request):
        """
        Get state changes in a block (experimental method).

        Args:
            changes_in_block_request: Dictionary with block change request parameters

        Returns:
            Dictionary containing state changes
        """
        return await self.json_rpc(
            "EXPERIMENTAL_changes_in_block", changes_in_block_request
        )

    async def get_validators_ordered(self, block_hash):
        """
        Get ordered validators for a block (experimental method).

        Args:
            block_hash: Block hash

        Returns:
            Dictionary containing ordered validator information
        """
        return await self.json_rpc("EXPERIMENTAL_validators_ordered", [block_hash])

    async def get_light_client_proof(
        self, outcome_type, tx_or_receipt_id, sender_or_receiver_id, light_client_head
    ):
        """
        Get light client proof for a transaction or receipt.

        Args:
            outcome_type: Type of outcome ("transaction" or "receipt")
            tx_or_receipt_id: Transaction hash or receipt ID
            sender_or_receiver_id: Sender ID (for transaction) or receiver ID (for receipt)
            light_client_head: Light client head block hash

        Returns:
            Dictionary containing light client proof
        """
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
        """
        Get next light client block.

        Args:
            last_block_hash: Hash of the last known block

        Returns:
            Dictionary containing next light client block information
        """
        return await self.json_rpc("next_light_client_block", [last_block_hash])
