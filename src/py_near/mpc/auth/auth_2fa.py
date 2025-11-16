from typing import Optional

from pydantic import BaseModel


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


