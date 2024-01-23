import base64
import json
from dataclasses import dataclass, field
from enum import Enum
from json import JSONDecodeError
from typing import List, Any, Optional, Union

import base58
import py_near_primitives
from py_near_primitives.py_near_primitives import (
    DelegateAction,
    TransferAction,
    DeleteAccountAction,
    FunctionCallAction,
    DeployContractAction,
    CreateAccountAction,
    SignedDelegateAction,
    DeleteKeyAction,
    AddKeyAction,
    StakeAction,
)
from py_near_primitives.py_near_primitives import (
    FunctionCallPermission,
    AccessKeyPermissionFieldless,
)

from py_near.exceptions.exceptions import parse_error

Action = Union[
    DelegateAction,
    TransferAction,
    DeleteAccountAction,
    FunctionCallAction,
    DeployContractAction,
    CreateAccountAction,
    SignedDelegateAction,
    DeleteKeyAction,
    AddKeyAction,
    StakeAction,
]


class ReceiptOutcome:
    logs: List[str]
    metadata: dict
    receipt_ids: List[str]
    status: dict
    tokens_burnt: str
    executor_id: str
    gas_burnt: int

    def __init__(self, data):
        self.logs = data["outcome"]["logs"]
        self.metadata = data["outcome"]["metadata"]
        self.receipt_ids = data["outcome"]["receipt_ids"]
        self.status = data["outcome"]["status"]
        self.tokens_burnt = data["outcome"]["tokens_burnt"]
        self.gas_burnt = data["outcome"]["gas_burnt"]

    @property
    def error(self):
        if "Failure" in self.status:
            error_type, args = list(
                self.status["Failure"]["ActionError"]["kind"].items()
            )[0]
            return parse_error(error_type, args)


class ActionType(str, Enum):
    FUNCTION_CALL = "FunctionCall"
    TRANSFER = "Transfer"
    DELETE_ACCOUNT = "DeleteAccount"
    CREATE_ACCOUNT = "CreateAccount"
    ADD_KEY = "AddKey"
    STAKE = "Stake"
    DELETE_KEY = "DeleteKey"
    DEPLOY_CONTRACT = "DeployContract"
    DELEGATE = "Delegate"


class PublicKeyPermissionType(str, Enum):
    FULL_ACCESS = "FullAccess"
    FUNCTION_CALL = "FunctionCall"


@dataclass
class AccessKey:
    permission_type: PublicKeyPermissionType
    nonce: int
    allowance: Optional[str]
    receiver_id: Optional[str]
    method_names: Optional[List[str]]

    @classmethod
    def build(cls, data: dict) -> "AccessKey":
        if data["permission"] == PublicKeyPermissionType.FULL_ACCESS:
            return cls(
                nonce=data["nonce"], permission_type=PublicKeyPermissionType.FULL_ACCESS
            )

        permission_type, permission_data = list(data["permission"].items())[0]
        return cls(
            nonce=data["nonce"],
            permission_type=PublicKeyPermissionType.FUNCTION_CALL,
            **permission_data,
        )


@dataclass
class ReceiptDelegateAction:
    actions: List["ReceiptAction"]
    sender_id: str
    receiver_id: str
    public_key: str
    nonce: int
    max_block_height: int

    @classmethod
    def build(cls, data: dict) -> "ReceiptDelegateAction":
        actions = [ReceiptAction.build(action) for action in data["actions"]]
        del data["actions"]
        return cls(
            actions=actions,
            **data,
        )

    @property
    def near_delegate_action(self) -> DelegateAction:
        return DelegateAction(
            sender_id=self.sender_id,
            receiver_id=self.receiver_id,
            actions=[a.near_action for a in self.actions],
            nonce=self.nonce,
            max_block_height=self.max_block_height,
            public_key=base58.b58decode(self.public_key),
        )

    @property
    def nep461_hash(self) -> bytes:
        return bytes(bytearray(self.near_delegate_action.get_nep461_hash()))


@dataclass
class DelegateActionModel:
    actions: List[
        Union[
            DelegateAction,
            TransferAction,
            DeleteAccountAction,
            FunctionCallAction,
            DeployContractAction,
            CreateAccountAction,
            SignedDelegateAction,
            DeleteKeyAction,
            AddKeyAction,
            StakeAction,
        ]
    ]
    sender_id: str
    receiver_id: str
    public_key: str
    nonce: int
    max_block_height: int

    @property
    def near_delegate_action(self) -> DelegateAction:
        return DelegateAction(
            sender_id=self.sender_id,
            receiver_id=self.receiver_id,
            actions=self.actions,
            nonce=self.nonce,
            max_block_height=self.max_block_height,
            public_key=base58.b58decode(self.public_key),
        )

    @property
    def nep461_hash(self) -> bytes:
        return bytes(bytearray(self.near_delegate_action.get_nep461_hash()))

    @staticmethod
    def bytes_to_json(data: bytes) -> dict:
        return json.loads(DelegateAction.bytes_to_json(data))

    @classmethod
    def from_bytes(cls, data: bytes) -> "DelegateActionModel":
        data = cls.bytes_to_json(data)
        actions = [ReceiptAction.build(action) for action in data.pop("actions")]
        raw_actions = []
        for act in actions:
            if act.transactions_type == ActionType.FUNCTION_CALL:
                raw_actions.append(
                    FunctionCallAction(
                        act.method_name,
                        base64.b64decode(act.args_raw),
                        int(act.gas),
                        int(act.deposit),
                    )
                )
            elif act.transactions_type == ActionType.ADD_KEY:
                if (
                    act.access_key.permission_type
                    == PublicKeyPermissionType.FUNCTION_CALL
                ):
                    ak = py_near_primitives.py_near_primitives.AccessKey(
                        act.access_key.nonce,
                        FunctionCallPermission(
                            act.access_key.receiver_id,
                            act.access_key.method_names,
                            act.access_key.allowance,
                        ),
                    )
                else:
                    ak = AccessKey(
                        act.access_key.nonce, AccessKeyPermissionFieldless.FullAccess
                    )
                bpk = base58.b58decode(act.public_key.split(":")[1])
                raw_actions.append(AddKeyAction(bpk, ak))
            else:
                raise Exception("Undelegeted action type")
        return cls(**data, actions=raw_actions)


