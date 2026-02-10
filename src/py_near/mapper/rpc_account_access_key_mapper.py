from typing import Union

from near_jsonrpc_models import AccessKeyPermissionViewGasKeyFullAccess, AccessKeyPermissionViewFullAccess, \
    AccessKeyPermissionViewFunctionCall, AccessKeyPermissionViewGasKeyFunctionCall, RpcQueryResponseAccessKeyView

from py_near.models import AccountAccessKey


class RpcAccountAccessKeyMapper:
    @staticmethod
    def to_high_level(view: RpcQueryResponseAccessKeyView) -> AccountAccessKey:
        """
        Convert low-level RpcQueryResponseAccessKeyView to high-level AccountAccessKey.
        """

        block_hash = str(view.block_hash)
        block_height = view.block_height
        nonce = view.nonce

        perm = view.permission.root

        if isinstance(perm, AccessKeyPermissionViewFullAccess):
            permission: Union[str, dict] = "FullAccess"

        elif isinstance(perm, AccessKeyPermissionViewFunctionCall):
            payload = perm.FunctionCall
            permission = {
                "allowance": str(payload.allowance) if payload.allowance else None,
                "receiver_id": payload.receiver_id,
                "method_names": payload.method_names
            }

        elif isinstance(perm, AccessKeyPermissionViewGasKeyFunctionCall):
            payload = perm.GasKeyFunctionCall
            permission = {
                "allowance": str(payload.allowance) if payload.allowance else None,
                "balance": str(payload.balance),
                "num_nonces": payload.num_nonces,
                "receiver_id": payload.receiver_id,
                "method_names": payload.method_names
            }

        elif isinstance(perm, AccessKeyPermissionViewGasKeyFullAccess):
            payload = perm.GasKeyFullAccess
            permission = {
                "balance": str(payload.balance),
                "num_nonces": payload.num_nonces
            }

        else:
            raise ValueError(f"Unsupported AccessKeyPermissionView: {type(perm)}")

        return AccountAccessKey(
            block_hash=block_hash,
            block_height=block_height,
            nonce=nonce,
            permission=permission
        )