import datetime
from hashlib import sha256
from typing import Optional

import base58
from nacl import signing
from pydantic import BaseModel

from py_near.account import Account
from py_near.mpc.auth.base import AuthContract


class Wallet2FA(BaseModel):
    wallet_id: str
    public_key: str
    delay_to_remove: int
    cancellation_at: int
    conditions: Optional[str] = None

    @classmethod
    def build(cls, data: dict, wallet_id):
        return cls(
            wallet_id=wallet_id,
            public_key=data["public_key"],
            cancellation_at=data["cancellation_at"],
            delay_to_remove=data["delay_to_remove"],
            conditions=data.get("conditions"),
        )


class AuthContract2FA(AuthContract):
    root_pk: signing.SigningKey
    contract_id: str = "2fa.auth.hot.tg"

    def __init__(self, root_pk: signing.SigningKey, near_account: Account = None):
        self.root_pk = root_pk
        self.near_account = near_account
        super().__init__()

    def generate_user_payload(self, msg_hash: bytes):
        auth_signature = base58.b58encode(self.root_pk.sign(msg_hash).signature).decode(
            "utf-8"
        )
        return auth_signature

    async def get_2fa_for_wallet(self, wallet_id: str) -> Optional[Wallet2FA]:
        if not self.near_account:
            raise ValueError("Near account is required")
        res = (
            await self.near_account.view_function(
                self.contract_id,
                "get_wallet_2fa",
                {
                    "wallet_id": wallet_id,
                },
            )
        ).result
        if res:
            return Wallet2FA.build(res, wallet_id)

    async def cancel_2fa(
        self, user_pk: signing.SigningKey, wallet_id: str, rule_id: int = 0
    ):
        if not self.near_account:
            raise ValueError("Near account is required")
        two_fa = await self.get_2fa_for_wallet(wallet_id)
        ts = int(datetime.datetime.utcnow().timestamp() * 10**9)

        if two_fa.cancellation_at == 0:
            msg_hash = sha256(f"CANCEL_2FA:{wallet_id}:{ts}".encode("utf-8")).digest()
            auth_signature = base58.b58encode(user_pk.sign(msg_hash).signature).decode(
                "utf-8"
            )
            return await self.near_account.function_call(
                self.contract_id,
                "cancel_2fa",
                {
                    "wallet_id": wallet_id,
                    "user_signature": auth_signature,
                    "timestamp": ts,
                },
                included=True,
            )
        else:
            if two_fa.cancellation_at < ts:
                raise ValueError(
                    f"2FA already cancelled at {datetime.datetime.fromtimestamp(two_fa.cancellation_at / 10**9)}"
                )
            return await self.near_account.function_call(
                self.contract_id,
                "complete_cancel_2fa",
                {
                    "wallet_id": wallet_id,
                    "rule_id": rule_id,
                },
                included=True,
            )
