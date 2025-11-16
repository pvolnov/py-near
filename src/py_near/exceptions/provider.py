import json
from typing import Optional

from loguru import logger


class JsonProviderError(Exception):
    trx_hash: Optional[str] = None
    error_json: dict

    def __init__(self, *args, error_json=None, **kargs):
        self.error_json = error_json


class TransactionError(JsonProviderError):
    pass


class AccountError(JsonProviderError):
    pass


class BlockError(JsonProviderError):
    pass


class AccessKeyError(JsonProviderError):
    pass


class UnknownAccessKeyError(AccessKeyError):
    """
    The requested public_key has not been found while viewing since the
    public key has not been created or has been already deleted
    """

    pass


class UnknownBlockError(BlockError):
    """
    The requested block has not been produced yet or it has been
    garbage-collected (cleaned up to save space on the RPC node)
    """

    pass


class InternalError(TransactionError, AccountError, BlockError):
    """
    Something went wrong with the node itself or overloaded
    """

    pass


class NoSyncedYetError(BlockError):
    """
    The node is still syncing and the requested block is not in the database yet
    """

    pass


class InvalidAccount(AccountError):
    """
    The requested account_id is invalid
    """

    pass


class UnknownAccount(AccountError):
    """
    The requested account_id has not been found while viewing since the
    account has not been created or has been already deleted
    """

    pass


class NoContractCodeError(AccountError):
    """
    The account does not have any contract deployed on it
    """

    pass


class TooLargeContractStateError(AccountError):
    """
    The requested contract state is too large to be returned from this node
    (the default limit is 50kb of state size)
    """

    pass


class UnavailableShardError(AccountError):
    """
    The node was unable to find the requested data because it does not track the shard where data is present
    """

    pass


class NoSyncedBlocksError(AccountError):
    """
    The node is still syncing and the requested block is not in the database yet
    """

    pass


class InvalidTransactionError(TransactionError):
    """
    An error happened during transaction execution
    """

    pass


class TxExecutionError(InvalidTransactionError):
    def __init__(self, data={}, error_json=None, **kwargs):
        super().__init__(error_json=error_json)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                logger.error(f"Failed to parse TxExecutionError data: {data}")
                raise InvalidTransactionError(data)
        data.update(kwargs)
        for key, value in data.items():
            setattr(self, key, value)


class InvalidTxError(TxExecutionError):
    pass


class ActionErrorKind(TxExecutionError):
    pass


class AccountAlreadyExists(ActionErrorKind):
    account_id: str


class AccountDoesNotExist(ActionErrorKind):
    account_id: str


class CreateAccountNotAllowed(ActionErrorKind):
    account_id: str
    predecessor_id: str


class ActorNoPermission(ActionErrorKind):
    account_id: str
    actor_id: str


class DeleteKeyDoesNotExist(ActionErrorKind):
    account_id: str
    public_key: str


class AddKeyAlreadyExists(ActionErrorKind):
    account_id: str
    public_key: str


class DeleteAccountStaking(ActionErrorKind):
    account_id: str


class DeleteAccountHasRent(ActionErrorKind):
    account_id: str
    balance: str


class RentUnpaid(ActionErrorKind):
    account_id: str
    amount: str


class TriesToUnstake(ActionErrorKind):
    account_id: str


class TriesToStake(ActionErrorKind):
    account_id: str
    stake: str
    locked: str
    balance: str


class FunctionCallError(ActionErrorKind):
    pass


class NewReceiptValidationError(ActionErrorKind):
    pass


_ACTION_ERROR_KINDS = {
    "AccountAlreadyExists": AccountAlreadyExists,
    "ActorNoPermission": ActorNoPermission,
    "CreateAccountNotAllowed": CreateAccountNotAllowed,
    "AccountDoesNotExist": AccountDoesNotExist,
    "DeleteKeyDoesNotExist": DeleteKeyDoesNotExist,
    "DeleteAccountStaking": DeleteAccountStaking,
    "AddKeyAlreadyExists": AddKeyAlreadyExists,
    "DeleteAccountHasRent": DeleteAccountHasRent,
    "RentUnpaid": RentUnpaid,
    "TriesToUnstake": TriesToUnstake,
    "TriesToStake": TriesToStake,
    "FunctionCallError": FunctionCallError,
    "ActionErrorKind": ActionErrorKind,
}


