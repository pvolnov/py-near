from dataclasses import dataclass
from enum import Enum
from typing import List, Any, Optional, Union


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


class TransactionData:
    hash: str
    public_key: str
    receiver_id: str
    signature: str
    signer_id: str
    nonce: int
    actions: List[dict]

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
        self.actions = actions
        self.nonce = nonce
        self.signer_id = signer_id
        self.public_key = public_key
        self.receiver_id = receiver_id
        self.signature = signature
        self.hash = hash

    @property
    def url(self):
        return f"https://explorer.near.org/transactions/{self.hash}"


class TransactionResult:
    receipt_outcome: List[ReceiptOutcome]
    transaction_outcome: ReceiptOutcome
    status: dict
    transaction: TransactionData

    def __init__(self, receipts_outcome, transaction_outcome, transaction, status):
        self.status = status
        self.transaction = TransactionData(**transaction)
        self.transaction_outcome = ReceiptOutcome(transaction_outcome)

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

    def __init__(self, block_hash, block_height, logs, result):
        self.block_hash = block_hash
        self.block_height = block_height
        self.logs = logs
        self.result = result


class PublicKeyPermissionType(str, Enum):
    FULL_ACCESS = "FullAccess"
    FUNCTION_CALL = "FunctionCall"


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
            return cls(nonce=data["nonce"], permission_type=PublicKeyPermissionType.FULL_ACCESS)

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
