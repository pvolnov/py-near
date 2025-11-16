import base64
from typing import Union, List

import base58
from nacl import signing, encoding
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
    """
    Sign and serialize a transaction.

    Args:
        account_id: Account ID that signs the transaction
        private_key: Private key (bytes or base58 string) for signing
        receiver_id: Account ID that receives the transaction
        nonce: Nonce value for the transaction
        actions: List of actions to include
        block_hash: Block hash to reference (bytes)

    Returns:
        Base64-encoded signed transaction string
    """
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
    """
    Calculate transaction hash without signing.

    Args:
        account_id: Account ID that signs the transaction
        private_key: Private key (bytes or base58 string) for deriving public key
        receiver_id: Account ID that receives the transaction
        nonce: Nonce value for the transaction
        actions: List of actions to include
        block_hash: Block hash to reference (bytes)

    Returns:
        Base58-encoded transaction hash string
    """
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
    """
    Create a CreateAccount action.

    Returns:
        CreateAccountAction instance
    """
    return CreateAccountAction()


def create_full_access_key_action(pk: Union[bytes, str]):
    """
    Create an AddKey action with full access permissions.

    Args:
        pk: Public key (bytes or base58 string)

    Returns:
        AddKeyAction instance with full access permissions
    """
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        public_key=pk,
        access_key=AccessKey(0, AccessKeyPermissionFieldless.FullAccess),
    )


def create_function_call_access_key_action(
    pk, allowance: int, receiver_id: str, method_names: List[str]
):
    """
    Create an AddKey action with function call permissions.

    Args:
        pk: Public key (bytes or base58 string)
        allowance: Maximum gas allowance (in yoctoNEAR gas units)
        receiver_id: Contract account ID that this key can interact with
        method_names: List of method names the key is allowed to call

    Returns:
        AddKeyAction instance with function call permissions
    """
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return AddKeyAction(
        pk,
        AccessKey(0, FunctionCallPermission(receiver_id, method_names, allowance)),
    )


def create_delete_access_key_action(pk: Union[bytes, str]):
    """
    Create a DeleteKey action.

    Args:
        pk: Public key (bytes or base58 string) to delete

    Returns:
        DeleteKeyAction instance
    """
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return DeleteKeyAction(pk)


def create_signed_delegate(action: DelegateAction, signature: bytes):
    """
    Create a SignedDelegate action.

    Args:
        action: DelegateAction to sign
        signature: Signature bytes for the delegate action

    Returns:
        SignedDelegateAction instance
    """
    return SignedDelegateAction(delegate_action=action, signature=signature)


def create_transfer_action(amount: int):
    """
    Create a Transfer action.

    Args:
        amount: Amount to transfer in yoctoNEAR

    Returns:
        TransferAction instance
    """
    return TransferAction(amount)


def create_staking_action(amount, pk: Union[bytes, str]):
    """
    Create a Stake action.

    Args:
        amount: Amount to stake in yoctoNEAR (as string)
        pk: Validator's public key (bytes or base58 string)

    Returns:
        StakeAction instance
    """
    if isinstance(pk, str):
        pk = base58.b58decode(pk.replace("ed25519:", ""))
    return StakeAction(amount, pk)


def create_deploy_contract_action(code: bytes):
    """
    Create a DeployContract action.

    Args:
        code: Compiled contract code (WASM bytes)

    Returns:
        DeployContractAction instance
    """
    return DeployContractAction(code)


def create_function_call_action(method_name: str, args, gas: int, deposit: int):
    """
    Create a FunctionCall action.

    Args:
        method_name: Name of the method to call
        args: Serialized method arguments (bytes)
        gas: Amount of gas to attach (in yoctoNEAR gas units)
        deposit: Amount of NEAR to attach (in yoctoNEAR)

    Returns:
        FunctionCallAction instance
    """
    return FunctionCallAction(method_name, args, gas, deposit)


def create_deploy_global_contract_action(
    code: bytes, use_account_id: bool = False
):
    """
    Create a DeployGlobalContract action.

    Args:
        code: Compiled contract code (WASM bytes)
        use_account_id: Deployment mode for the global contract

    Returns:
        DeployGlobalContractAction instance
    """
    if use_account_id:
        return DeployGlobalContractAction.from_account_id(code)
    return DeployGlobalContractAction.from_code_hash(code)


def create_use_global_contract_action_by_code_hash(hash_bytes: Union[bytes, str]):
    """
    Create a UseGlobalContract action identified by code hash.

    Args:
        hash_bytes: Contract code hash (32 bytes, bytes or base58 string)

    Returns:
        UseGlobalContractAction instance

    Raises:
        ValueError: If hash_bytes is not exactly 32 bytes
    """
    if isinstance(hash_bytes, str):
        hash_bytes = base58.b58decode(hash_bytes)
    if len(hash_bytes) != 32:
        raise ValueError("hash_bytes must be exactly 32 bytes")
    hash_array = bytes(hash_bytes[:32])
    return UseGlobalContractAction.from_code_hash(hash_array)


def create_use_global_contract_action_by_account_id(account_id: str):
    """
    Create a UseGlobalContract action identified by account ID.

    Args:
        account_id: Account ID of the global contract

    Returns:
        UseGlobalContractAction instance
    """
    return UseGlobalContractAction.from_account_id(account_id)
