import asyncio
import collections
import json
import sys
from typing import List, Union, Dict, Optional

from nacl.signing import VerifyKey

from py_near.constants import RPC_MAINNET

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    from collections.abc import MutableSet, MutableMapping

    collections.MutableSet = collections.abc.MutableSet
    collections.MutableMapping = collections.abc.MutableMapping
else:
    from collections import MutableSet

import base58
from nacl import signing, encoding
from loguru import logger
from py_near_primitives import DelegateAction

from py_near import constants
from py_near import transactions
from py_near import utils
from py_near.dapps.ft.async_client import FT
from py_near.exceptions.provider import (
    JsonProviderError,
    RPCTimeoutError,
)
from py_near.models import (
    TransactionResult,
    ViewFunctionResult,
    PublicKey,
    AccountAccessKey,
    DelegateActionModel,
    Action,
)
from py_near.providers import JsonProvider


class ViewFunctionError(Exception):
    """Exception raised when a view function call fails."""
    pass


class Account(object):
    """
    Account class for interacting with NEAR blockchain.

    This class provides methods for signing transactions, calling smart contracts,
    managing keys, and interacting with various NEAR protocol features.
    """

    _access_key: dict
    _lock: asyncio.Lock = None
    _lock_by_pk: Dict[str, asyncio.Lock] = {}
    _latest_block_hash: str
    _latest_block_hash_ts: float = 0
    _latest_block_height: int = 0
    _access_key_nonce: dict = collections.defaultdict(int)
    chain_id: str = "mainnet"

    def __init__(
        self,
        account_id: str = None,
        private_key: Union[List[Union[str, bytes]], str, bytes] = None,
        rpc_addr=RPC_MAINNET,
    ):
        """
        Initialize Account instance.

        Args:
            account_id: NEAR account identifier (e.g., "example.near")
            private_key: Private key(s) for signing transactions. Can be:
                - A single private key (str or bytes)
                - A list of private keys (str or bytes)
                - None (for read-only operations)
            rpc_addr: RPC endpoint URL or list of URLs for NEAR network
        """
        self._provider = JsonProvider(rpc_addr)
        self.account_id = account_id
        if private_key is None:
            private_keys = []
        elif isinstance(private_key, list):
            private_keys = private_key
        elif isinstance(private_key, str):
            private_keys = [private_key]
        elif isinstance(private_key, bytes):
            private_keys = [private_key]
        else:
            return

        self._free_signers = asyncio.Queue()
        self._signers = []
        self._signer_by_pk: Dict[str, bytes] = {}

        for pk in private_keys:
            if isinstance(pk, str):
                try:
                    pk = base58.b58decode(pk.replace("ed25519:", ""))
                except UnicodeEncodeError:
                    logger.error(f"Can't decode private key {pk[:10]}")
                    continue
            private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)
            public_key_b58 = base58.b58encode(private_key.verify_key.encode()).decode(
                "utf-8"
            )
            self._signer_by_pk[public_key_b58] = pk
            self._free_signers.put_nowait(pk)
            self._signers.append(pk)

    async def startup(self):
        """
        Initialize async resources for the account.

        Must be called before using async methods. Initializes locks and
        retrieves chain_id from the network.
        """
        self._lock = asyncio.Lock()
        self._lock_by_pk = collections.defaultdict(asyncio.Lock)
        self.chain_id = (await self._provider.get_status())["chain_id"]

    async def shutdown(self):
        """
        Clean up async resources.

        Closes the RPC provider connection. Should be called when done
        using the account instance.
        """
        await self._provider.shutdown()

    async def _update_last_block_hash(self):
        """
        Update the latest block hash from the network.

        If the cached block hash is older than 50 blocks, it will be refreshed.
        This is necessary because transactions with outdated block hashes will fail.
        """
        if self._latest_block_hash_ts + 50 > utils.timestamp():
            return
        self._latest_block_hash = (await self._provider.get_status())["sync_info"][
            "latest_block_hash"
        ]
        self._latest_block_height = (await self._provider.get_status())["sync_info"][
            "latest_block_height"
        ]
        self._latest_block_hash_ts = utils.timestamp()

    async def sign_and_submit_tx(
        self, receiver_id, actions: List[Action], nowait=False, included=False
    ) -> Union[TransactionResult, str]:
        """
        Sign and submit a transaction to the blockchain.

        Args:
            receiver_id: Account ID that will receive the transaction
            actions: List of actions to include in the transaction
            nowait: LEGACY, now same as included
            included: If True, wait until transaction is included in a block,
                then return transaction hash. Takes precedence over nowait.

        Returns:
            Transaction hash (str) if nowait=True or included=True,
            TransactionResult if nowait=False and included=False

        Raises:
            ValueError: If no private keys are configured
        """
        if not self._signers:
            raise ValueError("You must provide a private key or seed to call methods")
        await self._update_last_block_hash()
        included = included or nowait

        pk = await self._free_signers.get()
        await self._free_signers.put(pk)

        if self._access_key_nonce[pk] == 0:
            access_key = await self.get_access_key(pk)
            self._access_key_nonce[pk] = access_key.nonce
        self._access_key_nonce[pk] += 1

        block_hash = base58.b58decode(self._latest_block_hash.encode("utf8"))
        trx_hash = transactions.calc_trx_hash(
            self.account_id,
            pk,
            receiver_id,
            self._access_key_nonce[pk],
            actions,
            block_hash,
        )
        serialized_tx = transactions.sign_and_serialize_transaction(
            self.account_id,
            pk,
            receiver_id,
            self._access_key_nonce[pk],
            actions,
            block_hash,
        )

        try:
            if included:
                try:
                    await self._provider.send_tx_included(serialized_tx)
                except RPCTimeoutError as e:
                    if "Transaction not included" in str(e):
                        logger.error(f"Transaction not included {trx_hash}")
                return trx_hash
            return await self._provider.send_tx_and_wait(
                serialized_tx, trx_hash=trx_hash, receiver_id=receiver_id
            )
        except JsonProviderError as e:
            e.trx_hash = trx_hash
            raise
        except Exception as e:
            e.trx_hash = trx_hash
            raise
        finally:
            await self._free_signers.put(pk)

    @property
    def signer(self) -> Optional[bytes]:
        """
        Get the first configured private key signer.

        Returns:
            First private key as bytes, or None if no signers are configured
        """
        if not self._signers:
            return None
        return self._signers[0]

    @property
    def provider(self) -> JsonProvider:
        """
        Get the RPC provider instance.

        Returns:
            JsonProvider instance used for RPC calls
        """
        return self._provider

    async def get_access_key(self, pk: bytes) -> AccountAccessKey:
        """
        Get access key information for a public key.

        Args:
            pk: Private key (bytes) to get the corresponding public key access key info.
                If None, uses the first configured signer.

        Returns:
            AccountAccessKey containing nonce, permissions, and block info

        Raises:
            ValueError: If the RPC response contains an error
        """
        if pk is None:
            pk = self._signers[0]

        private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)
        public_key = private_key.verify_key
        resp = await self._provider.get_access_key(
            self.account_id, base58.b58encode(public_key.encode()).decode("utf8")
        )
        if "error" in resp:
            raise ValueError(resp["error"])
        return AccountAccessKey(**resp)

    async def get_access_key_list(self, account_id: str = None) -> List[PublicKey]:
        """
        Get list of all access keys for an account.

        Args:
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            List of PublicKey objects with their access key information
        """
        if account_id is None:
            account_id = self.account_id
        resp = await self._provider.get_access_key_list(account_id)
        result = []
        if "keys" in resp and isinstance(resp["keys"], list):
            for key in resp["keys"]:
                result.append(PublicKey(**key))
        return result

    async def fetch_state(self) -> dict:
        """
        Fetch account state from the blockchain.

        Returns:
            Dictionary containing account information (balance, code_hash, etc.)
        """
        return await self._provider.get_account(self.account_id)

    async def send_money(
        self, account_id: str, amount: int, nowait: bool = False, included=False
    ) -> TransactionResult:
        """
        Send NEAR tokens to another account.

        Args:
            account_id: Receiver account ID
            amount: Amount to send in yoctoNEAR (1 NEAR = 10^24 yoctoNEAR)
            nowait: If True, return transaction hash immediately
            included: If True, wait until transaction is included in a block

        Returns:
            Transaction hash (str) or TransactionResult depending on flags
        """
        return await self.sign_and_submit_tx(
            account_id, [transactions.create_transfer_action(amount)], nowait, included
        )

    async def function_call(
        self,
        contract_id: str,
        method_name: str,
        args: dict,
        gas: int = constants.DEFAULT_ATTACHED_GAS,
        amount: int = 0,
        nowait: bool = False,
        included=False,
    ):
        """
        Call a function on a smart contract.

        Args:
            contract_id: Smart contract account ID
            method_name: Name of the method to call
            args: Dictionary of arguments to pass to the method (will be JSON serialized)
            gas: Amount of gas to attach (in yoctoNEAR gas units).
                Default is 200 TGas (200 * 10^12)
            amount: Amount of NEAR to attach (in yoctoNEAR). Default is 0
            nowait: If True, return transaction hash immediately
            included: If True, wait until transaction is included in a block

        Returns:
            Transaction hash (str) or TransactionResult depending on flags
        """
        ser_args = json.dumps(args).encode("utf8")
        return await self.sign_and_submit_tx(
            contract_id,
            [
                transactions.create_function_call_action(
                    method_name, ser_args, gas, amount
                )
            ],
            nowait,
            included,
        )

    async def use_global_contract(
        self,
        account_id: Optional[str] = None,
        contract_code_hash: Union[str, bytes, None] = None,
        nowait=False,
        included=False,
    ):
        """
        Use a global contract by account ID or code hash.

        Args:
            account_id: Account ID of the global contract to use
            contract_code_hash: Code hash of the global contract to use (32 bytes)
            nowait: If True, return transaction hash immediately
            included: If True, wait until transaction is included in a block

        Returns:
            Transaction hash (str) or TransactionResult depending on flags

        Raises:
            ValueError: If neither account_id nor contract_code_hash is provided
        """
        actions = []
        if account_id:
            actions.append(
                transactions.create_use_global_contract_action_by_account_id(account_id)
            )
        elif contract_code_hash:
            actions.append(
                transactions.create_use_global_contract_action_by_code_hash(
                    contract_code_hash
                )
            )
        else:
            raise ValueError("Either account_id or contract_code_hash must be provided")
        return await self.sign_and_submit_tx(
            self.account_id,
            actions,
            nowait,
            included,
        )

    async def create_account(
        self,
        account_id: str,
        public_key: Union[str, bytes],
        initial_balance: int,
        nowait=False,
    ):
        """
        Create a new sub-account under the current account.

        For example, if current account is "test.near", you can create "sub.test.near".

        Args:
            account_id: New account ID (must be a subdomain of current account)
            public_key: Public key to add to the new account (full access)
            initial_balance: Initial balance to transfer in yoctoNEAR
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        actions = [
            transactions.create_create_account_action(),
            transactions.create_full_access_key_action(public_key),
            transactions.create_transfer_action(initial_balance),
        ]
        return await self.sign_and_submit_tx(account_id, actions, nowait)

    async def add_public_key(
        self,
        public_key: Union[str, bytes],
        receiver_id: str,
        method_names: List[str] = None,
        allowance: int = constants.ALLOWANCE,
        nowait=False,
    ):
        """
        Add a function call access key to the account.

        The key will have permission to call specific methods on a smart contract
        with a limited gas allowance.

        Args:
            public_key: Public key to add (str or bytes)
            receiver_id: Smart contract account ID that this key can interact with
            method_names: List of method names the key is allowed to call.
                Empty list means all methods. Default is empty list.
            allowance: Maximum amount of gas this key can use (in yoctoNEAR gas units).
                Default is 25 TGas
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        if method_names is None:
            method_names = []
        actions = [
            transactions.create_function_call_access_key_action(
                public_key, allowance, receiver_id, method_names
            ),
        ]
        return await self.sign_and_submit_tx(self.account_id, actions, nowait)

    async def add_full_access_public_key(
        self, public_key: Union[str, bytes], nowait=False
    ) -> TransactionResult:
        """
        Add a full access public key to the account.

        Full access keys can perform any action on behalf of the account.

        Args:
            public_key: Public key to add (str or bytes)
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        actions = [
            transactions.create_full_access_key_action(public_key),
        ]
        return await self.sign_and_submit_tx(self.account_id, actions, nowait)

    async def delete_public_key(self, public_key: Union[str, bytes], nowait=False):
        """
        Delete a public key from the account.

        Args:
            public_key: Public key to delete (str or bytes)
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        actions = [
            transactions.create_delete_access_key_action(public_key),
        ]
        return await self.sign_and_submit_tx(self.account_id, actions, nowait)

    async def call_delegate_transaction(
        self,
        delegate_action: Union[DelegateAction, DelegateActionModel],
        signature: Union[bytes, str],
        nowait=False,
        included=False,
    ):
        """
        Execute a signed delegate action transaction.

        Args:
            delegate_action: DelegateAction or DelegateActionModel to execute
            signature: Signature for the delegate action (bytes or base58 string)
            nowait: If True, return transaction hash immediately
            included: If True, wait until transaction is included in a block

        Returns:
            Transaction hash (str) or TransactionResult
        """
        if isinstance(signature, str):
            signature = base58.b58decode(signature.replace("ed25519:", ""))
        if isinstance(delegate_action, DelegateActionModel):
            delegate_action = delegate_action.near_delegate_action

        actions = [
            transactions.create_signed_delegate(delegate_action, signature),
        ]
        return await self.sign_and_submit_tx(
            delegate_action.sender_id, actions, nowait, included
        )

    async def deploy_contract(self, contract_code: bytes, nowait=False):
        """
        Deploy smart contract code to the account.

        Args:
            contract_code: Compiled contract code (WASM bytes)
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult
        """
        return await self.sign_and_submit_tx(
            self.account_id,
            [transactions.create_deploy_contract_action(contract_code)],
            nowait,
        )

    async def stake(self, public_key: str, amount: str, nowait=False):
        """
        Stake NEAR tokens with a validator.

        Args:
            public_key: Validator's public key to stake with
            amount: Amount of NEAR to stake (as string in yoctoNEAR)
            nowait: If True, return transaction hash immediately

        Returns:
            Transaction hash (str) or TransactionResult

        Note:
            Account must have sufficient balance to meet validator pool requirements
        """
        return await self.sign_and_submit_tx(
            self.account_id,
            [transactions.create_staking_action(public_key, amount)],
            nowait,
        )

    async def view_function(
        self,
        contract_id: str,
        method_name: str,
        args: dict,
        block_id: Optional[int] = None,
        threshold: Optional[int] = None,
    ) -> ViewFunctionResult:
        """
        Call a view function on a smart contract (read-only).

        View functions cannot modify contract state and do not require a transaction.

        Args:
            contract_id: Smart contract account ID
            method_name: Name of the view method to call
            args: Dictionary of arguments (will be JSON serialized)
            block_id: Optional block ID to query at a specific block height
            threshold: Minimum number of nodes that must return the same result
                (for consensus verification)

        Returns:
            ViewFunctionResult containing the method result, logs, and block info

        Raises:
            ViewFunctionError: If the view function call fails
        """
        result = await self._provider.view_call(
            contract_id,
            method_name,
            json.dumps(args).encode("utf8"),
            block_id=block_id,
            threshold=threshold,
        )
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads("".join([chr(x) for x in result["result"]]))
        return ViewFunctionResult(**result)

    async def create_delegate_action(
        self, actions: List[Action], receiver_id, public_key: Optional[str] = None
    ):
        """
        Create a delegate action from a list of actions.

        Delegate actions allow signing transactions that can be executed later
        by another account.

        Args:
            actions: List of actions to include in the delegate action
            receiver_id: Account ID that will receive the delegate action
            public_key: Optional public key to use for signing. If None, uses
                the first configured signer

        Returns:
            DelegateActionModel ready to be signed
        """
        if public_key is None:
            pk = self._signers[0]
        else:
            pk = self._signer_by_pk[public_key]
        access_key = await self.get_access_key(pk)
        await self._update_last_block_hash()

        private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)
        verifying_key: VerifyKey = private_key.verify_key
        return DelegateActionModel(
            sender_id=self.account_id,
            receiver_id=receiver_id,
            actions=actions,
            nonce=access_key.nonce + 1,
            max_block_height=self._latest_block_height + 1000,
            public_key=base58.b58encode(verifying_key.encode()).decode("utf-8"),
        )

    def sign_delegate_transaction(
        self, delegate_action: Union[DelegateAction, DelegateActionModel]
    ) -> str:
        """
        Sign a delegate action transaction.

        Args:
            delegate_action: DelegateAction or DelegateActionModel to sign

        Returns:
            Base58-encoded signature string

        Raises:
            ValueError: If the public key is not found in the signer list
        """
        if isinstance(delegate_action, DelegateActionModel):
            delegate_action = delegate_action.near_delegate_action
        nep461_hash = bytes(bytearray(delegate_action.get_nep461_hash()))

        public_key = base58.b58encode(
            bytes(bytearray(delegate_action.public_key))  # noqa
        ).decode("utf-8")

        if public_key not in self._signer_by_pk:
            raise ValueError(f"Public key {public_key} not found in signer list")

        private_key = signing.SigningKey(
            self._signer_by_pk[public_key][:32], encoder=encoding.RawEncoder
        )
        sign = private_key.sign(nep461_hash).signature
        return base58.b58encode(sign).decode("utf-8")

    async def get_balance(self, account_id: str = None) -> int:
        """
        Get account balance in yoctoNEAR.

        Args:
            account_id: Account ID to query. If None, uses the current account.

        Returns:
            Account balance in yoctoNEAR (1 NEAR = 10^24 yoctoNEAR).
            Returns 0 if account does not exist.
        """
        if account_id is None:
            account_id = self.account_id
        data = await self._provider.get_account(account_id)
        if not data:
            return 0
        return int(data["amount"])

    @property
    def ft(self):
        """
        Get fungible token (FT) client.

        Returns:
            FT client instance for interacting with fungible tokens
        """
        return FT(self)
