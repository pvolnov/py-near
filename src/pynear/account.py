import asyncio
import json
from typing import List, Union

import base58
from pyonear.account_id import AccountId
from pyonear.crypto import InMemorySigner, ED25519SecretKey
from pyonear.transaction import Action

from pynear import utils
from pynear import constants
from pynear.dapps.ft.async_client import FT
from pynear.dapps.phone.async_client import Phone
from pynear.exceptions.exceptions import (
    AccountAlreadyExistsError,
    AccountDoesNotExistError,
    CreateAccountNotAllowedError,
    ActorNoPermissionError,
    DeleteKeyDoesNotExistError,
    AddKeyAlreadyExistsError,
    DeleteAccountStakingError,
    DeleteAccountHasRentError,
    RentUnpaidError,
    TriesToUnstakeError,
    TriesToStakeError,
    FunctionCallError,
    NewReceiptValidationError,
)
from pynear.models import (
    TransactionResult,
    ViewFunctionResult,
    PublicKey,
    AccountAccessKey,
)
from pynear.providers import JsonProvider
from pynear import transactions



_ERROR_TYPE_TO_EXCEPTION = {
    "AccountAlreadyExists": AccountAlreadyExistsError,
    "AccountDoesNotExist": AccountDoesNotExistError,
    "CreateAccountNotAllowed": CreateAccountNotAllowedError,
    "ActorNoPermission": ActorNoPermissionError,
    "DeleteKeyDoesNotExist": DeleteKeyDoesNotExistError,
    "AddKeyAlreadyExists": AddKeyAlreadyExistsError,
    "DeleteAccountStaking": DeleteAccountStakingError,
    "DeleteAccountHasRent": DeleteAccountHasRentError,
    "RentUnpaid": RentUnpaidError,
    "TriesToUnstake": TriesToUnstakeError,
    "TriesToStake": TriesToStakeError,
    "FunctionCallError": FunctionCallError,
    "NewReceiptValidationError": NewReceiptValidationError,
}


class ViewFunctionError(Exception):
    pass


class Account(object):
    """
    This class implement all blockchain functions for your account
    """

    _access_key: dict
    _lock: asyncio.Lock
    _latest_block_hash: str
    _latest_block_hash_ts: float = 0
    chain_id: str = "mainnet"

    def __init__(
        self, account_id, private_key, rpc_addr=constants.RPC_MAINNET
    ):
        if isinstance(private_key, str):
            private_key = base58.b58decode(private_key.replace("ed25519:", ""))
        self._provider = JsonProvider(rpc_addr)

        self._signer = InMemorySigner(
            AccountId(account_id),
            ED25519SecretKey(private_key).public_key(),
            ED25519SecretKey(private_key),
        )
        self._account_id = account_id

    async def startup(self):
        """
        Initialize async object
        :return:
        """
        self._lock = asyncio.Lock()
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
        self._latest_block_hash_ts = utils.timestamp()

    async def _sign_and_submit_tx(
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
        async with self._lock:
            access_key = await self.get_access_key()
            await self._update_last_block_hash()

            block_hash = base58.b58decode(self._latest_block_hash.encode("utf8"))
            serialized_tx = transactions.sign_and_serialize_transaction(
                receiver_id,
                access_key.nonce + 1,
                actions,
                block_hash,
                self._signer,
            )
            if nowait:
                return await self._provider.send_tx(serialized_tx)

            result = await self._provider.send_tx_and_wait(serialized_tx)
            if "Failure" in result["status"]:
                error_type, args = list(
                    result["status"]["Failure"]["ActionError"]["kind"].items()
                )[0]
                raise _ERROR_TYPE_TO_EXCEPTION[error_type](**args)

        return TransactionResult(**result)

    @property
    def account_id(self) -> AccountId:
        return self._account_id

    @property
    def signer(self) -> InMemorySigner:
        return self._signer

    @property
    def provider(self) -> JsonProvider:
        return self._provider

    async def get_access_key(self) -> AccountAccessKey:
        """
        Get access key for current account
        :return: AccountAccessKey
        """
        return AccountAccessKey(
            **await self._provider.get_access_key(
                self._account_id, str(self._signer.public_key)
            )
        )

    async def get_access_key_list(self, account_id: str = None) -> List[PublicKey]:
        """
        Get access key list for account_id, if account_id is None, get access key list for current account
        :param account_id:
        :return: list of PublicKey
        """
        if account_id is None:
            account_id = self._account_id
        resp = await self._provider.get_access_key_list(account_id)
        result = []
        if "keys" in resp and isinstance(resp["keys"], list):
            for key in resp["keys"]:
                result.append(PublicKey(**key))
        return result

    async def fetch_state(self) -> dict:
        """Fetch state for given account."""
        return await self._provider.get_account(self._account_id)

    async def send_money(self, account_id: str, amount: int, nowait: bool = False) -> TransactionResult:
        """
        Send money to account_id
        :param account_id: receiver account id
        :param amount: amount in yoctoNEAR
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
        """
        return await self._sign_and_submit_tx(
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
        args = json.dumps(args).encode("utf8")
        return await self._sign_and_submit_tx(
            contract_id,
            [transactions.create_function_call_action(method_name, args, gas, amount)],
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
        return await self._sign_and_submit_tx(account_id, actions, nowait)

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
        return await self._sign_and_submit_tx(self._account_id, actions, nowait)

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
        return await self._sign_and_submit_tx(self._account_id, actions, nowait)

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
        return await self._sign_and_submit_tx(self._account_id, actions, nowait)

    async def deploy_contract(self, contract_code: bytes, nowait=False):
        """
        Deploy smart contract to account
        :param contract_code: smart contract code
        :param nowait: if nowait is True, return transaction hash, else wait execution
        :return: transaction hash or TransactionResult
        """
        return await self._sign_and_submit_tx(
            self._account_id,
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
        return await self._sign_and_submit_tx(
            self._account_id,
            [transactions.create_staking_action(public_key, amount)],
            nowait,
        )

    async def view_function(
        self, contract_id: str, method_name: str, args: dict
    ) -> ViewFunctionResult:
        """
        Call view function on smart contract. View function is read only function, it can't change state
        :param contract_id: smart contract account id
        :param method_name: method name to call
        :param args: json args to call method
        :return: result of view function call
        """
        result = await self._provider.view_call(
            contract_id, method_name, json.dumps(args).encode("utf8")
        )
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads("".join([chr(x) for x in result["result"]]))
        return ViewFunctionResult(**result)

    async def get_balance(self, account_id: str = None) -> int:
        """
        Get account balance
        :param account_id: if account_id is None, return balance of current account
        :return: balance of account in yoctoNEAR
        """
        if account_id is None:
            account_id = self._account_id
        return int((await self._provider.get_account(account_id))["amount"])

    @property
    def phone(self):
        """
        Get client for phone.herewallet.near
        :return: Phone(self)
        """
        return Phone(self)

    @property
    def ft(self):
        """
        Get client for fungible tokens
        :return: FT(self)
        """
        return FT(self)
