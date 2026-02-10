from near_jsonrpc_models import AccessKeyInfoView

from py_near.mapper.rpc_access_key_mapper import RpcAccessKeyMapper
from py_near.models import PublicKey


class RpcPublicKeyMapper:
    @staticmethod
    def to_high_level(view: AccessKeyInfoView) -> PublicKey:
        """
        Convert a low-level AccessKeyInfoView (RPC model) to high-level PublicKey.
        """
        return PublicKey(
            public_key=view.public_key.root,
            access_key=RpcAccessKeyMapper.to_high_level(view.access_key)
        )