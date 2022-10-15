import base58
import json
import itertools

from async_near import transactions
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
from async_near.models import TransactionResult, ViewFunctionResult
from async_near.signer import Signer
from async_near.providers import JsonProvider

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
    _account: dict
    _access_key: dict

    def __init__(self, provider: JsonProvider, signer: Signer):
        self._provider = provider
        self._signer = signer
        self._account_id = signer.account_id

    async def startup(self):
        await self._provider.startup()
        self._account = await self._provider.get_account(self._account_id)
        self._access_key = await self._provider.get_access_key(
            self._account_id, self._signer.key_pair.encoded_public_key()
        )

    async def _sync_acc(self):
        self._account = await self._provider.get_account(self._account_id)

    async def _sign_and_submit_tx(self, receiver_id, actions) -> TransactionResult:
        self._access_key["nonce"] += 1
        block_hash = (await self._provider.get_status())["sync_info"][
            "latest_block_hash"
        ]
        block_hash = base58.b58decode(block_hash.encode("utf8"))
        serialzed_tx = transactions.sign_and_serialize_transaction(
            receiver_id, self._access_key["nonce"], actions, block_hash, self._signer
        )
        result = await self._provider.send_tx_and_wait(serialzed_tx)
        if "Failure" in result["status"]:
            error_type, args = list(
                result["status"]["Failure"]["ActionError"]["kind"].items()
            )[0]
            raise _ERROR_TYPE_TO_EXCEPTION[error_type](**args)
        await self._sync_acc()

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

    @property
    def access_key(self):
        return self._access_key

    @property
    def state(self):
        return self._account

    async def fetch_state(self):
        """Fetch state for given account."""
        self._account = await self.provider.get_account(self.account_id)

    async def send_money(self, account_id, amount):
        """Sends funds to given account_id given amount."""
        return await self._sign_and_submit_tx(
            account_id, [transactions.create_transfer_action(amount)]
        )

    async def function_call(
        self, contract_id, method_name, args, gas=DEFAULT_ATTACHED_GAS, amount=0
    ):
        args = json.dumps(args).encode("utf8")
        return await self._sign_and_submit_tx(
            contract_id,
            [transactions.create_function_call_action(method_name, args, gas, amount)],
        )

    async def create_account(self, account_id, public_key, initial_balance):
        actions = [
            transactions.create_create_account_action(),
            transactions.create_full_access_key_action(public_key),
            transactions.create_transfer_action(initial_balance),
        ]
        return await self._sign_and_submit_tx(account_id, actions)

    async def deploy_contract(self, contract_code):
        return await self._sign_and_submit_tx(
            self._account_id,
            [transactions.create_deploy_contract_action(contract_code)],
        )

    async def stake(self, public_key, amount):
        return await self._sign_and_submit_tx(
            self._account_id, [transactions.create_staking_action(public_key, amount)]
        )

    async def create_and_deploy_contract(
        self, contract_id, public_key, contract_code, initial_balance
    ):
        actions = [
            transactions.create_create_account_action(),
            transactions.create_transfer_action(initial_balance),
            transactions.create_deploy_contract_action(contract_code),
        ] + (
            [transactions.create_full_access_key_action(public_key)]
            if public_key is not None
            else []
        )
        return await self._sign_and_submit_tx(contract_id, actions)

    async def create_deploy_and_init_contract(
        self,
        contract_id,
        public_key,
        contract_code,
        initial_balance,
        args,
        gas=DEFAULT_ATTACHED_GAS,
        init_method_name="new",
    ):
        args = json.dumps(args).encode("utf8")
        actions = [
            transactions.create_create_account_action(),
            transactions.create_transfer_action(initial_balance),
            transactions.create_deploy_contract_action(contract_code),
            transactions.create_function_call_action(init_method_name, args, gas, 0),
        ] + (
            [transactions.create_full_access_key_action(public_key)]
            if public_key is not None
            else []
        )
        return await self._sign_and_submit_tx(contract_id, actions)

    async def view_function(self, contract_id, method_name, args) -> ViewFunctionResult:
        result = await self._provider.view_call(
            contract_id, method_name, json.dumps(args).encode("utf8")
        )
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads("".join([chr(x) for x in result["result"]]))
        return ViewFunctionResult(**result)
