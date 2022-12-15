from pydantic import BaseModel


class StakingData(BaseModel):
    apy_value: int
    last_accrual_ts: int
    accrued: int
