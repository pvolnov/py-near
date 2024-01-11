import json
from dataclasses import dataclass

from py_near.exceptions.provider import LackBalanceForState


class RpcNotAvailableError(Exception):
    pass


class RpcEmptyResponse(Exception):
    pass


class ActionErrorKind(Exception):
    def __init__(self, **kargs):
        for arg, value in kargs.items():
            setattr(self, arg, value)


@dataclass
class AccountAlreadyExistsError(ActionErrorKind):
    """
    Happens when CreateAccount action tries to create an account with account_id which is already exists in the storage
    """

    account_id: str


class AccountDoesNotExistError(ActionErrorKind):
    """
    Happens when TX receiver_id doesn't exist (but action is not Action::CreateAccount)
    """

    pass


class CreateAccountNotAllowedError(ActionErrorKind):
    """
    A newly created account must be under a namespace of the creator account
    """

    account_id: str
    predecessor_id: str

    def __init__(self, account_id, predecessor_id):
        self.predecessor_id = predecessor_id
        self.account_id = account_id


class ActorNoPermissionError(ActionErrorKind):
    """
    Administrative actions like `DeployContract`, `Stake`, `AddKey`, `DeleteKey`.
    can be proceed only if sender=receiver or the first TX action is a `CreateAccount` action
    """

    account_id: str
    actor_id: str

    def __init__(self, account_id, actor_id):
        self.actor_id = actor_id
        self.account_id = account_id


class DeleteKeyDoesNotExistError(ActionErrorKind):
    """
    Account tries to remove an access key that doesn't exist
    """

    account_id: str
    public_key: str

    def __init__(self, account_id, public_key):
        self.actor_id = public_key
        self.account_id = account_id


class AddKeyAlreadyExistsError(ActionErrorKind):
    """
    The public key is already used for an existing access key
    """

    account_id: str
    public_key: str

    def __init__(self, account_id, public_key):
        self.actor_id = public_key
        self.account_id = account_id


class DeleteAccountStakingError(ActionErrorKind):
    """
    Account is staking and can not be deleted
    """

    account_id: str

    def __init__(self, account_id):
        self.account_id = account_id


class DeleteAccountHasRentError(ActionErrorKind):
    """
    Foreign sender (sender=!receiver) can delete an account only if a target account hasn't enough tokens to pay rent
    """

    account_id: str
    balance: str

    def __init__(self, account_id, balance):
        self.balance = balance
        self.account_id = account_id


class RentUnpaidError(ActionErrorKind):
    """
    ActionReceipt can't be completed, because the remaining balance will not be enough to pay rent.
    """

    account_id: str
    amount: str

    def __init__(self, account_id, amount):
        self.amount = amount
        self.account_id = account_id


class TriesToUnstakeError(ActionErrorKind):
    """
    Account is not yet staked, but tries to unstake
    """

    account_id: str

    def __init__(self, account_id):
        self.account_id = account_id


class TriesToStakeError(ActionErrorKind):
    """
    The account doesn't have enough balance to increase the stake.
    """

    account_id: str
    stake: str
    locked: str
    balance: str

    def __init__(self, account_id, stake, locked, balance):
        self.account_id = account_id
        self.stake = stake
        self.locked = locked
        self.balance = balance


class FunctionCallError(ActionErrorKind):
    """
    An error occurred during a `FunctionCall` Action.
    """

    error: dict

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error = kwargs


class ExecutionError(FunctionCallError):
    """
    An error occurred during a `FunctionCall` Action.
    """


class NewReceiptValidationError(ActionErrorKind):
    """
    Error occurs when a new `ActionReceipt` created by the `FunctionCall` action fails
    """

    pass


class DelegateActionExpired(ActionErrorKind):
    """
    Error occurs when a new `DelegateActionExpired` created by the `FunctionCall` action fails
    """

    pass


class DelegateActionInvalidNonce(ActionErrorKind):
    """
    Nonce must be greater sender[public_key].nonce
    """

    pass


class DelegateActionInvalidSignature(ActionErrorKind):
    """
    Signature does not match the provided actions and given signer public key
    """

    pass


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
    "ExecutionError": ExecutionError,
    "NewReceiptValidationError": NewReceiptValidationError,
    "DelegateActionExpired": DelegateActionExpired,
    "LackBalanceForState": LackBalanceForState,
    "DelegateActionInvalidNonce": DelegateActionInvalidNonce,
    "DelegateActionInvalidSignature": DelegateActionInvalidSignature,
}


def parse_error(error_type, args):
    return _ERROR_TYPE_TO_EXCEPTION[error_type](**args)