class ActionError(TxExecutionError):
    index: Optional[int]
    kind: ActionErrorKind

    def __init__(self, data, error_json=None):
        self.error_json = error_json
        if isinstance(data, str):
            data = json.loads(data)
        self.index = data.get("index", None)
        key, value = list(data["kind"].items())[0]
        self.kind = _ACTION_ERROR_KINDS[key](value)


class InvalidNonce(InvalidTxError):
    tx_nonce: int
    ak_nonce: int


class InvalidAccessKeyError(InvalidTxError):
    pass


class InvalidSignerId(InvalidTxError):
    signer_id: str


class SignerDoesNotExist(InvalidTxError):
    signer_id: str


class InvalidReceiverId(InvalidTxError):
    receiver_id: str


class NotEnoughBalance(InvalidTxError):
    signer_id: str
    balance: str
    cost: str


class LackBalanceForState(InvalidTxError):
    amount: str
    signer_id: str


class CostOverflow(InvalidTxError):
    pass


class InvalidChain(InvalidTxError):
    pass


class Expired(InvalidTxError):
    pass


class ActionsValidation(InvalidTxError):
    pass


class InvalidSignature(InvalidTxError):
    pass


class RPCTimeoutError(TransactionError):
    """
    Transaction was routed, but has not been recorded on chain in 10 seconds.
    """

    pass


# import inspect
# import sys
# clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
# res = {}
# for c in clsmembers:
#     print(f"\"{c[0]}\": {c[0]},")


ERROR_CODE_TO_EXCEPTION = {
    "AccessKeyError": AccessKeyError,
    "AccountAlreadyExists": AccountAlreadyExists,
    "AccountDoesNotExist": AccountDoesNotExist,
    "AccountError": AccountError,
    "ActionError": ActionError,
    "ActionErrorKind": ActionErrorKind,
    "ActionsValidation": ActionsValidation,
    "ActorNoPermission": ActorNoPermission,
    "AddKeyAlreadyExists": AddKeyAlreadyExists,
    "BlockError": BlockError,
    "CostOverflow": CostOverflow,
    "CreateAccountNotAllowed": CreateAccountNotAllowed,
    "DeleteAccountHasRent": DeleteAccountHasRent,
    "DeleteAccountStaking": DeleteAccountStaking,
    "DeleteKeyDoesNotExist": DeleteKeyDoesNotExist,
    "Expired": Expired,
    "FunctionCallError": FunctionCallError,
    "InternalError": InternalError,
    "InvalidAccessKeyError": InvalidAccessKeyError,
    "InvalidAccount": InvalidAccount,
    "InvalidChain": InvalidChain,
    "InvalidNonce": InvalidNonce,
    "InvalidReceiverId": InvalidReceiverId,
    "InvalidSignature": InvalidSignature,
    "InvalidSignerId": InvalidSignerId,
    "InvalidTransactionError": InvalidTransactionError,
    "InvalidTxError": InvalidTxError,
    "JsonProviderError": JsonProviderError,
    "NewReceiptValidationError": NewReceiptValidationError,
    "NoContractCodeError": NoContractCodeError,
    "NoSyncedBlocksError": NoSyncedBlocksError,
    "NoSyncedYetError": NoSyncedYetError,
    "NotEnoughBalance": NotEnoughBalance,
    "LackBalanceForState": LackBalanceForState,
    "RentUnpaid": RentUnpaid,
    "RpcTimeoutError": RPCTimeoutError,
    "SignerDoesNotExist": SignerDoesNotExist,
    "TooLargeContractStateError": TooLargeContractStateError,
    "TransactionError": TransactionError,
    "TriesToStake": TriesToStake,
    "TriesToUnstake": TriesToUnstake,
    "TxExecutionError": TxExecutionError,
    "UnavailableShardError": UnavailableShardError,
    "UnknownAccessKeyError": UnknownAccessKeyError,
    "UnknownAccount": UnknownAccount,
    "UnknownBlockError": UnknownBlockError,
}
