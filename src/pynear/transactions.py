from typing import Union, List

import base58
from pyonear.account import (
    AccessKey,
    AccessKeyPermissionFieldless,
    FunctionCallPermission,
)
from pyonear.account_id import AccountId
from pyonear.crypto import ED25519PublicKey, InMemorySigner
from pyonear.crypto_hash import CryptoHash
from pyonear.transaction import (
    CreateAccountAction,
    AddKeyAction,
    DeleteKeyAction,
    TransferAction,
    DeployContractAction,
    FunctionCallAction,
    StakeAction,
    Transaction,
)


def sign_and_serialize_transaction(
    receiver_id, nonce, actions, block_hash, signer: InMemorySigner
) -> str:
    return (
        Transaction(
            signer.account_id,
            signer.public_key,
            nonce,
            AccountId(receiver_id),
            CryptoHash(block_hash),
            actions,
        )
        .sign(signer)
        .to_base64()
    )


def create_create_account_action():
    return CreateAccountAction()


def create_full_access_key_action(pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        public_key=ED25519PublicKey(pk),
        access_key=AccessKey(0, AccessKeyPermissionFieldless.FullAccess),
    )


def create_function_call_access_key_action(
    pk, allowance: int, receiver_id: str, method_names: List[str]
):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        ED25519PublicKey(pk),
        AccessKey(0, FunctionCallPermission(receiver_id, method_names, allowance)),
    )


def create_delete_access_key_action(pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    key = ED25519PublicKey(pk)
    return DeleteKeyAction(key)


def create_transfer_action(amount: int):
    return TransferAction(amount)


def create_staking_action(amount, pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    key = ED25519PublicKey(pk)
    return StakeAction(amount, key)


def create_deploy_contract_action(code: bytes):
    return DeployContractAction(code)


def create_function_call_action(method_name: str, args, gas: int, deposit: int):
    return FunctionCallAction(method_name, args, gas, deposit)
