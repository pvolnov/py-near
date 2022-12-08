import asyncio
import datetime
import json
from typing import List, Union

import base58

from async_near import transactions
from async_near.dapps.ft.async_client import FT
from async_near.dapps.phone.async_client import Phone
from async_near.exceptions.execution import (
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
from async_near.models import TransactionResult, ViewFunctionResult, PublicKey
from async_near.providers import JsonProvider
from async_near.signer import Signer

DEFAULT_ATTACHED_GAS = 200000000000000


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
    _access_key: dict
    _lock: asyncio.Lock
    _latest_block_hash: str
    _latest_block_hash_ts: float = 0

    def __init__(self, provider: JsonProvider, signer: Signer):
        self._provider = provider
        self._signer = signer
        self._account_id = signer.account_id

    async def startup(self):
        self._lock = asyncio.Lock()

    async def _update_last_block_hash(self):
        if self._latest_block_hash_ts + 50 > datetime.datetime.utcnow().timestamp():
            return
        self._latest_block_hash = (await self._provider.get_status())["sync_info"][
            "latest_block_hash"
        ]
        self._latest_block_hash_ts = datetime.datetime.utcnow().timestamp()

    async def _sign_and_submit_tx(
        self, receiver_id, actions, nowait=False
    ) -> Union[TransactionResult, str]:
        async with self._lock:
            access_key = await self.get_access_key()
            await self._update_last_block_hash()

            block_hash = base58.b58decode(self._latest_block_hash.encode("utf8"))
            serialzed_tx = transactions.sign_and_serialize_transaction(
                receiver_id,
                access_key["nonce"] + 1,
                actions,
                block_hash,
                self._signer,
            )
            if nowait:
                return await self._provider.send_tx(serialzed_tx)

            result = await self._provider.send_tx_and_wait(serialzed_tx)
            if "Failure" in result["status"]:
                error_type, args = list(
                    result["status"]["Failure"]["ActionError"]["kind"].items()
                )[0]
                raise _ERROR_TYPE_TO_EXCEPTION[error_type](**args)

        return TransactionResult(**result)

    @property
    def account_id(self):
        return self._account_id

    @property
    def signer(self):
        return self._signer

    @property
    def provider(self):
        return self._provider

    async def get_access_key(self):
        return await self._provider.get_access_key(
            self._account_id, self._signer.key_pair.encoded_public_key()
        )

    async def get_access_key_list(self, account_id: str = None) -> List[PublicKey]:
        if account_id is None:
            account_id = self._account_id
        resp = await self._provider.get_access_key_list(account_id)
        result = []
        for key in resp["keys"]:
            result.append(PublicKey.build(key))
        return result

    async def fetch_state(self):
        """Fetch state for given account."""
        return await self._provider.get_account(self._account_id)

    async def send_money(self, account_id: str, amount: int, nowait=False):
        """Sends funds to given account_id given amount."""
        return await self._sign_and_submit_tx(
            account_id, [transactions.create_transfer_action(amount)], nowait
        )

    async def function_call(
        self,
        contract_id,
        method_name,
        args,
        gas=DEFAULT_ATTACHED_GAS,
        amount=0,
        nowait=False,
    ):
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
        allowance: int = 25000000000000000000000,
        nowait=False,
    ):
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
    ):
        actions = [
            transactions.create_full_access_key_action(public_key),
        ]
        return await self._sign_and_submit_tx(self._account_id, actions, nowait)

    async def delete_public_key(self, public_key: Union[str, bytes], nowait=False):
        actions = [
            transactions.create_delete_access_key_action(public_key),
        ]
        return await self._sign_and_submit_tx(self._account_id, actions, nowait)

    async def deploy_contract(self, contract_code: bytes, nowait=False):
        return await self._sign_and_submit_tx(
            self._account_id,
            [transactions.create_deploy_contract_action(contract_code)],
            nowait,
        )

    async def stake(self, public_key: str, amount: str, nowait=False):
        return await self._sign_and_submit_tx(
            self._account_id,
            [transactions.create_staking_action(public_key, amount)],
            nowait,
        )

    async def view_function(
        self, contract_id: str, method_name: str, args: dict
    ) -> ViewFunctionResult:
        result = await self._provider.view_call(
            contract_id, method_name, json.dumps(args).encode("utf8")
        )
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads("".join([chr(x) for x in result["result"]]))
        return ViewFunctionResult(**result)

    @property
    def phone(self):
        return Phone(self)

    @property
    def ft(self):
        return FT(self)
