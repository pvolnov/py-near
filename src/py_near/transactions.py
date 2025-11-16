import base64
from typing import Union, List
from nacl import signing, encoding
import base58
from py_near_primitives import (
    CreateAccountAction,
    AddKeyAction,
    DeleteKeyAction,
    TransferAction,
    SignedDelegateAction,
    DelegateAction,
    DeployContractAction,
    FunctionCallAction,
    StakeAction,
    Transaction,
    AccessKey,
    AccessKeyPermissionFieldless,
    FunctionCallPermission,
    DeployGlobalContractAction,
    UseGlobalContractAction,
    GlobalContractDeployMode,
    GlobalContractIdentifierCodeHash,
    GlobalContractIdentifierAccountId,
)

from py_near.models import Action


def sign_and_serialize_transaction(
    account_id,
    private_key,
    receiver_id,
    nonce,
    actions: List[Action],
    block_hash: bytes,
) -> str:
    if isinstance(private_key, str):
        pk = base58.b58decode(private_key.replace("ed25519:", ""))
    else:
        pk = private_key
    private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)

    transaction = Transaction(
        account_id,
        private_key.verify_key.encode(),
        nonce,
        receiver_id,
        block_hash,
        actions,
    )

    signed_trx = bytes(bytearray(transaction.to_vec(pk)))
    return base64.b64encode(signed_trx).decode("utf-8")


def calc_trx_hash(
    account_id,
    private_key,
    receiver_id,
    nonce,
    actions: List[Action],
    block_hash: bytes,
) -> str:
    if isinstance(private_key, str):
        pk = base58.b58decode(private_key.replace("ed25519:", ""))
    else:
        pk = private_key
    private_key = signing.SigningKey(pk[:32], encoder=encoding.RawEncoder)

    transaction = Transaction(
        account_id,
        private_key.verify_key.encode(),
        nonce,
        receiver_id,
        block_hash,
        actions,
    )

    signed_trx = bytes(bytearray(transaction.get_hash()))
    return base58.b58encode(signed_trx).decode("utf-8")


def create_create_account_action():
    return CreateAccountAction()


def create_full_access_key_action(pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        public_key=pk,
        access_key=AccessKey(0, AccessKeyPermissionFieldless.FullAccess),
    )


def create_function_call_access_key_action(
    pk, allowance: int, receiver_id: str, method_names: List[str]
):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        pk,
        AccessKey(0, FunctionCallPermission(receiver_id, method_names, allowance)),
    )


def create_delete_access_key_action(pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return DeleteKeyAction(pk)


def create_signed_delegate(action: DelegateAction, signature: bytes):
    return SignedDelegateAction(delegate_action=action, signature=signature)


def create_transfer_action(amount: int):
    return TransferAction(amount)


def create_staking_action(amount, pk: Union[bytes, str]):
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return StakeAction(amount, pk)


def create_deploy_contract_action(code: bytes):
    return DeployContractAction(code)


def create_function_call_action(method_name: str, args, gas: int, deposit: int):
    return FunctionCallAction(method_name, args, gas, deposit)


def create_deploy_global_contract_action(
    code: bytes, deploy_mode: GlobalContractDeployMode
):
    return DeployGlobalContractAction(code, deploy_mode)


def create_use_global_contract_action_by_code_hash(hash_bytes: Union[bytes, str]):
    if isinstance(hash_bytes, str):
        hash_bytes = base58.b58decode(hash_bytes)
    if len(hash_bytes) != 32:
        raise ValueError("hash_bytes must be exactly 32 bytes")
    hash_array = bytes(hash_bytes[:32])
    identifier = GlobalContractIdentifierCodeHash(hash_array)
    return UseGlobalContractAction(identifier)


def create_use_global_contract_action_by_account_id(account_id: str):
    identifier = GlobalContractIdentifierAccountId(account_id)
    return UseGlobalContractAction(identifier)
