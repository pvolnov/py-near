from enum import Enum
from typing import Optional, Dict, List

from pydantic import BaseModel


class DropPermissionEnum(str, Enum):
    CLAIM = "claim"
    CREATE_ACCOUNT_AND_CLAIM = "create_account_and_claim"


class DropKeyConfig(BaseModel):
    remaining_uses: int
    last_used: int
    allowance: int
    key_id: int
    pw_per_use: Optional[Dict[int, bytes]]
    pw_per_key: Optional[bytes]


class DropTimeConfig(BaseModel):
    start: Optional[int]
    end: Optional[int]
    throttle: Optional[int]
    interval: Optional[int]


class DropUsageConfig(BaseModel):
    permissions: Optional[DropPermissionEnum]
    refund_deposit: Optional[bool]
    auto_delete_drop: Optional[bool]
    auto_withdraw: Optional[bool]


class DropConfig(BaseModel):
    uses_per_key: Optional[int]
    time: Optional[DropTimeConfig]
    usage: Optional[DropUsageConfig]
    root_account_id: Optional[str]


class SimpleData(BaseModel):
    lazy_register: Optional[bool]


class JsonFTData(BaseModel):
    contract_id: str
    sender_id: str
    balance_per_use: int


class JsonNFTData(BaseModel):
    sender_id: str
    contract_id: str


class FCConfig(BaseModel):
    attached_gas: Optional[int]


class MethodData(BaseModel):
    receiver_id: str
    method_name: str
    args: str
    attached_deposit: int
    account_id_field: Optional[str]
    drop_id_field: Optional[str]
    key_id_field: Optional[str]


class FCData(BaseModel):
    methods: List[Optional[List[MethodData]]]
    config: Optional[FCConfig]


class JsonKeyInfo(BaseModel):
    drop_id: str
    pk: str
    cur_key_use: int
    remaining_uses: int
    last_used: int
    allowance: int
    key_id: int


class JsonPasswordForUse(BaseModel):
    pw: str
    key_use: int


class CreateDropModel(BaseModel):
    public_keys: Optional[List[str]]
    deposit_per_use: int
    drop_id: Optional[str]
    config: Optional[DropConfig]
    metadata: Optional[str]
    simple: Optional[SimpleData]
    ft: Optional[JsonFTData]
    nft: Optional[JsonNFTData]
    fc: Optional[FCData]
    passwords_per_use: Optional[List[Optional[List[JsonPasswordForUse]]]]
    passwords_per_key: Optional[List[Optional[str]]]
