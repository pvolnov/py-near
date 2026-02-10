from near_jsonrpc_models import AccessKeyInfoView, AccessKeyPermissionViewFullAccess, \
    AccessKeyPermissionViewFunctionCall, AccessKeyPermissionViewGasKeyFunctionCall, \
    AccessKeyPermissionViewGasKeyFullAccess, AccessKeyView

from py_near.models import AccessKey, PublicKeyPermissionType


class RpcAccessKeyMapper:
    @staticmethod
    def to_high_level(view: AccessKeyView) -> AccessKey:
        perm = view.permission.root

        if isinstance(perm, AccessKeyPermissionViewFullAccess):
            return AccessKey(
                nonce=view.nonce,
                permission_type=PublicKeyPermissionType.FULL_ACCESS
            )

        elif isinstance(perm, AccessKeyPermissionViewFunctionCall):
            payload = perm.FunctionCall
            return AccessKey(
                nonce=view.nonce,
                permission_type=PublicKeyPermissionType.FUNCTION_CALL,
                allowance=str(payload.allowance) if payload.allowance else None,
                receiver_id=payload.receiver_id,
                method_names=payload.method_names
            )

        elif isinstance(perm, AccessKeyPermissionViewGasKeyFunctionCall):
            payload = perm.GasKeyFunctionCall
            return AccessKey(
                nonce=view.nonce,
                permission_type=PublicKeyPermissionType.GAS_KEY_FUNCTION_CALL,
                allowance=str(payload.allowance) if payload.allowance else None,
                receiver_id=payload.receiver_id,
                method_names=payload.method_names
            )

        elif isinstance(perm, AccessKeyPermissionViewGasKeyFullAccess):
            return AccessKey(
                nonce=view.nonce,
                permission_type=PublicKeyPermissionType.GAS_KEY_FULL_ACCESS
            )

        else:
            raise ValueError(f"Unsupported permission type: {type(perm)}")
