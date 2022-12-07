import hashlib
from dataclasses import dataclass
from typing import Union, List

import base58

from async_near.serializer import BinarySerializer


@dataclass
class Signature:
    keyType: int
    data: bytes


@dataclass
class PublicKey:
    keyType: int
    data: bytes


@dataclass
class FunctionCallPermission:
    allowance: int
    receiverId: str
    methodNames: List[str]


class FullAccessPermission:
    pass


@dataclass
class AccessKeyPermission:
    enum: str
    data: Union[FunctionCallPermission, FullAccessPermission]


@dataclass
class AccessKey:
    nonce: int
    permission: AccessKeyPermission


class CreateAccount:
    pass


class DeployContract:
    pass


@dataclass
class FunctionCall:
    methodName: str
    args: bytes
    gas: int
    deposit: str


@dataclass
class Transfer:
    deposit: int


@dataclass
class Stake:
    stake: str
    publicKey: PublicKey


@dataclass
class AddKey:
    accessKey: AccessKey
    publicKey: PublicKey


@dataclass
class DeleteKey:
    publicKey: PublicKey


class DeleteAccount:
    pass


@dataclass
class Action:
    enum: str
    data: Union[
        Transfer, Stake, FunctionCall, AddKey, CreateAccount, DeleteKey, DeployContract
    ]


@dataclass
class Transaction:
    signerId: str
    publicKey: PublicKey
    nonce: int
    receiverId: str
    actions: List[Action]
    blockHash: str


@dataclass
class SignedTransaction:
    transaction: Transaction
    signature: Signature


tx_schema = dict(
    [
        [Signature, {"kind": "struct", "fields": [["keyType", "u8"], ["data", [64]]]}],
        [
            SignedTransaction,
            {
                "kind": "struct",
                "fields": [["transaction", Transaction], ["signature", Signature]],
            },
        ],
        [
            Transaction,
            {
                "kind": "struct",
                "fields": [
                    ["signerId", "string"],
                    ["publicKey", PublicKey],
                    ["nonce", "u64"],
                    ["receiverId", "string"],
                    ["blockHash", [32]],
                    ["actions", [Action]],
                ],
            },
        ],
        [PublicKey, {"kind": "struct", "fields": [["keyType", "u8"], ["data", [32]]]}],
        [
            AccessKey,
            {
                "kind": "struct",
                "fields": [
                    ["nonce", "u64"],
                    ["permission", AccessKeyPermission],
                ],
            },
        ],
        [
            AccessKeyPermission,
            {
                "kind": "enum",
                "field": "enum",
                "values": [
                    ["functionCall", FunctionCallPermission],
                    ["fullAccess", FullAccessPermission],
                ],
            },
        ],
        [
            FunctionCallPermission,
            {
                "kind": "struct",
                "fields": [
                    ["allowance", {"kind": "option", "type": "u128"}],
                    ["receiverId", "string"],
                    ["methodNames", ["string"]],
                ],
            },
        ],
        [FullAccessPermission, {"kind": "struct", "fields": []}],
        [
            Action,
            {
                "kind": "enum",
                "field": "enum",
                "values": [
                    ["createAccount", CreateAccount],
                    ["deployContract", DeployContract],
                    ["functionCall", FunctionCall],
                    ["transfer", Transfer],
                    ["stake", Stake],
                    ["addKey", AddKey],
                    ["deleteKey", DeleteKey],
                    ["deleteAccount", DeleteAccount],
                ],
            },
        ],
        [CreateAccount, {"kind": "struct", "fields": []}],
        [DeployContract, {"kind": "struct", "fields": [["code", ["u8"]]]}],
        [
            FunctionCall,
            {
                "kind": "struct",
                "fields": [
                    ["methodName", "string"],
                    ["args", ["u8"]],
                    ["gas", "u64"],
                    ["deposit", "u128"],
                ],
            },
        ],
        [Transfer, {"kind": "struct", "fields": [["deposit", "u128"]]}],
        [
            Stake,
            {"kind": "struct", "fields": [["stake", "u128"], ["publicKey", PublicKey]]},
        ],
        [
            AddKey,
            {
                "kind": "struct",
                "fields": [["publicKey", PublicKey], ["accessKey", AccessKey]],
            },
        ],
        [DeleteKey, {"kind": "struct", "fields": [["publicKey", PublicKey]]}],
        [DeleteAccount, {"kind": "struct", "fields": [["beneficiaryId", "string"]]}],
    ]
)


def sign_and_serialize_transaction(receiverId, nonce, actions, blockHash, signer):
    if signer.public_key is None:
        raise ValueError("Signer must have a public key")
    if blockHash is None:
        raise ValueError("Block hash is required")
    tx = Transaction(
        signer.account_id,
        PublicKey(0, signer.public_key),
        nonce,
        receiverId,
        actions,
        blockHash,
    )

    msg = BinarySerializer(tx_schema).serialize(tx)
    hash_ = hashlib.sha256(msg).digest()

    signature = Signature(0, signer.sign(hash_))
    signedTx = SignedTransaction(tx, signature)
    return BinarySerializer(tx_schema).serialize(signedTx)


def create_create_account_action():
    createAccount = CreateAccount()
    action = Action("createAccount", createAccount)
    return action


def create_full_access_key_action(pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    permission = AccessKeyPermission("fullAccess", FullAccessPermission())
    accessKey = AccessKey(0, permission)
    publicKey = PublicKey(0, pk)
    addKey = AddKey(accessKey, publicKey)
    action = Action("addKey", addKey)
    return action


def create_function_call_access_key_action(
    pk, allowance: int, receiverId: str, methodNames: List[str]
):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    permission = AccessKeyPermission(
        "functionCall", FunctionCallPermission(allowance, receiverId, methodNames)
    )
    accessKey = AccessKey(0, permission)
    publicKey = PublicKey(0, pk)
    addKey = AddKey(accessKey, publicKey)
    action = Action("addKey", addKey)
    return action


def create_delete_access_key_action(pk):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    publicKey = PublicKey(0, pk)
    deleteKey = DeleteKey(publicKey)
    action = Action("deleteKey", deleteKey)
    return action


def create_transfer_action(amount: int):
    transfer = Transfer(amount)
    action = Action("transfer", transfer)
    return action


create_payment_action = create_transfer_action


def create_staking_action(amount, pk):
    stake = Stake(amount, PublicKey(0, pk))
    action = Action("stake", stake)
    return action


def create_deploy_contract_action(code):
    deployContract = DeployContract()
    deployContract.code = code
    action = Action("deployContract", deployContract)
    return action


def create_function_call_action(method_name, args, gas, deposit):
    function_call = FunctionCall(method_name, args, gas, deposit)
    action = Action("functionCall", function_call)
    return action
