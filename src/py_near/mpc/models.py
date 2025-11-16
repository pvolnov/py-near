from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class CurveType(int, Enum):
    SECP256K1 = 0
    ED25519 = 1


_WALLET_REGISTER = "mpc.hot.tg"


class WalletAccessModel(BaseModel):
    account_id: str
    metadata: Optional[str] = None
    chain_id: int
    msg: Optional[str] = None

    def generate_user_payload(self):
        raise NotImplementedError()


class WalletModel(BaseModel):
    access_list: List[WalletAccessModel]
    key_gen: int = 0

    @classmethod
    def build(cls, data: dict):
        return cls(
            access_list=[WalletAccessModel(**x) for x in data["access_list"]],
            key_gen=data["key_gen"],
        )