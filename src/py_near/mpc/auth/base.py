from py_near.account import Account
from py_near.mpc.models import WalletAccessModel


class AuthContract:
    contract_id: str

    def __init__(self, near_account: Account = None):
        self.near_account = near_account

    async def grant_access(
        self,
        wallet_id: str,
        access: WalletAccessModel,
        near_account,
        wallet_auth_method=0,
    ):
        raise NotImplementedError("Grant access is not implemented")

    async def revoke_assess(
        self, wallet_id: str, near_account: Account, access_id: int
    ):
        raise NotImplementedError("Revoke access is not implemented")

    def generate_user_payload(self, msg_hash: bytes) -> str:
        raise NotImplementedError("Generate user payload is not implemented")