@dataclass
class ReceiptAction:
    transactions_type: ActionType
    # Transaction
    deposit: Optional[str] = None
    gas: Optional[str] = field(default=None)
    # DeployContract
    code: Optional[str] = field(default=None)
    # FunctionCall
    method_name: Optional[str] = field(default=None)
    args: Any = field(default=None)
    args_raw: Any = field(default=None)
    # DeleteAccount
    beneficiary_id: Optional[str] = field(default=None)
    # AddKey
    public_key: Optional[str] = field(default=None)
    access_key: Optional[AccessKey] = field(default=None)
    # Stake
    stake: Optional[int] = field(default=None)
    # Delegate
    signature: Optional[str] = field(default=None)
    delegate_action: Optional[ReceiptDelegateAction] = field(default=None)

    @classmethod
    def build(cls, data: dict) -> "ReceiptAction":
        if isinstance(data, str) and data == "CreateAccount":
            return cls(transactions_type=ActionType.CREATE_ACCOUNT)

        action_type, action_data = list(data.items())[0]
        access_key = None
        args = args_raw = None
        if action_type == ActionType.ADD_KEY:
            access_key = AccessKey.build(action_data["access_key"])
        elif action_type == ActionType.FUNCTION_CALL:
            args_raw = action_data["args"]
            try:
                args = base64.b64decode(action_data["args"])
                args = json.loads(args)
            except (UnicodeDecodeError, JSONDecodeError):
                args = None

        if action_type == ActionType.DELEGATE:
            delegate_action = ReceiptDelegateAction.build(
                action_data["delegate_action"]
            )
            return cls(
                transactions_type=action_type,
                signature=action_data["signature"],
                delegate_action=delegate_action,
            )

        action_data.pop("args", None)
        action_data.pop("access_key", None)
        return cls(
            transactions_type=action_type,
            access_key=access_key,
            args=args,
            args_raw=args_raw,
            **action_data,
        )


class TransactionData:
    hash: str
    public_key: str
    receiver_id: str
    signature: str
    signer_id: str
    nonce: int
    actions: List[ReceiptAction]

    def __init__(
        self,
        hash,
        public_key,
        receiver_id,
        signature,
        signer_id,
        nonce,
        actions,
        **kargs,
    ):
        self.actions = [ReceiptAction.build(a) for a in actions]
        self.nonce = nonce
        self.signer_id = signer_id
        self.public_key = public_key
        self.receiver_id = receiver_id
        self.signature = signature
        self.hash = hash

    @property
    def url(self):
        return f"https://nearblocks.io/ru/txns/{self.hash}"


class TransactionResult:
    receipt_outcome: List[ReceiptOutcome]
    receipts: List[dict] = []
    transaction_outcome: ReceiptOutcome
    status: dict
    transaction: TransactionData

    def __init__(
        self, receipts_outcome, transaction_outcome, transaction, status, **kargs
    ):
        self.status = status
        self.transaction = TransactionData(**transaction)
        self.transaction_outcome = ReceiptOutcome(transaction_outcome)
        if "receipts" in kargs:
            self.receipts = kargs["receipts"]

        self.receipt_outcome = []
        for ro in receipts_outcome:
            self.receipt_outcome.append(ReceiptOutcome(ro))

    @property
    def logs(self):
        logs = self.transaction_outcome.logs
        for ro in self.receipt_outcome:
            logs.extend(ro.logs)
        return logs


class ViewFunctionResult:
    block_hash: str
    block_height: str
    logs: List[str]
    result: Any

    def __init__(self, block_height, logs, result, block_hash=""):
        self.block_hash = block_hash
        self.block_height = block_height
        self.logs = logs
        self.result = result


@dataclass
class AccessKey:
    permission_type: PublicKeyPermissionType
    nonce: int
    allowance: Optional[str] = None
    receiver_id: Optional[str] = None
    method_names: Optional[List[str]] = None

    @classmethod
    def build(cls, data: dict) -> "AccessKey":
        if data["permission"] == PublicKeyPermissionType.FULL_ACCESS:
            return cls(
                nonce=data["nonce"], permission_type=PublicKeyPermissionType.FULL_ACCESS
            )

        permission_type, permission_data = list(data["permission"].items())[0]
        return cls(
            nonce=data["nonce"],
            permission_type=PublicKeyPermissionType.FUNCTION_CALL,
            **permission_data,
        )


@dataclass
class PublicKey:
    public_key: str
    access_key: AccessKey

    @classmethod
    def build(cls, data: dict) -> "PublicKey":
        return cls(
            data["public_key"],
            AccessKey.build(data["access_key"]),
        )


@dataclass
class AccountAccessKey:
    block_hash: str
    block_height: int
    nonce: int
    permission: Union[str, dict]
