import asyncio
import collections
import json
from typing import List, Union, Dict, Optional

import base58
from nacl import signing, encoding
from loguru import logger
from py_near_primitives import DelegateAction

from py_near import constants
from py_near import transactions
from py_near import utils
from py_near.dapps.ft.async_client import FT
from py_near.dapps.staking.async_client import Staking
from py_near.exceptions.provider import (
    JsonProviderError,
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
    pass


class Account(object):
    """
    This class implement all blockchain functions for your account
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
        rpc_addr="https://rpc.mainnet.near.org",
    ):
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
            public_key = private_key.verify_key
            self._signer_by_pk[public_key] = pk
            self._free_signers.put_nowait(pk)
            self._signers.append(pk)

    async def startup(self):
        """
        Initialize async object
        :return:
        """
        self._lock = asyncio.Lock()
        self._lock_by_pk = collections.defaultdict(asyncio.Lock)
        self.chain_id = (await self._provider.get_status())["chain_id"]

    async def _update_last_block_hash(self):
        """
        Update last block hash& If it's older than 50 block before, transaction will fail
        :return: last block hash
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
        self, receiver_id, actions: List[Action], nowait=False
    ) -> Union[TransactionResult, str]:
        """
        Sign transaction and send it to blockchain
        :param receiver_id:
        :param actions: list of actions
        :param nowait: if nowait is True, return transaction hash, else wait execution
        confirm and return TransactionResult
        :return: transaction hash or TransactionResult
        """
        if not self._signers:
            raise ValueError("You must provide a private key or seed to call methods")
        await self._update_last_block_hash()

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
            if nowait:
                return await self._provider.send_tx(serialized_tx)
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
        if not self._signers:
            return None
        return self._signers[0]

    @property
    def provider(self) -> JsonProvider:
        return self._provider

    async def get_access_key(self, pk: bytes) -> AccountAccessKey:
        """
        Get access key for current account
        :return: AccountAccessKey
        """
        if pk is None:
            pk = self._signers[0]

        private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)
        public_key = private_key.verify_key
        public_key.to_curve25519_public_key()

        resp = await self._provider.get_access_key(
            self.account_id, base58.b58encode(public_key.encode()).decode("utf8")
        )
        if "error" in resp:
            raise ValueError(resp["error"])
        return AccountAccessKey(**resp)

    async def get_access_key_list(self, account_id: str = None) -> List[PublicKey]:
        """
        Get access key list for account_id, if account_id is None, get access key list for current account
        :param account_id:
        :return: list of PublicKey
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
        """Fetch state for given account."""
        return await self._provider.get_account(self.account_id)

    async def send_money(
        self, account_id: str, amount: int, nowait: bool = False
    ) -> TransactionResult:
        """
        Send money to account_id
        :param account_id: receiver account id
        :param amount: amount in yoctoNEAR
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
        """
        return await self.sign_and_submit_tx(
            account_id, [transactions.create_transfer_action(amount)], nowait
        )

    async def function_call(
        self,
        contract_id: str,
        method_name: str,
        args: dict,
        gas: int = constants.DEFAULT_ATTACHED_GAS,
        amount: int = 0,
        nowait: bool = False,
    ):
        """
        Call function on smart contract
        :param contract_id: smart contract address
        :param method_name: call method name
        :param args: json params for method
        :param gas: amount of attachment gas. Default is 200000000000000
        :param amount: amount of attachment NEAR, Default is 0
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
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
        )

    async def create_account(
        self,
        account_id: str,
        public_key: Union[str, bytes],
        initial_balance: int,
        nowait=False,
    ):
        """
        Create new account in subdomain of current account. For example, if current account is "test.near",
        you can create "wwww.test.near"
        :param account_id: new account id
        :param public_key: add public key to new account
        :param initial_balance: amount to transfer NEAR to new account
        :param nowait: is nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
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
        Add public key to account with access to smart contract methods
        :param public_key: public_key to add
        :param receiver_id: smart contract account id
        :param method_names: list of method names to allow
        :param allowance: maximum amount of gas to use for this key
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
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
        Add public key to account with full access
        :param public_key: public_key to add
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
        """
        actions = [
            transactions.create_full_access_key_action(public_key),
        ]
        return await self.sign_and_submit_tx(self.account_id, actions, nowait)

    async def delete_public_key(self, public_key: Union[str, bytes], nowait=False):
        """
        Delete public key from account
        :param public_key: public_key to delete
        :param nowait: is nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
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
    ):
        if isinstance(signature, str):
            signature = base58.b58decode(signature.replace("ed25519:", ""))
        if isinstance(delegate_action, DelegateActionModel):
            delegate_action = delegate_action.near_delegate_action

        actions = [
            transactions.create_signed_delegate(delegate_action, signature),
        ]
        return await self.sign_and_submit_tx(delegate_action.sender_id, actions, nowait)

    async def deploy_contract(self, contract_code: bytes, nowait=False):
        """
        Deploy smart contract to account
        :param contract_code: smart contract code
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
        """
        return await self.sign_and_submit_tx(
            self.account_id,
            [transactions.create_deploy_contract_action(contract_code)],
            nowait,
        )

    async def stake(self, public_key: str, amount: str, nowait=False):
        """
        Stake NEAR on account. Account must have enough balance to be in validators pool
        :param public_key: public_key to stake
        :param amount: amount of NEAR to stake
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
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
    ) -> ViewFunctionResult:
        """
        Call view function on smart contract. View function is read only function, it can't change state
        :param contract_id: smart contract account id
        :param method_name: method name to call
        :param args: json args to call method
        :param block_id: execution view transaction in block with given id
        :return: result of view function call
        """
        result = await self._provider.view_call(
            contract_id, method_name, json.dumps(args).encode("utf8"), block_id=block_id
        )
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads("".join([chr(x) for x in result["result"]]))
        return ViewFunctionResult(**result)

    async def create_delegate_action(
        self, actions: List[Action], receiver_id, public_key: Optional[str] = None
    ):
        """
        Create delegate action from list of actions
        :param actions:
        :param receiver_id:
        :return:
        """
        if public_key is None:
            pk = self._signers[0]
        else:
            pk = self._signer_by_pk[public_key]
        access_key = await self.get_access_key(pk)
        await self._update_last_block_hash()

        private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)
        verifying_key = private_key.verify_key
        return DelegateActionModel(
            sender_id=self.account_id,
            receiver_id=receiver_id,
            actions=actions,
            nonce=access_key.nonce + 1,
            max_block_height=self._latest_block_height + 1000,
            public_key=base58.b58encode(verifying_key.to_bytes()).decode("utf-8"),
        )

    def sign_delegate_transaction(
        self, delegate_action: Union[DelegateAction, DelegateActionModel]
    ) -> str:
        """
        Sign delegate transaction
        :param delegate_action: DelegateAction or DelegateActionModel
        :return: signature (bytes)
        """
        if isinstance(delegate_action, DelegateActionModel):
            delegate_action = delegate_action.near_delegate_action
        nep461_hash = bytes(bytearray(delegate_action.get_nep461_hash()))

        public_key = base58.b58encode(
            bytes(bytearray(delegate_action.public_key))  # noqa
        ).decode("utf-8")

        if public_key not in self._signer_by_pk:
            raise ValueError(f"Public key {public_key} not found in signer list")

        private_key = signing.SigningKey(self._signer_by_pk[public_key], encoder=encoding.RawEncoder)
        sign = private_key.sign(nep461_hash)
        return base58.b58encode(sign).decode("utf-8")

    async def get_balance(self, account_id: str = None) -> int:
        """
        Get account balance
        :param account_id: if account_id is None, return balance of current account
        :return: balance of account in yoctoNEAR
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
        Get client for fungible tokens
        :return: FT(self)
        """
        return FT(self)

    @property
    def staking(self):
        """
        Get client for staking
        :return: Staking(self)
        """
        return Staking(self)
